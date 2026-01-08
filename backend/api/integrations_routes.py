"""
Integrations Routes
LeadHunter AI - Marketplace API

Endpoints:
- GET  /api/integrations/templates     - List templates
- GET  /api/integrations/categories    - List categories
- POST /api/integrations               - Create integration
- GET  /api/integrations               - List user integrations
- PUT  /api/integrations/:id/toggle    - Toggle on/off
- DELETE /api/integrations/:id         - Delete
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.core.integrations import integrations_service
from backend.core.auth import get_current_user


router = APIRouter(prefix="/api/integrations", tags=["Integrations"])


# =============================================================================
# MODELS
# =============================================================================

class CreateIntegrationRequest(BaseModel):
    template_id: str
    webhook_url: str
    config: Optional[Dict] = None


class IntegrationResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/templates", response_model=IntegrationResponse)
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """List available automation templates"""
    templates = integrations_service.get_templates(category)
    return IntegrationResponse(success=True, data={"templates": templates})


@router.get("/categories", response_model=IntegrationResponse)
async def list_categories():
    """List available categories"""
    categories = integrations_service.get_categories()
    return IntegrationResponse(success=True, data={"categories": categories})


@router.post("", response_model=IntegrationResponse)
async def create_integration(
    request: CreateIntegrationRequest,
    user: Dict = Depends(get_current_user)
):
    """Create a new integration from template"""
    result = await integrations_service.create_integration(
        user_id=user["id"],
        template_id=request.template_id,
        webhook_url=request.webhook_url,
        config=request.config
    )
    
    if result["success"]:
        return IntegrationResponse(success=True, data=result["integration"])
    else:
        return IntegrationResponse(success=False, error=result.get("error"))


@router.get("", response_model=IntegrationResponse)
async def list_integrations(user: Dict = Depends(get_current_user)):
    """List user's integrations"""
    integrations = await integrations_service.list_user_integrations(user["id"])
    return IntegrationResponse(success=True, data={"integrations": integrations})


@router.put("/{integration_id}/toggle", response_model=IntegrationResponse)
async def toggle_integration(
    integration_id: str,
    user: Dict = Depends(get_current_user)
):
    """Toggle integration on/off"""
    result = await integrations_service.toggle_integration(user["id"], integration_id)
    
    if result["success"]:
        return IntegrationResponse(success=True, data=result)
    else:
        return IntegrationResponse(success=False, error=result.get("error"))


@router.delete("/{integration_id}", response_model=IntegrationResponse)
async def delete_integration(
    integration_id: str,
    user: Dict = Depends(get_current_user)
):
    """Delete an integration"""
    result = await integrations_service.delete_integration(user["id"], integration_id)
    
    if result["success"]:
        return IntegrationResponse(success=True, data={"message": "Deleted"})
    else:
        return IntegrationResponse(success=False, error=result.get("error"))
