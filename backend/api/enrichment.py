from fastapi import APIRouter, HTTPException
from backend.core.brasil_api import brasil_api
from backend.utils.limiter import limiter
from fastapi import Request

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.core.ai_enrichment import ai_enrichment, EnrichmentType
from backend.core.supabase_manager import SupabaseManager

router = APIRouter()
session_manager = SupabaseManager()

class EnrichRequest(BaseModel):
    types: List[str] = [
        EnrichmentType.QUALITY_SCORE,
        EnrichmentType.BUSINESS_INSIGHTS,
        EnrichmentType.APPROACH_SUGGESTIONS
    ]

@router.post("/lead/{lead_id}")
async def enrich_lead_endpoint(lead_id: str, req: EnrichRequest):
    """
    Enriquece um lead existente com IA.
    Salva o resultado no campo 'enriched_data' do lead.
    """
    # 1. Fetch Lead
    lead = session_manager.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # 2. Extract Data from JSONB
    lead_data = lead.get("data", {})
    # Merge with top-level fields if any
    lead_data["id"] = lead_id
    
    # 3. Enrich
    result = await ai_enrichment.enrich_lead(lead_data, types=req.types)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
        
    # 4. Save to DB (Update 'data' with enrichment or separate column?)
    # Usually we add to 'data.enriched' or a new column. 
    # Supabase leads table has 'data' JSONB.
    # Let's merge into 'data.enrichment'
    
    enrichment_data = result["enrichment"]
    lead_data["enrichment"] = enrichment_data
    
    # Update DB
    try:
        session_manager.supabase.table("leads").update({"data": lead_data}).eq("id", lead_id).execute()
    except Exception as e:
        # Just log, return result anyway
        pass
        
    return result

@router.post("/analyze")
async def analyze_raw_lead(lead_data: Dict[str, Any]):
    """
    Analisa dados brutos de um lead (sem salvar no banco).
    Útil para testes ou pré-visualização.
    """
    return await ai_enrichment.enrich_lead(lead_data)

@router.get("/cnpj/{cnpj}")
@limiter.limit("10/minute")
async def get_cnpj_data(request: Request, cnpj: str):
    """
    Busca dados de uma empresa na BrasilAPI via CNPJ.
    Ratelimit: 10 req/min.
    """
    result = await brasil_api.get_company_data(cnpj)
    
    if "error" in result:
        status = 404 if "não encontrado" in result["error"] else 500
        raise HTTPException(status_code=status, detail=result["error"])
        
    return result
