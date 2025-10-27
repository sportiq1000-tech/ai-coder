"""
Enhanced caching layer with Redis (Upstash) and in-memory fallback
"""
from typing import Optional, Any
import json
import hashlib
from functools import wraps
import asyncio
from utils.logger import logger
from utils.config import settings

# Try to import Redis, fallback to dict cache if unavailable
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis library not available, using in-memory cache")


class RedisCache:
    """Async Redis cache with automatic fallback to in-memory"""
    
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.memory_cache: dict = {}
        self.enabled = settings.CACHE_ENABLED
        self.use_redis = False
        self._connection_tested = False
        
        # Initialize Redis if available and configured
        if REDIS_AVAILABLE and settings.REDIS_URL and settings.REDIS_URL.strip():
            asyncio.create_task(self._init_redis())
        else:
            logger.info("Using in-memory cache (Redis not configured)")
    
    async def _init_redis(self):
        """Initialize Redis connection asynchronously"""
        try:
            # Support both Redis URL formats
            if settings.REDIS_URL.startswith('redis://'):
                # Standard Redis URL
                self.redis_client = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=3,
                    socket_timeout=3,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            elif settings.REDIS_URL.startswith('https://'):
                # Upstash REST API (use different client)
                # For now, fallback to memory for REST API
                logger.warning("Upstash REST API detected, using memory cache. Consider using Redis URL format.")
                return
            else:
                logger.warning(f"Invalid Redis URL format, using memory cache")
                return
            
            # Test connection
            await self._test_redis_connection()
            
        except Exception as e:
            logger.error(f"Redis initialization failed: {e}, using memory cache")
            self.redis_client = None
            self.use_redis = False
    
    async def _test_redis_connection(self):
        """Test Redis connection and set flag"""
        if not self.redis_client or self._connection_tested:
            return
        
        try:
            await self.redis_client.ping()
            self.use_redis = True
            self._connection_tested = True
            logger.info("Redis connection successful - using Redis cache")
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}, falling back to memory cache")
            self.use_redis = False
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.enabled:
            return None
        
        try:
            if self.use_redis and self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    logger.debug(f"Redis cache hit: {key[:20]}...")
                    return json.loads(value)
                return None
            else:
                value = self.memory_cache.get(key)
                if value:
                    logger.debug(f"Memory cache hit: {key[:20]}...")
                return value
                
        except Exception as e:
            logger.error(f"Cache get error: {e}, trying fallback")
            # Fallback to memory cache on Redis error
            return self.memory_cache.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds
            
        Returns:
            Success status
        """
        if not self.enabled:
            return False
        
        try:
            serialized = json.dumps(value)
            
            if self.use_redis and self.redis_client:
                try:
                    await self.redis_client.setex(key, ttl, serialized)
                    logger.debug(f"Redis cache set: {key[:20]}... (TTL: {ttl}s)")
                    return True
                except Exception as redis_error:
                    logger.warning(f"Redis set failed: {redis_error}, using memory cache")
                    self.use_redis = False
                    # Fall through to memory cache
            
            # Memory cache fallback
            self.memory_cache[key] = value
            logger.debug(f"Memory cache set: {key[:20]}... (TTL: {ttl}s)")
            # Schedule expiration
            asyncio.create_task(self._expire_key(key, ttl))
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key
            
        Returns:
            Success status
        """
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.delete(key)
                logger.debug(f"Redis cache delete: {key[:20]}...")
            
            # Also remove from memory cache
            self.memory_cache.pop(key, None)
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            # Still try memory cache
            self.memory_cache.pop(key, None)
            return False
    
    async def clear(self) -> bool:
        """
        Clear all cache
        
        Returns:
            Success status
        """
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.flushdb()
                logger.info("Redis cache cleared")
            
            self.memory_cache.clear()
            logger.info("Memory cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self.memory_cache.clear()  # Still clear memory
            return False
    
    async def get_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache stats
        """
        stats = {
            "type": "redis" if self.use_redis else "memory",
            "enabled": self.enabled,
            "memory_cache_size": len(self.memory_cache),
            "redis_connected": self.use_redis
        }
        
        if self.use_redis and self.redis_client:
            try:
                info = await self.redis_client.info()
                stats["redis_info"] = {
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands": info.get("total_commands_processed", 0)
                }
            except Exception as e:
                logger.error(f"Failed to get Redis stats: {e}")
        
        return stats
    
    async def _expire_key(self, key: str, ttl: int):
        """Expire key after TTL (for memory cache)"""
        await asyncio.sleep(ttl)
        self.memory_cache.pop(key, None)
        logger.debug(f"Memory cache expired: {key[:20]}...")
    
    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """
        Generate cache key from arguments
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            MD5 hash string
        """
        key_data = {
            'args': [str(arg) for arg in args],
            'kwargs': {k: str(v) for k, v in sorted(kwargs.items())}
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis: {e}")


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """
    Get singleton cache instance
    
    Returns:
        RedisCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator to cache function results
    
    Usage:
        @cached(ttl=1800, key_prefix="review")
        async def my_function(param1, param2):
            ...
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache key
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            cache_key = f"{key_prefix}:{RedisCache.generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit: {func.__name__}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(cache_key, result, ttl)
            logger.info(f"Cache miss: {func.__name__} - stored in cache")
            
            return result
        return wrapper
    return decorator
# Export alias for backward compatibility
Cache = RedisCache