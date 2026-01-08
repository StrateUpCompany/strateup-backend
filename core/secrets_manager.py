"""
Secrets Manager
LeadHunter AI - Secure Credentials Management

Features:
- Multiple backends (env, Vault, AWS Secrets Manager)
- Secret caching with TTL
- Auto-rotation support
- Audit logging

Usage:
    secrets = SecretsManager()
    db_password = secrets.get("SUPABASE_PASSWORD")
"""
import os
import hashlib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import lru_cache
from abc import ABC, abstractmethod
from backend.utils.logger import logger


# =============================================================================
# SECRET BACKENDS
# =============================================================================

class SecretBackend(ABC):
    """Abstract base class for secret backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a secret by key."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for logging."""
        pass


class EnvBackend(SecretBackend):
    """
    Environment variable backend.
    Fallback for local development.
    """
    
    @property
    def name(self) -> str:
        return "environment"
    
    def get(self, key: str) -> Optional[str]:
        return os.getenv(key)
    
    def is_available(self) -> bool:
        return True  # Always available


class VaultBackend(SecretBackend):
    """
    HashiCorp Vault backend.
    Enterprise-grade secret management.
    """
    
    def __init__(self):
        self.vault_addr = os.getenv("VAULT_ADDR")
        self.vault_token = os.getenv("VAULT_TOKEN")
        self.vault_path = os.getenv("VAULT_SECRET_PATH", "secret/data/leadhunter")
        self._client = None
    
    @property
    def name(self) -> str:
        return "vault"
    
    def _get_client(self):
        """Lazy load Vault client."""
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(
                    url=self.vault_addr,
                    token=self.vault_token
                )
            except ImportError:
                logger.warning("hvac not installed, Vault backend unavailable")
                return None
        return self._client
    
    def get(self, key: str) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            secret = client.secrets.kv.v2.read_secret_version(
                path=self.vault_path.replace("secret/data/", "")
            )
            return secret["data"]["data"].get(key)
        except Exception as e:
            logger.error(f"Vault read error: {e}")
            return None
    
    def is_available(self) -> bool:
        return bool(self.vault_addr and self.vault_token)


