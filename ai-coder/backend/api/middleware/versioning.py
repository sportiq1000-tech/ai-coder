"""
API Versioning Middleware
Handles version routing and backward compatibility
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from utils.logger import logger
from datetime import datetime

class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    Handles API versioning and backward compatibility
    - /api/v1/* - Current version (recommended)
    - /api/* - Legacy (redirects to v1, deprecated)
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Track if this is a legacy endpoint call
        is_legacy = False
        
        # Handle legacy /api/ routes (not /api/v1/)
        if path.startswith("/api/") and not path.startswith("/api/v1/"):
            # Internal path rewrite for routing
            original_path = path
            new_path = path.replace("/api/", "/api/v1/", 1)
            request.scope["path"] = new_path
            is_legacy = True
            
            # Log deprecation warning (not on health checks to reduce noise)
            if not path.endswith("/health"):
                logger.warning(
                    f"DEPRECATED API call: {original_path} → "
                    f"Please use /api/v1/ instead. "
                    f"Client: {request.client.host if request.client else 'unknown'}"
                )
        
        # Process request
        response = await call_next(request)
        
        # Add version headers to all API responses
        if path.startswith("/api/"):
            response.headers["X-API-Version"] = "1.0"
            if is_legacy:
                response.headers["X-API-Deprecated"] = "true"
                response.headers["X-API-Migration"] = "Use /api/v1/ prefix"
        
        return response