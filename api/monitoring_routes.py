"""
Monitoring Routes
LeadHunter AI - Metrics & Health API

Endpoints:
- GET  /metrics              - Prometheus metrics
- GET  /health               - Health check
- GET  /api/monitoring/stats - Dashboard stats
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from typing import Dict, Any
from backend.core.monitoring import metrics_collector, health_checker, alert_manager


router = APIRouter(tags=["Monitoring"])


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return metrics_collector.to_prometheus()


@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with all components"""
    return await health_checker.run_checks()


@router.get("/api/monitoring/stats")
async def monitoring_stats():
    """Get monitoring statistics for dashboard"""
    metrics = metrics_collector.get_metrics()
    
    return {
        "success": True,
        "data": {
            "uptime": metrics["uptime_seconds"],
            "total_requests": metrics["total_requests"],
            "total_errors": metrics["total_errors"],
            "error_rate": (
                metrics["total_errors"] / metrics["total_requests"] 
                if metrics["total_requests"] > 0 else 0
            ),
            "active_connections": metrics["active_connections"],
            "top_endpoints": sorted(
                metrics["requests_by_endpoint"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "status_codes": metrics["status_codes"]
        }
    }


@router.get("/api/monitoring/alerts")
async def get_alerts():
    """Get triggered alerts"""
    return {
        "success": True,
        "data": {
            "alerts": alert_manager.get_triggered()
        }
    }
