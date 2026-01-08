"""
Analytics Routes
LeadHunter AI - Analytics API

Endpoints:
- GET /api/analytics/overview   - Dashboard overview
- GET /api/analytics/requests   - Requests trend
- GET /api/analytics/endpoints  - Top endpoints
- GET /api/analytics/cache      - Cache statistics
- GET /api/analytics/keys       - API keys usage
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from backend.core.analytics import analytics


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# =============================================================================
# MODELS
# =============================================================================

class OverviewResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


class TrendResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/overview", response_model=OverviewResponse)
async def get_overview():
    """
    Get dashboard overview with key metrics.
    
    Returns:
    - requests_today: Total requests today
    - requests_change_pct: Change vs yesterday
    - cache_hit_rate: Cache hit percentage
    - avg_latency_ms: Average response time
    - error_rate_pct: Error percentage
    """
    data = analytics.get_overview()
    return OverviewResponse(success=True, data=data)


@router.get("/requests", response_model=TrendResponse)
async def get_requests_trend(
    days: int = Query(7, ge=1, le=30, description="Number of days"),
    hourly: bool = Query(False, description="Get hourly instead of daily")
):
    """
    Get requests trend over time.
    
    Args:
        days: Number of days to include (1-30)
        hourly: If true, return hourly data for last 24h
    """
    if hourly:
        data = analytics.get_hourly_requests(hours=24)
    else:
        data = analytics.get_requests_trend(days=days)
    
    return TrendResponse(success=True, data=data)


@router.get("/endpoints", response_model=TrendResponse)
async def get_top_endpoints(
    limit: int = Query(10, ge=1, le=50, description="Number of endpoints"),
    date: Optional[str] = Query(None, description="Date (YYYY-MM-DD)")
):
    """
    Get top endpoints by request count.
    
    Args:
        limit: Max number of endpoints to return
        date: Specific date (default: today)
    """
    data = analytics.get_top_endpoints(limit=limit, date=date)
    return TrendResponse(success=True, data=data)


@router.get("/cache", response_model=OverviewResponse)
async def get_cache_stats():
    """
    Get cache statistics.
    
    Returns:
    - today_hits: Cache hits today
    - today_misses: Cache misses today
    - hit_rate_pct: Hit rate percentage
    - redis_available: Redis connectivity status
    """
    data = analytics.get_cache_stats()
    return OverviewResponse(success=True, data=data)


@router.get("/keys", response_model=TrendResponse)
async def get_api_keys_usage(
    limit: int = Query(10, ge=1, le=50, description="Number of keys")
):
    """
    Get API key usage statistics.
    
    Args:
        limit: Max number of keys to return
    """
    data = analytics.get_api_keys_usage(limit=limit)
    return TrendResponse(success=True, data=data)


@router.get("/errors", response_model=OverviewResponse)
async def get_errors(
    date: Optional[str] = Query(None, description="Date (YYYY-MM-DD)")
):
    """
    Get error statistics.
    
    Args:
        date: Specific date (default: today)
    """
    data = analytics.get_errors(date=date)
    return OverviewResponse(success=True, data=data)
