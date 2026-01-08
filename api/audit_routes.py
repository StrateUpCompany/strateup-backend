"""
Audit Routes
LeadHunter AI - Audit API

Endpoints:
- GET /api/audit/logs       - List logs with filters
- GET /api/audit/logs/{id}  - Get log details
- GET /api/audit/export     - Export as CSV
- GET /api/audit/stats      - Get statistics
"""
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.core.audit_log import audit_logger, AuditAction


router = APIRouter(prefix="/api/audit", tags=["Audit"])


# =============================================================================
# MODELS
# =============================================================================

class LogsResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    total: int


class StatsResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


class LogDetailResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/logs", response_model=LogsResponse)
async def list_logs(
    user_id: Optional[str] = Query(None, description="Filter by user"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    days: int = Query(7, ge=1, le=90, description="Days to look back"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    List audit logs with filters.
    """
    logs = await audit_logger.query(
        user_id=user_id,
        action=action,
        resource=resource,
        days=days,
        limit=limit,
        offset=offset
    )
    
    return LogsResponse(success=True, data=logs, total=len(logs))


@router.get("/logs/{log_id}", response_model=LogDetailResponse)
async def get_log(log_id: str):
    """
    Get a specific log entry by ID.
    """
    log = await audit_logger.get_log(log_id)
    
    if log:
        return LogDetailResponse(success=True, data=log)
    else:
        return LogDetailResponse(success=False, error="Log not found")


@router.get("/export")
async def export_logs(
    user_id: Optional[str] = Query(None, description="Filter by user"),
    days: int = Query(30, ge=1, le=365, description="Days to export")
):
    """
    Export audit logs as CSV.
    """
    csv_content = await audit_logger.export_csv(user_id=user_id, days=days)
    
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_logs_{days}d.csv"}
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    days: int = Query(7, ge=1, le=90, description="Stats period")
):
    """
    Get audit statistics.
    """
    stats = await audit_logger.get_stats(days=days)
    return StatsResponse(success=True, data=stats)


@router.get("/actions")
async def list_actions():
    """
    List all available audit actions.
    """
    actions = [
        {"id": a.value, "name": a.value.replace(".", " ").replace("_", " ").title()}
        for a in AuditAction
    ]
    return {"success": True, "data": actions}
