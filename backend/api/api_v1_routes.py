"""
API v1 Routes - Public API
LeadHunter AI

Endpoints:
- GET  /api/v1/search/instagram/{username}
- GET  /api/v1/search/google-maps
- POST /api/v1/clone/analyze
- GET  /api/v1/usage
- POST /api/v1/keys (generate key)
- GET  /api/v1/keys (list keys)
- DELETE /api/v1/keys/{key_id} (revoke key)
"""
import hashlib
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query, Depends
from pydantic import BaseModel
from backend.utils.logger import logger
from backend.core.api_keys import api_key_manager, validate_api_key, ApiTier
from backend.core.rate_limiter import rate_limiter
from backend.core.apify_client import get_apify_client


router = APIRouter(prefix="/api/v1", tags=["Public API v1"])


# =============================================================================
# MODELS
# =============================================================================

class GenerateKeyRequest(BaseModel):
    name: str = "Default"
    tier: str = "free"


class AnalyzeCloneRequest(BaseModel):
    url: str
    prompt_type: str = "copy_analysis"


class ApiResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


# =============================================================================
# DEPENDENCY: API KEY AUTH + RATE LIMIT
# =============================================================================

async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """
    Dependency to verify API key and check rate limits.
    Returns key info if valid, raises 401/429 otherwise.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Set X-API-Key header."
        )
    
    # Validate key
    key_info = await validate_api_key(x_api_key)
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked API key."
        )
    
    # Check rate limit
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    tier = key_info["tier"].value if isinstance(key_info["tier"], ApiTier) else key_info["tier"]
    
    allowed, limit_info = rate_limiter.check(key_hash, tier)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded.",
            headers={
                "X-RateLimit-Limit": str(limit_info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": limit_info["resets_at"],
                "Retry-After": str(limit_info["retry_after"])
            }
        )
    
    # Add rate limit headers to response
    key_info["_rate_limit"] = limit_info
    key_info["_key_hash"] = key_hash
    
    return key_info


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@router.get("/search/instagram/{username}", response_model=ApiResponse)
async def search_instagram(
    username: str,
    key_info: dict = Depends(verify_api_key)
):
    """
    Search Instagram profile by username.
    
    Returns profile data including:
    - username, fullName, biography
    - followersCount, followsCount, postsCount
    - profilePicUrl, externalUrl
    - email, phone (if in bio)
    """
    try:
        client = get_apify_client()
        result = await client.scrape_instagram_profile(username)
        
        if result.get("success"):
            return ApiResponse(success=True, data=result["profile"])
        else:
            return ApiResponse(success=False, error=result.get("error", "Not found"))
    
    except Exception as e:
        logger.error(f"Instagram search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/google-maps", response_model=ApiResponse)
async def search_google_maps(
    query: str = Query(..., description="Search query (e.g., 'pizzaria')"),
    location: str = Query("Brazil", description="Location (e.g., 'São Paulo')"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    min_rating: float = Query(0.0, ge=0, le=5, description="Minimum rating"),
    min_reviews: int = Query(0, ge=0, description="Minimum reviews"),
    key_info: dict = Depends(verify_api_key)
):
    """
    Search businesses on Google Maps.
    
    Returns list of businesses with:
    - name, address, phone, website
    - rating, reviewsCount, category
    - placeId, url
    """
    try:
        client = get_apify_client()
        result = await client.search_google_maps(
            query=query,
            location=location,
            limit=limit,
            min_rating=min_rating,
            min_reviews=min_reviews
        )
        
        if result.get("success"):
            return ApiResponse(success=True, data={"businesses": result["businesses"]})
        else:
            return ApiResponse(success=False, error=result.get("error", "Search failed"))
    
    except Exception as e:
        logger.error(f"Google Maps search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CLONE ENDPOINTS
# =============================================================================

@router.post("/clone/analyze", response_model=ApiResponse)
async def analyze_clone(
    request: AnalyzeCloneRequest,
    key_info: dict = Depends(verify_api_key)
):
    """
    Analyze a webpage/funnel with AI.
    
    Prompt types:
    - copy_analysis: Analyze copywriting
    - funnel_strategy: Analyze funnel strategy
    - funnel_critique: Critique funnel flow
    - swipe_rewrite: Extract copy structure
    """
    try:
        from backend.core.engine import Engine
        from backend.core.ai_manager import AIManager
        
        # Clone the page
        engine = Engine()
        clone_result = engine.clone_url(request.url)
        
        if not clone_result.get("success"):
            return ApiResponse(success=False, error="Failed to clone URL")
        
        # Analyze with AI
        ai = AIManager()
        text = clone_result.get("text_content", "")[:15000]
        analysis = ai.analyze_text(text, request.prompt_type)
        
        return ApiResponse(success=True, data={
            "url": request.url,
            "prompt_type": request.prompt_type,
            "analysis": analysis
        })
    
    except Exception as e:
        logger.error(f"Clone analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# USAGE & KEYS ENDPOINTS
# =============================================================================

@router.get("/usage", response_model=ApiResponse)
async def get_usage(
    x_api_key: str = Header(..., alias="X-API-Key"),
    key_info: dict = Depends(verify_api_key)
):
    """
    Get API usage statistics.
    
    Returns:
    - requests_today: Current request count
    - daily_limit: Your tier's daily limit
    - remaining: Remaining requests today
    - resets_at: When the limit resets (UTC)
    """
    usage = await api_key_manager.get_key_usage(x_api_key)
    return ApiResponse(success=True, data=usage)


@router.post("/keys", response_model=ApiResponse)
async def create_api_key(
    request: GenerateKeyRequest,
    # In production, this should require user authentication
    user_id: str = Query("demo-user", description="User ID")
):
    """
    Generate a new API key.
    
    **Important**: The full key is only returned once. Store it securely.
    """
    try:
        tier = ApiTier(request.tier) if request.tier in [t.value for t in ApiTier] else ApiTier.FREE
        result = await api_key_manager.generate_key(
            user_id=user_id,
            tier=tier,
            name=request.name
        )
        return ApiResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Key generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys", response_model=ApiResponse)
async def list_api_keys(
    user_id: str = Query("demo-user", description="User ID")
):
    """
    List all API keys for a user.
    
    Note: Only key prefixes are shown for security.
    """
    try:
        keys = await api_key_manager.list_keys(user_id)
        return ApiResponse(success=True, data={"keys": keys})
    except Exception as e:
        logger.error(f"List keys error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/keys/{key_prefix}", response_model=ApiResponse)
async def revoke_api_key(
    key_prefix: str,
    full_key: str = Query(..., description="Full API key to revoke")
):
    """
    Revoke an API key.
    
    Requires the full key for security.
    """
    try:
        success = await api_key_manager.revoke_key(full_key)
        if success:
            return ApiResponse(success=True, data={"message": "Key revoked"})
        else:
            return ApiResponse(success=False, error="Key not found")
    except Exception as e:
        logger.error(f"Revoke key error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
