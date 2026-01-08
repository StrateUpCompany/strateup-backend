"""
Multi-Tenant Service
LeadHunter AI - White-label SaaS

Features:
- Organization management
- Custom branding
- Subdomain support
"""
import os
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime
from backend.utils.logger import logger

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


# =============================================================================
# MODELS
# =============================================================================

class TenantConfig:
    """Tenant branding configuration"""
    
    def __init__(
        self,
        name: str,
        slug: str,
        logo_url: str = None,
        primary_color: str = "#06b6d4",
        secondary_color: str = "#8b5cf6",
        custom_domain: str = None
    ):
        self.name = name
        self.slug = slug
        self.logo_url = logo_url
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.custom_domain = custom_domain
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "slug": self.slug,
            "logo_url": self.logo_url,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "custom_domain": self.custom_domain
        }


# =============================================================================
# TENANT SERVICE
# =============================================================================

class TenantService:
    """
    Multi-tenant organization management.
    
    Usage:
        tenant = TenantService()
        
        # Create organization
        org = await tenant.create_organization(
            name="Agency X",
            owner_id="user123"
        )
        
        # Get tenant by subdomain
        config = await tenant.get_by_subdomain("agencyx")
    """
    
    _instance = None
    _memory_tenants: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._memory_tenants = {}
        self._supabase: Optional[Client] = None
        
        if SUPABASE_AVAILABLE:
            self._connect_supabase()
    
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if url and key:
            try:
                self._supabase = create_client(url, key)
                logger.info("Connected to Supabase for tenants")
            except Exception as e:
                logger.warning(f"Supabase connection failed: {e}")
    
    # =========================================================================
    # ORGANIZATION CRUD
    # =========================================================================
    
    async def create_organization(
        self,
        name: str,
        owner_id: str,
        branding: Dict = None
    ) -> Dict[str, Any]:
        """Create a new organization"""
        org_id = secrets.token_urlsafe(16)
        slug = name.lower().replace(" ", "-").replace("_", "-")[:32]
        now = datetime.utcnow().isoformat()
        
        org_data = {
            "id": org_id,
            "name": name,
            "slug": slug,
            "owner_id": owner_id,
            "created_at": now,
            "is_active": True,
            "plan": "free",
            "branding": branding or {
                "logo_url": None,
                "primary_color": "#06b6d4",
                "secondary_color": "#8b5cf6"
            },
            "settings": {},
            "members": [owner_id]
        }
        
        # Store
        if self._supabase:
            try:
                self._supabase.table("organizations").insert(org_data).execute()
            except Exception as e:
                logger.error(f"Failed to create org: {e}")
                self._memory_tenants[org_id] = org_data
        else:
            self._memory_tenants[org_id] = org_data
        
        return {"success": True, "organization": org_data}
    
    async def get_organization(self, org_id: str) -> Optional[Dict]:
        """Get organization by ID"""
        if self._supabase:
            try:
                result = self._supabase.table("organizations").select("*").eq("id", org_id).execute()
                if result.data:
                    return result.data[0]
            except:
                pass
        
        return self._memory_tenants.get(org_id)
    
    async def get_by_subdomain(self, subdomain: str) -> Optional[Dict]:
        """Get organization by subdomain/slug"""
        if self._supabase:
            try:
                result = self._supabase.table("organizations").select("*").eq("slug", subdomain).execute()
                if result.data:
                    return result.data[0]
            except:
                pass
        
        for org in self._memory_tenants.values():
            if org.get("slug") == subdomain:
                return org
        
        return None
    
    async def update_branding(
        self,
        org_id: str,
        branding: Dict
    ) -> Dict[str, Any]:
        """Update organization branding"""
        org = await self.get_organization(org_id)
        if not org:
            return {"success": False, "error": "Organization not found"}
        
        org["branding"] = {**org.get("branding", {}), **branding}
        
        if self._supabase:
            try:
                self._supabase.table("organizations").update(
                    {"branding": org["branding"]}
                ).eq("id", org_id).execute()
            except:
                pass
        
        if org_id in self._memory_tenants:
            self._memory_tenants[org_id] = org
        
        return {"success": True, "branding": org["branding"]}
    
    async def add_member(self, org_id: str, user_id: str) -> Dict[str, Any]:
        """Add member to organization"""
        org = await self.get_organization(org_id)
        if not org:
            return {"success": False, "error": "Organization not found"}
        
        members = org.get("members", [])
        if user_id not in members:
            members.append(user_id)
            org["members"] = members
            
            if self._supabase:
                try:
                    self._supabase.table("organizations").update(
                        {"members": members}
                    ).eq("id", org_id).execute()
                except:
                    pass
        
        return {"success": True, "members": members}
    
    async def get_user_organizations(self, user_id: str) -> List[Dict]:
        """Get all organizations for a user"""
        orgs = []
        
        if self._supabase:
            try:
                result = self._supabase.table("organizations").select("*").contains("members", [user_id]).execute()
                if result.data:
                    orgs = result.data
            except:
                pass
        
        for org in self._memory_tenants.values():
            if user_id in org.get("members", []):
                orgs.append(org)
        
        return orgs


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

tenant_service = TenantService()
