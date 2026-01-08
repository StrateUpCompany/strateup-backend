"""
Email Service
LeadHunter AI - Email Marketing Integration

Features:
- Send emails via SendGrid
- Template-based emails
- Tracking and stats
"""
import os
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from backend.utils.logger import logger


# =============================================================================
# EMAIL TEMPLATES
# =============================================================================

class EmailTemplate(Enum):
    WELCOME = "welcome"
    LEAD_NURTURE = "lead_nurture"
    PROPOSAL = "proposal"
    WEEKLY_REPORT = "weekly_report"
    CUSTOM = "custom"


TEMPLATES = {
    EmailTemplate.WELCOME: {
        "subject": "Bem-vindo ao LeadHunter AI! 🚀",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #06b6d4;">Bem-vindo ao LeadHunter AI!</h1>
            <p>Olá <strong>{{name}}</strong>,</p>
            <p>Sua conta foi criada com sucesso. Agora você tem acesso a:</p>
            <ul>
                <li>🔍 Data Hunter - Encontre leads qualificados</li>
                <li>🎯 Funnel Cloner - Clone páginas de alta conversão</li>
                <li>🤖 AI Analysis - Análise inteligente de copy</li>
            </ul>
            <p><a href="{{dashboard_url}}" style="background: #06b6d4; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">Acessar Dashboard</a></p>
            <p style="color: #666; font-size: 12px;">LeadHunter AI - Sua máquina de geração de leads</p>
        </div>
        """
    },
    EmailTemplate.LEAD_NURTURE: {
        "subject": "{{company_name}} - Temos uma proposta para você",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">Olá {{contact_name}},</h2>
            <p>Encontramos seu perfil através do {{source}} e acreditamos que podemos ajudar {{company_name}}.</p>
            <p>{{custom_message}}</p>
            <p><a href="{{cta_url}}" style="background: #8b5cf6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">{{cta_text}}</a></p>
            <p style="color: #666;">{{sender_name}}<br>{{sender_company}}</p>
        </div>
        """
    },
    EmailTemplate.PROPOSAL: {
        "subject": "Proposta Comercial - {{service_name}}",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #06b6d4;">Proposta Comercial</h1>
            <p>Prezado(a) <strong>{{client_name}}</strong>,</p>
            <p>Conforme nossa conversa, segue proposta para {{service_name}}:</p>
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0;">Investimento: {{price}}</h3>
                <p style="margin: 0;">{{description}}</p>
            </div>
            <p>{{closing_message}}</p>
            <p><a href="{{accept_url}}" style="background: #22c55e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">Aceitar Proposta</a></p>
        </div>
        """
    },
    EmailTemplate.WEEKLY_REPORT: {
        "subject": "📊 Relatório Semanal - {{week}}",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #06b6d4;">Relatório Semanal</h1>
            <p>Olá {{name}}, aqui está seu resumo da semana:</p>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #22c55e;">{{leads_count}}</div>
                    <div style="font-size: 12px; color: #666;">Leads</div>
                </div>
                <div style="background: #f0f9ff; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #06b6d4;">{{clones_count}}</div>
                    <div style="font-size: 12px; color: #666;">Clones</div>
                </div>
                <div style="background: #faf5ff; padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #8b5cf6;">{{api_calls}}</div>
                    <div style="font-size: 12px; color: #666;">API Calls</div>
                </div>
            </div>
            <p style="margin-top: 20px;"><a href="{{dashboard_url}}" style="color: #06b6d4;">Ver detalhes no dashboard →</a></p>
        </div>
        """
    }
}


# =============================================================================
# EMAIL SERVICE
# =============================================================================

