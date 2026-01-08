
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from backend.core.webhook_manager import webhook_manager

router = APIRouter()

class WebhookSubscriptionCreate(BaseModel):
    url: str
    events: List[str]
    user_id: Optional[str] = None

@router.post("/", status_code=201)
async def subscribe_webhook(sub: WebhookSubscriptionCreate):
    """
    Subscribe to webhooks.
    """
    try:
        result = await webhook_manager.subscribe(sub.url, sub.events, sub.user_id)
        return {"success": True, "subscription": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{subscription_id}")
async def unsubscribe_webhook(subscription_id: str):
    """
    Unsubscribe a webhook.
    """
    success = await webhook_manager.unsubscribe(subscription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found or failed to delete")
    return {"success": True}

@router.get("/")
async def list_webhooks(user_id: Optional[str] = None):
    """
    List subscriptions.
    """
    return await webhook_manager.list_subscriptions(user_id)

@router.post("/test")
async def test_webhook_endpoint(webhook_id: str):
    """
    Manually trigger a test event for a specific webhook.
    """
    # For MVP, we just dispatch a generic event to all (or filter if we implemented ID filtering in dispatch)
    # The current dispatch logic sends to ALL matching event subscribers.
    # To test a specific ID, we'd need to update manager.dispatch or just fetch the URL and send direct.
    
    # Simple approach: fetch URL and send direct 'test.ping'
    try:
        # We need to access db directly or add method to manager.
        # Let's add a helper to manager to 'test' a specific sub? 
        # Or just dispatch 'test.ping' event and if they subscribed to it...
        # But UI implies testing a SPECIFIC webhook regardless of events.
        
        # Let's read the sub to get URL
        from backend.core.supabase_manager import SupabaseManager
        import httpx
        
        db = SupabaseManager()
        res = db.supabase.table("webhook_subscriptions").select("*").eq("id", webhook_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Webhook not found")
            
        sub = res.data[0]
        url = sub["url"]
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={
                "event": "test.ping",
                "timestamp": "now",
                "payload": {"message": "Test from LeadHunter AI"}
            })
            return {"success": True, "status": resp.status_code}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
