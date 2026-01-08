
from backend.core.database import db
from datetime import datetime
import asyncio

class AuditLogger:
    @staticmethod
    async def log_action(
        actor_id: str,
        action: str,
        target_resource: str,
        target_id: str = None,
        ip_address: str = None,
        details: dict = {}
    ):
        """
        Logs a system action to the audit_logs table.
        Fire-and-forget (async) to avoid slowing down the request.
        """
        try:
            payload = {
                "actor_id": actor_id,
                "action": action,
                "target_resource": target_resource,
                "target_id": target_id,
                "ip_address": ip_address,
                "details": details,
                "created_at": datetime.now().isoformat()
            }
            
            # Using Supabase async client if available, or wrapping sync in thread
            # Since our 'db' is currently sync in some contexts, we assume 'db' wrapper handles it
            # or we run it in executor if strictly blocking.
            # For MVP simplicity with Supabase-py sync client:
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: db.table("audit_logs").insert(payload).execute())
            
        except Exception as e:
            # Fallback logging (disk or stdout) if DB fails
            print(f"❌ Audit Log Failed: {e} | Action: {action} by {actor_id}")

audit_logger = AuditLogger()
