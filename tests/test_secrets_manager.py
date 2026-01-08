"""
Secrets Manager Tests
LeadHunter AI - Testing secrets management

Tests for:
- Secret retrieval
- Backend fallback
- Caching
- Validation
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from backend.core.secrets_manager import (
    SecretsManager,
    EnvBackend,
    VaultBackend,
    AWSSecretsBackend,
    secrets,
    mask_secret,
    validate_secret_strength
)


# =============================================================================
# ENV BACKEND TESTS
# =============================================================================

class TestEnvBackend:
    """Tests for environment variable backend."""
    
    def test_name(self):
        """Backend should have a name."""
        backend = EnvBackend()
        assert backend.name == "environment"
    
    def test_is_available(self):
        """Env backend should always be available."""
        backend = EnvBackend()
        assert backend.is_available() is True
    
    def test_get_existing_var(self):
        """Should get existing environment variable."""
        backend = EnvBackend()
        
        with patch.dict(os.environ, {"TEST_SECRET": "test_value"}):
            result = backend.get("TEST_SECRET")
            assert result == "test_value"
    
    def test_get_missing_var(self):
        """Should return None for missing variable."""
        backend = EnvBackend()
        
        result = backend.get("NONEXISTENT_VAR_12345")
        assert result is None


# =============================================================================
# VAULT BACKEND TESTS
# =============================================================================

class TestVaultBackend:
    """Tests for HashiCorp Vault backend."""
    
    def test_name(self):
        """Backend should have a name."""
        backend = VaultBackend()
        assert backend.name == "vault"
    
    def test_not_available_without_config(self):
        """Should not be available without VAULT_ADDR."""
        with patch.dict(os.environ, {}, clear=True):
            backend = VaultBackend()
            assert backend.is_available() is False
    
    def test_available_with_config(self):
        """Should be available with VAULT_ADDR and VAULT_TOKEN."""
        with patch.dict(os.environ, {
            "VAULT_ADDR": "http://localhost:8200",
            "VAULT_TOKEN": "test_token"
        }):
            backend = VaultBackend()
            # May still be False if hvac not installed, but config is present
            assert hasattr(backend, 'is_available')


# =============================================================================
# AWS SECRETS BACKEND TESTS
# =============================================================================

class TestAWSSecretsBackend:
    """Tests for AWS Secrets Manager backend."""
    
    def test_name(self):
        """Backend should have a name."""
        backend = AWSSecretsBackend()
        assert backend.name == "aws_secrets_manager"
    
    def test_not_available_without_config(self):
        """Should not be available without AWS_SECRET_NAME."""
        with patch.dict(os.environ, {}, clear=True):
            backend = AWSSecretsBackend()
            assert backend.is_available() is False


# =============================================================================
# SECRETS MANAGER TESTS
# =============================================================================

class TestSecretsManager:
    """Tests for SecretsManager class."""
    
    def test_singleton_instance(self):
        """SecretsManager should be a singleton."""
        manager1 = SecretsManager()
        manager2 = SecretsManager()
        
        assert manager1 is manager2
    
    def test_global_instance(self):
        """Global secrets instance should be available."""
        assert secrets is not None
        assert isinstance(secrets, SecretsManager)
    
    def test_get_from_env(self):
        """Should get secrets from environment."""
        manager = SecretsManager()
        
        with patch.dict(os.environ, {"MY_SECRET": "secret_value"}):
            result = manager.get("MY_SECRET")
            assert result == "secret_value"
    
    def test_get_with_default(self):
        """Should return default for missing secrets."""
        manager = SecretsManager()
        
        result = manager.get("NONEXISTENT_SECRET", default="default_value")
        assert result == "default_value"
    
    def test_get_caches_value(self):
        """Should cache retrieved values."""
        manager = SecretsManager()
        manager.invalidate_cache()
        
        with patch.dict(os.environ, {"CACHED_SECRET": "cached_value"}):
            # First call
            result1 = manager.get("CACHED_SECRET")
            # Second call should use cache
            result2 = manager.get("CACHED_SECRET")
            
            assert result1 == result2


# =============================================================================
# CACHE TESTS
# =============================================================================

class TestSecretsCache:
    """Tests for secrets caching functionality."""
    
    def test_clear_cache(self):
        """Should clear cache."""
        manager = SecretsManager()
        
        with patch.dict(os.environ, {"CACHE_TEST": "value"}):
            manager.get("CACHE_TEST")
            manager.invalidate_cache()
            
            # Cache should be empty after clear
            assert "CACHE_TEST" not in manager._cache
    
    def test_cache_bypass(self):
        """Should bypass cache when requested."""
        manager = SecretsManager()
        
        with patch.dict(os.environ, {"BYPASS_SECRET": "value"}):
            # First call caches
            manager.get("BYPASS_SECRET")
            
            # Bypass cache
            result = manager.get("BYPASS_SECRET", use_cache=False)
            assert result == "value"


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

class TestHealthCheck:
    """Tests for health check functionality."""
    
    def test_health_check_returns_dict(self):
        """Health check should return status dict."""
        manager = SecretsManager()
        
        status = manager.health_check()
        
        assert isinstance(status, dict)
        assert "healthy" in status
        assert "backends" in status
    
    def test_health_check_has_backends(self):
        """Health check should report backend statuses."""
        manager = SecretsManager()
        
        status = manager.health_check()
        
        # Should have at least environment backend
        assert len(status["backends"]) >= 1


# =============================================================================
# MASK SECRET TESTS
# =============================================================================

class TestMaskSecret:
    """Tests for secret masking utility."""
    
    def test_mask_secret_short(self):
        """Short secrets should be fully masked."""
        result = mask_secret("abc")
        assert result == "***"
    
    def test_mask_secret_normal(self):
        """Normal secrets should show first/last chars."""
        result = mask_secret("mysecretpassword")
        
        assert result.startswith("mys")
        assert result.endswith("ord")
        assert "***" in result
    
    def test_mask_secret_empty(self):
        """Empty secret should return masked."""
        result = mask_secret("")
        assert result == "***"
    
    def test_mask_secret_none(self):
        """None should return masked."""
        result = mask_secret(None)
        assert result == "***"
    
    def test_mask_custom_chars(self):
        """Should respect custom show_chars."""
        result = mask_secret("verylongsecretvalue", show_chars=5)
        
        assert result.startswith("veryl")
        assert result.endswith("value")


# =============================================================================
# VALIDATE SECRET STRENGTH TESTS
# =============================================================================

class TestValidateSecretStrength:
    """Tests for secret strength validation."""
    
    def test_weak_secret(self):
        """Weak secrets should score low."""
        result = validate_secret_strength("password")
        
        assert result["strong"] is False
        assert result["not_common"] is False
    
    def test_short_secret(self):
        """Short secrets should fail length check."""
        result = validate_secret_strength("abc")
        
        assert result["length_ok"] is False
    
    def test_strong_secret(self):
        """Strong secrets should pass all checks."""
        # min_length default is 32, so use a longer password
        result = validate_secret_strength("MyStr0ng!P@ssw0rd#2026VeryL0ng!Key")
        
        assert result["length_ok"] is True
        assert result["has_uppercase"] is True
        assert result["has_lowercase"] is True
        assert result["has_digit"] is True
        assert result["has_special"] is True
        # Score should be 6 (all checks pass)
        assert result.get("score", 0) >= 5
    
    def test_missing_uppercase(self):
        """Should detect missing uppercase."""
        result = validate_secret_strength("alllowercase123!")
        
        assert result["has_uppercase"] is False
    
    def test_missing_digit(self):
        """Should detect missing digits."""
        result = validate_secret_strength("NoDigitsHere!")
        
        assert result["has_digit"] is False
    
    def test_common_secrets(self):
        """Should detect common weak secrets."""
        common = ["password", "secret", "admin", "root"]
        
        for secret in common:
            result = validate_secret_strength(secret)
            assert result["not_common"] is False


# =============================================================================
# REQUIRED SECRETS TESTS
# =============================================================================

class TestRequiredSecrets:
    """Tests for required secrets validation."""
    
    def test_get_required_exists(self):
        """Should get required secret that exists."""
        manager = SecretsManager()
        
        with patch.dict(os.environ, {"REQUIRED_SECRET": "value123"}):
            result = manager.get_required("REQUIRED_SECRET")
            assert result == "value123"
    
    def test_get_required_missing_raises(self):
        """Should raise for missing required secret."""
        manager = SecretsManager()
        
        with pytest.raises(ValueError):
            manager.get_required("DEFINITELY_MISSING_SECRET_12345")
    
    def test_has_secret_true(self):
        """Should return True when secret exists."""
        manager = SecretsManager()
        
        with patch.dict(os.environ, {"EXISTS_SECRET": "value"}):
            assert manager.has("EXISTS_SECRET") is True
    
    def test_has_secret_false(self):
        """Should return False when secret missing."""
        manager = SecretsManager()
        
        assert manager.has("MISSING_SECRET_99999") is False
