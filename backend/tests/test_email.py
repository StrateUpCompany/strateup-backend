"""
Email Service Tests
LeadHunter AI - Testing email module

Tests for:
- Email sending
- Template rendering
- SendGrid integration
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from backend.core.email_service import (
    EmailService,
    EmailTemplate,
    email_service,
    send_email,
    send_template_email
)


# =============================================================================
# EMAIL SERVICE TESTS
# =============================================================================

class TestEmailService:
    """Tests for EmailService class."""
    
    def test_singleton_instance(self):
        """EmailService should be a singleton."""
        service1 = EmailService()
        service2 = EmailService()
        
        assert service1 is service2
    
    def test_global_instance(self):
        """Global email_service instance should be available."""
        assert email_service is not None
        assert isinstance(email_service, EmailService)
    
    def test_is_configured(self):
        """Should check if SendGrid is configured."""
        service = EmailService()
        result = service.is_configured()
        
        assert isinstance(result, bool)


# =============================================================================
# EMAIL TEMPLATE TESTS
# =============================================================================

class TestEmailTemplate:
    """Tests for email template definitions."""
    
    def test_template_values(self):
        """Templates should have correct values."""
        assert EmailTemplate.WELCOME.value == "welcome"
        assert EmailTemplate.LEAD_NURTURE.value == "lead_nurture"
        assert EmailTemplate.PROPOSAL.value == "proposal"
        assert EmailTemplate.WEEKLY_REPORT.value == "weekly_report"
        assert EmailTemplate.CUSTOM.value == "custom"


# =============================================================================
# SEND EMAIL TESTS (MOCKED)
# =============================================================================

class TestSendEmail:
    """Tests for email sending (mocked)."""
    
    @pytest.mark.asyncio
    async def test_send_email(self):
        """Should send email."""
        service = EmailService()
        
        with patch.object(service, '_http_client', MagicMock()) as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_client.post = AsyncMock(return_value=mock_response)
            
            result = await service.send(
                to="test@example.com",
                subject="Test Email",
                html="<p>This is a test</p>"
            )
            
            # Should return result dict
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_send_template_email(self):
        """Should send templated email."""
        service = EmailService()
        
        with patch.object(service, 'send', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}
            
            result = await service.send_template(
                to="test@example.com",
                template=EmailTemplate.WELCOME,
                data={"name": "John", "company": "Acme"}
            )
            
            assert isinstance(result, dict)


# =============================================================================
# TEMPLATE RENDERING TESTS
# =============================================================================

class TestTemplateRendering:
    """Tests for template rendering."""
    
    def test_render_template(self):
        """Should render template with variables."""
        service = EmailService()
        
        html = service._render_template(
            "Hello {{name}}, welcome to {{company}}!",
            {"name": "John", "company": "Acme"}
        )
        
        assert "John" in html
        assert "Acme" in html


# =============================================================================
# BULK EMAIL TESTS
# =============================================================================

class TestBulkEmail:
    """Tests for bulk email functionality."""
    
    @pytest.mark.asyncio
    async def test_send_bulk(self):
        """Should send bulk emails."""
        service = EmailService()
        
        recipients = [
            {"email": "user1@example.com", "data": {"name": "User 1"}},
            {"email": "user2@example.com", "data": {"name": "User 2"}},
        ]
        
        with patch.object(service, 'send_template', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}
            
            result = await service.send_bulk(
                recipients=recipients,
                template=EmailTemplate.WELCOME,
                common_data={"company": "Acme"}
            )
            
            assert isinstance(result, dict)
            assert "success" in result or "failed" in result


# =============================================================================
# GET TEMPLATES TESTS
# =============================================================================

class TestGetTemplates:
    """Tests for listing templates."""
    
    def test_get_templates(self):
        """Should list available templates."""
        service = EmailService()
        
        templates = service.get_templates()
        
        assert isinstance(templates, list)
        assert len(templates) > 0


# =============================================================================
# GET STATS TESTS
# =============================================================================

class TestGetStats:
    """Tests for email statistics."""
    
    def test_get_stats(self):
        """Should get email stats."""
        service = EmailService()
        
        stats = service.get_stats()
        
        assert isinstance(stats, dict)


# =============================================================================
# PREVIEW TEMPLATE TESTS
# =============================================================================

class TestPreviewTemplate:
    """Tests for template preview."""
    
    def test_preview_template(self):
        """Should preview rendered template."""
        service = EmailService()
        
        preview = service.preview_template(
            template=EmailTemplate.WELCOME,
            data={"name": "Test", "company": "Acme"}
        )
        
        assert isinstance(preview, dict)
        assert "html" in preview or "subject" in preview


# =============================================================================
# CONVENIENCE FUNCTIONS TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    @pytest.mark.asyncio
    async def test_send_email_function(self):
        """Convenience send_email function should work."""
        with patch.object(email_service, 'send', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}
            
            result = await send_email(
                to="test@example.com",
                subject="Test",
                html="<p>Test</p>"
            )
            
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_send_template_email_function(self):
        """Convenience send_template_email function should work."""
        with patch.object(email_service, 'send_template', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}
            
            result = await send_template_email(
                to="test@example.com",
                template="welcome",
                data={"name": "Test"}
            )
            
            assert isinstance(result, dict)
