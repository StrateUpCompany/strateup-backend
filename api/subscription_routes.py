
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict
import os
# from supabase import create_client, Client # Removed local init
from backend.core.database import db as supabase
from datetime import datetime, timedelta

# Initialize Router
router = APIRouter(prefix="/subscriptions", tags=["Monetization"])

# Supabase Client
# supabase is now imported from core.database

class CheckoutRequest(BaseModel):
    user_id: str
    plan_id: str = "agency_brl_monthly"
    email: str

class SubscriptionStatus(BaseModel):
    is_active: bool
    plan: str
    expires_at: Optional[datetime]

@router.post("/checkout")
async def create_checkout_session(req: CheckoutRequest):
    """
    Creates a Payment Session (Stripe/Asaas Logic).
    For MVP: Simulates a successful checkout link.
    """
    try:
        # 1. In a real app, this would call stripe.checkout.sessions.create()
        # 2. Return the checkout URL
        
        # Simulation
        return {
            "checkout_url": f"https://checkout.stripe.com/pay/cs_test_mock?client_reference_id={req.user_id}",
            "mock_success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{user_id}", response_model=SubscriptionStatus)
async def get_subscription_status(user_id: str):
    """
    Checks if the user has an active subscription.
    """
    try:
        res = supabase.table("subscriptions")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .execute()
            
        if not res.data:
            return SubscriptionStatus(is_active=False, plan="free", expires_at=None)
            
        sub = res.data[0]
        # Parse timestamp safely
        expires = datetime.fromisoformat(sub["current_period_end"].replace("Z", "+00:00"))
        
        return SubscriptionStatus(
            is_active=True, 
            plan=sub["plan_id"],
            expires_at=expires
        )
        
    except Exception as e:
        # Log error in production
        print(f"Sub Check Error: {e}")
        return SubscriptionStatus(is_active=False, plan="free", expires_at=None)

@router.post("/webhook/mock_success")
async def mock_payment_success(user_id: str):
    """
    Internal Dev Tool: Force-activates a subscription for a user.
    Called by the 'Simulate Payment' button in CheckoutView.
    """
    try:
        # Create or Update Subscription
        expires = (datetime.now() + timedelta(days=30)).isoformat()
        
        data = {
            "user_id": user_id,
            "plan_id": "agency_brl_monthly",
            "status": "active",
            "current_period_end": expires,
            "stripe_subscription_id": "sub_mock_12345"
        }
        
        supabase.table("subscriptions").insert(data).execute()
        return {"status": "success", "message": "User upgraded to Agency Plan"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
