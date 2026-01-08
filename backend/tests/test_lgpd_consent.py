"""
LGPD Consent Tests
LeadHunter AI - Testing LGPD compliance module

Tests for:
- Consent types
- Consent recording
- Consent checking
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.core.lgpd_consent import LGPDConsentManager, require_consent


# =============================================================================
# LGPD CONSENT MANAGER TESTS
# =============================================================================

class TestLGPDConsentManager:
    """Tests for LGPDConsentManager class."""
    
    def test_consent_types_defined(self):
        """Should have all consent types defined."""
        assert "data_collection" in LGPDConsentManager.CONSENT_TYPES
        assert "cookies" in LGPDConsentManager.CONSENT_TYPES
        assert "email_marketing" in LGPDConsentManager.CONSENT_TYPES
        assert "third_party" in LGPDConsentManager.CONSENT_TYPES
    
    def test_consent_types_have_descriptions(self):
        """Each consent type should have a description."""
        for key, desc in LGPDConsentManager.CONSENT_TYPES.items():
            assert isinstance(desc, str)
            assert len(desc) > 0


# =============================================================================
# RECORD CONSENT TESTS
# =============================================================================

class TestRecordConsent:
    """Tests for consent recording."""
    
    @pytest.mark.asyncio
    async def test_record_consent_valid_type(self):
        """Should record valid consent type."""
        manager = LGPDConsentManager()
        
        with patch.object(manager, 'db', MagicMock()) as mock_db:
            mock_db.insert = AsyncMock(return_value={"id": 1})
            
            result = await manager.record_consent(
                user_id="user123",
                consent_type="data_collection",
                granted=True
            )
            
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_record_consent_invalid_type(self):
        """Should raise for invalid consent type."""
        manager = LGPDConsentManager()
        
        with pytest.raises(ValueError):
            await manager.record_consent(
                user_id="user123",
                consent_type="invalid_type",
                granted=True
            )
    
    @pytest.mark.asyncio
    async def test_record_consent_with_metadata(self):
        """Should record consent with metadata."""
        manager = LGPDConsentManager()
        
        with patch.object(manager, 'db', MagicMock()) as mock_db:
            mock_db.insert = AsyncMock(return_value={"id": 1})
            
            result = await manager.record_consent(
                user_id="user123",
                consent_type="cookies",
                granted=True,
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                metadata={"source": "modal"}
            )
            
            assert isinstance(result, dict)


# =============================================================================
# GET USER CONSENTS TESTS
# =============================================================================

class TestGetUserConsents:
    """Tests for getting user consents."""
    
    @pytest.mark.asyncio
    async def test_get_user_consents(self):
        """Should get user consents."""
        manager = LGPDConsentManager()
        
        with patch.object(manager, 'db', MagicMock()) as mock_db:
            mock_db.query = AsyncMock(return_value=[
                {"consent_type": "data_collection", "granted": True, "created_at": "2026-01-01"},
                {"consent_type": "cookies", "granted": False, "created_at": "2026-01-01"}
            ])
            
            result = await manager.get_user_consents("user123")
            
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_get_user_consents_empty(self):
        """Should return empty dict for new user."""
        manager = LGPDConsentManager()
        
        with patch.object(manager, 'db', MagicMock()) as mock_db:
            mock_db.query = AsyncMock(return_value=[])
            
            result = await manager.get_user_consents("new_user")
            
            assert result == {}


# =============================================================================
# HAS CONSENT TESTS
# =============================================================================

class TestHasConsent:
    """Tests for checking consent."""
    
    @pytest.mark.asyncio
    async def test_has_consent_true(self):
        """Should return True when consent granted."""
        manager = LGPDConsentManager()
        
        with patch.object(manager, 'get_user_consents', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data_collection": True}
            
            result = await manager.has_consent("user123", "data_collection")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_has_consent_false(self):
        """Should return False when consent not granted."""
        manager = LGPDConsentManager()
        
        with patch.object(manager, 'get_user_consents', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data_collection": False}
            
            result = await manager.has_consent("user123", "data_collection")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_has_consent_missing(self):
        """Should return False when consent not recorded."""
        manager = LGPDConsentManager()
        
        with patch.object(manager, 'get_user_consents', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {}
            
            result = await manager.has_consent("user123", "data_collection")
            
            assert result is False


# =============================================================================
# REVOKE CONSENT TESTS
# =============================================================================

class TestRevokeConsent:
    """Tests for revoking consent."""
    
    @pytest.mark.asyncio
    async def test_revoke_consent(self):
        """Should revoke consent."""
        manager = LGPDConsentManager()
        
        with patch.object(manager, 'record_consent', new_callable=AsyncMock) as mock_record:
            mock_record.return_value = {"id": 1}
            
            result = await manager.revoke_consent("user123", "data_collection")
            
            assert result is True
            mock_record.assert_called_once()


# =============================================================================
# AUDIT LOG TESTS
# =============================================================================

class TestAuditLog:
    """Tests for audit log."""
    
    @pytest.mark.asyncio
    async def test_get_consent_audit_log(self):
        """Should get audit log."""
        manager = LGPDConsentManager()
        
        with patch.object(manager, 'db', MagicMock()) as mock_db:
            mock_db.query = AsyncMock(return_value=[
                {"consent_type": "data_collection", "granted": True, "created_at": "2026-01-01"},
                {"consent_type": "data_collection", "granted": False, "created_at": "2026-01-02"}
            ])
            
            result = await manager.get_consent_audit_log("user123")
            
            assert isinstance(result, list)
            assert len(result) == 2


# =============================================================================
# REQUIRE CONSENT DECORATOR TESTS
# =============================================================================

class TestRequireConsentDecorator:
    """Tests for require_consent decorator."""
    
    def test_decorator_exists(self):
        """Decorator should exist."""
        assert callable(require_consent)
    
    def test_decorator_returns_function(self):
        """Decorator should return a function."""
        decorator = require_consent("data_collection")
        
        assert callable(decorator)
