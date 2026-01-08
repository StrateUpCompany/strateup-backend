"""
Tests for Secrets Manager
LeadHunter AI - Security Verification
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from backend.core.secrets_manager import (
    SecretsManager, 
    EnvBackend, 
    VaultBackend, 
    AWSSecretsBackend,
    get_secret,
    get_required_secret
)

# Use a test-specific instance to avoid caching issues across tests
@pytest.fixture
def secrets_manager():
    # Reset singleton for testing
    SecretsManager._instance = None
    manager = SecretsManager()
    manager._backends = [] # Clear default backends
    return manager

class TestSecretsManager:
    """Tests for Secrets Manager Core Logic"""

    def test_env_backend(self, secrets_manager):
        """Should retrieve from environment variables."""
        backend = EnvBackend()
        secrets_manager._backends = [backend]
        
        with patch.dict(os.environ, {"TEST_SECRET": "value123"}):
            assert secrets_manager.get("TEST_SECRET") == "value123"

    def test_priority_order(self, secrets_manager):
        """Should respect backend priority."""
        # 1. Mock Vault (High priority)
        vault_mock = MagicMock()
        vault_mock.get.return_value = "vault_value"
        vault_mock.name = "vault"
        vault_mock.is_available.return_value = True

        # 2. Mock Env (Low priority)
        env_mock = MagicMock()
        env_mock.get.return_value = "env_value"
        env_mock.name = "env"

        secrets_manager._backends = [vault_mock, env_mock]

        # Should return Vault value
        assert secrets_manager.get("KEY", use_cache=False) == "vault_value"
        assert vault_mock.get.called

    def test_caching(self, secrets_manager):
        """Should cache values to reduce backend unexpected calls."""
        backend = MagicMock()
        backend.get.return_value = "cached_val"
        backend.name = "mock"
        secrets_manager._backends = [backend]

        # First call
        val1 = secrets_manager.get("CACHED_KEY")
        assert val1 == "cached_val"
        assert backend.get.call_count == 1

        # Second call (should be cached)
        val2 = secrets_manager.get("CACHED_KEY")
        assert val2 == "cached_val"
        assert backend.get.call_count == 1  # Still 1

    def test_required_secret(self, secrets_manager):
        """Should raise error if required secret is missing."""
        secrets_manager._backends = []
        
        with pytest.raises(ValueError, match="Required secret 'MISSING' is not configured"):
            secrets_manager.get_required("MISSING")

    def test_audit_log(self, secrets_manager):
        """Should log access attempts."""
        backend = MagicMock()
        backend.get.return_value = "secret"
        backend.name = "mock"
        secrets_manager._backends = [backend]

        secrets_manager.get("AUDIT_KEY")
        
        logs = secrets_manager.get_audit_log()
        assert len(logs) > 0
        assert logs[-1]["key"] == "AUDIT_KEY"
        assert logs[-1]["success"] is True

    def test_convenience_functions(self):
        """Test global helper functions."""
        # Reset singleton
        SecretsManager._instance = None
        
        with patch.dict(os.environ, {"GLOBAL_KEY": "global_val"}):
            assert get_secret("GLOBAL_KEY") == "global_val"
            assert get_required_secret("GLOBAL_KEY") == "global_val"

    def test_security_utilities(self):
        """Test utilities like masking."""
        from backend.core.secrets_manager import mask_secret, validate_secret_strength
        
        # Masking
        assert mask_secret("1234567890", show_chars=2) == "12***90"
        assert mask_secret("short") == "***"
        
        # Validation
        weak = validate_secret_strength("password")
        assert weak["strong"] is False
        
        strong = validate_secret_strength("CorrectHorseBatteryStaple!1234", min_length=10)
        assert strong["strong"] is True
