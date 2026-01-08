"""
Billing Service
LeadHunter AI - Stripe Integration

Features:
- Subscription management
- Usage-based billing
- Invoice generation
"""
import os
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from backend.utils.logger import logger


# =============================================================================
# PLANS
# =============================================================================

class BillingPlan(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLAN_DETAILS = {
    BillingPlan.FREE: {
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "features": {
            "leads_per_month": 100,
            "clones_per_month": 10,
            "api_requests_per_day": 100,
            "team_members": 1,
            "custom_branding": False,
            "priority_support": False
        }
    },
    BillingPlan.PRO: {
        "name": "Pro",
        "price_monthly": 49,
        "price_yearly": 470,
        "features": {
            "leads_per_month": 1000,
            "clones_per_month": 100,
            "api_requests_per_day": 1000,
            "team_members": 5,
            "custom_branding": True,
            "priority_support": False
        }
    },
    BillingPlan.ENTERPRISE: {
        "name": "Enterprise",
        "price_monthly": 199,
        "price_yearly": 1990,
        "features": {
            "leads_per_month": -1,  # Unlimited
            "clones_per_month": -1,
            "api_requests_per_day": -1,
            "team_members": -1,
            "custom_branding": True,
            "priority_support": True
        }
    }
}


# =============================================================================
# BILLING SERVICE
# =============================================================================

class BillingService:
    """
    Billing and subscription management.
    
    Usage:
        billing = BillingService()
        
        # Get plans
        plans = billing.get_plans()
        
        # Subscribe
        result = await billing.subscribe(
            user_id="user123",
            plan=BillingPlan.PRO
        )
        
        # Check usage
        usage = await billing.get_usage(user_id="user123")
    """
    
    _instance = None
    _subscriptions: Dict[str, Dict] = {}
    _usage: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._subscriptions = {}
        self._usage = {}
        self._stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    
    def is_configured(self) -> bool:
        """Check if Stripe is configured"""
        return bool(self._stripe_key and self._stripe_key.startswith("sk_"))
    
    # =========================================================================
    # PLANS
    # =========================================================================
    
    def get_plans(self) -> List[Dict]:
        """Get available billing plans"""
        return [
            {
                "id": plan.value,
                **PLAN_DETAILS[plan]
            }
            for plan in BillingPlan
        ]
    
    def get_plan(self, plan_id: str) -> Optional[Dict]:
        """Get plan details"""
        try:
            plan = BillingPlan(plan_id)
            return {"id": plan.value, **PLAN_DETAILS[plan]}
        except ValueError:
            return None
    
    # =========================================================================
    # SUBSCRIPTIONS
    # =========================================================================
    
    async def subscribe(
        self,
        user_id: str,
        plan: BillingPlan,
        billing_cycle: str = "monthly"
    ) -> Dict[str, Any]:
        """Create or update subscription"""
        now = datetime.utcnow()
        
        subscription = {
            "id": secrets.token_urlsafe(16),
            "user_id": user_id,
            "plan": plan.value,
            "billing_cycle": billing_cycle,
            "status": "active",
            "created_at": now.isoformat(),
            "current_period_start": now.isoformat(),
            "current_period_end": (
                now + timedelta(days=30 if billing_cycle == "monthly" else 365)
            ).isoformat()
        }
        
        self._subscriptions[user_id] = subscription
        
        # Initialize usage
        self._usage[user_id] = {
            "leads": 0,
            "clones": 0,
            "api_requests": 0,
            "period_start": now.isoformat()
        }
        
        return {"success": True, "subscription": subscription}
    
    async def get_subscription(self, user_id: str) -> Optional[Dict]:
        """Get user's subscription"""
        return self._subscriptions.get(user_id, {
            "plan": "free",
            "status": "active"
        })
    
    async def cancel_subscription(self, user_id: str) -> Dict[str, Any]:
        """Cancel subscription"""
        if user_id in self._subscriptions:
            self._subscriptions[user_id]["status"] = "cancelled"
            self._subscriptions[user_id]["plan"] = "free"
            return {"success": True}
        
        return {"success": False, "error": "No subscription found"}
    
    # =========================================================================
    # USAGE
    # =========================================================================
    
    async def get_usage(self, user_id: str) -> Dict[str, Any]:
        """Get current usage for user"""
        usage = self._usage.get(user_id, {
            "leads": 0,
            "clones": 0,
            "api_requests": 0
        })
        
        subscription = await self.get_subscription(user_id)
        plan_id = subscription.get("plan", "free")
        
        try:
            plan = BillingPlan(plan_id)
            limits = PLAN_DETAILS[plan]["features"]
        except:
            limits = PLAN_DETAILS[BillingPlan.FREE]["features"]
        
        return {
            "usage": usage,
            "limits": limits,
            "plan": plan_id
        }
    
    async def track_usage(
        self,
        user_id: str,
        metric: str,
        amount: int = 1
    ) -> Dict[str, Any]:
        """Track usage for a metric"""
        if user_id not in self._usage:
            self._usage[user_id] = {
                "leads": 0,
                "clones": 0,
                "api_requests": 0
            }
        
        if metric in self._usage[user_id]:
            self._usage[user_id][metric] += amount
        
        # Check if over limit
        usage_data = await self.get_usage(user_id)
        limits = usage_data["limits"]
        current = usage_data["usage"]
        
        # Map metric names to limit names
        metric_map = {
            "leads": "leads_per_month",
            "clones": "clones_per_month",
            "api_requests": "api_requests_per_day"
        }
        
        limit_key = metric_map.get(metric)
        if limit_key and limits.get(limit_key, -1) != -1:
            if current.get(metric, 0) > limits[limit_key]:
                return {"success": False, "error": "Usage limit exceeded"}
        
        return {"success": True, "usage": self._usage[user_id]}
    
    # =========================================================================
    # INVOICES
    # =========================================================================
    
    async def get_invoices(self, user_id: str) -> List[Dict]:
        """Get user's invoices (mock)"""
        # In production, this would fetch from Stripe
        return []


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

billing_service = BillingService()
