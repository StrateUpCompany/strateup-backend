"""
Audit Logger
LeadHunter AI - Compliance & Debugging

Features:
- Log all user actions
- Query logs with filters
- Export for compliance
"""
import os
import secrets
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from backend.utils.logger import logger
from backend.core.cache_manager import cache

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


# =============================================================================
# AUDIT ACTIONS
# =============================================================================

class AuditAction(Enum):
    # User actions
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    
    # Lead actions
    LEAD_CREATE = "lead.create"
    LEAD_UPDATE = "lead.update"
    LEAD_DELETE = "lead.delete"
    LEAD_EXPORT = "lead.export"
    
    # Clone actions
    CLONE_START = "clone.start"
    CLONE_COMPLETE = "clone.complete"
    CLONE_ERROR = "clone.error"
    
    # API actions
    API_REQUEST = "api.request"
    API_KEY_CREATE = "api_key.create"
    API_KEY_REVOKE = "api_key.revoke"
    
    # Webhook actions
    WEBHOOK_CREATE = "webhook.create"
    WEBHOOK_TRIGGER = "webhook.trigger"
    WEBHOOK_DELETE = "webhook.delete"
    
    # System actions
    SYSTEM_ERROR = "system.error"
    SYSTEM_CONFIG = "system.config"


# =============================================================================
# AUDIT LOGGER
# =============================================================================

