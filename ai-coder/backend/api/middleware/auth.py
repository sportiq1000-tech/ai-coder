"""
Authentication middleware for API key validation
SECURITY FIX - Phase 1: API Key Authentication System
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from typing import Optional, Dict
import hashlib
import os
from datetime import datetime
from utils.logger import logger

# SECURITY FIX: API Key header extraction
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyManager:
    """Manages API key validation and metadata"""
    
    def __init__(self):
        self.valid_keys: Dict[str, dict] = {}
        self.load_api_keys()
        logger.info(f"APIKeyManager initialized with {len(self.valid_keys)} keys")
    
    def load_api_keys(self):
        """
        Load API keys from environment variable
        Format: API_KEYS=key1:user1:limit1,key2:user2:limit2
        """
        api_keys_config = os.getenv("API_KEYS", "")
        
        if api_keys_config:
            for key_config in api_keys_config.split(","):
                parts = key_config.strip().split(":")
                if len(parts) >= 2:
                    key = parts[0].strip()
                    # Hash the key for secure storage
                    key_hash = hashlib.sha256(key.encode()).hexdigest()
                    
                    self.valid_keys[key_hash] = {
                        "user": parts[1].strip(),
                        "rate_limit": int(parts[2]) if len(parts) > 2 else 60,
                        "created": datetime.now().isoformat(),
                        "request_count": 0
                    }
                    logger.info(f"Loaded API key for user: {parts[1].strip()}")
        
        # DEVELOPMENT MODE: Add default key if none configured
        if not self.valid_keys and os.getenv("APP_ENV", "development") == "development":
            dev_key = "dev_key_change_in_production"
            key_hash = hashlib.sha256(dev_key.encode()).hexdigest()
            self.valid_keys[key_hash] = {
                "user": "developer",
                "rate_limit": 100,
                "created": datetime.now().isoformat(),
                "request_count": 0
            }
            logger.warning(f"⚠️  DEVELOPMENT MODE: Using default API key: {dev_key}")
            logger.warning("⚠️  Change this in production via API_KEYS environment variable!")
    
    def validate_key(self, api_key: str) -> Optional[dict]:
        """
        Validate API key and return key info if valid
        """
        if not api_key:
            return None
        
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Check if key exists
        key_info = self.valid_keys.get(key_hash)
        
        if key_info:
            # Increment request count
            key_info["request_count"] += 1
            logger.debug(f"Valid API key used by: {key_info['user']}")
        
        return key_info
    
    def get_user_rate_limit(self, api_key: str) -> int:
        """Get rate limit for specific API key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_info = self.valid_keys.get(key_hash)
        return key_info.get("rate_limit", 60) if key_info else 60


# SECURITY FIX: Global API key manager instance
api_key_manager = APIKeyManager()


# SECURITY FIX: Authentication dependency for FastAPI routes
async def verify_api_key(api_key: str = Security(api_key_header)) -> dict:
    """
    Dependency to verify API key in requests
    Use this in route dependencies: Depends(verify_api_key)
    """
    if not api_key:
        logger.warning("Request without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "API key required",
                "message": "Please provide API key via X-API-Key header"
            }
        )
    
    key_info = api_key_manager.validate_key(api_key)
    
    if not key_info:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Invalid API key",
                "message": "The provided API key is not valid"
            }
        )
    
    return key_info


# SECURITY FIX: Optional authentication (for endpoints that can work with or without auth)
async def optional_verify_api_key(api_key: str = Security(api_key_header)) -> Optional[dict]:
    """
    Optional authentication - returns key info if present, None if not
    Doesn't raise exception if no key provided
    """
    if not api_key:
        return None
    
    return api_key_manager.validate_key(api_key)
# SECURITY FIX - Phase 2C: Admin role verification
async def verify_admin_api_key(api_key: str = Security(api_key_header)) -> dict:
    """
    Verify API key and check if user has admin role
    Raises 403 if user is not admin
    """
    # First verify the key is valid
    key_info = api_key_manager.validate_key(api_key)
    
    if not key_info:
        logger.warning(f"Invalid API key attempt on admin endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Invalid API key",
                "message": "The provided API key is not valid"
            }
        )
    
    # Check if user has admin role
    if key_info.get("user") != "admin":
        logger.warning(f"Non-admin user attempted admin access: {key_info.get('user')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Admin access required",
                "message": "This endpoint requires admin privileges"
            }
        )
    
    logger.info(f"Admin access granted to: {key_info.get('user')}")
    return key_info