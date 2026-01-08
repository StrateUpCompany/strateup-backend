"""
Authentication Tests
LeadHunter AI - Testing auth module

Tests for:
- Password hashing
- JWT tokens
- Token creation and verification
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from backend.core.auth import (
    AuthService,
    UserRole,
    auth_service
)


# =============================================================================
# PASSWORD HASHING TESTS
# =============================================================================

class TestPasswordHashing:
    """Tests for password hashing functionality."""
    
    def test_hash_password(self):
        """Password should be hashed."""
        auth = AuthService()
        hashed = auth._hash_password("mypassword123")
        
        assert hashed != "mypassword123"
        assert ":" in hashed  # salt:hash format
    
    def test_hash_different_each_time(self):
        """Same password should produce different hashes (due to salt)."""
        auth = AuthService()
        hash1 = auth._hash_password("samepassword")
        hash2 = auth._hash_password("samepassword")
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
    
    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        auth = AuthService()
        password = "correctpassword"
        hashed = auth._hash_password(password)
        
        assert auth._verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        auth = AuthService()
        hashed = auth._hash_password("correctpassword")
        
        assert auth._verify_password("wrongpassword", hashed) is False
    
    def test_verify_password_empty(self):
        """Empty password should not match anything."""
        auth = AuthService()
        hashed = auth._hash_password("somepassword")
        
        assert auth._verify_password("", hashed) is False


# =============================================================================
# JWT TOKEN TESTS
# =============================================================================

class TestJWTTokens:
    """Tests for JWT token generation and validation."""
    
    def test_create_access_token(self):
        """Should create valid access token."""
        auth = AuthService()
        token = auth.create_access_token(
            user_id="user_123",
            email="test@example.com",
            role="user"
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
    
    def test_create_refresh_token(self):
        """Should create refresh token."""
        auth = AuthService()
        token = auth.create_refresh_token(user_id="user_123")
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_verify_token_valid(self):
        """Valid token should verify successfully."""
        auth = AuthService()
        token = auth.create_access_token(
            user_id="user_456",
            email="verify@example.com",
            role="user"
        )
        
        payload = auth.verify_token(token)
        
        assert payload is not None
        assert payload.get("sub") == "user_456"
        assert payload.get("email") == "verify@example.com"
    
    def test_verify_token_invalid(self):
        """Invalid token should return None."""
        auth = AuthService()
        result = auth.verify_token("invalid.token.here")
        
        assert result is None
    
    def test_verify_token_tampered(self):
        """Tampered token should fail verification."""
        auth = AuthService()
        token = auth.create_access_token(
            user_id="user_789",
            email="tamper@example.com",
            role="user"
        )
        
        # Tamper with the token
        tampered = token[:-10] + "XXXXXXXXXX"
        result = auth.verify_token(tampered)
        
        assert result is None
    
    def test_create_tokens_pair(self):
        """Should create access + refresh token pair."""
        auth = AuthService()
        tokens = auth.create_tokens(
            user_id="user_pair",
            email="pair@example.com",
            role="admin"
        )
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["access_token"] != tokens["refresh_token"]


# =============================================================================
# USER ROLE TESTS
# =============================================================================

class TestUserRoles:
    """Tests for user role handling."""
    
    def test_user_role_values(self):
        """User roles should have correct values."""
        # UserRole is an Enum
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.ENTERPRISE.value == "enterprise"
    
    def test_role_in_token(self):
        """Role should be included in access token."""
        auth = AuthService()
        token = auth.create_access_token(
            user_id="admin_user",
            email="admin@example.com",
            role="admin"
        )
        
        payload = auth.verify_token(token)
        assert payload.get("role") == "admin"


# =============================================================================
# SINGLETON TESTS
# =============================================================================

class TestAuthServiceSingleton:
    """Tests for AuthService singleton pattern."""
    
    def test_singleton_instance(self):
        """AuthService should be a singleton."""
        service1 = AuthService()
        service2 = AuthService()
        
        assert service1 is service2
    
    def test_global_instance(self):
        """Global auth_service should be available."""
        assert auth_service is not None
        assert isinstance(auth_service, AuthService)


# =============================================================================
# TOKEN PAYLOAD TESTS
# =============================================================================

class TestTokenPayload:
    """Tests for token payload structure."""
    
    def test_access_token_has_type(self):
        """Access token should have type field."""
        auth = AuthService()
        token = auth.create_access_token(
            user_id="type_test",
            email="type@example.com",
            role="user"
        )
        
        payload = auth.verify_token(token)
        assert payload.get("type") == "access"
    
    def test_refresh_token_has_type(self):
        """Refresh token should have type field."""
        auth = AuthService()
        token = auth.create_refresh_token(user_id="refresh_type_test")
        
        payload = auth.verify_token(token)
        assert payload.get("type") == "refresh"
    
    def test_token_has_expiry(self):
        """Tokens should have expiry."""
        auth = AuthService()
        token = auth.create_access_token(
            user_id="exp_test",
            email="exp@example.com",
            role="user"
        )
        
        payload = auth.verify_token(token)
        assert "exp" in payload


# =============================================================================
# AUTH SERVICE METHODS TESTS
# =============================================================================

class TestAuthServiceMethods:
    """Tests for AuthService additional methods."""
    
    def test_has_register_method(self):
        """AuthService should have register method."""
        auth = AuthService()
        assert hasattr(auth, 'register')
        assert callable(auth.register)
    
    def test_has_login_method(self):
        """AuthService should have login method."""
        auth = AuthService()
        assert hasattr(auth, 'login')
        assert callable(auth.login)
    
    def test_has_refresh_tokens_method(self):
        """AuthService should have refresh_tokens method."""
        auth = AuthService()
        assert hasattr(auth, 'refresh_tokens')
        assert callable(auth.refresh_tokens)
    
    def test_has_get_current_user_method(self):
        """AuthService should have get_current_user method."""
        auth = AuthService()
        assert hasattr(auth, 'get_current_user')
        assert callable(auth.get_current_user)