class AuditLogger:
    """
    Logs all user actions for compliance and debugging.
    
    Usage:
        audit = AuditLogger()
        
        # Log an action
        audit.log(
            action=AuditAction.LEAD_CREATE,
            user_id="user123",
            resource_id="lead456",
            metadata={"email": "test@example.com"}
        )
        
        # Query logs
        logs = await audit.query(user_id="user123", days=7)
    """
    
    MAX_LOGS_IN_MEMORY = 10000
    CACHE_TTL = 604800  # 7 days
    
    _instance = None
    _memory_logs: List[Dict] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._memory_logs = []
        self._supabase: Optional[Client] = None
        
        if SUPABASE_AVAILABLE:
            self._connect_supabase()
    
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if url and key:
            try:
                self._supabase = create_client(url, key)
                logger.info("Connected to Supabase for audit logs")
            except Exception as e:
                logger.warning(f"Supabase connection failed: {e}")
    
    # =========================================================================
    # LOGGING METHODS
    # =========================================================================
    
    def log(
        self,
        action: AuditAction,
        user_id: str = None,
        resource: str = None,
        resource_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        metadata: Dict = None,
        success: bool = True
    ) -> str:
        """
        Log an audit event.
        
        Args:
            action: Action type
            user_id: User who performed the action
            resource: Resource type (leads, clones, etc.)
            resource_id: Specific resource ID
            ip_address: Client IP
            user_agent: Client user agent
            metadata: Additional data
            success: Whether action succeeded
        
        Returns:
            Log entry ID
        """
        log_id = secrets.token_urlsafe(16)
        now = datetime.utcnow().isoformat() + "Z"
        
        entry = {
            "id": log_id,
            "timestamp": now,
            "action": action.value,
            "user_id": user_id or "system",
            "resource": resource,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata or {},
            "success": success
        }
        
        # Store in Supabase if available
        if self._supabase:
            try:
                self._supabase.table("audit_logs").insert(entry).execute()
            except Exception as e:
                logger.error(f"Failed to store audit log: {e}")
                self._store_in_memory(entry)
        else:
            self._store_in_memory(entry)
        
        # Also cache recent logs for quick access
        self._cache_recent_log(entry)
        
        logger.debug(f"Audit: {action.value} by {user_id or 'system'}")
        return log_id
    
    def _store_in_memory(self, entry: Dict):
        """Store log in memory (fallback)"""
        self._memory_logs.append(entry)
        
        # Trim if too many
        if len(self._memory_logs) > self.MAX_LOGS_IN_MEMORY:
            self._memory_logs = self._memory_logs[-self.MAX_LOGS_IN_MEMORY:]
    
    def _cache_recent_log(self, entry: Dict):
        """Cache recent log for quick aggregation"""
        date_key = entry["timestamp"][:10]
        cache_key = f"audit:recent:{date_key}"
        
        try:
            recent = cache.get(cache_key, cache_type="default") or []
            recent.append({
                "id": entry["id"],
                "action": entry["action"],
                "user_id": entry["user_id"],
                "timestamp": entry["timestamp"]
            })
            
            # Keep last 100 per day in cache
            cache.set(cache_key, recent[-100:], cache_type="default", ttl=172800)
        except:
            pass
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    async def query(
        self,
        user_id: str = None,
        action: str = None,
        resource: str = None,
        days: int = 7,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Query audit logs with filters.
        
        Args:
            user_id: Filter by user
            action: Filter by action type
            resource: Filter by resource type
            days: Number of days to look back
            limit: Max results
            offset: Pagination offset
        
        Returns:
            List of log entries
        """
        logs = []
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
        
        # Query Supabase
        if self._supabase:
            try:
                query = self._supabase.table("audit_logs").select("*")
                query = query.gte("timestamp", cutoff)
                
                if user_id:
                    query = query.eq("user_id", user_id)
                if action:
                    query = query.eq("action", action)
                if resource:
                    query = query.eq("resource", resource)
                
                query = query.order("timestamp", desc=True)
                query = query.range(offset, offset + limit - 1)
                
                result = query.execute()
                if result.data:
                    logs = result.data
            except Exception as e:
                logger.error(f"Audit query failed: {e}")
        
        # Add memory logs
        for entry in reversed(self._memory_logs):
            if entry["timestamp"] < cutoff:
                continue
            if user_id and entry["user_id"] != user_id:
                continue
            if action and entry["action"] != action:
                continue
            if resource and entry["resource"] != resource:
                continue
            logs.append(entry)
            if len(logs) >= limit:
                break
        
        # Sort by timestamp desc
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        return logs[:limit]
    
    async def get_log(self, log_id: str) -> Optional[Dict]:
        """Get a specific log entry by ID"""
        if self._supabase:
            try:
                result = self._supabase.table("audit_logs").select("*").eq("id", log_id).execute()
                if result.data:
                    return result.data[0]
            except:
                pass
        
        # Check memory
        for entry in self._memory_logs:
            if entry["id"] == log_id:
                return entry
        
        return None
    
    async def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get audit statistics"""
        logs = await self.query(days=days, limit=10000)
        
        # Count by action
        action_counts = {}
        user_counts = {}
        hourly = {}
        
        for log in logs:
            # Action counts
            action = log["action"]
            action_counts[action] = action_counts.get(action, 0) + 1
            
            # User counts
            user = log["user_id"]
            user_counts[user] = user_counts.get(user, 0) + 1
            
            # Hourly distribution
            hour = log["timestamp"][11:13]
            hourly[hour] = hourly.get(hour, 0) + 1
        
        # Success rate
        successes = sum(1 for l in logs if l.get("success", True))
        success_rate = (successes / len(logs) * 100) if logs else 100
        
        return {
            "total_logs": len(logs),
            "period_days": days,
            "success_rate_pct": round(success_rate, 1),
            "by_action": dict(sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_user": dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_hour": hourly
        }
    
    async def export_csv(self, user_id: str = None, days: int = 30) -> str:
        """Export logs as CSV string"""
        logs = await self.query(user_id=user_id, days=days, limit=10000)
        
        if not logs:
            return "timestamp,action,user_id,resource,resource_id,success\n"
        
        lines = ["timestamp,action,user_id,resource,resource_id,success"]
        for log in logs:
            lines.append(
                f"{log['timestamp']},{log['action']},{log['user_id']},"
                f"{log.get('resource', '')},{log.get('resource_id', '')},{log.get('success', True)}"
            )
        
        return "\n".join(lines)


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

audit_logger = AuditLogger()


def log_audit(action: str, **kwargs) -> str:
    """Convenience function to log an audit event"""
    try:
        action_enum = AuditAction(action)
        return audit_logger.log(action_enum, **kwargs)
    except ValueError:
        logger.warning(f"Unknown audit action: {action}")
        return ""
