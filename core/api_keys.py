"""
API Keys Management
LeadHunter AI - Public API

Features:
- Generate unique API keys
- Validate keys and return user/tier info
- Revoke keys
- Track usage

Key Format: lh_{env}_{24_chars}
- lh_live_xxxxxxxxxxxxxxxxxxxx (production)
- lh_test_xxxxxxxxxxxxxxxxxxxx (sandbox)
"""
import os
import secrets
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
from backend.utils.logger import logger

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase not installed. API keys will use in-memory storage.")


# =============================================================================
# TIER CONFIGURATION
# =============================================================================

class ApiTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


TIER_LIMITS = {
    ApiTier.FREE: 100,          # 100 requests/day
    ApiTier.PRO: 1000,          # 1000 requests/day
    ApiTier.ENTERPRISE: -1,     # Unlimited (-1)
}

TIER_NAMES = {
    ApiTier.FREE: "Free",
    ApiTier.PRO: "Pro",
    ApiTier.ENTERPRISE: "Enterprise",
}


# =============================================================================
# API KEY MANAGER
# =============================================================================

class ApiKeyManager:
    """
    Manages API keys for public API access.
    
    Usage:
        manager = ApiKeyManager()
        
        # Generate a new key
        key_info = await manager.generate_key(user_id="user123", tier=ApiTier.FREE)
        # → {"key": "lh_live_abc123...", "tier": "free", ...}
        
        # Validate a key
        info = await manager.validate_key("lh_live_abc123...")
        # → {"user_id": "user123", "tier": "free", ...} or None
        
        # Revoke a key
        await manager.revoke_key("lh_live_abc123...")
    """
    
    KEY_PREFIX = "lh"
    KEY_LENGTH = 24
    
    _instance = None
    _memory_store: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._memory_store = {}
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
                logger.info("Connected to Supabase for API keys")
            except Exception as e:
                logger.warning(f"Supabase connection failed: {e}")
    
    def _generate_key_string(self, environment: str = "live") -> str:
        """Generate a unique API key string"""
        random_part = secrets.token_urlsafe(self.KEY_LENGTH)[:self.KEY_LENGTH]
        return f"{self.KEY_PREFIX}_{environment}_{random_part}"
    
    def _hash_key(self, key: str) -> str:
        """Hash key for storage (security)"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    async def generate_key(
        self,
        user_id: str,
        tier: ApiTier = ApiTier.FREE,
        name: str = "Default",
        environment: str = "live"
    ) -> Dict[str, Any]:
        """
        Generate a new API key for a user.
        
        Args:
            user_id: User ID in your system
            tier: API tier (free, pro, enterprise)
            name: Friendly name for the key
            environment: live or test
        
        Returns:
            {
                "key": "lh_live_xxx...",
                "key_id": "uuid",
                "name": "Default",
                "tier": "free",
                "created_at": "2026-01-03T..."
            }
        """
        key = self._generate_key_string(environment)
        key_hash = self._hash_key(key)
        now = datetime.utcnow().isoformat()
        
        key_data = {
            "id": secrets.token_urlsafe(16),
            "user_id": user_id,
            "key_hash": key_hash,
            "key_prefix": key[:15] + "...",  # Store prefix for display
            "name": name,
            "tier": tier.value,
            "environment": environment,
            "created_at": now,
            "last_used_at": None,
            "revoked_at": None,
            "is_active": True
        }
        
        # Store in Supabase if available
        if self._supabase:
            try:
                result = self._supabase.table("api_keys").insert(key_data).execute()
                logger.info(f"API key created in Supabase: {key_data['key_prefix']}")
            except Exception as e:
                logger.error(f"Failed to store key in Supabase: {e}")
                # Fallback to memory
                self._memory_store[key_hash] = key_data
        else:
            self._memory_store[key_hash] = key_data
        
        return {
            "key": key,  # Only returned once, never stored in plain text
            "key_id": key_data["id"],
            "key_prefix": key_data["key_prefix"],
            "name": name,
            "tier": tier.value,
            "created_at": now
        }
    
    async def validate_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key.
        
        Args:
            key: The full API key string
        
        Returns:
            Key info if valid, None if invalid/revoked
        """
        if not key or not key.startswith(f"{self.KEY_PREFIX}_"):
            return None
        
        key_hash = self._hash_key(key)
        
        # Check Supabase first
        if self._supabase:
            try:
                result = self._supabase.table("api_keys").select("*").eq(
                    "key_hash", key_hash
                ).eq("is_active", True).execute()
                
                if result.data and len(result.data) > 0:
                    key_data = result.data[0]
                    
                    # Update last_used_at
                    self._supabase.table("api_keys").update({
                        "last_used_at": datetime.utcnow().isoformat()
                    }).eq("id", key_data["id"]).execute()
                    
                    return {
                        "user_id": key_data["user_id"],
                        "tier": ApiTier(key_data["tier"]),
                        "name": key_data["name"],
                        "environment": key_data["environment"],
                        "daily_limit": TIER_LIMITS[ApiTier(key_data["tier"])]
                    }
            except Exception as e:
                logger.error(f"Supabase validation failed: {e}")
        
        # Fallback to memory
        if key_hash in self._memory_store:
            key_data = self._memory_store[key_hash]
            if key_data.get("is_active", True):
                return {
                    "user_id": key_data["user_id"],
                    "tier": ApiTier(key_data["tier"]),
                    "name": key_data["name"],
                    "environment": key_data["environment"],
                    "daily_limit": TIER_LIMITS[ApiTier(key_data["tier"])]
                }
        
        return None
    
    async def revoke_key(self, key: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key: The full API key string
        
        Returns:
            True if revoked, False if not found
        """
        key_hash = self._hash_key(key)
        
        if self._supabase:
            try:
                result = self._supabase.table("api_keys").update({
                    "is_active": False,
                    "revoked_at": datetime.utcnow().isoformat()
                }).eq("key_hash", key_hash).execute()
                
                if result.data:
                    logger.info(f"API key revoked: {key[:15]}...")
                    return True
            except Exception as e:
                logger.error(f"Supabase revoke failed: {e}")
        
        # Fallback to memory
        if key_hash in self._memory_store:
            self._memory_store[key_hash]["is_active"] = False
            self._memory_store[key_hash]["revoked_at"] = datetime.utcnow().isoformat()
            return True
        
        return False
    
    async def list_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all API keys for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of key info (without the actual key)
        """
        keys = []
        
        if self._supabase:
            try:
                result = self._supabase.table("api_keys").select(
                    "id, key_prefix, name, tier, environment, created_at, last_used_at, is_active"
                ).eq("user_id", user_id).execute()
                
                if result.data:
                    keys = result.data
            except Exception as e:
                logger.error(f"Supabase list failed: {e}")
        
        # Add memory keys
        for key_hash, data in self._memory_store.items():
            if data["user_id"] == user_id:
                keys.append({
                    "id": data["id"],
                    "key_prefix": data["key_prefix"],
                    "name": data["name"],
                    "tier": data["tier"],
                    "environment": data["environment"],
                    "created_at": data["created_at"],
                    "last_used_at": data.get("last_used_at"),
                    "is_active": data.get("is_active", True)
                })
        
        return keys
    
    async def get_key_usage(self, key: str) -> Dict[str, Any]:
        """Get usage stats for an API key"""
        from backend.core.rate_limiter import rate_limiter
        
        key_info = await self.validate_key(key)
        if not key_info:
            return {"error": "Invalid key"}
        
        key_hash = self._hash_key(key)
        usage = rate_limiter.get_usage(key_hash)
        
        return {
            "tier": key_info["tier"].value,
            "daily_limit": key_info["daily_limit"],
            "requests_today": usage.get("count", 0),
            "remaining": usage.get("remaining", key_info["daily_limit"]),
            "resets_at": usage.get("resets_at")
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

api_key_manager = ApiKeyManager()


async def generate_api_key(user_id: str, tier: str = "free", name: str = "Default") -> Dict:
    """Convenience function"""
    tier_enum = ApiTier(tier) if tier in [t.value for t in ApiTier] else ApiTier.FREE
    return await api_key_manager.generate_key(user_id, tier_enum, name)


async def validate_api_key(key: str) -> Optional[Dict]:
    """Convenience function"""
    return await api_key_manager.validate_key(key)
