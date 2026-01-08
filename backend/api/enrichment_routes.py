"""
AI Enrichment Routes
LeadHunter AI - Lead Enrichment API

Endpoints:
- POST /api/enrichment/lead      - Enrich single lead
- POST /api/enrichment/batch     - Batch enrich leads
- GET  /api/enrichment/stats     - Get stats
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.core.ai_enrichment import ai_enrichment
from backend.core.auth import get_current_user


router = APIRouter(prefix="/api/enrichment", tags=["AI Enrichment"])


# =============================================================================
# MODELS
# =============================================================================

class EnrichLeadRequest(BaseModel):
    lead: Dict[str, Any]
    types: Optional[List[str]] = None


class BatchEnrichRequest(BaseModel):
    leads: List[Dict[str, Any]]
    types: Optional[List[str]] = None


class EnrichmentResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/lead", response_model=EnrichmentResponse)
async def enrich_lead(
    request: EnrichLeadRequest,
    user: Dict = Depends(get_current_user)
):
    """Enrich a single lead with AI analysis"""
    result = await ai_enrichment.enrich_lead(
        lead=request.lead,
        types=request.types
    )
    
    if result["success"]:
        return EnrichmentResponse(success=True, data=result["enrichment"])
    else:
        return EnrichmentResponse(success=False, error=result.get("error"))


@router.post("/batch", response_model=EnrichmentResponse)
async def batch_enrich(
    request: BatchEnrichRequest,
    user: Dict = Depends(get_current_user)
):
    """Batch enrich multiple leads"""
    result = await ai_enrichment.batch_enrich(
        leads=request.leads,
        types=request.types
    )
    
    return EnrichmentResponse(success=True, data=result)


@router.get("/stats", response_model=EnrichmentResponse)
async def get_stats():
    """Get enrichment statistics"""
    stats = ai_enrichment.get_stats()
    return EnrichmentResponse(success=True, data=stats)


@router.post("/clear-cache", response_model=EnrichmentResponse)
async def clear_cache(user: Dict = Depends(get_current_user)):
    """Clear enrichment cache"""
    ai_enrichment.clear_cache()
    return EnrichmentResponse(success=True, data={"message": "Cache cleared"})
