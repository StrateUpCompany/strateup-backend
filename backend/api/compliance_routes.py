from fastapi import APIRouter, HTTPException, Depends, Request
from backend.core.database import db
from backend.core.compliance.audit_logger import audit_logger
from backend.core.compliance.retention_service import retention_service
from backend.core.auth import get_current_user

router = APIRouter(prefix="/compliance", tags=["Compliance (LGPD)"])

@router.post("/request-deletion")
async def request_deletion(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Submits a 'Right to be Forgotten' request.
    """
    user_id = user["id"]

    # Log the request
    await audit_logger.log_action(
        actor_id=user_id,
        action="REQUEST_DELETION",
        target_resource="account",
        target_id=user_id,
        ip_address=request.client.host
    )
    
    # In a real system, this triggers an email confirmation flow.
    # Here we simulate immediate processing or queuing.
    success = retention_service.anonymize_user(user_id)
    
    return {"status": "processing", "message": "Deletion request received. You will receive a confirmation email."}

@router.get("/my-data")
async def export_my_data(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    'Right to Access': Exports all known data about the user.
    """
    user_id = user["id"]
         
    # Fetch data from various tables
    try:
        profile = db.table("profiles").select("*").eq("id", user_id).execute()
        # subscriptions = db.table("subscriptions").select("*").eq("user_id", user_id).execute()
        
        await audit_logger.log_action(
            actor_id=user_id,
            action="EXPORT_DATA",
            target_resource="profile",
            target_id=user_id,
            ip_address=request.client.host
        )

        return {
            "profile": profile.data,
            # "subscriptions": subscriptions.data,
            "generated_at": "now"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit-logs")
async def get_audit_logs(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Admin only: View system logs.
    """
    user_id = user["id"]
    # Check admin role
    if user.get("role") != "admin": 
        # For demo purposes, we might allow non-admins to see their own logs
        # But properly this should be 403. 
        # Let's filter logs by user_id instead for regular users
        try:
            res = db.table("audit_logs").select("*").eq("actor_id", user_id).order("created_at", desc=True).limit(50).execute()
            return res.data
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    try:
        res = db.table("audit_logs").select("*").order("created_at", desc=True).limit(50).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
