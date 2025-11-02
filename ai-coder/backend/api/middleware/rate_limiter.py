"""
Rate limiting middleware
SECURITY FIX - Phase 2: Enhanced rate limiting with per-API-key limits
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict, deque
from datetime import datetime, timedelta
import time
import hashlib
from utils.config import settings
from utils.logger import logger


class EnhancedRateLimiter:
    """
    Multi-tier rate limiter with per-API-key, per-IP, and global limits
    """
    
    def __init__(self):
              # Different buckets for different limits
        self.buckets = {
            'ip': defaultdict(lambda: deque()),
            'api_key': defaultdict(lambda: deque()),
            'global': defaultdict(lambda: deque())  # ← FIXED: Now a defaultdict
        }
        
        # Configurable limits
        self.limits = {
            'ip': {'requests': 60, 'window': 60},  # 60 req/min per IP
            'api_key': {'requests': 100, 'window': 60},  # 100 req/min per key
            'global': {'requests': 1000, 'window': 60}  # 1000 req/min total
        }
        
        # Track violations
        self.violations = defaultdict(int)
        self.blocked_until = {}
        
        logger.info("Enhanced rate limiter initialized")
    
    def check_rate_limit(
        self, 
        identifier: str, 
        identifier_type: str = 'ip',
        custom_limit: int = None
    ) -> tuple[bool, str]:
        """
        Check if request should be allowed
        Returns (is_allowed, error_message_or_empty)
        """
        now = datetime.now()
        
        # Check if temporarily blocked
        if identifier in self.blocked_until:
            if now < self.blocked_until[identifier]:
                remaining = (self.blocked_until[identifier] - now).seconds
                return False, f"Blocked for {remaining} seconds due to violations"
            else:
                del self.blocked_until[identifier]
                self.violations[identifier] = 0
        
        # Get the appropriate bucket
        bucket = self.buckets[identifier_type][identifier]
        limit_config = self.limits[identifier_type]
        
        # Use custom limit if provided (from API key config)
        max_requests = custom_limit or limit_config['requests']
        window = limit_config['window']
        
        # Remove old entries outside the window
        cutoff = now - timedelta(seconds=window)
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        
        # Check if limit exceeded
        if len(bucket) >= max_requests:
            # Track violation
            self.violations[identifier] += 1
            
            # Block if too many violations
            if self.violations[identifier] >= 3:
                self.blocked_until[identifier] = now + timedelta(minutes=5)
                logger.warning(f"Blocking {identifier} for 5 minutes (violations: {self.violations[identifier]})")
                return False, "Too many rate limit violations. Blocked for 5 minutes"
            
            return False, f"Rate limit exceeded: {max_requests} requests per {window} seconds"
        
        # Add current request
        bucket.append(now)
        
        # Also check global bucket
        global_bucket = self.buckets['global']['all']
        global_cutoff = now - timedelta(seconds=self.limits['global']['window'])
        while global_bucket and global_bucket[0] < global_cutoff:
            global_bucket.popleft()
        
        if len(global_bucket) >= self.limits['global']['requests']:
            return False, "Global rate limit exceeded. Please try again later"
        
        global_bucket.append(now)
        
        return True, ""
    
    def get_remaining_requests(self, identifier: str, identifier_type: str = 'ip') -> int:
        """Get remaining requests in current window"""
        now = datetime.now()
        bucket = self.buckets[identifier_type][identifier]
        limit_config = self.limits[identifier_type]
        
        cutoff = now - timedelta(seconds=limit_config['window'])
        active_requests = sum(1 for req_time in bucket if req_time > cutoff)
        
        return limit_config['requests'] - active_requests


# SECURITY FIX - Phase 2: Global rate limiter instance
rate_limiter = EnhancedRateLimiter()


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with API key awareness"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        logger.info(f"RateLimiter middleware initialized: {self.rpm} RPM default")
    
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Skip rate limiting for health and docs
        if request.url.path in ["/", "/api/health", "/api/ping", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host
        
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        
        if api_key:
            # Use API key for rate limiting (more generous)
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            allowed, message = rate_limiter.check_rate_limit(
                key_hash, 
                'api_key'
            )
            identifier_type = "API key"
            remaining = rate_limiter.get_remaining_requests(key_hash, 'api_key')
        else:
            # Use IP for rate limiting (stricter)
            allowed, message = rate_limiter.check_rate_limit(
                client_ip, 
                'ip'
            )
            identifier_type = "IP"
            remaining = rate_limiter.get_remaining_requests(client_ip, 'ip')
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {identifier_type}: {message}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": message,
                    "retry_after": 60
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(100 if api_key else 60)
        
        return response