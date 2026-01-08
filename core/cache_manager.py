"""
Cache Manager - Redis-based caching system

Features:
- Redis caching with fallback to in-memory
- Decorator for easy function caching
- Configurable TTL per cache type
- Automatic key generation from function args
"""
import os
import json
import hashlib
import functools
from typing import Any, Optional, Callable, Union
from datetime import timedelta
from backend.utils.logger import logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory cache fallback.")


# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

CACHE_CONFIG = {
    "apify": {"ttl": 86400, "prefix": "apify"},      # 24 hours
    "clone": {"ttl": 604800, "prefix": "clone"},      # 7 days
    "ai": {"ttl": 3600, "prefix": "ai"},              # 1 hour
    "default": {"ttl": 3600, "prefix": "cache"},      # 1 hour
}


# =============================================================================
# CACHE MANAGER
# =============================================================================

class CacheManager:
    """
    Redis-based cache manager with in-memory fallback.
    
    Usage:
        cache = CacheManager()
        
        # Direct usage
        cache.set("key", "value", ttl=3600)
        value = cache.get("key")
        
        # With decorator
        @cache.cached(cache_type="apify")
        def expensive_function(arg):
            return result
    """
    
    _instance = None
    _memory_cache: dict = {}
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._memory_cache = {}
        self._redis: Optional[redis.Redis] = None
        
        if REDIS_AVAILABLE:
            self._connect_redis()
    
    def _connect_redis(self):
        """Connect to Redis server"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        try:
            self._redis = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
                max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", 10)),
                health_check_interval=30
            )
            # Test connection
            self._redis.ping()
            logger.info(f"Connected to Redis: {redis_url}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
            self._redis = None
    
    @property
    def is_redis_available(self) -> bool:
        """Check if Redis is connected"""
        if self._redis is None:
            return False
        try:
            self._redis.ping()
            return True
        except:
            return False
    
    def _make_key(self, key: str, cache_type: str = "default") -> str:
        """Generate prefixed cache key"""
        prefix = CACHE_CONFIG.get(cache_type, CACHE_CONFIG["default"])["prefix"]
        return f"{prefix}:{key}"
    
    def _get_ttl(self, cache_type: str = "default", custom_ttl: Optional[int] = None) -> int:
        """Get TTL for cache type"""
        if custom_ttl is not None:
            return custom_ttl
        return CACHE_CONFIG.get(cache_type, CACHE_CONFIG["default"])["ttl"]
    
    # =========================================================================
    # CORE METHODS
    # =========================================================================
    
    def get(self, key: str, cache_type: str = "default") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            cache_type: Type of cache (apify, clone, ai, default)
        
        Returns:
            Cached value or None if not found
        """
        full_key = self._make_key(key, cache_type)
        
        # Try Redis first
        if self.is_redis_available:
            try:
                value = self._redis.get(full_key)
                if value:
                    logger.debug(f"Cache HIT (redis): {full_key}")
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Fallback to memory
        if full_key in self._memory_cache:
            logger.debug(f"Cache HIT (memory): {full_key}")
            return self._memory_cache[full_key]
        
        logger.debug(f"Cache MISS: {full_key}")
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        cache_type: str = "default",
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            cache_type: Type of cache
            ttl: Optional custom TTL in seconds
        
        Returns:
            True if successful
        """
        full_key = self._make_key(key, cache_type)
        ttl_seconds = self._get_ttl(cache_type, ttl)
        
        try:
            serialized = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error(f"Cannot serialize value for caching: {e}")
            return False
        
        # Try Redis first
        if self.is_redis_available:
            try:
                self._redis.setex(full_key, ttl_seconds, serialized)
                logger.debug(f"Cache SET (redis): {full_key}, ttl={ttl_seconds}s")
                return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        # Fallback to memory
        self._memory_cache[full_key] = value
        logger.debug(f"Cache SET (memory): {full_key}")
        return True
    
    def delete(self, key: str, cache_type: str = "default") -> bool:
        """Delete key from cache"""
        full_key = self._make_key(key, cache_type)
        
        if self.is_redis_available:
            try:
                self._redis.delete(full_key)
            except:
                pass
        
        self._memory_cache.pop(full_key, None)
        return True
    
    def exists(self, key: str, cache_type: str = "default") -> bool:
        """Check if key exists in cache"""
        full_key = self._make_key(key, cache_type)
        
        if self.is_redis_available:
            try:
                return self._redis.exists(full_key) > 0
            except:
                pass
        
        return full_key in self._memory_cache
    
    def clear(self, cache_type: Optional[str] = None) -> int:
        """
        Clear cache.
        
        Args:
            cache_type: If specified, only clear keys of this type
        
        Returns:
            Number of keys deleted
        """
        count = 0
        
        if cache_type:
            prefix = CACHE_CONFIG.get(cache_type, CACHE_CONFIG["default"])["prefix"]
            pattern = f"{prefix}:*"
        else:
            pattern = "*"
        
        if self.is_redis_available:
            try:
                keys = self._redis.keys(pattern)
                if keys:
                    count = self._redis.delete(*keys)
            except:
                pass
        
        # Clear memory cache
        if cache_type:
            prefix = CACHE_CONFIG.get(cache_type, CACHE_CONFIG["default"])["prefix"]
            to_delete = [k for k in self._memory_cache if k.startswith(f"{prefix}:")]
            for k in to_delete:
                del self._memory_cache[k]
            count += len(to_delete)
        else:
            count += len(self._memory_cache)
            self._memory_cache.clear()
        
        return count
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        stats = {
            "redis_available": self.is_redis_available,
            "memory_keys": len(self._memory_cache),
        }
        
        if self.is_redis_available:
            try:
                info = self._redis.info("stats")
                stats["redis_hits"] = info.get("keyspace_hits", 0)
                stats["redis_misses"] = info.get("keyspace_misses", 0)
                stats["redis_keys"] = self._redis.dbsize()
            except:
                pass
        
        return stats
    
    # =========================================================================
    # DECORATOR
    # =========================================================================
    
    def cached(
        self,
        cache_type: str = "default",
        ttl: Optional[int] = None,
        key_builder: Optional[Callable] = None
    ):
        """
        Decorator to cache function results.
        
        Args:
            cache_type: Type of cache
            ttl: Optional custom TTL
            key_builder: Optional function to build cache key from args
        
        Usage:
            @cache.cached(cache_type="apify")
            def search_leads(query, location):
                return expensive_api_call()
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Default: hash of function name + args
                    key_parts = [func.__name__] + [str(a) for a in args]
                    key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
                    key_str = ":".join(key_parts)
                    cache_key = hashlib.md5(key_str.encode()).hexdigest()
                
                # Check cache
                cached_value = self.get(cache_key, cache_type)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Store in cache
                if result is not None:
                    self.set(cache_key, result, cache_type, ttl)
                
                return result
            
            # Add method to bypass cache
            def bypass(*args, **kwargs):
                return func(*args, **kwargs)
            wrapper.bypass = bypass
            
            return wrapper
        return decorator
    
    async def cached_async(
        self,
        cache_type: str = "default",
        ttl: Optional[int] = None
    ):
        """Async version of cached decorator"""
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                key_parts = [func.__name__] + [str(a) for a in args]
                key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
                key_str = ":".join(key_parts)
                cache_key = hashlib.md5(key_str.encode()).hexdigest()
                
                cached_value = self.get(cache_key, cache_type)
                if cached_value is not None:
                    return cached_value
                
                result = await func(*args, **kwargs)
                
                if result is not None:
                    self.set(cache_key, result, cache_type, ttl)
                
                return result
            return wrapper
        return decorator


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

cache = CacheManager()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def cached(cache_type: str = "default", ttl: Optional[int] = None):
    """Convenience decorator using global cache instance"""
    return cache.cached(cache_type=cache_type, ttl=ttl)


def get_cache() -> CacheManager:
    """Get the global cache instance"""
    return cache
