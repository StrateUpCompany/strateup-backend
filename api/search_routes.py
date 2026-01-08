
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, List
from backend.core.advanced_search import advanced_search
from pydantic import BaseModel

router = APIRouter()

class SearchResponse(BaseModel):
    results: List[Dict]
    total: int
    page: int
    limit: int

@router.get("/leads", response_model=SearchResponse)
async def search_leads(
    q: Optional[str] = None,
    source: Optional[str] = None,
    has_email: Optional[bool] = None,
    has_phone: Optional[bool] = None,
    industry: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """
    Search leads with filters.
    """
    filters = {}
    if source: filters["source"] = source
    if has_email is not None: filters["has_email"] = has_email
    if has_phone is not None: filters["has_phone"] = has_phone
    if industry: filters["industry"] = industry
    
    offset = (page - 1) * limit
    
    result = await advanced_search.search_leads(
        query=q,
        filters=filters,
        limit=limit,
        offset=offset
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result

@router.get("/projects")
async def search_projects(q: str):
    """Search projects by URL or status"""
    return await advanced_search.search_projects(q)
