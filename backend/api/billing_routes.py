"""
Billing Routes
LeadHunter AI - Billing API

Endpoints:
- GET  /api/billing/plans         - List plans
- GET  /api/billing/subscription  - Get current subscription
- POST /api/billing/subscribe     - Subscribe to plan
- POST /api/billing/cancel        - Cancel subscription
- GET  /api/billing/usage         - Get usage stats
- GET  /api/billing/invoices      - Get invoices
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.core.billing import billing_service, BillingPlan
from backend.core.auth import get_current_user


router = APIRouter(prefix="/api/billing", tags=["Billing"])


# =============================================================================
# MODELS
# =============================================================================

class SubscribeRequest(BaseModel):
    plan: str
    billing_cycle: str = "monthly"


class BillingResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/plans", response_model=BillingResponse)
async def list_plans():
    """List available billing plans"""
    plans = billing_service.get_plans()
    return BillingResponse(success=True, data={"plans": plans})


@router.get("/subscription", response_model=BillingResponse)
async def get_subscription(user: Dict = Depends(get_current_user)):
    """Get current user's subscription"""
    subscription = await billing_service.get_subscription(user["id"])
    return BillingResponse(success=True, data={"subscription": subscription})


@router.post("/subscribe", response_model=BillingResponse)
async def subscribe(
    request: SubscribeRequest,
    user: Dict = Depends(get_current_user)
):
    """Subscribe to a plan"""
    try:
        plan = BillingPlan(request.plan)
    except ValueError:
        return BillingResponse(success=False, error=f"Invalid plan: {request.plan}")
    
    result = await billing_service.subscribe(
        user_id=user["id"],
        plan=plan,
        billing_cycle=request.billing_cycle
    )
    
    if result["success"]:
        return BillingResponse(success=True, data=result)
    else:
        return BillingResponse(success=False, error=result.get("error"))


@router.post("/cancel", response_model=BillingResponse)
async def cancel_subscription(user: Dict = Depends(get_current_user)):
    """Cancel subscription"""
    result = await billing_service.cancel_subscription(user["id"])
    
    if result["success"]:
        return BillingResponse(success=True, data={"message": "Subscription cancelled"})
    else:
        return BillingResponse(success=False, error=result.get("error"))


@router.get("/usage", response_model=BillingResponse)
async def get_usage(user: Dict = Depends(get_current_user)):
    """Get current usage stats"""
    usage = await billing_service.get_usage(user["id"])
    return BillingResponse(success=True, data=usage)


@router.get("/invoices", response_model=BillingResponse)
async def get_invoices(user: Dict = Depends(get_current_user)):
    """Get user's invoices"""
    invoices = await billing_service.get_invoices(user["id"])
    return BillingResponse(success=True, data={"invoices": invoices})
