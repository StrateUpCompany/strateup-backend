"""
Webhook Manager
LeadHunter AI - Real-time Notifications

Features:
- Send webhooks to HTTP endpoints, Slack, Discord
- Queue for retry on failure
- Event-based triggers
"""
import os
import httpx
import asyncio
import secrets
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from backend.utils.logger import logger
from backend.core.cache_manager import cache
from backend.core.secrets_manager import get_secret

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


# =============================================================================
# WEBHOOK TYPES & EVENTS
# =============================================================================

class WebhookType(Enum):
    HTTP = "http"
    SLACK = "slack"
    DISCORD = "discord"


class WebhookEvent(Enum):
    NEW_LEAD = "new_lead"
    CLONE_COMPLETE = "clone_complete"
    ANALYSIS_COMPLETE = "analysis_complete"
    API_LIMIT_REACHED = "api_limit_reached"


# =============================================================================
# WEBHOOK MANAGER
# =============================================================================

class WebhookManager:
    """
    Manages webhooks for real-time notifications.
    
    Usage:
        manager = WebhookManager()
        
        # Register a webhook
        await manager.register(
            user_id="user123",
            url="https://hooks.slack.com/...",
            webhook_type=WebhookType.SLACK,
            events=[WebhookEvent.NEW_LEAD]
        )
        
        # Trigger an event
        await manager.trigger(
            event=WebhookEvent.NEW_LEAD,
            data={"lead_id": "123", "email": "test@example.com"}
        )
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    TIMEOUT = 10  # seconds
    
    _instance = None
    _memory_webhooks: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._memory_webhooks = {}
        self._supabase: Optional[Client] = None
        self._http_client = httpx.AsyncClient(timeout=self.TIMEOUT)
        
        if SUPABASE_AVAILABLE:
            self._connect_supabase()
    
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = get_secret("SUPABASE_URL")
        key = get_secret("SUPABASE_KEY")
        
        if url and key:
            try:
                self._supabase = create_client(url, key)
                logger.info("Connected to Supabase for webhooks")
            except Exception as e:
                logger.warning(f"Supabase connection failed: {e}")
    
    # =========================================================================
    # REGISTRATION METHODS
    # =========================================================================
    
    async def register(
        self,
        user_id: str,
        url: str,
        webhook_type: WebhookType = WebhookType.HTTP,
        events: List[WebhookEvent] = None,
        name: str = "Default",
        secret: str = None
    ) -> Dict[str, Any]:
        """
        Register a new webhook.
        
        Args:
            user_id: User ID
            url: Webhook URL
            webhook_type: Type (http, slack, discord)
            events: List of events to trigger
            name: Friendly name
            secret: Optional secret for signing
        
        Returns:
            Created webhook info
        """
        webhook_id = secrets.token_urlsafe(16)
        now = datetime.utcnow().isoformat()
        
        webhook_data = {
            "id": webhook_id,
            "user_id": user_id,
            "url": url,
            "type": webhook_type.value,
            "events": [e.value for e in (events or [WebhookEvent.NEW_LEAD])],
            "name": name,
            "secret": secret or secrets.token_urlsafe(32),
            "is_active": True,
            "created_at": now,
            "last_triggered_at": None,
            "failure_count": 0
        }
        
        # Store in Supabase if available
        if self._supabase:
            try:
                self._supabase.table("webhooks").insert(webhook_data).execute()
                logger.info(f"Webhook registered in Supabase: {name}")
            except Exception as e:
                logger.error(f"Failed to store webhook: {e}")
                self._memory_webhooks[webhook_id] = webhook_data
        else:
            self._memory_webhooks[webhook_id] = webhook_data
        
        return {
            "id": webhook_id,
            "name": name,
            "url": url[:50] + "..." if len(url) > 50 else url,
            "type": webhook_type.value,
            "events": [e.value for e in (events or [WebhookEvent.NEW_LEAD])],
            "created_at": now
        }
    
    async def list_webhooks(self, user_id: str) -> List[Dict[str, Any]]:
        """List all webhooks for a user"""
        webhooks = []
        
        if self._supabase:
            try:
                result = self._supabase.table("webhooks").select(
                    "id, name, url, type, events, is_active, created_at, last_triggered_at, failure_count"
                ).eq("user_id", user_id).execute()
                
                if result.data:
                    webhooks = result.data
            except Exception as e:
                logger.error(f"Supabase list failed: {e}")
        
        # Add memory webhooks
        for wh_id, data in self._memory_webhooks.items():
            if data["user_id"] == user_id:
                webhooks.append({
                    "id": data["id"],
                    "name": data["name"],
                    "url": data["url"][:50] + "..." if len(data["url"]) > 50 else data["url"],
                    "type": data["type"],
                    "events": data["events"],
                    "is_active": data["is_active"],
                    "created_at": data["created_at"],
                    "last_triggered_at": data.get("last_triggered_at"),
                    "failure_count": data.get("failure_count", 0)
                })
        
        return webhooks
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook"""
        if self._supabase:
            try:
                self._supabase.table("webhooks").delete().eq("id", webhook_id).execute()
                logger.info(f"Webhook deleted: {webhook_id}")
                return True
            except Exception as e:
                logger.error(f"Delete failed: {e}")
        
        if webhook_id in self._memory_webhooks:
            del self._memory_webhooks[webhook_id]
            return True
        
        return False
    
    # =========================================================================
    # TRIGGER METHODS
    # =========================================================================
    
    async def trigger(
        self,
        event: WebhookEvent,
        data: Dict[str, Any],
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Trigger webhooks for an event.
        
        Args:
            event: Event type
            data: Event data payload
            user_id: Optional filter by user
        
        Returns:
            Summary of sent webhooks
        """
        # Get all webhooks for this event
        webhooks = await self._get_webhooks_for_event(event, user_id)
        
        results = {
            "event": event.value,
            "webhooks_triggered": 0,
            "successes": 0,
            "failures": 0
        }
        
        for webhook in webhooks:
            if not webhook.get("is_active", True):
                continue
            
            success = await self._send_webhook(webhook, event, data)
            results["webhooks_triggered"] += 1
            
            if success:
                results["successes"] += 1
            else:
                results["failures"] += 1
        
        return results
    
    async def _get_webhooks_for_event(
        self,
        event: WebhookEvent,
        user_id: str = None
    ) -> List[Dict]:
        """Get all webhooks subscribed to an event"""
        webhooks = []
        
        # From Supabase
        if self._supabase:
            try:
                query = self._supabase.table("webhooks").select("*").eq("is_active", True)
                if user_id:
                    query = query.eq("user_id", user_id)
                result = query.execute()
                
                if result.data:
                    for wh in result.data:
                        if event.value in wh.get("events", []):
                            webhooks.append(wh)
            except Exception as e:
                logger.error(f"Supabase query failed: {e}")
        
        # From memory
        for wh_id, data in self._memory_webhooks.items():
            if not data.get("is_active", True):
                continue
            if user_id and data["user_id"] != user_id:
                continue
            if event.value in data.get("events", []):
                webhooks.append(data)
        
        return webhooks
    
    async def _send_webhook(
        self,
        webhook: Dict,
        event: WebhookEvent,
        data: Dict[str, Any]
    ) -> bool:
        """Send a single webhook"""
        webhook_type = WebhookType(webhook["type"])
        url = webhook["url"]
        
        payload = {
            "event": event.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        }
        
        try:
            if webhook_type == WebhookType.SLACK:
                success = await self._send_slack(url, event, data)
            elif webhook_type == WebhookType.DISCORD:
                success = await self._send_discord(url, event, data)
            else:
                success = await self._send_http(url, payload, webhook.get("secret"))
            
            if success:
                await self._update_webhook_status(webhook["id"], success=True)
            else:
                await self._update_webhook_status(webhook["id"], success=False)
            
            return success
            
        except Exception as e:
            logger.error(f"Webhook send error: {e}")
            await self._update_webhook_status(webhook["id"], success=False)
            return False
    
    async def _send_http(self, url: str, payload: Dict, secret: str = None) -> bool:
        """Send HTTP POST webhook"""
        headers = {"Content-Type": "application/json"}
        
        if secret:
            import hmac
            import hashlib
            import json
            signature = hmac.new(
                secret.encode(),
                json.dumps(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        
        try:
            response = await self._http_client.post(url, json=payload, headers=headers)
            success = 200 <= response.status_code < 300
            logger.info(f"HTTP webhook sent: {url} -> {response.status_code}")
            return success
        except Exception as e:
            logger.error(f"HTTP webhook failed: {e}")
            return False
    
    async def _send_slack(self, url: str, event: WebhookEvent, data: Dict) -> bool:
        """Send Slack webhook"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔔 {event.value.replace('_', ' ').title()}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{k}:*\n{v}"}
                    for k, v in list(data.items())[:10]
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Sent from LeadHunter AI • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                    }
                ]
            }
        ]
        
        try:
            response = await self._http_client.post(url, json={"blocks": blocks})
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack webhook failed: {e}")
            return False
    
    async def _send_discord(self, url: str, event: WebhookEvent, data: Dict) -> bool:
        """Send Discord webhook"""
        embed = {
            "title": f"🔔 {event.value.replace('_', ' ').title()}",
            "color": 0x06b6d4,  # Cyan
            "fields": [
                {"name": k, "value": str(v)[:1024], "inline": True}
                for k, v in list(data.items())[:25]
            ],
            "footer": {
                "text": f"LeadHunter AI • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            }
        }
        
        try:
            response = await self._http_client.post(url, json={"embeds": [embed]})
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error(f"Discord webhook failed: {e}")
            return False
    
    async def _update_webhook_status(self, webhook_id: str, success: bool):
        """Update webhook status after trigger"""
        now = datetime.utcnow().isoformat()
        
        if self._supabase:
            try:
                if success:
                    self._supabase.table("webhooks").update({
                        "last_triggered_at": now,
                        "failure_count": 0
                    }).eq("id", webhook_id).execute()
                else:
                    # Increment failure count
                    self._supabase.rpc("increment_webhook_failures", {"wh_id": webhook_id}).execute()
            except:
                pass
        
        if webhook_id in self._memory_webhooks:
            self._memory_webhooks[webhook_id]["last_triggered_at"] = now
            if success:
                self._memory_webhooks[webhook_id]["failure_count"] = 0
            else:
                self._memory_webhooks[webhook_id]["failure_count"] = \
                    self._memory_webhooks[webhook_id].get("failure_count", 0) + 1
    
    async def test_webhook(self, webhook_id: str) -> bool:
        """Test a webhook with sample data"""
        # Find webhook
        webhook = None
        
        if self._supabase:
            try:
                result = self._supabase.table("webhooks").select("*").eq("id", webhook_id).execute()
                if result.data:
                    webhook = result.data[0]
            except:
                pass
        
        if not webhook and webhook_id in self._memory_webhooks:
            webhook = self._memory_webhooks[webhook_id]
        
        if not webhook:
            return False
        
        test_data = {
            "test": True,
            "message": "This is a test webhook from LeadHunter AI",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self._send_webhook(webhook, WebhookEvent.NEW_LEAD, test_data)


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

webhook_manager = WebhookManager()


async def trigger_webhook(event: str, data: Dict, user_id: str = None):
    """Convenience function to trigger webhooks"""
    try:
        event_enum = WebhookEvent(event)
        return await webhook_manager.trigger(event_enum, data, user_id)
    except ValueError:
        logger.error(f"Invalid webhook event: {event}")
        return None