class AWSSecretsBackend(SecretBackend):
    """
    AWS Secrets Manager backend.
    For AWS-hosted deployments.
    """
    
    def __init__(self):
        self.secret_name = os.getenv("AWS_SECRET_NAME", "leadhunter/production")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self._client = None
        self._cache: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        return "aws_secrets_manager"
    
    def _get_client(self):
        """Lazy load AWS client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "secretsmanager",
                    region_name=self.region
                )
            except ImportError:
                logger.warning("boto3 not installed, AWS backend unavailable")
                return None
        return self._client
    
    def _load_secrets(self) -> Dict[str, str]:
        """Load all secrets from AWS."""
        if self._cache:
            return self._cache
        
        client = self._get_client()
        if not client:
            return {}
        
        try:
            response = client.get_secret_value(SecretId=self.secret_name)
            self._cache = json.loads(response["SecretString"])
            return self._cache
        except Exception as e:
            logger.error(f"AWS Secrets Manager error: {e}")
            return {}
    
    def get(self, key: str) -> Optional[str]:
        secrets = self._load_secrets()
        return secrets.get(key)
    
    def is_available(self) -> bool:
        return bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_ROLE_ARN"))


# =============================================================================
# SECRETS MANAGER
# =============================================================================

class SecretsManager:
    """
    Unified secrets management with multiple backends.
    
    Priority order:
    1. HashiCorp Vault (if configured)
    2. AWS Secrets Manager (if configured)
    3. Environment variables (fallback)
    
    Usage:
        secrets = SecretsManager()
        
        # Get a secret
        api_key = secrets.get("OPENAI_API_KEY")
        
        # Get with default
        model = secrets.get("OLLAMA_MODEL", default="llama3")
        
        # Check if secret exists
        if secrets.has("STRIPE_SECRET_KEY"):
            ...
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._backends: List[SecretBackend] = []
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        self._cache_ttl = timedelta(minutes=5)
        self._audit_log: List[Dict] = []
        
        # Initialize backends in priority order
        self._init_backends()
        
        logger.info(f"SecretsManager initialized with backends: {self.available_backends}")
    
    def _init_backends(self):
        """Initialize secret backends in priority order."""
        # 1. Vault (highest priority)
        vault = VaultBackend()
        if vault.is_available():
            self._backends.append(vault)
        
        # 2. AWS Secrets Manager
        aws = AWSSecretsBackend()
        if aws.is_available():
            self._backends.append(aws)
        
        # 3. Environment (always available as fallback)
        self._backends.append(EnvBackend())
    
    @property
    def available_backends(self) -> List[str]:
        """Get list of available backend names."""
        return [b.name for b in self._backends]
    
    def get(self, key: str, default: Optional[str] = None, use_cache: bool = True) -> Optional[str]:
        """
        Get a secret value.
        
        Args:
            key: Secret key name
            default: Default value if not found
            use_cache: Whether to use cached value
        
        Returns:
            Secret value or default
        """
        # Check cache first
        if use_cache and key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
            else:
                del self._cache[key]
        
        # Try each backend in order
        for backend in self._backends:
            try:
                value = backend.get(key)
                if value is not None:
                    # Cache the value
                    self._cache[key] = (value, datetime.now() + self._cache_ttl)
                    
                    # Audit log (don't log the actual value!)
                    self._log_access(key, backend.name, success=True)
                    
                    return value
            except Exception as e:
                logger.error(f"Error getting {key} from {backend.name}: {e}")
                continue
        
        self._log_access(key, "none", success=False)
        return default
    
    def has(self, key: str) -> bool:
        """Check if a secret exists."""
        return self.get(key) is not None
    
    def get_required(self, key: str) -> str:
        """
        Get a required secret. Raises if not found.
        
        Raises:
            ValueError: If secret is not configured
        """
        value = self.get(key)
        if value is None:
            raise ValueError(f"Required secret '{key}' is not configured")
        return value
    
    def invalidate_cache(self, key: Optional[str] = None):
        """
        Invalidate cached secrets.
        
        Args:
            key: Specific key to invalidate, or None for all
        """
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
        logger.info(f"Cache invalidated: {key or 'all'}")
    
    def _log_access(self, key: str, backend: str, success: bool):
        """Log secret access for auditing."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "key": key,
            "backend": backend,
            "success": success,
            "key_hash": hashlib.sha256(key.encode()).hexdigest()[:16]
        }
        self._audit_log.append(entry)
        
        # Keep only last 1000 entries
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries."""
        return self._audit_log[-limit:]
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all backends.
        
        Returns:
            Dict with status of each backend
        """
        status = {
            "healthy": True,
            "backends": {},
            "cache_size": len(self._cache)
        }
        
        for backend in self._backends:
            try:
                is_available = backend.is_available()
                status["backends"][backend.name] = {
                    "available": is_available,
                    "status": "ok" if is_available else "unavailable"
                }
            except Exception as e:
                status["backends"][backend.name] = {
                    "available": False,
                    "status": "error",
                    "error": str(e)
                }
                status["healthy"] = False
        
        return status


# =============================================================================
# SECURITY UTILITIES
# =============================================================================

def mask_secret(value: str, show_chars: int = 4) -> str:
    """
    Mask a secret for safe logging.
    
    Example:
        mask_secret("sk-1234567890abcdef") -> "sk-1***cdef"
    """
    if not value or len(value) <= show_chars * 2:
        return "***"
    
    return f"{value[:show_chars]}***{value[-show_chars:]}"


def validate_secret_strength(secret: str, min_length: int = 32) -> Dict[str, Any]:
    """
    Validate secret strength.
    
    Returns:
        Dict with validation results
    """
    checks = {
        "length_ok": len(secret) >= min_length,
        "has_uppercase": any(c.isupper() for c in secret),
        "has_lowercase": any(c.islower() for c in secret),
        "has_digit": any(c.isdigit() for c in secret),
        "has_special": any(not c.isalnum() for c in secret),
        "not_common": secret.lower() not in [
            "password", "secret", "admin", "root", 
            "your-super-secret-jwt-key-change-in-production"
        ]
    }
    
    score = sum(checks.values())
    checks["score"] = score
    checks["strong"] = score >= 5
    
    return checks


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

secrets = SecretsManager()


# Convenience functions
def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a secret value."""
    return secrets.get(key, default)


def get_required_secret(key: str) -> str:
    """Get a required secret."""
    return secrets.get_required(key)
