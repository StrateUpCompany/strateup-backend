"""
Email Routes
LeadHunter AI - Email API

Endpoints:
- POST /api/email/send        - Send email
- POST /api/email/template    - Send using template
- GET  /api/email/templates   - List templates
- POST /api/email/preview     - Preview template
- GET  /api/email/stats       - Get statistics
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from backend.core.email_service import email_service, EmailTemplate


router = APIRouter(prefix="/api/email", tags=["Email"])


# =============================================================================
# MODELS
# =============================================================================

class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    html: str
    reply_to: Optional[str] = None


class SendTemplateRequest(BaseModel):
    to: EmailStr
    template: str
    data: Dict[str, Any]


class PreviewRequest(BaseModel):
    template: str
    data: Dict[str, Any]


class EmailResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/send", response_model=EmailResponse)
async def send_email(request: SendEmailRequest):
    """
    Send a custom email.
    
    Requires SENDGRID_API_KEY to be configured.
    """
    result = await email_service.send(
        to=request.to,
        subject=request.subject,
        html=request.html,
        reply_to=request.reply_to
    )
    
    if result["success"]:
        return EmailResponse(success=True, data=result)
    else:
        return EmailResponse(success=False, error=result.get("error"))


@router.post("/template", response_model=EmailResponse)
async def send_template_email(request: SendTemplateRequest):
    """
    Send an email using a template.
    
    Available templates:
    - welcome
    - lead_nurture
    - proposal
    - weekly_report
    """
    try:
        template = EmailTemplate(request.template)
    except ValueError:
        return EmailResponse(success=False, error=f"Invalid template: {request.template}")
    
    result = await email_service.send_template(
        to=request.to,
        template=template,
        data=request.data
    )
    
    if result["success"]:
        return EmailResponse(success=True, data=result)
    else:
        return EmailResponse(success=False, error=result.get("error"))


@router.get("/templates", response_model=EmailResponse)
async def list_templates():
    """
    List available email templates.
    """
    templates = email_service.get_templates()
    return EmailResponse(success=True, data={"templates": templates})


@router.post("/preview", response_model=EmailResponse)
async def preview_template(request: PreviewRequest):
    """
    Preview a template with sample data.
    """
    try:
        template = EmailTemplate(request.template)
    except ValueError:
        return EmailResponse(success=False, error=f"Invalid template: {request.template}")
    
    preview = email_service.preview_template(template, request.data)
    
    if "error" in preview:
        return EmailResponse(success=False, error=preview["error"])
    else:
        return EmailResponse(success=True, data=preview)


@router.get("/stats", response_model=EmailResponse)
async def get_stats():
    """
    Get email statistics.
    """
    stats = email_service.get_stats()
    return EmailResponse(success=True, data=stats)


@router.get("/config", response_model=EmailResponse)
async def get_config():
    """
    Check email configuration status.
    """
    return EmailResponse(success=True, data={
        "configured": email_service.is_configured(),
        "provider": "SendGrid"
    })
