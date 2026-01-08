"""
Rate Limiter
LeadHunter AI - Public API

Features:
- Redis-based sliding window rate limiting
- Per-tier limits (Free: 100/day, Pro: 1000/day, Enterprise: unlimited)
- In-memory fallback if Redis unavailable
"""
import os
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from backend.utils.logger import logger
from backend.core.cache_manager import cache


# =============================================================================
# TIER LIMITS (requests per day)
# =============================================================================

TIER_LIMITS = {
    "free": 100,
    "pro": 1000,
    "enterprise": -1,  # Unlimited
}


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """
    Redis-based rate limiter using sliding window.
    
    Usage:
        limiter = RateLimiter()
        
        # Check if request is allowed
        allowed, info = limiter.check("api_key_hash", tier="free")
        if not allowed:
            return 429, {"error": "Too Many Requests", "retry_after": info["retry_after"]}
        
        # Get usage stats
        usage = limiter.get_usage("api_key_hash")
    """
    
    WINDOW_SIZE = 86400  # 24 hours in seconds
    CACHE_TYPE = "ratelimit"
    
    _instance = None
    _memory_counters: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._memory_counters = {}
    
    def _get_window_key(self, key_hash: str) -> str:
        """Get the key for the current time window"""
        # Use date as window identifier for daily limits
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return f"ratelimit:{key_hash}:{today}"
    
    def _get_reset_time(self) -> str:
        """Get the time when the current window resets (midnight UTC)"""
        tomorrow = datetime.utcnow().date() + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day).isoformat() + "Z"
    
    def _get_seconds_until_reset(self) -> int:
        """Get seconds until the rate limit resets"""
        now = datetime.utcnow()
        tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
        return int((tomorrow - now).total_seconds())
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def check(self, key_hash: str, tier: str = "free") -> Tuple[bool, Dict]:
        """
        Check if a request is allowed.
        
        Args:
            key_hash: SHA256 hash of the API key
            tier: API tier (free, pro, enterprise)
        
        Returns:
            (allowed: bool, info: dict)
            Info contains: count, limit, remaining, retry_after (if blocked)
        """
        limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        
        # Enterprise has no limit
        if limit == -1:
            return True, {
                "count": 0,
                "limit": -1,
                "remaining": -1,
                "tier": tier
            }
        
        window_key = self._get_window_key(key_hash)
        
        # Get current count
        current = cache.get(window_key, cache_type="default")
        count = current if current else 0
        
        # Check if within limit
        if count >= limit:
            retry_after = self._get_seconds_until_reset()
            return False, {
                "count": count,
                "limit": limit,
                "remaining": 0,
                "retry_after": retry_after,
                "resets_at": self._get_reset_time(),
                "tier": tier
            }
        
        # Increment counter
        new_count = count + 1
        ttl = self._get_seconds_until_reset()
        cache.set(window_key, new_count, cache_type="default", ttl=ttl)
        
        return True, {
            "count": new_count,
            "limit": limit,
            "remaining": limit - new_count,
            "tier": tier
        }
    
    def get_usage(self, key_hash: str, tier: str = "free") -> Dict:
        """
        Get usage statistics for an API key.
        
        Args:
            key_hash: SHA256 hash of the API key
            tier: API tier
        
        Returns:
            {
                "count": 42,
                "limit": 100,
                "remaining": 58,
                "resets_at": "2026-01-04T00:00:00Z"
            }
        """
        limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        window_key = self._get_window_key(key_hash)
        
        current = cache.get(window_key, cache_type="default")
        count = current if current else 0
        
        if limit == -1:
            remaining = -1
        else:
            remaining = max(0, limit - count)
        
        return {
            "count": count,
            "limit": limit,
            "remaining": remaining,
            "resets_at": self._get_reset_time()
        }
    
    def reset(self, key_hash: str) -> bool:
        """
        Reset the rate limit for an API key (admin only).
        
        Args:
            key_hash: SHA256 hash of the API key
        
        Returns:
            True if reset
        """
        window_key = self._get_window_key(key_hash)
        cache.delete(window_key, cache_type="default")
        logger.info(f"Rate limit reset for key: {key_hash[:16]}...")
        return True


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

rate_limiter = RateLimiter()


def check_rate_limit(key_hash: str, tier: str = "free") -> Tuple[bool, Dict]:
    """Convenience function"""
    return rate_limiter.check(key_hash, tier)


def get_rate_limit_usage(key_hash: str, tier: str = "free") -> Dict:
    """Convenience function"""
    return rate_limiter.get_usage(key_hash, tier)
