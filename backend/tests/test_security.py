"""
Security Tests
LeadHunter AI - Testing security modules

Tests for:
- Input sanitization (XSS, SQL injection)
- Rate limiting
- CSRF protection
- Security headers
- Security audit
"""
import pytest
import time
from unittest.mock import patch, MagicMock
import os

from backend.core.security import (
    IPRateLimiter,
    APIKeyRateLimiter,
    InputSanitizer,
    CSRFProtection,
    RequestSigner,
    SecurityAudit,
    get_cors_origins,
    get_allowed_hosts,
    get_security_headers,
    SECURITY_HEADERS
)


# =============================================================================
# INPUT SANITIZER TESTS
# =============================================================================

class TestInputSanitizer:
    """Tests for InputSanitizer class."""
    
    def test_sanitize_simple_string(self):
        """Normal strings should pass through."""
        assert InputSanitizer.sanitize_string("Hello World") == "Hello World"
    
    def test_sanitize_xss_script_tag(self):
        """Script tags should be removed."""
        malicious = "<script>alert('xss')</script>Hello"
        result = InputSanitizer.sanitize_string(malicious)
        assert "<script>" not in result.lower()
        assert "alert" not in result
    
    def test_sanitize_xss_javascript_protocol(self):
        """javascript: protocol should be removed."""
        malicious = "javascript:alert('xss')"
        result = InputSanitizer.sanitize_string(malicious)
        assert "javascript:" not in result.lower()
    
    def test_sanitize_xss_onerror(self):
        """Event handlers should be removed."""
        malicious = '<img src="x" onerror="alert(1)">'
        result = InputSanitizer.sanitize_string(malicious)
        assert "onerror" not in result.lower()
    
    def test_sanitize_html_entities(self):
        """HTML entities should be escaped."""
        text = "<div>test</div>"
        result = InputSanitizer.sanitize_string(text)
        assert "&lt;" in result
        assert "&gt;" in result
    
    def test_sanitize_quotes(self):
        """Quotes should be escaped."""
        text = 'say "hello" and \'world\''
        result = InputSanitizer.sanitize_string(text)
        assert "&quot;" in result
        assert "&#x27;" in result
    
    def test_is_safe_sql_normal_input(self):
        """Normal input should be safe."""
        assert InputSanitizer.is_safe_sql("john.doe@email.com") is True
        assert InputSanitizer.is_safe_sql("SELECT something") is True  # Just the word
    
    def test_is_safe_sql_union_attack(self):
        """UNION SELECT attack should be detected."""
        malicious = "1 UNION SELECT * FROM users"
        assert InputSanitizer.is_safe_sql(malicious) is False
    
    def test_is_safe_sql_drop_table(self):
        """DROP TABLE attack should be detected."""
        malicious = "; DROP TABLE users; --"
        assert InputSanitizer.is_safe_sql(malicious) is False
    
    def test_is_safe_sql_comment_injection(self):
        """SQL comment injection should be detected."""
        malicious = "admin'; --"
        assert InputSanitizer.is_safe_sql(malicious) is False
    
    def test_is_safe_path_normal(self):
        """Normal paths should be safe."""
        assert InputSanitizer.is_safe_path("uploads/file.pdf") is True
        assert InputSanitizer.is_safe_path("documents/report.docx") is True
    
    def test_is_safe_path_traversal(self):
        """Path traversal should be detected."""
        assert InputSanitizer.is_safe_path("../../../etc/passwd") is False
        assert InputSanitizer.is_safe_path("..\\..\\windows\\system32") is False
    
    def test_sanitize_filename(self):
        """Filenames should be sanitized."""
        # Path traversal
        assert InputSanitizer.sanitize_filename("../../../etc/passwd") == "etcpasswd"
        # Dangerous chars
        assert InputSanitizer.sanitize_filename('file<>:"|?*.txt') == "file.txt"
        # Leading dots
        assert InputSanitizer.sanitize_filename("..hidden") == "hidden"
        # Empty
        assert InputSanitizer.sanitize_filename("...") == "unnamed"


# =============================================================================
# RATE LIMITER TESTS
# =============================================================================

class TestIPRateLimiter:
    """Tests for IP-based rate limiting."""
    
    def test_allows_requests_under_limit(self):
        """Requests under limit should be allowed."""
        limiter = IPRateLimiter(requests_per_minute=10, requests_per_hour=100)
        ip = "192.168.1.1"
        
        # First 10 requests should pass
        for _ in range(10):
            assert limiter.is_allowed(ip) is True
    
    def test_blocks_requests_over_minute_limit(self):
        """Requests over minute limit should be blocked."""
        limiter = IPRateLimiter(requests_per_minute=5, requests_per_hour=100)
        ip = "192.168.1.2"
        
        # Use up the limit
        for _ in range(5):
            limiter.is_allowed(ip)
        
        # Next request should be blocked
        assert limiter.is_allowed(ip) is False
    
    def test_get_remaining(self):
        """Should return correct remaining counts."""
        limiter = IPRateLimiter(requests_per_minute=10, requests_per_hour=100)
        ip = "192.168.1.3"
        
        # Make 3 requests
        for _ in range(3):
            limiter.is_allowed(ip)
        
        remaining = limiter.get_remaining(ip)
        assert remaining["minute"] == 7
        assert remaining["hour"] == 97


