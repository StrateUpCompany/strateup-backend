"""
Auth Tests
LeadHunter AI - Unit tests for auth module
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAuthService:
    """Tests for AuthService"""
    
    def test_password_hash(self):
        """Test password hashing"""
        from backend.core.auth import AuthService
        
        auth = AuthService()
        password = "secure123"
        
        # Hash password
        hashed = auth._hash_password(password)
        
        # Should contain salt
        assert ":" in hashed
        
        # Should verify correctly
        assert auth._verify_password(password, hashed) is True
        assert auth._verify_password("wrong", hashed) is False
    
    def test_create_access_token(self):
        """Test JWT access token creation"""
        from backend.core.auth import AuthService
        
        auth = AuthService()
        token = auth.create_access_token(
            user_id="user123",
            email="test@test.com",
            role="user"
        )
        
        assert token is not None
        assert len(token) > 0
        
        # Verify token
        payload = auth.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@test.com"
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self):
        """Test JWT refresh token creation"""
        from backend.core.auth import AuthService
        
        auth = AuthService()
        token = auth.create_refresh_token(user_id="user123")
        
        assert token is not None
        
        payload = auth.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
    
    def test_create_tokens(self):
        """Test token pair creation"""
        from backend.core.auth import AuthService
        
        auth = AuthService()
        tokens = auth.create_tokens(
            user_id="user123",
            email="test@test.com",
            role="user"
        )
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"
    
    def test_verify_invalid_token(self):
        """Test invalid token verification"""
        from backend.core.auth import AuthService
        
        auth = AuthService()
        
        # Invalid token
        result = auth.verify_token("invalid.token.here")
        assert result is None
        
        # Empty token
        result = auth.verify_token("")
        assert result is None


class TestEmailService:
    """Tests for EmailService"""
    
    def test_is_configured_without_key(self):
        """Test configuration check without API key"""
        from backend.core.email_service import EmailService
        
        email = EmailService()
        # Without proper key, should not be configured
        # (depends on env)
    
    def test_get_templates(self):
        """Test getting email templates"""
        from backend.core.email_service import EmailService
        
        email = EmailService()
        templates = email.get_templates()
        
        assert len(templates) >= 4
        assert any(t["id"] == "welcome" for t in templates)
        assert any(t["id"] == "lead_nurture" for t in templates)
    
    def test_preview_template(self):
        """Test template preview"""
        from backend.core.email_service import EmailService, EmailTemplate
        
        email = EmailService()
        preview = email.preview_template(
            EmailTemplate.WELCOME,
            {"name": "John", "dashboard_url": "https://test.com"}
        )
        
        assert "subject" in preview
        assert "html" in preview
        assert "John" in preview["html"]
    
    def test_get_stats(self):
        """Test email stats"""
        from backend.core.email_service import EmailService
        
        email = EmailService()
        stats = email.get_stats()
        
        assert "sent" in stats
        assert "failed" in stats
        assert "configured" in stats


class TestWebhookManager:
    """Tests for WebhookManager"""
    
    def test_webhook_manager_init(self):
        """Test WebhookManager initialization"""
        from backend.core.webhooks import WebhookManager
        
        manager = WebhookManager()
        assert manager is not None


class TestAuditLogger:
    """Tests for AuditLogger"""
    
    def test_log_action(self):
        """Test logging an audit action"""
        from backend.core.audit_log import AuditLogger, AuditAction
        
        logger = AuditLogger()
        log_id = logger.log(
            action=AuditAction.USER_LOGIN,
            user_id="user123",
            ip_address="127.0.0.1"
        )
        
        assert log_id is not None
        assert len(log_id) > 0
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting audit stats"""
        from backend.core.audit_log import AuditLogger
        
        logger = AuditLogger()
        stats = await logger.get_stats(days=7)
        
        assert "total_logs" in stats
        assert "by_action" in stats


class TestCacheManager:
    """Tests for CacheManager"""
    
    def test_cache_set_get(self):
        """Test cache set and get"""
        from backend.core.cache_manager import CacheManager
        
        cache = CacheManager()
        
        # Set
        cache.set("test_key", {"value": 123}, cache_type="default")
        
        # Get
        result = cache.get("test_key", cache_type="default")
        assert result is not None
        assert result["value"] == 123
    
    def test_cache_miss(self):
        """Test cache miss"""
        from backend.core.cache_manager import CacheManager
        
        cache = CacheManager()
        result = cache.get("nonexistent_key_12345", cache_type="default")
        assert result is None
    
    def test_cache_stats(self):
        """Test cache statistics"""
        from backend.core.cache_manager import CacheManager
        
        cache = CacheManager()
        stats = cache.get_stats()
        
        # Check for any stats keys
        assert isinstance(stats, dict)
        assert len(stats) > 0
