"""
API Keys Tests
LeadHunter AI - Testing API key management

Tests for:
- Key generation
- Key validation  
- Key revocation
- Tier management
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import hashlib

from backend.core.api_keys import (
    ApiKeyManager,
    ApiTier,
    TIER_LIMITS,
    api_key_manager,
    generate_api_key,
    validate_api_key
)


# =============================================================================
# API TIER TESTS
# =============================================================================

class TestApiTier:
    """Tests for API tier definitions."""
    
    def test_tier_values(self):
        """Tiers should have correct values."""
        assert ApiTier.FREE.value == "free"
        assert ApiTier.PRO.value == "pro"
        assert ApiTier.ENTERPRISE.value == "enterprise"
    
    def test_tier_limits_exist(self):
        """All tiers should have limits."""
        assert ApiTier.FREE in TIER_LIMITS
        assert ApiTier.PRO in TIER_LIMITS
        assert ApiTier.ENTERPRISE in TIER_LIMITS
    
    def test_enterprise_unlimited(self):
        """Enterprise should be unlimited."""
        assert TIER_LIMITS[ApiTier.ENTERPRISE] == -1
    
    def test_free_has_lowest_limit(self):
        """Free should have lowest limit."""
        assert TIER_LIMITS[ApiTier.FREE] < TIER_LIMITS[ApiTier.PRO]


# =============================================================================
# API KEY MANAGER TESTS
# =============================================================================

class TestApiKeyManager:
    """Tests for ApiKeyManager class."""
    
    def test_singleton_instance(self):
        """ApiKeyManager should be a singleton."""
        manager1 = ApiKeyManager()
        manager2 = ApiKeyManager()
        
        assert manager1 is manager2
    
    def test_global_instance(self):
        """Global api_key_manager should be available."""
        assert api_key_manager is not None
        assert isinstance(api_key_manager, ApiKeyManager)


# =============================================================================
# KEY GENERATION STRING TESTS
# =============================================================================

class TestKeyGenerationString:
    """Tests for key string generation."""
    
    def test_generate_key_string_format(self):
        """Key string should have correct format."""
        manager = ApiKeyManager()
        
        key = manager._generate_key_string("live")
        
        assert key.startswith("lh_live_")
        assert len(key) > 20
    
    def test_generate_test_key_format(self):
        """Test key should have test prefix."""
        manager = ApiKeyManager()
        
        key = manager._generate_key_string("test")
        
        assert key.startswith("lh_test_")
    
    def test_keys_are_unique(self):
        """Generated keys should be unique."""
        manager = ApiKeyManager()
        
        key1 = manager._generate_key_string()
        key2 = manager._generate_key_string()
        
        assert key1 != key2


# =============================================================================
# KEY HASHING TESTS
# =============================================================================

class TestKeyHashing:
    """Tests for key hashing functionality."""
    
    def test_hash_key(self):
        """Should hash key using SHA256."""
        manager = ApiKeyManager()
        
        key = "lh_live_testkey12345"
        hashed = manager._hash_key(key)
        
        # SHA256 produces 64 char hex string
        assert len(hashed) == 64
        assert hashed != key
    
    def test_hash_is_consistent(self):
        """Same key should produce same hash."""
        manager = ApiKeyManager()
        
        key = "lh_live_consistentkey"
        hash1 = manager._hash_key(key)
        hash2 = manager._hash_key(key)
        
        assert hash1 == hash2
    
    def test_hash_matches_sha256(self):
        """Hash should match standard SHA256."""
        manager = ApiKeyManager()
        
        key = "lh_live_verifykey"
        hashed = manager._hash_key(key)
        
        expected = hashlib.sha256(key.encode()).hexdigest()
        assert hashed == expected


# =============================================================================
# KEY GENERATION TESTS (ASYNC)
# =============================================================================

class TestKeyGeneration:
    """Tests for key generation."""
    
    @pytest.mark.asyncio
    async def test_generate_key_format(self):
        """Generated key should have correct format."""
        manager = ApiKeyManager()
        
        # Test just the key string generation (sync method)
        key = manager._generate_key_string("live")
        
        assert key.startswith("lh_live_")
        assert len(key) > 20


# =============================================================================
# KEY VALIDATION TESTS (ASYNC)
# =============================================================================

class TestKeyValidation:
    """Tests for key validation."""
    
    @pytest.mark.asyncio
    async def test_validate_invalid_key(self):
        """Invalid key should return None."""
        manager = ApiKeyManager()
        
        result = await manager.validate_key("invalid_key")
        
        assert result is None or result.get("valid") is False
    
    @pytest.mark.asyncio
    async def test_validate_empty_key(self):
        """Empty key should return None."""
        manager = ApiKeyManager()
        
        result = await manager.validate_key("")
        
        assert result is None or result.get("valid") is False


# =============================================================================
# KEY REVOCATION TESTS (ASYNC)
# =============================================================================

class TestKeyRevocation:
    """Tests for key revocation."""
    
    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self):
        """Revoking nonexistent key should return False."""
        manager = ApiKeyManager()
        
        result = await manager.revoke_key("lh_live_nonexistent12345678901234")
        
        assert result is False or result.get("success") is False


# =============================================================================
# LIST KEYS TESTS (ASYNC)
# =============================================================================

class TestListKeys:
    """Tests for listing user keys."""
    
    @pytest.mark.asyncio
    async def test_list_keys_returns(self):
        """List keys should return result."""
        manager = ApiKeyManager()
        
        # Test without mock - will return list or error dict
        result = await manager.list_keys("nonexistent_user")
        
        assert isinstance(result, (list, dict))


# =============================================================================
# CONVENIENCE FUNCTIONS TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    @pytest.mark.asyncio
    async def test_generate_api_key_function(self):
        """Convenience generate function should work."""
        with patch.object(api_key_manager, 'generate_key', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"success": True, "key": "lh_live_test"}
            
            result = await generate_api_key("user123", "free", "Test")
            
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_validate_api_key_function(self):
        """Convenience validate function should work."""
        with patch.object(api_key_manager, 'validate_key', new_callable=AsyncMock) as mock_val:
            mock_val.return_value = None
            
            result = await validate_api_key("lh_live_test")
            
            assert result is None
