"""
Tenant Routes
LeadHunter AI - White-label API

Endpoints:
- POST /api/tenant/organizations     - Create org
- GET  /api/tenant/organizations     - List user orgs
- GET  /api/tenant/organizations/:id - Get org
- PUT  /api/tenant/branding          - Update branding
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.core.tenant import tenant_service
from backend.core.auth import get_current_user


router = APIRouter(prefix="/api/tenant", tags=["Tenant"])


# =============================================================================
# MODELS
# =============================================================================

class CreateOrgRequest(BaseModel):
    name: str
    branding: Optional[Dict] = None


class UpdateBrandingRequest(BaseModel):
    org_id: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None


class TenantResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/organizations", response_model=TenantResponse)
async def create_organization(
    request: CreateOrgRequest,
    user: Dict = Depends(get_current_user)
):
    """Create a new organization"""
    result = await tenant_service.create_organization(
        name=request.name,
        owner_id=user["id"],
        branding=request.branding
    )
    
    if result["success"]:
        return TenantResponse(success=True, data=result["organization"])
    else:
        return TenantResponse(success=False, error=result.get("error"))


@router.get("/organizations", response_model=TenantResponse)
async def list_organizations(user: Dict = Depends(get_current_user)):
    """List all organizations for current user"""
    orgs = await tenant_service.get_user_organizations(user["id"])
    return TenantResponse(success=True, data={"organizations": orgs})


@router.get("/organizations/{org_id}", response_model=TenantResponse)
async def get_organization(org_id: str):
    """Get organization by ID"""
    org = await tenant_service.get_organization(org_id)
    
    if org:
        return TenantResponse(success=True, data=org)
    else:
        return TenantResponse(success=False, error="Organization not found")


@router.get("/subdomain/{subdomain}", response_model=TenantResponse)
async def get_by_subdomain(subdomain: str):
    """Get organization by subdomain (public)"""
    org = await tenant_service.get_by_subdomain(subdomain)
    
    if org:
        # Return only public branding info
        public_data = {
            "name": org["name"],
            "slug": org["slug"],
            "branding": org.get("branding", {})
        }
        return TenantResponse(success=True, data=public_data)
    else:
        return TenantResponse(success=False, error="Not found")


@router.put("/branding", response_model=TenantResponse)
async def update_branding(
    request: UpdateBrandingRequest,
    user: Dict = Depends(get_current_user)
):
    """Update organization branding"""
    branding = {}
    if request.logo_url:
        branding["logo_url"] = request.logo_url
    if request.primary_color:
        branding["primary_color"] = request.primary_color
    if request.secondary_color:
        branding["secondary_color"] = request.secondary_color
    
    result = await tenant_service.update_branding(
        org_id=request.org_id,
        branding=branding
    )
    
    if result["success"]:
        return TenantResponse(success=True, data=result)
    else:
        return TenantResponse(success=False, error=result.get("error"))


@router.post("/organizations/{org_id}/members/{user_id}", response_model=TenantResponse)
async def add_member(
    org_id: str,
    user_id: str,
    user: Dict = Depends(get_current_user)
):
    """Add member to organization"""
    result = await tenant_service.add_member(org_id, user_id)
    
    if result["success"]:
        return TenantResponse(success=True, data=result)
    else:
        return TenantResponse(success=False, error=result.get("error"))
