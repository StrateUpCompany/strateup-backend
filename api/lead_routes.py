
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.core.email_client import EmailClient
from backend.core.database import db as supabase
import os

router = APIRouter(prefix="/leads", tags=["Leads"])

# Init Supabase (Now imported from core)
# url: str = os.getenv("SUPABASE_URL")
# key: str = os.getenv("SUPABASE_SERVICE_KEY")
# supabase: Client = create_client(url, key)

email_client = EmailClient()

class LeadCreate(BaseModel):
    email: str
    source: Optional[str] = "unknown"
    notes: Optional[str] = None

@router.post("/")
async def create_lead(lead: LeadCreate):
    try:
        # 1. Save to Supabase
        data = {
            "email": lead.email,
            "source": lead.source,
            "status": "new",
            "meta_data": {"notes": lead.notes} 
        }
        # Assuming 'leads' table exists. If not, we need to create it.
        # Check if lead exists first to avoid duplicates
        existing = supabase.table("leads").select("*").eq("email", lead.email).execute()
        
        if not existing.data:
            supabase.table("leads").insert(data).execute()
        else:
            # Update source/notes if needed, or just proceed
            pass
            
        # 2. Trigger Welcome Email (Day 0)
        # We fire and forget here (or await if critical)
        try:
            email_client.send_welcome_sequence(lead.email)
        except Exception as e:
            print(f"Failed to send welcome email: {e}")

        return {"message": "Lead captured and email queued", "success": True}

    except Exception as e:
        print(f"Error creating lead: {e}")
        # Return success anyway to not block the UI if DB fails (fail-safe)
        # But for debugging we might want to know.
        raise HTTPException(status_code=500, detail=str(e))