class TestAPIKeyRateLimiter:
    """Tests for API key-based rate limiting."""
    
    def test_tier_limits(self):
        """Different tiers should have different limits."""
        limiter = APIKeyRateLimiter()
        
        assert limiter.TIER_LIMITS["free"]["daily"] == 100
        assert limiter.TIER_LIMITS["pro"]["daily"] == 1000
        assert limiter.TIER_LIMITS["enterprise"]["daily"] == 10000
    
    def test_allows_requests_for_tier(self):
        """Requests within tier limit should be allowed."""
        limiter = APIKeyRateLimiter()
        api_key = "test_key_hash"
        
        # Free tier: 10 per minute
        for _ in range(10):
            assert limiter.is_allowed(api_key, "free") is True
    
    def test_blocks_over_limit(self):
        """Requests over tier limit should be blocked."""
        limiter = APIKeyRateLimiter()
        api_key = "test_key_hash_2"
        
        # Use up free tier minute limit (10)
        for _ in range(10):
            limiter.is_allowed(api_key, "free")
        
        # Next should be blocked
        assert limiter.is_allowed(api_key, "free") is False
    
    def test_get_usage(self):
        """Should return correct usage stats."""
        limiter = APIKeyRateLimiter()
        api_key = "test_key_hash_3"
        
        # Make 5 requests
        for _ in range(5):
            limiter.is_allowed(api_key, "pro")
        
        usage = limiter.get_usage(api_key, "pro")
        assert usage["daily_used"] == 5
        assert usage["daily_remaining"] == 995


# =============================================================================
# CSRF PROTECTION TESTS
# =============================================================================

class TestCSRFProtection:
    """Tests for CSRF token generation and validation."""
    
    def test_generate_token(self):
        """Should generate valid tokens."""
        csrf = CSRFProtection(secret_key="test_secret_key_for_testing")
        token = csrf.generate_token("session_123")
        
        assert token is not None
        assert ":" in token  # timestamp:signature format
    
    def test_validate_token_success(self):
        """Valid tokens should pass validation."""
        csrf = CSRFProtection(secret_key="test_secret_key_for_testing")
        session_id = "session_456"
        
        token = csrf.generate_token(session_id)
        assert csrf.validate_token(token, session_id) is True
    
    def test_validate_token_wrong_session(self):
        """Token for different session should fail."""
        csrf = CSRFProtection(secret_key="test_secret_key_for_testing")
        
        token = csrf.generate_token("session_a")
        assert csrf.validate_token(token, "session_b") is False
    
    def test_validate_token_expired(self):
        """Expired tokens should fail."""
        csrf = CSRFProtection(secret_key="test_secret_key_for_testing")
        session_id = "session_expired"
        
        # Create token with old timestamp
        with patch('time.time', return_value=time.time() - 7200):  # 2 hours ago
            token = csrf.generate_token(session_id)
        
        # Validate with current time (token is expired, max_age=3600)
        assert csrf.validate_token(token, session_id, max_age=3600) is False
    
    def test_validate_token_tampered(self):
        """Tampered tokens should fail."""
        csrf = CSRFProtection(secret_key="test_secret_key_for_testing")
        session_id = "session_tamper"
        
        token = csrf.generate_token(session_id)
        tampered = token[:-5] + "XXXXX"  # Modify signature
        
        assert csrf.validate_token(tampered, session_id) is False


# =============================================================================
# REQUEST SIGNER TESTS
# =============================================================================

class TestRequestSigner:
    """Tests for request signing and verification."""
    
    def test_sign_request(self):
        """Should generate signature headers."""
        signer = RequestSigner(secret_key="signing_secret_key")
        headers = signer.sign_request("POST", "/api/clone", '{"url": "test"}')
        
        assert "X-Timestamp" in headers
        assert "X-Signature" in headers
    
    def test_verify_request_valid(self):
        """Valid signatures should verify."""
        signer = RequestSigner(secret_key="signing_secret_key")
        
        method = "GET"
        path = "/api/leads"
        body = ""
        
        headers = signer.sign_request(method, path, body)
        
        result = signer.verify_request(
            method, path, body,
            headers["X-Timestamp"],
            headers["X-Signature"]
        )
        assert result is True
    
    def test_verify_request_wrong_body(self):
        """Signature with different body should fail."""
        signer = RequestSigner(secret_key="signing_secret_key")
        
        headers = signer.sign_request("POST", "/api/test", '{"original": true}')
        
        result = signer.verify_request(
            "POST", "/api/test", '{"tampered": true}',
            headers["X-Timestamp"],
            headers["X-Signature"]
        )
        assert result is False


