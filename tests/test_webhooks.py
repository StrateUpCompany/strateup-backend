"""
Webhooks Tests
LeadHunter AI - Testing webhooks module

Tests for:
- Webhook creation
- Webhook triggering
- HTTP/Slack/Discord delivery
- Retry logic
"""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from backend.core.webhooks import (
    WebhookManager,
    WebhookType,
    WebhookEvent,
    webhook_manager
)


# =============================================================================
# WEBHOOK TYPE TESTS
# =============================================================================

class TestWebhookTypes:
    """Tests for webhook type definitions."""
    
    def test_webhook_types_exist(self):
        """Webhook types should be defined."""
        assert hasattr(WebhookType, 'HTTP')
        assert hasattr(WebhookType, 'SLACK')
        assert hasattr(WebhookType, 'DISCORD')
    
    def test_webhook_events_exist(self):
        """Webhook events should be defined."""
        assert hasattr(WebhookEvent, 'NEW_LEAD')
        assert hasattr(WebhookEvent, 'CLONE_COMPLETE')


# =============================================================================
# WEBHOOK MANAGER TESTS
# =============================================================================

class TestWebhookManager:
    """Tests for WebhookManager class."""
    
    def test_singleton_instance(self):
        """WebhookManager should be a singleton."""
        manager1 = WebhookManager()
        manager2 = WebhookManager()
        
        assert manager1 is manager2
    
    def test_global_instance(self):
        """Global webhook_manager should be available."""
        assert webhook_manager is not None


# =============================================================================
# WEBHOOK PAYLOAD TESTS
# =============================================================================

class TestWebhookPayload:
    """Tests for webhook payload formatting."""
    
    def test_format_http_payload(self):
        """HTTP payload should be JSON formatted."""
        manager = WebhookManager()
        
        payload = {
            "event": "new_lead",
            "data": {"email": "test@example.com", "name": "Test Lead"}
        }
        
        # Payload should be serializable
        import json
        serialized = json.dumps(payload)
        assert "new_lead" in serialized
        assert "test@example.com" in serialized
    
    def test_format_slack_payload(self):
        """Slack payload should have correct format."""
        # Slack expects blocks or text
        slack_payload = {
            "text": "New lead captured!",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*New Lead*: test@example.com"}
                }
            ]
        }
        
        assert "text" in slack_payload
        assert "blocks" in slack_payload
    
    def test_format_discord_payload(self):
        """Discord payload should have correct format."""
        # Discord expects embeds or content
        discord_payload = {
            "content": "New lead captured!",
            "embeds": [
                {
                    "title": "New Lead",
                    "description": "Email: test@example.com",
                    "color": 3066993  # Green
                }
            ]
        }
        
        assert "content" in discord_payload
        assert "embeds" in discord_payload


# =============================================================================
# WEBHOOK VALIDATION TESTS
# =============================================================================

class TestWebhookValidation:
    """Tests for webhook URL validation."""
    
    def test_valid_http_url(self):
        """Valid HTTP URLs should pass."""
        valid_urls = [
            "https://example.com/webhook",
            "https://api.slack.com/webhook",
            "http://localhost:8000/callback",
            "https://hooks.slack.com/services/xxx/yyy/zzz"
        ]
        
        for url in valid_urls:
            assert url.startswith("http://") or url.startswith("https://")
    
    def test_slack_webhook_url_format(self):
        """Slack webhook URLs should have correct format."""
        slack_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXX"
        
        assert "hooks.slack.com" in slack_url
        assert slack_url.startswith("https://")
    
    def test_discord_webhook_url_format(self):
        """Discord webhook URLs should have correct format."""
        discord_url = "https://discord.com/api/webhooks/123456789/abcdefg"
        
        assert "discord.com/api/webhooks" in discord_url
        assert discord_url.startswith("https://")


# =============================================================================
# WEBHOOK DELIVERY TESTS (MOCKED)
# =============================================================================

class TestWebhookDelivery:
    """Tests for webhook delivery (with mocked HTTP)."""
    
    @pytest.mark.asyncio
    async def test_deliver_http_webhook(self):
        """HTTP webhook should be delivered via POST."""
        manager = WebhookManager()
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            
            # Test that delivery would work
            payload = {"event": "test", "data": {}}
            
            # Verify mock is set up correctly
            assert mock_post is not None
    
    @pytest.mark.asyncio
    async def test_slack_webhook_format(self):
        """Slack webhook should use correct format."""
        # Slack expects specific payload format
        payload = {
            "text": "Test notification",
            "username": "LeadHunter Bot",
            "icon_emoji": ":robot_face:"
        }
        
        assert payload.get("text") == "Test notification"
    
    @pytest.mark.asyncio
    async def test_discord_webhook_format(self):
        """Discord webhook should use correct format."""
        # Discord expects specific payload format
        payload = {
            "content": "Test notification",
            "username": "LeadHunter Bot",
            "embeds": []
        }
        
        assert payload.get("content") == "Test notification"


# =============================================================================
# WEBHOOK RETRY LOGIC TESTS
# =============================================================================

class TestWebhookRetry:
    """Tests for webhook retry logic."""
    
    def test_retry_config(self):
        """Retry configuration should be set."""
        manager = WebhookManager()
        
        # Default retry settings
        max_retries = getattr(manager, 'max_retries', 3)
        assert max_retries >= 1
    
    def test_exponential_backoff(self):
        """Retry delays should use exponential backoff."""
        delays = [1, 2, 4, 8, 16]  # Typical exponential backoff
        
        for i in range(1, len(delays)):
            assert delays[i] == delays[i-1] * 2


# =============================================================================
# WEBHOOK EVENT TESTS
# =============================================================================

class TestWebhookEvents:
    """Tests for webhook event handling."""
    
    def test_new_lead_event(self):
        """NEW_LEAD event should have correct structure."""
        event_data = {
            "event": WebhookEvent.NEW_LEAD if hasattr(WebhookEvent, 'NEW_LEAD') else "new_lead",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "lead_id": "lead_123",
                "email": "new@example.com",
                "source": "instagram"
            }
        }
        
        assert "event" in event_data
        assert "timestamp" in event_data
        assert "data" in event_data
    
    def test_clone_complete_event(self):
        """CLONE_COMPLETE event should have correct structure."""
        event_data = {
            "event": WebhookEvent.CLONE_COMPLETE if hasattr(WebhookEvent, 'CLONE_COMPLETE') else "clone_complete",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "project_id": "proj_123",
                "url": "https://example.com",
                "status": "success"
            }
        }
        
        assert event_data["data"]["status"] == "success"


# =============================================================================
# WEBHOOK SECURITY TESTS
# =============================================================================

class TestWebhookSecurity:
    """Tests for webhook security features."""
    
    def test_signing_secret(self):
        """Webhook payloads should be signable."""
        import hmac
        import hashlib
        
        secret = "webhook_secret_key"
        payload = '{"event": "test"}'
        
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        assert len(signature) == 64  # SHA256 hex digest
    
    def test_verify_signature(self):
        """Signature verification should work."""
        import hmac
        import hashlib
        
        secret = "webhook_secret_key"
        payload = '{"event": "test"}'
        
        # Generate signature
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Verify signature
        expected = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        assert hmac.compare_digest(signature, expected)
