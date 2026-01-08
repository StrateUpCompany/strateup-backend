"""
Analytics Collector
LeadHunter AI - Metrics & Tracking

Features:
- Track API requests (endpoint, method, status, latency)
- Track cache hits/misses
- Daily/weekly/monthly aggregations
- Top endpoints and API keys stats
"""
import os
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from backend.utils.logger import logger
from backend.core.cache_manager import cache


# =============================================================================
# ANALYTICS COLLECTOR
# =============================================================================

class AnalyticsCollector:
    """
    Collects and aggregates analytics data using Redis.
    
    Usage:
        analytics = AnalyticsCollector()
        
        # Track a request
        analytics.track_request(
            endpoint="/api/v1/search/instagram/nike",
            method="GET",
            status_code=200,
            latency_ms=150,
            api_key_hash="abc123..."
        )
        
        # Get stats
        stats = analytics.get_overview()
    """
    
    PREFIX = "analytics"
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
    
    def _get_date_key(self, date: datetime = None) -> str:
        """Get date key for aggregation"""
        if date is None:
            date = datetime.utcnow()
        return date.strftime("%Y-%m-%d")
    
    def _get_hour_key(self, date: datetime = None) -> str:
        """Get hour key for hourly aggregation"""
        if date is None:
            date = datetime.utcnow()
        return date.strftime("%Y-%m-%d:%H")
    
    # =========================================================================
    # TRACKING METHODS
    # =========================================================================
    
    def track_request(
        self,
        endpoint: str,
        method: str = "GET",
        status_code: int = 200,
        latency_ms: float = 0,
        api_key_hash: str = None,
        user_id: str = None
    ):
        """
        Track an API request.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: Response status code
            latency_ms: Request latency in milliseconds
            api_key_hash: Hash of the API key used
            user_id: User ID if authenticated
        """
        date_key = self._get_date_key()
        hour_key = self._get_hour_key()
        
        try:
            # Increment daily request count
            daily_key = f"{self.PREFIX}:requests:{date_key}"
            current = cache.get(daily_key, cache_type="default") or 0
            cache.set(daily_key, current + 1, cache_type="default", ttl=604800)  # 7 days
            
            # Increment hourly request count
            hourly_key = f"{self.PREFIX}:requests:hourly:{hour_key}"
            current_hourly = cache.get(hourly_key, cache_type="default") or 0
            cache.set(hourly_key, current_hourly + 1, cache_type="default", ttl=172800)  # 48 hours
            
            # Track endpoint popularity
            endpoint_base = endpoint.split("?")[0]  # Remove query params
            endpoint_key = f"{self.PREFIX}:endpoints:{date_key}"
            endpoints = cache.get(endpoint_key, cache_type="default") or {}
            endpoints[endpoint_base] = endpoints.get(endpoint_base, 0) + 1
            cache.set(endpoint_key, endpoints, cache_type="default", ttl=604800)
            
            # Track status codes
            status_key = f"{self.PREFIX}:status:{date_key}"
            statuses = cache.get(status_key, cache_type="default") or {}
            status_group = f"{status_code // 100}xx"
            statuses[status_group] = statuses.get(status_group, 0) + 1
            cache.set(status_key, statuses, cache_type="default", ttl=604800)
            
            # Track latency (rolling average)
            latency_key = f"{self.PREFIX}:latency:{date_key}"
            latency_data = cache.get(latency_key, cache_type="default") or {"sum": 0, "count": 0}
            latency_data["sum"] += latency_ms
            latency_data["count"] += 1
            cache.set(latency_key, latency_data, cache_type="default", ttl=604800)
            
            # Track API key usage
            if api_key_hash:
                key_usage_key = f"{self.PREFIX}:keys:{date_key}"
                key_usage = cache.get(key_usage_key, cache_type="default") or {}
                short_hash = api_key_hash[:16]
                key_usage[short_hash] = key_usage.get(short_hash, 0) + 1
                cache.set(key_usage_key, key_usage, cache_type="default", ttl=604800)
            
            logger.debug(f"Tracked request: {method} {endpoint} -> {status_code}")
            
        except Exception as e:
            logger.error(f"Analytics tracking error: {e}")
    
    def track_cache_hit(self, hit: bool = True):
        """Track cache hit or miss"""
        date_key = self._get_date_key()
        cache_key = f"{self.PREFIX}:cache:{date_key}"
        
        try:
            data = cache.get(cache_key, cache_type="default") or {"hits": 0, "misses": 0}
            if hit:
                data["hits"] += 1
            else:
                data["misses"] += 1
            cache.set(cache_key, data, cache_type="default", ttl=604800)
        except Exception as e:
            logger.error(f"Cache tracking error: {e}")
    
    def track_error(self, error_type: str, endpoint: str = None):
        """Track an error occurrence"""
        date_key = self._get_date_key()
        error_key = f"{self.PREFIX}:errors:{date_key}"
        
        try:
            errors = cache.get(error_key, cache_type="default") or {}
            errors[error_type] = errors.get(error_type, 0) + 1
            cache.set(error_key, errors, cache_type="default", ttl=604800)
        except Exception as e:
            logger.error(f"Error tracking error: {e}")
    
    # =========================================================================
    # RETRIEVAL METHODS
    # =========================================================================
    
    def get_overview(self) -> Dict[str, Any]:
        """Get overview of all analytics"""
        date_key = self._get_date_key()
        yesterday_key = self._get_date_key(datetime.utcnow() - timedelta(days=1))
        
        # Today's requests
        requests_today = cache.get(f"{self.PREFIX}:requests:{date_key}", cache_type="default") or 0
        requests_yesterday = cache.get(f"{self.PREFIX}:requests:{yesterday_key}", cache_type="default") or 0
        
        # Cache stats
        cache_data = cache.get(f"{self.PREFIX}:cache:{date_key}", cache_type="default") or {"hits": 0, "misses": 0}
        total_cache = cache_data["hits"] + cache_data["misses"]
        cache_rate = (cache_data["hits"] / total_cache * 100) if total_cache > 0 else 0
        
        # Latency
        latency_data = cache.get(f"{self.PREFIX}:latency:{date_key}", cache_type="default") or {"sum": 0, "count": 0}
        avg_latency = (latency_data["sum"] / latency_data["count"]) if latency_data["count"] > 0 else 0
        
        # Status codes
        statuses = cache.get(f"{self.PREFIX}:status:{date_key}", cache_type="default") or {}
        error_rate = (statuses.get("4xx", 0) + statuses.get("5xx", 0)) / max(requests_today, 1) * 100
        
        # Change calculations
        requests_change = ((requests_today - requests_yesterday) / max(requests_yesterday, 1)) * 100
        
        return {
            "requests_today": requests_today,
            "requests_yesterday": requests_yesterday,
            "requests_change_pct": round(requests_change, 1),
            "cache_hit_rate": round(cache_rate, 1),
            "cache_hits": cache_data["hits"],
            "cache_misses": cache_data["misses"],
            "avg_latency_ms": round(avg_latency, 2),
            "error_rate_pct": round(error_rate, 2),
            "status_codes": statuses,
            "date": date_key
        }
    
    def get_requests_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get requests trend for the last N days"""
        trend = []
        today = datetime.utcnow()
        
        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            date_key = self._get_date_key(date)
            count = cache.get(f"{self.PREFIX}:requests:{date_key}", cache_type="default") or 0
            trend.append({
                "date": date_key,
                "requests": count
            })
        
        return trend
    
    def get_hourly_requests(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly requests for the last N hours"""
        trend = []
        now = datetime.utcnow()
        
        for i in range(hours - 1, -1, -1):
            hour = now - timedelta(hours=i)
            hour_key = self._get_hour_key(hour)
            count = cache.get(f"{self.PREFIX}:requests:hourly:{hour_key}", cache_type="default") or 0
            trend.append({
                "hour": hour_key,
                "requests": count
            })
        
        return trend
    
    def get_top_endpoints(self, limit: int = 10, date: str = None) -> List[Dict[str, Any]]:
        """Get top endpoints by request count"""
        date_key = date or self._get_date_key()
        endpoints = cache.get(f"{self.PREFIX}:endpoints:{date_key}", cache_type="default") or {}
        
        # Sort by count
        sorted_endpoints = sorted(endpoints.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [{"endpoint": e, "count": c} for e, c in sorted_endpoints]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics"""
        date_key = self._get_date_key()
        cache_data = cache.get(f"{self.PREFIX}:cache:{date_key}", cache_type="default") or {"hits": 0, "misses": 0}
        
        total = cache_data["hits"] + cache_data["misses"]
        hit_rate = (cache_data["hits"] / total * 100) if total > 0 else 0
        
        # Get Redis stats if available
        redis_stats = cache.get_stats()
        
        return {
            "today_hits": cache_data["hits"],
            "today_misses": cache_data["misses"],
            "today_total": total,
            "hit_rate_pct": round(hit_rate, 1),
            "redis_available": redis_stats.get("redis_available", False),
            "redis_keys": redis_stats.get("redis_keys", 0)
        }
    
    def get_api_keys_usage(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get API key usage stats"""
        date_key = self._get_date_key()
        key_usage = cache.get(f"{self.PREFIX}:keys:{date_key}", cache_type="default") or {}
        
        # Sort by usage
        sorted_keys = sorted(key_usage.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [{"key_hash": k, "requests": r} for k, r in sorted_keys]
    
    def get_errors(self, date: str = None) -> Dict[str, Any]:
        """Get error statistics"""
        date_key = date or self._get_date_key()
        errors = cache.get(f"{self.PREFIX}:errors:{date_key}", cache_type="default") or {}
        
        return {
            "date": date_key,
            "errors": errors,
            "total": sum(errors.values())
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

analytics = AnalyticsCollector()


def track_request(**kwargs):
    """Convenience function"""
    analytics.track_request(**kwargs)


def track_cache_hit(hit: bool = True):
    """Convenience function"""
    analytics.track_cache_hit(hit)
