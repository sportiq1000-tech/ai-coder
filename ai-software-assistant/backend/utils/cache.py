"""
Caching layer with Redis fallback to in-memory
"""
from typing import Optional, Any
import json
import hashlib
from datetime import timedelta
from functools import wraps
import asyncio
from utils.logger import logger
from utils.config import settings

# Try to import Redis, fallback to dict cache if unavailable
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")


class Cache:
    """Async cache with Redis backend and in-memory fallback"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: dict = {}
        self.enabled = True
        self.use_redis = False
        
        if REDIS_AVAILABLE and settings.REDIS_URL:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,  # Quick timeout
                    retry_on_timeout=False
                )
                # Test connection
                asyncio.create_task(self._test_redis_connection())
            except Exception as e:
                logger.warning(f"Redis initialization failed: {e}, using memory cache")
                self.redis_client = None
        else:
            logger.info("Using in-memory cache (Redis not configured)")
    
    async def _test_redis_connection(self):
        """Test Redis connection and set flag"""
        try:
            await self.redis_client.ping()
            self.use_redis = True
            logger.info("Redis connection successful")
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}, falling back to memory cache")
            self.use_redis = False
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None
        
        try:
            if self.use_redis and self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            # Fallback to memory cache on error
            return self.memory_cache.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """Set value in cache with TTL in seconds"""
        if not self.enabled:
            return False
        
        try:
            serialized = json.dumps(value)
            
            if self.use_redis and self.redis_client:
                try:
                    await self.redis_client.setex(
                        key,
                        timedelta(seconds=ttl),
                        serialized
                    )
                except Exception as redis_error:
                    logger.warning(f"Redis set failed: {redis_error}, using memory cache")
                    self.use_redis = False
                    # Fall through to memory cache
                    self.memory_cache[key] = value
                    asyncio.create_task(self._expire_key(key, ttl))
            else:
                self.memory_cache[key] = value
                # Simple TTL for memory cache (async cleanup)
                asyncio.create_task(self._expire_key(key, ttl))
            
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.delete(key)
            else:
                self.memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            self.memory_cache.pop(key, None)  # Fallback
            return False
    
    async def clear(self) -> bool:
        """Clear all cache"""
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self.memory_cache.clear()  # Fallback
            return False
    
    async def _expire_key(self, key: str, ttl: int):
        """Expire key after TTL (for memory cache)"""
        await asyncio.sleep(ttl)
        self.memory_cache.pop(key, None)
    
    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            'args': args,
            'kwargs': kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()


# Global cache instance
_cache_instance: Optional[Cache] = None


def get_cache() -> Cache:
    """Get singleton cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = Cache()
    return _cache_instance


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator to cache function results
    
    Usage:
        @cached(ttl=1800, key_prefix="review")
        async def my_function(param1, param2):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            cache_key = f"{key_prefix}:{Cache.generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit: {func.__name__}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(cache_key, result, ttl)
            logger.info(f"Cache miss: {func.__name__}")
            
            return result
        return wrapper
    return decorator