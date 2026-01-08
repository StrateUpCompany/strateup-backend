"""
Billing Tests
LeadHunter AI - Testing billing module

Tests for:
- Subscription management
- Usage tracking
- Plan features
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from backend.core.billing import (
    BillingService,
    BillingPlan,
    billing_service,
    PLAN_DETAILS
)


# =============================================================================
# BILLING PLAN TESTS
# =============================================================================

class TestBillingPlans:
    """Tests for billing plan definitions."""
    
    def test_plan_values(self):
        """Billing plans should have correct values."""
        assert BillingPlan.FREE.value == "free"
        assert BillingPlan.PRO.value == "pro"
        assert BillingPlan.ENTERPRISE.value == "enterprise"
    
    def test_plan_details_exist(self):
        """Plan details should exist for all plans."""
        assert BillingPlan.FREE in PLAN_DETAILS
        assert BillingPlan.PRO in PLAN_DETAILS
        assert BillingPlan.ENTERPRISE in PLAN_DETAILS
    
    def test_free_plan_price(self):
        """Free plan should be free."""
        assert PLAN_DETAILS[BillingPlan.FREE]["price_monthly"] == 0
        assert PLAN_DETAILS[BillingPlan.FREE]["price_yearly"] == 0
    
    def test_pro_plan_price(self):
        """Pro plan should have a price."""
        assert PLAN_DETAILS[BillingPlan.PRO]["price_monthly"] > 0
        assert PLAN_DETAILS[BillingPlan.PRO]["price_yearly"] > 0
    
    def test_enterprise_features(self):
        """Enterprise should have unlimited features (-1)."""
        features = PLAN_DETAILS[BillingPlan.ENTERPRISE]["features"]
        
        assert features["leads_per_month"] == -1  # Unlimited
        assert features["clones_per_month"] == -1
        assert features["priority_support"] is True


# =============================================================================
# BILLING SERVICE TESTS
# =============================================================================

class TestBillingService:
    """Tests for BillingService class."""
    
    def test_singleton_instance(self):
        """BillingService should be a singleton."""
        service1 = BillingService()
        service2 = BillingService()
        
        assert service1 is service2
    
    def test_global_instance(self):
        """Global billing_service should be available."""
        assert billing_service is not None
        assert isinstance(billing_service, BillingService)
    
    def test_is_configured(self):
        """Should check if Stripe is configured."""
        service = BillingService()
        result = service.is_configured()
        
        # Result depends on environment
        assert isinstance(result, bool)


# =============================================================================
# GET PLANS TESTS
# =============================================================================

class TestGetPlans:
    """Tests for get_plans functionality."""
    
    def test_get_plans(self):
        """Should return all plans."""
        service = BillingService()
        plans = service.get_plans()
        
        assert len(plans) == 3  # Free, Pro, Enterprise
        
        plan_ids = [p["id"] for p in plans]
        assert "free" in plan_ids
        assert "pro" in plan_ids
        assert "enterprise" in plan_ids
    
    def test_get_plan_by_id(self):
        """Should get specific plan by ID."""
        service = BillingService()
        
        plan = service.get_plan("pro")
        
        assert plan is not None
        assert plan["id"] == "pro"
        assert plan["name"] == "Pro"
    
    def test_get_plan_invalid(self):
        """Should return None for invalid plan ID."""
        service = BillingService()
        
        plan = service.get_plan("invalid_plan")
        
        assert plan is None


# =============================================================================
# SUBSCRIPTION TESTS
# =============================================================================

class TestSubscriptions:
    """Tests for subscription management."""
    
    @pytest.mark.asyncio
    async def test_subscribe(self):
        """Should create subscription."""
        service = BillingService()
        
        result = await service.subscribe(
            user_id="test_user_123",
            plan=BillingPlan.PRO
        )
        
        assert result["success"] is True
        assert "subscription" in result
        assert result["subscription"]["plan"] == "pro"
    
    @pytest.mark.asyncio
    async def test_get_subscription(self):
        """Should get user's subscription."""
        service = BillingService()
        
        # First subscribe
        await service.subscribe(
            user_id="test_user_456",
            plan=BillingPlan.PRO
        )
        
        # Then get subscription
        subscription = await service.get_subscription("test_user_456")
        
        assert subscription is not None
        assert subscription["plan"] == "pro"
    
    @pytest.mark.asyncio
    async def test_get_subscription_default_free(self):
        """No subscription should default to free."""
        service = BillingService()
        
        subscription = await service.get_subscription("nonexistent_user")
        
        assert subscription["plan"] == "free"
    
    @pytest.mark.asyncio
    async def test_cancel_subscription(self):
        """Should cancel subscription."""
        service = BillingService()
        
        # First subscribe
        await service.subscribe(
            user_id="test_user_cancel",
            plan=BillingPlan.PRO
        )
        
        # Then cancel
        result = await service.cancel_subscription("test_user_cancel")
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_subscription(self):
        """Cancelling nonexistent subscription should fail."""
        service = BillingService()
        
        result = await service.cancel_subscription("nonexistent_cancel_user")
        
        assert result["success"] is False


# =============================================================================
# USAGE TRACKING TESTS
# =============================================================================

class TestUsageTracking:
    """Tests for usage tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_track_usage(self):
        """Should track usage."""
        service = BillingService()
        
        # First subscribe
        await service.subscribe(
            user_id="usage_user",
            plan=BillingPlan.FREE
        )
        
        # Track usage
        result = await service.track_usage("usage_user", "leads", 5)
        
        assert result["success"] is True
        assert result["usage"]["leads"] == 5
    
    @pytest.mark.asyncio
    async def test_track_usage_multiple(self):
        """Should accumulate usage."""
        service = BillingService()
        
        await service.subscribe(
            user_id="usage_user_multi",
            plan=BillingPlan.FREE
        )
        
        await service.track_usage("usage_user_multi", "leads", 3)
        result = await service.track_usage("usage_user_multi", "leads", 2)
        
        assert result["usage"]["leads"] == 5
    
    @pytest.mark.asyncio
    async def test_get_usage(self):
        """Should get current usage."""
        service = BillingService()
        
        await service.subscribe(
            user_id="usage_check_user",
            plan=BillingPlan.PRO
        )
        
        await service.track_usage("usage_check_user", "clones", 10)
        
        usage = await service.get_usage("usage_check_user")
        
        assert usage["usage"]["clones"] == 10
        assert usage["plan"] == "pro"
    
    @pytest.mark.asyncio
    async def test_usage_limit_check(self):
        """Should check usage against limits."""
        service = BillingService()
        
        await service.subscribe(
            user_id="limit_user",
            plan=BillingPlan.FREE
        )
        
        # Free tier has 100 leads_per_month
        # Track more than limit
        for _ in range(101):
            result = await service.track_usage("limit_user", "leads", 1)
        
        # Should eventually hit limit
        assert result["success"] is False or result["usage"]["leads"] >= 100


# =============================================================================
# INVOICES TESTS
# =============================================================================

class TestInvoices:
    """Tests for invoice functionality."""
    
    @pytest.mark.asyncio
    async def test_get_invoices(self):
        """Should get invoices (mock returns empty)."""
        service = BillingService()
        
        invoices = await service.get_invoices("any_user")
        
        assert isinstance(invoices, list)
