
import logging
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.core.supabase_manager import SupabaseManager

logger = logging.getLogger("WebhookManager")

class WebhookManager:
    """
    Manages websocket subscriptions and dispatches events to external URLs.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized: return
        self.db = SupabaseManager()
        self._initialized = True
        
    async def subscribe(self, url: str, events: List[str], user_id: str = None) -> Dict[str, Any]:
        """
        Subscribe a URL to specific events.
        """
        try:
            data = {
                "url": url,
                "events": events,
                "user_id": user_id
            }
            res = self.db.supabase.table("webhook_subscriptions").insert(data).execute()
            if res.data:
                logger.info(f"Webhook subscribed: {url} for {events}")
                return res.data[0]
            return {}
        except Exception as e:
            logger.error(f"Failed to subscribe webhook: {e}")
            raise e

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove a subscription.
        """
        try:
            self.db.supabase.table("webhook_subscriptions").delete().eq("id", subscription_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
            return False
            
    async def list_subscriptions(self, user_id: str = None) -> List[Dict]:
        """
        List active subscriptions.
        """
        try:
            req = self.db.supabase.table("webhook_subscriptions").select("*")
            if user_id:
                req = req.eq("user_id", user_id)
            res = req.execute()
            return res.data
        except Exception as e:
            logger.error(f"Failed to list subscriptions: {e}")
            return []

    async def dispatch(self, event_name: str, payload: Dict[str, Any]):
        """
        Dispatch an event to all subscribers.
        This fires distinct async tasks for each subscriber to avoid blocking.
        """
        try:
            # 1. Get subscribers for this event
            # Note: Postgres doesn't have easy array contains for TEXT[] in PostgREST without specific operators.
            # We'll fetch all and filter in memory for MVP, or use 'cs' (contains) operator if Supabase supports it well on text arrays.
            # Supabase-py 'cs': .cs("events", [event_name])
            
            res = self.db.supabase.table("webhook_subscriptions").select("*").cs("events", [event_name]).execute()
            subscribers = res.data or []
            
            if not subscribers:
                return

            logger.info(f"Dispatching event '{event_name}' to {len(subscribers)} subscribers.")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                tasks = []
                for sub in subscribers:
                    tasks.append(self._send_payload(client, sub["url"], event_name, payload))
                
                # Run all webhook posts concurrently
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            # Don't let webhook failure crash the app
            logger.error(f"Dispatch error for {event_name}: {e}")

    async def _send_payload(self, client: httpx.AsyncClient, url: str, event: str, payload: Dict):
        """Helper to send individual webhook"""
        wrapper = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }
        try:
            resp = await client.post(url, json=wrapper)
            if resp.status_code >= 400:
                logger.warning(f"Webhook failed {url}: Status {resp.status_code}")
            else:
                logger.debug(f"Webhook sent {url}: OK")
        except Exception as e:
            logger.warning(f"Webhook delivery failed {url}: {e}")

# Singleton
webhook_manager = WebhookManager()