class EmailService:
    """
    Email service using SendGrid.
    
    Usage:
        email = EmailService()
        
        # Send simple email
        await email.send(
            to="user@example.com",
            subject="Hello",
            html="<p>World</p>"
        )
        
        # Send template email
        await email.send_template(
            to="user@example.com",
            template=EmailTemplate.WELCOME,
            data={"name": "John"}
        )
    """
    
    SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
    
    _instance = None
    _stats: Dict[str, int] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._api_key = os.getenv("SENDGRID_API_KEY", "")
        self._from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@leadhunter.ai")
        self._from_name = os.getenv("SENDGRID_FROM_NAME", "LeadHunter AI")
        self._stats = {"sent": 0, "failed": 0}
        self._http_client = httpx.AsyncClient(timeout=30)
    
    def is_configured(self) -> bool:
        """Check if SendGrid is configured"""
        return bool(self._api_key and self._api_key.startswith("SG."))
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Simple template rendering with {{variable}} syntax"""
        result = template
        for key, value in data.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
    
    # =========================================================================
    # SEND METHODS
    # =========================================================================
    
    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        from_email: str = None,
        from_name: str = None,
        reply_to: str = None,
        cc: List[str] = None,
        bcc: List[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to: Recipient email
            subject: Email subject
            html: HTML content
            from_email: Sender email (optional)
            from_name: Sender name (optional)
            reply_to: Reply-to email (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
        
        Returns:
            {"success": bool, "message_id": str or None, "error": str or None}
        """
        if not self.is_configured():
            logger.warning("SendGrid not configured, email not sent")
            return {
                "success": False,
                "error": "SendGrid not configured. Set SENDGRID_API_KEY in .env"
            }
        
        payload = {
            "personalizations": [{
                "to": [{"email": to}],
                "subject": subject
            }],
            "from": {
                "email": from_email or self._from_email,
                "name": from_name or self._from_name
            },
            "content": [{"type": "text/html", "value": html}]
        }
        
        if cc:
            payload["personalizations"][0]["cc"] = [{"email": e} for e in cc]
        if bcc:
            payload["personalizations"][0]["bcc"] = [{"email": e} for e in bcc]
        if reply_to:
            payload["reply_to"] = {"email": reply_to}
        
        try:
            response = await self._http_client.post(
                self.SENDGRID_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code in [200, 201, 202]:
                self._stats["sent"] += 1
                message_id = response.headers.get("X-Message-Id", "")
                logger.info(f"Email sent to {to}: {subject}")
                return {"success": True, "message_id": message_id}
            else:
                self._stats["failed"] += 1
                error = response.text
                logger.error(f"SendGrid error: {error}")
                return {"success": False, "error": error}
                
        except Exception as e:
            self._stats["failed"] += 1
            logger.error(f"Email send error: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_template(
        self,
        to: str,
        template: EmailTemplate,
        data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an email using a template.
        
        Args:
            to: Recipient email
            template: Template type
            data: Template variables
            **kwargs: Additional send() arguments
        
        Returns:
            {"success": bool, "message_id": str or None, "error": str or None}
        """
        if template not in TEMPLATES:
            return {"success": False, "error": f"Template not found: {template}"}
        
        tpl = TEMPLATES[template]
        subject = self._render_template(tpl["subject"], data)
        html = self._render_template(tpl["html"], data)
        
        return await self.send(to=to, subject=subject, html=html, **kwargs)
    
    async def send_bulk(
        self,
        recipients: List[Dict[str, Any]],
        template: EmailTemplate,
        common_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Send bulk emails using a template.
        
        Args:
            recipients: List of {"email": str, "data": dict}
            template: Template type
            common_data: Data shared by all recipients
        
        Returns:
            {"success": int, "failed": int, "errors": list}
        """
        results = {"success": 0, "failed": 0, "errors": []}
        
        for recipient in recipients:
            data = {**(common_data or {}), **(recipient.get("data", {}))}
            result = await self.send_template(
                to=recipient["email"],
                template=template,
                data=data
            )
            
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "email": recipient["email"],
                    "error": result.get("error")
                })
        
        return results
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """List available templates"""
        return [
            {
                "id": t.value,
                "name": t.value.replace("_", " ").title(),
                "subject": TEMPLATES[t]["subject"]
            }
            for t in EmailTemplate if t != EmailTemplate.CUSTOM
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get email statistics"""
        total = self._stats["sent"] + self._stats["failed"]
        success_rate = (self._stats["sent"] / total * 100) if total > 0 else 0
        
        return {
            "sent": self._stats["sent"],
            "failed": self._stats["failed"],
            "total": total,
            "success_rate_pct": round(success_rate, 1),
            "configured": self.is_configured()
        }
    
    def preview_template(
        self,
        template: EmailTemplate,
        data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Preview a rendered template"""
        if template not in TEMPLATES:
            return {"error": f"Template not found: {template}"}
        
        tpl = TEMPLATES[template]
        return {
            "subject": self._render_template(tpl["subject"], data),
            "html": self._render_template(tpl["html"], data)
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

email_service = EmailService()


async def send_email(to: str, subject: str, html: str) -> Dict:
    """Convenience function"""
    return await email_service.send(to, subject, html)


async def send_template_email(to: str, template: str, data: Dict) -> Dict:
    """Convenience function"""
    try:
        tpl_enum = EmailTemplate(template)
        return await email_service.send_template(to, tpl_enum, data)
    except ValueError:
        return {"success": False, "error": f"Invalid template: {template}"}
