
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from backend.core.export_service import export_service
from backend.core.advanced_search import advanced_search
import io

router = APIRouter()

@router.get("/leads")
async def export_leads(
    q: str = None,
    source: str = None,
    industry: str = None,
    format: str = "csv"
):
    """
    Export leads matching filters.
    Format: csv, xlsx, json
    """
    # Reuse Search Logic to get filtered data
    # Increase limit for export (e.g. 1000 or unlimited? careful with memory)
    limit = 1000 
    
    filters = {}
    if source: filters["source"] = source
    if industry: filters["industry"] = industry
    
    result = await advanced_search.search_leads(
        query=q,
        filters=filters,
        limit=limit
    )
    
    data = result.get("results", [])
    
    if not data:
        raise HTTPException(status_code=404, detail="No leads found to export")
        
    filename = f"leads_export.{format}"
    
    if format == "csv":
        csv_str = export_service.export_to_csv(data)
        return StreamingResponse(
            io.StringIO(csv_str),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    elif format == "json":
        json_str = export_service.export_to_json(data)
        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    elif format == "xlsx":
        excel_bytes = export_service.export_to_excel(data)
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format")