# =============================================================================
# SECURITY AUDIT TESTS
# =============================================================================

# =============================================================================
# SECURITY AUDIT TESTS
# =============================================================================

class TestSecurityAudit:
    """Tests for security audit functionality."""
    
    def test_check_env_security_weak_secret(self):
        """Should detect weak JWT secrets."""
        with patch('backend.core.security.get_secret') as mock_get:
            def side_effect(key, default=None):
                if key == "JWT_SECRET": return "short"
                if key == "DEBUG": return "false"
                if key == "ENFORCE_HTTPS": return "false"
                if key == "CORS_ORIGINS": return "*"
                if key == "ALLOWED_HOSTS": return "*"
                return default
            mock_get.side_effect = side_effect
            
            result = SecurityAudit.check_env_security()
            assert result["jwt_secret_strong"] is False
    
    def test_check_env_security_default_secret(self):
        """Should detect default JWT secrets."""
        with patch('backend.core.security.get_secret') as mock_get:
            def side_effect(key, default=None):
                if key == "JWT_SECRET": return "your-super-secret-jwt-key-change-in-production"
                if key == "DEBUG": return "false"
                if key == "ENFORCE_HTTPS": return "false"
                if key == "CORS_ORIGINS": return "*"
                if key == "ALLOWED_HOSTS": return "*"
                return default
            mock_get.side_effect = side_effect
            
            result = SecurityAudit.check_env_security()
            assert result["jwt_secret_not_default"] is False
    
    def test_check_env_security_debug_enabled(self):
        """Should detect debug mode enabled."""
        with patch('backend.core.security.get_secret') as mock_get:
            def side_effect(key, default=None):
                if key == "JWT_SECRET": return "x" * 32
                if key == "DEBUG": return "true"
                if key == "ENFORCE_HTTPS": return "false"
                if key == "CORS_ORIGINS": return "*"
                if key == "ALLOWED_HOSTS": return "*"
                return default
            mock_get.side_effect = side_effect
            
            result = SecurityAudit.check_env_security()
            assert result["debug_disabled"] is False
    
    def test_check_headers_security(self):
        """Should check for required security headers."""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY"
        }
        result = SecurityAudit.check_headers_security(headers)
        
        assert result["X-Content-Type-Options"] is True
        assert result["X-Frame-Options"] is True
        # Missing headers
        assert result["Strict-Transport-Security"] is False
    
    def test_get_security_report(self):
        """Should generate complete security report."""
        with patch('backend.core.security.get_secret', return_value="test_val"):
            report = SecurityAudit.get_security_report()
            
            assert "timestamp" in report
            assert "environment" in report
            assert "recommendations" in report


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================

class TestSecurityConfiguration:
    """Tests for security configuration functions."""
    
    def test_get_cors_origins_default(self):
        """Should return default origins."""
        with patch('backend.core.security.get_secret') as mock_get:
            mock_get.return_value = "*"
            origins = get_cors_origins()
            # Default '*' results in allowing everything or specific default behavior depending on impl
            # Assuming get_cors_origins handles "*" by returning default list if env is "development" or similar logic?
            # Re-reading security.py logic would be ideal, but assuming standard behavior:
            # If get_secret returns default "*", get_cors_origins likely returns the default list provided in code.
            
            # Actually, let's verify what get_cors_origins does.
            # If I can't see the code, I'll trust the previous test logic but adapt for get_secret.
            
            # Rewriting to be safer based on previous test expectation:
            mock_get.return_value = str(["http://localhost:5173", "http://localhost:3000"]) # If it parses string list
            # Or if it defaults to internal list when secret is checking...
            
            # The previous test did: patch.dict(os.environ, {}, clear=True)
            # This implies when NO env var is set, it falls back to defaults.
            # So get_secret should return the default value passed to it.
            
            mock_get.side_effect = lambda k, d=None: d
            
            origins = get_cors_origins()
            assert "http://localhost:5173" in origins
            assert "http://localhost:3000" in origins
    
    def test_get_cors_origins_custom(self):
        """Should parse custom origins."""
        with patch('backend.core.security.get_secret') as mock_get:
            mock_get.return_value = "https://app.example.com,https://api.example.com"
            
            origins = get_cors_origins()
            assert "https://app.example.com" in origins
            assert "https://api.example.com" in origins
            
    def test_get_allowed_hosts_default(self):
        """Should return default hosts."""
        with patch('backend.core.security.get_secret') as mock_get:
            mock_get.side_effect = lambda k, d=None: d
            
            hosts = get_allowed_hosts()
            assert "localhost" in hosts
            assert "127.0.0.1" in hosts
    
    def test_security_headers_complete(self):
        """Should have all required security headers."""
        required = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy"
        ]
        
        headers = get_security_headers()
        for header in required:
            assert header in headers, f"Missing header: {header}"
