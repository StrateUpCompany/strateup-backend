"""
Integrations Marketplace
LeadHunter AI - Third-party Integrations

Features:
- n8n/Zapier webhooks
- Pre-built automations
- Custom triggers
"""
import os
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from backend.utils.logger import logger


# =============================================================================
# INTEGRATION TYPES
# =============================================================================

class IntegrationType(Enum):
    ZAPIER = "zapier"
    N8N = "n8n"
    MAKE = "make"
    CUSTOM = "custom"


class TriggerEvent(Enum):
    NEW_LEAD = "new_lead"
    LEAD_EXPORTED = "lead_exported"
    CLONE_COMPLETE = "clone_complete"
    ANALYSIS_DONE = "analysis_done"
    PROPOSAL_CREATED = "proposal_created"
    API_LIMIT_REACHED = "api_limit_reached"


# =============================================================================
# PRE-BUILT AUTOMATIONS
# =============================================================================

AUTOMATION_TEMPLATES = [
    {
        "id": "lead_to_crm",
        "name": "Lead → CRM",
        "description": "Envia leads automaticamente para seu CRM",
        "trigger": TriggerEvent.NEW_LEAD.value,
        "category": "crm",
        "icon": "💼"
    },
    {
        "id": "lead_to_sheet",
        "name": "Lead → Google Sheets",
        "description": "Adiciona leads em uma planilha",
        "trigger": TriggerEvent.NEW_LEAD.value,
        "category": "productivity",
        "icon": "📊"
    },
    {
        "id": "clone_to_slack",
        "name": "Clone → Slack",
        "description": "Notifica no Slack quando clone termina",
        "trigger": TriggerEvent.CLONE_COMPLETE.value,
        "category": "notifications",
        "icon": "💬"
    },
    {
        "id": "proposal_to_email",
        "name": "Proposta → Email",
        "description": "Envia proposta por email automaticamente",
        "trigger": TriggerEvent.PROPOSAL_CREATED.value,
        "category": "sales",
        "icon": "📧"
    },
    {
        "id": "lead_ai_enrichment",
        "name": "Lead → AI Enrichment",
        "description": "Enriquece lead com dados de AI",
        "trigger": TriggerEvent.NEW_LEAD.value,
        "category": "ai",
        "icon": "🤖"
    }
]


# =============================================================================
# INTEGRATIONS SERVICE
# =============================================================================

class IntegrationsService:
    """
    Marketplace de integrações e automações.
    
    Usage:
        integrations = IntegrationsService()
        
        # List templates
        templates = integrations.get_templates()
        
        # Create integration
        integration = await integrations.create(
            user_id="user123",
            template_id="lead_to_crm",
            config={"crm_url": "..."}
        )
    """
    
    _instance = None
    _user_integrations: Dict[str, List[Dict]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._user_integrations = {}
    
    def get_templates(self, category: str = None) -> List[Dict]:
        """Get available automation templates"""
        templates = AUTOMATION_TEMPLATES
        
        if category:
            templates = [t for t in templates if t.get("category") == category]
        
        return templates
    
    def get_categories(self) -> List[Dict]:
        """Get available categories"""
        return [
            {"id": "crm", "name": "CRM", "icon": "💼"},
            {"id": "productivity", "name": "Productivity", "icon": "📊"},
            {"id": "notifications", "name": "Notifications", "icon": "🔔"},
            {"id": "sales", "name": "Sales", "icon": "💰"},
            {"id": "ai", "name": "AI", "icon": "🤖"}
        ]
    
    async def create_integration(
        self,
        user_id: str,
        template_id: str,
        webhook_url: str,
        config: Dict = None
    ) -> Dict[str, Any]:
        """Create a new integration from template"""
        template = next(
            (t for t in AUTOMATION_TEMPLATES if t["id"] == template_id),
            None
        )
        
        if not template:
            return {"success": False, "error": "Template not found"}
        
        integration_id = secrets.token_urlsafe(16)
        now = datetime.utcnow().isoformat()
        
        integration = {
            "id": integration_id,
            "template_id": template_id,
            "name": template["name"],
            "trigger": template["trigger"],
            "webhook_url": webhook_url,
            "config": config or {},
            "is_active": True,
            "created_at": now,
            "last_triggered": None,
            "trigger_count": 0
        }
        
        if user_id not in self._user_integrations:
            self._user_integrations[user_id] = []
        
        self._user_integrations[user_id].append(integration)
        
        return {"success": True, "integration": integration}
    
    async def list_user_integrations(self, user_id: str) -> List[Dict]:
        """List all integrations for a user"""
        return self._user_integrations.get(user_id, [])
    
    async def toggle_integration(
        self,
        user_id: str,
        integration_id: str
    ) -> Dict[str, Any]:
        """Toggle integration on/off"""
        integrations = self._user_integrations.get(user_id, [])
        
        for i in integrations:
            if i["id"] == integration_id:
                i["is_active"] = not i["is_active"]
                return {"success": True, "is_active": i["is_active"]}
        
        return {"success": False, "error": "Integration not found"}
    
    async def delete_integration(
        self,
        user_id: str,
        integration_id: str
    ) -> Dict[str, Any]:
        """Delete an integration"""
        integrations = self._user_integrations.get(user_id, [])
        
        for i, integration in enumerate(integrations):
            if integration["id"] == integration_id:
                integrations.pop(i)
                return {"success": True}
        
        return {"success": False, "error": "Integration not found"}


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

integrations_service = IntegrationsService()
