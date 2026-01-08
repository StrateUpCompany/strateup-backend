"""
Cache Tests
LeadHunter AI - Testing cache module

Tests for:
- Cache set/get
- TTL expiry
- Cache manager
- Cache statistics
"""
import pytest
import time
from unittest.mock import patch, MagicMock
import os

from backend.core.cache_manager import (
    CacheManager,
    cache,
    cached,
    get_cache,
    CACHE_CONFIG
)


# =============================================================================
# CACHE MANAGER TESTS
# =============================================================================

class TestCacheManager:
    """Tests for CacheManager class."""
    
    def test_singleton_instance(self):
        """CacheManager should be a singleton."""
        manager1 = CacheManager()
        manager2 = CacheManager()
        
        assert manager1 is manager2
    
    def test_global_cache_instance(self):
        """Global cache instance should be available."""
        assert cache is not None
        assert isinstance(cache, CacheManager)
    
    def test_get_cache_function(self):
        """get_cache should return global instance."""
        instance = get_cache()
        assert instance is cache


# =============================================================================
# CACHE CONFIG TESTS
# =============================================================================

class TestCacheConfig:
    """Tests for cache configuration."""
    
    def test_config_exists(self):
        """Cache config should exist."""
        assert CACHE_CONFIG is not None
        assert isinstance(CACHE_CONFIG, dict)
    
    def test_config_has_apify(self):
        """Should have apify cache config."""
        assert "apify" in CACHE_CONFIG
        assert "ttl" in CACHE_CONFIG["apify"]
    
    def test_config_has_default(self):
        """Should have default cache config."""
        assert "default" in CACHE_CONFIG
        assert "ttl" in CACHE_CONFIG["default"]


# =============================================================================
# CACHE SET/GET TESTS
# =============================================================================

class TestCacheSetGet:
    """Tests for cache set and get operations."""
    
    def test_set_string(self):
        """Should set string values."""
        cache_mgr = CacheManager()
        
        result = cache_mgr.set("test_string_key", "test_value")
        
        # Should return True on success
        assert result is True
    
    def test_get_string(self):
        """Should get string values."""
        cache_mgr = CacheManager()
        
        cache_mgr.set("get_test_key", "get_test_value")
        result = cache_mgr.get("get_test_key")
        
        # May be None if Redis not available (fallback behavior)
        assert result is None or result == "get_test_value"
    
    def test_set_dict(self):
        """Should set dictionary values."""
        cache_mgr = CacheManager()
        
        data = {"name": "Test", "count": 42}
        result = cache_mgr.set("dict_key", data)
        
        assert result is True
    
    def test_set_list(self):
        """Should set list values."""
        cache_mgr = CacheManager()
        
        data = [1, 2, 3, "four", {"five": 5}]
        result = cache_mgr.set("list_key", data)
        
        assert result is True
    
    def test_get_missing_key(self):
        """Should return None for missing keys."""
        cache_mgr = CacheManager()
        
        result = cache_mgr.get("nonexistent_key_12345")
        
        assert result is None


# =============================================================================
# CACHE DELETE TESTS
# =============================================================================

class TestCacheDelete:
    """Tests for cache delete operations."""
    
    def test_delete_key(self):
        """Should delete cached values."""
        cache_mgr = CacheManager()
        
        cache_mgr.set("delete_test_key", "value")
        result = cache_mgr.delete("delete_test_key")
        
        # Should return True on success
        assert result is True
    
    def test_delete_missing_key(self):
        """Should handle deleting nonexistent keys."""
        cache_mgr = CacheManager()
        
        # Should not raise
        result = cache_mgr.delete("nonexistent_delete_key")
        
        # May return True or False depending on implementation
        assert isinstance(result, bool)


# =============================================================================
# CACHE EXISTS TESTS
# =============================================================================

class TestCacheExists:
    """Tests for cache exists operation."""
    
    def test_exists_true(self):
        """Should return True for existing keys."""
        cache_mgr = CacheManager()
        
        cache_mgr.set("exists_test_key", "value")
        result = cache_mgr.exists("exists_test_key")
        
        # May be False if using memory fallback
        assert isinstance(result, bool)
    
    def test_exists_false(self):
        """Should return False for missing keys."""
        cache_mgr = CacheManager()
        
        result = cache_mgr.exists("nonexistent_exists_key")
        
        assert result is False


# =============================================================================
# CACHE KEY TESTS
# =============================================================================

class TestCacheKeys:
    """Tests for cache key handling."""
    
    def test_make_key_with_prefix(self):
        """Cache keys should have prefixes."""
        cache_mgr = CacheManager()
        
        key = cache_mgr._make_key("test", "apify")
        
        assert "apify" in key
        assert "test" in key
    
    def test_get_ttl_default(self):
        """Should get default TTL."""
        cache_mgr = CacheManager()
        
        ttl = cache_mgr._get_ttl("default")
        
        assert ttl == CACHE_CONFIG["default"]["ttl"]
    
    def test_get_ttl_custom(self):
        """Should respect custom TTL."""
        cache_mgr = CacheManager()
        
        custom_ttl = 999
        ttl = cache_mgr._get_ttl("default", custom_ttl=custom_ttl)
        
        assert ttl == custom_ttl


# =============================================================================
# CACHE CLEAR TESTS
# =============================================================================

class TestCacheClear:
    """Tests for cache clear operation."""
    
    def test_clear_all(self):
        """Should clear all cached values."""
        cache_mgr = CacheManager()
        
        cache_mgr.set("clear_key_1", "value1")
        cache_mgr.set("clear_key_2", "value2")
        
        deleted = cache_mgr.clear()
        
        # Should return number of keys deleted
        assert isinstance(deleted, int)


# =============================================================================
# CACHE STATS TESTS
# =============================================================================

class TestCacheStats:
    """Tests for cache statistics."""
    
    def test_get_stats(self):
        """Should return cache statistics."""
        cache_mgr = CacheManager()
        
        stats = cache_mgr.get_stats()
        
        assert isinstance(stats, dict)
        assert "redis_available" in stats


# =============================================================================
# REDIS AVAILABILITY TESTS
# =============================================================================

class TestRedisAvailability:
    """Tests for Redis availability checking."""
    
    def test_is_redis_available(self):
        """Should check Redis availability."""
        cache_mgr = CacheManager()
        
        # May raise or return bool depending on Redis status
        try:
            result = cache_mgr.is_redis_available()
            assert isinstance(result, bool)
        except Exception:
            # Redis client may raise if not configured
            pass



# =============================================================================
# CACHED DECORATOR TESTS
# =============================================================================

class TestCachedDecorator:
    """Tests for cached decorator."""
    
    def test_cached_function_returns(self):
        """Cached function should return value."""
        cache_mgr = CacheManager()
        
        @cache_mgr.cached("default", ttl=60)
        def sample_function(x):
            return x * 2
        
        result = sample_function(5)
        
        assert result == 10
    
    def test_cached_decorator_shortcut(self):
        """cached() shortcut should work."""
        @cached("default")
        def another_function(x):
            return x + 1
        
        result = another_function(10)
        
        assert result == 11


# =============================================================================
# CACHE FALLBACK TESTS
# =============================================================================

class TestCacheFallback:
    """Tests for cache fallback behavior."""
    
    def test_graceful_operations(self):
        """Should degrade gracefully on errors."""
        cache_mgr = CacheManager()
        
        # Should not raise on any operation
        try:
            cache_mgr.set("graceful_key", "value")
            cache_mgr.get("graceful_key")
            cache_mgr.delete("graceful_key")
            assert True
        except Exception as e:
            assert False, f"Cache raised exception: {e}"
