"""
Monitoring Service
LeadHunter AI - Prometheus Metrics & Alerts

Features:
- Application metrics
- Health checks
- Alert configuration
"""
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from backend.utils.logger import logger


# =============================================================================
# METRICS
# =============================================================================

class MetricsCollector:
    """
    Collects and exposes Prometheus-style metrics.
    
    Usage:
        metrics = MetricsCollector()
        
        # Track request
        metrics.track_request("GET /api/leads", 200, 0.150)
        
        # Get metrics
        data = metrics.get_metrics()
    """
    
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
        self._start_time = time.time()
        
        # Counters
        self._request_count = defaultdict(int)
        self._error_count = defaultdict(int)
        self._status_codes = defaultdict(int)
        
        # Histograms (latency buckets)
        self._latency_sum = defaultdict(float)
        self._latency_count = defaultdict(int)
        
        # Gauges
        self._active_connections = 0
        self._queue_size = 0
    
    # =========================================================================
    # TRACKING
    # =========================================================================
    
    def track_request(
        self,
        endpoint: str,
        status_code: int,
        latency: float
    ):
        """Track an HTTP request"""
        self._request_count[endpoint] += 1
        self._status_codes[status_code] += 1
        self._latency_sum[endpoint] += latency
        self._latency_count[endpoint] += 1
        
        if status_code >= 400:
            self._error_count[endpoint] += 1
    
    def track_error(self, error_type: str):
        """Track an error"""
        self._error_count[error_type] += 1
    
    def set_connections(self, count: int):
        """Set active connections count"""
        self._active_connections = count
    
    def set_queue_size(self, size: int):
        """Set queue size"""
        self._queue_size = size
    
    # =========================================================================
    # EXPORTS
    # =========================================================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics in a structured format"""
        uptime = time.time() - self._start_time
        
        # Calculate average latencies
        avg_latencies = {}
        for endpoint, total in self._latency_sum.items():
            count = self._latency_count[endpoint]
            avg_latencies[endpoint] = total / count if count > 0 else 0
        
        return {
            # Info
            "uptime_seconds": uptime,
            "start_time": datetime.fromtimestamp(self._start_time).isoformat(),
            
            # Counters
            "total_requests": sum(self._request_count.values()),
            "total_errors": sum(self._error_count.values()),
            "requests_by_endpoint": dict(self._request_count),
            "errors_by_type": dict(self._error_count),
            "status_codes": dict(self._status_codes),
            
            # Latency
            "avg_latency_by_endpoint": avg_latencies,
            
            # Gauges
            "active_connections": self._active_connections,
            "queue_size": self._queue_size
        }
    
    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # Uptime
        uptime = time.time() - self._start_time
        lines.append(f"leadhunter_uptime_seconds {uptime}")
        
        # Request counts
        for endpoint, count in self._request_count.items():
            safe_endpoint = endpoint.replace(" ", "_").replace("/", "_")
            lines.append(f'leadhunter_requests_total{{endpoint="{safe_endpoint}"}} {count}')
        
        # Error counts
        for error_type, count in self._error_count.items():
            lines.append(f'leadhunter_errors_total{{type="{error_type}"}} {count}')
        
        # Status codes
        for code, count in self._status_codes.items():
            lines.append(f'leadhunter_http_status_total{{code="{code}"}} {count}')
        
        # Gauges
        lines.append(f"leadhunter_active_connections {self._active_connections}")
        lines.append(f"leadhunter_queue_size {self._queue_size}")
        
        return "\n".join(lines)


# =============================================================================
# HEALTH CHECKS
# =============================================================================

class HealthChecker:
    """
    Health check service.
    """
    
    def __init__(self):
        self._checks = {}
    
    def register_check(self, name: str, check_fn):
        """Register a health check function"""
        self._checks[name] = check_fn
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        all_healthy = True
        
        for name, check_fn in self._checks.items():
            try:
                result = await check_fn() if callable(check_fn) else check_fn
                results[name] = {"status": "healthy" if result else "unhealthy"}
                if not result:
                    all_healthy = False
            except Exception as e:
                results[name] = {"status": "unhealthy", "error": str(e)}
                all_healthy = False
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": results,
            "timestamp": datetime.utcnow().isoformat()
        }


# =============================================================================
# ALERTS
# =============================================================================

class AlertManager:
    """
    Alert configuration and management.
    """
    
    def __init__(self):
        self._alerts = []
        self._triggered = []
    
    def add_alert(
        self,
        name: str,
        condition: str,
        threshold: float,
        channel: str = "slack"
    ):
        """Add an alert rule"""
        self._alerts.append({
            "name": name,
            "condition": condition,
            "threshold": threshold,
            "channel": channel
        })
    
    def check_alerts(self, metrics: Dict) -> List[Dict]:
        """Check alerts against current metrics"""
        triggered = []
        
        for alert in self._alerts:
            # Simple condition evaluation
            if alert["condition"] == "error_rate_high":
                total = metrics.get("total_requests", 0)
                errors = metrics.get("total_errors", 0)
                if total > 0 and (errors / total) > alert["threshold"]:
                    triggered.append({
                        **alert,
                        "triggered_at": datetime.utcnow().isoformat(),
                        "value": errors / total
                    })
        
        self._triggered.extend(triggered)
        return triggered
    
    def get_triggered(self) -> List[Dict]:
        """Get all triggered alerts"""
        return self._triggered


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

metrics_collector = MetricsCollector()
health_checker = HealthChecker()
alert_manager = AlertManager()

# Default alerts
alert_manager.add_alert(
    name="High Error Rate",
    condition="error_rate_high",
    threshold=0.05,  # 5%
    channel="slack"
)
