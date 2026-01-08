"""
Security Middleware & Utilities
LeadHunter AI - OWASP Compliance

Features:
- Rate limiting per IP and API key
- Security headers (OWASP)
- Input sanitization (XSS, SQL injection)
- CORS configuration
- CSRF protection
- Request signing
"""
import os
import re
import time
import hashlib
import hmac
import secrets
from typing import Dict, Optional, Callable, List, Any
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from backend.utils.logger import logger
from backend.core.secrets_manager import get_secret, get_required_secret


# =============================================================================
# RATE LIMITING (per IP)
# =============================================================================

class IPRateLimiter:
    """
    IP-based rate limiting to prevent DDoS.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self._minute_counts: Dict[str, list] = defaultdict(list)
        self._hour_counts: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed to make a request"""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # Clean old entries
        self._minute_counts[ip] = [t for t in self._minute_counts[ip] if t > minute_ago]
        self._hour_counts[ip] = [t for t in self._hour_counts[ip] if t > hour_ago]
        
        # Check limits
        if len(self._minute_counts[ip]) >= self.requests_per_minute:
            return False
        if len(self._hour_counts[ip]) >= self.requests_per_hour:
            return False
        
        # Record request
        self._minute_counts[ip].append(now)
        self._hour_counts[ip].append(now)
        
        return True
    
    def get_remaining(self, ip: str) -> Dict[str, int]:
        """Get remaining requests for IP"""
        return {
            "minute": max(0, self.requests_per_minute - len(self._minute_counts[ip])),
            "hour": max(0, self.requests_per_hour - len(self._hour_counts[ip]))
        }


# =============================================================================
# API KEY RATE LIMITING
# =============================================================================

class APIKeyRateLimiter:
    """
    API key-based rate limiting for authenticated requests.
    Different limits per tier.
    """
    
    TIER_LIMITS = {
        "free": {"daily": 100, "minute": 10},
        "pro": {"daily": 1000, "minute": 60},
        "enterprise": {"daily": 10000, "minute": 300}
    }
    
    def __init__(self):
        self._daily_counts: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "date": None})
        self._minute_counts: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, api_key_hash: str, tier: str = "free") -> bool:
        """Check if API key is within rate limits"""
        now = time.time()
        today = datetime.now().date()
        limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["free"])
        
        # Reset daily count if new day
        if self._daily_counts[api_key_hash]["date"] != today:
            self._daily_counts[api_key_hash] = {"count": 0, "date": today}
        
        # Clean minute counts
        minute_ago = now - 60
        self._minute_counts[api_key_hash] = [
            t for t in self._minute_counts[api_key_hash] if t > minute_ago
        ]
        
        # Check limits
        if self._daily_counts[api_key_hash]["count"] >= limits["daily"]:
            return False
        if len(self._minute_counts[api_key_hash]) >= limits["minute"]:
            return False
        
        # Record request
        self._daily_counts[api_key_hash]["count"] += 1
        self._minute_counts[api_key_hash].append(now)
        
        return True
    
    def get_usage(self, api_key_hash: str, tier: str = "free") -> Dict[str, Any]:
        """Get current usage for API key"""
        limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["free"])
        daily = self._daily_counts[api_key_hash]
        
        return {
            "daily_used": daily["count"],
            "daily_limit": limits["daily"],
            "daily_remaining": max(0, limits["daily"] - daily["count"]),
            "minute_used": len(self._minute_counts[api_key_hash]),
            "minute_limit": limits["minute"]
        }


# =============================================================================
# INPUT SANITIZATION
# =============================================================================

class InputSanitizer:
    """
    Input sanitization to prevent XSS and injection.
    """
    
    # Patterns to remove/escape
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<object',
        r'<embed',
        r'<svg[^>]*onload',
        r'<img[^>]*onerror',
        r'expression\s*\(',
        r'vbscript:',
        r'data:text/html',
    ]
    
    SQL_PATTERNS = [
        r";\s*--",
        r"'\s*OR\s+'",
        r"UNION\s+SELECT",
        r"DROP\s+TABLE",
        r"DELETE\s+FROM",
        r"INSERT\s+INTO",
        r"UPDATE\s+.*\s+SET",
        r"EXEC\s*\(",
        r"EXECUTE\s*\(",
    ]
    
    PATH_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"/etc/passwd",
        r"/etc/shadow",
        r"C:\\Windows",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """Remove potentially dangerous content from string"""
        if not isinstance(value, str):
            return value
        
        # Remove XSS patterns
        for pattern in cls.XSS_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Escape HTML entities
        value = value.replace('<', '&lt;').replace('>', '&gt;')
        value = value.replace('"', '&quot;').replace("'", '&#x27;')
        
        return value
    
    @classmethod
    def is_safe_sql(cls, value: str) -> bool:
        """Check if string is safe from SQL injection"""
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False
        return True
    
    @classmethod
    def is_safe_path(cls, value: str) -> bool:
        """Check if string is safe from path traversal"""
        for pattern in cls.PATH_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False
        return True
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path separators
        filename = filename.replace('/', '').replace('\\', '')
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
        # Remove leading dots
        filename = filename.lstrip('.')
        return filename or 'unnamed'


# =============================================================================
# CSRF PROTECTION
# =============================================================================

class CSRFProtection:
    """
    CSRF token generation and validation.
    """
    
    TOKEN_LENGTH = 32
    TOKEN_HEADER = "X-CSRF-Token"
    TOKEN_COOKIE = "csrf_token"
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or get_secret("JWT_SECRET") or secrets.token_hex(32)
    
    def generate_token(self, session_id: str) -> str:
        """Generate a CSRF token for a session"""
        timestamp = str(int(time.time()))
        message = f"{session_id}:{timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{timestamp}:{signature}"
    
    def validate_token(self, token: str, session_id: str, max_age: int = 3600) -> bool:
        """Validate a CSRF token"""
        try:
            parts = token.split(':')
            if len(parts) != 2:
                return False
            
            timestamp, signature = parts
            
            # Check age
            token_time = int(timestamp)
            if time.time() - token_time > max_age:
                return False
            
            # Verify signature
            message = f"{session_id}:{timestamp}"
            expected = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected)
        except (ValueError, TypeError):
            return False


# =============================================================================
# REQUEST SIGNING
# =============================================================================

class RequestSigner:
    """
    Sign and verify API requests for enhanced security.
    """
    
    SIGNATURE_HEADER = "X-Signature"
    TIMESTAMP_HEADER = "X-Timestamp"
    MAX_REQUEST_AGE = 300  # 5 minutes
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or get_secret("API_SIGNING_KEY", "")
    
    def sign_request(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Generate signature headers for a request"""
        timestamp = str(int(time.time()))
        message = f"{method}:{path}:{timestamp}:{body}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            self.TIMESTAMP_HEADER: timestamp,
            self.SIGNATURE_HEADER: signature
        }
    
    def verify_request(
        self, 
        method: str, 
        path: str, 
        body: str,
        timestamp: str,
        signature: str
    ) -> bool:
        """Verify a signed request"""
        try:
            # Check timestamp freshness
            request_time = int(timestamp)
            if abs(time.time() - request_time) > self.MAX_REQUEST_AGE:
                return False
            
            # Verify signature
            message = f"{method}:{path}:{timestamp}:{body}"
            expected = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected)
        except (ValueError, TypeError):
            return False


# =============================================================================
# SECURITY HEADERS
# =============================================================================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none';"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
}


def get_security_headers() -> Dict[str, str]:
    """Get security headers for responses"""
    return SECURITY_HEADERS.copy()


# =============================================================================
# SECURITY MIDDLEWARE
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Add security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        return response


# =============================================================================
# CORS CONFIGURATION
# =============================================================================

def get_cors_origins() -> list:
    """Get allowed CORS origins from environment"""
    origins_str = get_secret(
        "CORS_ORIGINS", 
        "http://localhost:5173,http://localhost:3000"
    )
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


def get_allowed_hosts() -> list:
    """Get allowed hosts from environment"""
    hosts_str = get_secret(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1"
    )
    return [host.strip() for host in hosts_str.split(",") if host.strip()]


# =============================================================================
# SECURITY AUDIT
# =============================================================================

class SecurityAudit:
    """
    Security audit and vulnerability checking.
    """
    
    WEAK_SECRETS = [
        "secret", "password", "admin", "root", "test", "demo",
        "your-super-secret-jwt-key-change-in-production",
        "changeme", "default", "123456"
    ]
    
    @staticmethod
    def check_env_security() -> Dict[str, Any]:
        """Comprehensive environment security check"""
        jwt_secret = get_secret("JWT_SECRET", "")
        
        checks = {
            "jwt_secret_set": bool(jwt_secret),
            "jwt_secret_strong": len(jwt_secret) >= 32,
            "jwt_secret_not_default": jwt_secret.lower() not in SecurityAudit.WEAK_SECRETS,
            "jwt_secret_strong": len(jwt_secret) >= 32,
            "jwt_secret_not_default": jwt_secret.lower() not in SecurityAudit.WEAK_SECRETS,
            "debug_disabled": get_secret("DEBUG", "false").lower() != "true",
            "https_enforced": get_secret("ENFORCE_HTTPS", "false").lower() == "true",
            "cors_restrictive": get_secret("CORS_ORIGINS", "*") != "*",
            "allowed_hosts_set": get_secret("ALLOWED_HOSTS", "*") != "*",
        }
        
        # Calculate security score
        passed = sum(checks.values())
        total = len(checks)
        checks["score"] = f"{passed}/{total}"
        checks["passed"] = passed == total
        
        return checks
    
    @staticmethod
    def check_headers_security(headers: Dict) -> Dict[str, bool]:
        """Check if security headers are present"""
        required = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]
        result = {h: h in headers for h in required}
        result["all_present"] = all(result.values())
        return result
    
    @staticmethod
    def get_security_report() -> Dict[str, Any]:
        """Generate comprehensive security report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "environment": SecurityAudit.check_env_security(),
            "recommendations": SecurityAudit._get_recommendations()
        }
    
    @staticmethod
    def _get_recommendations() -> List[str]:
        """Get security recommendations based on current config"""
        recommendations = []
        
        jwt_secret = get_secret("JWT_SECRET", "")
        if len(jwt_secret) < 32:
            recommendations.append("Generate a stronger JWT_SECRET (at least 32 chars)")
        
        if get_secret("DEBUG", "").lower() == "true":
            recommendations.append("Disable DEBUG mode in production")
        
        if get_secret("CORS_ORIGINS", "*") == "*":
            recommendations.append("Configure specific CORS_ORIGINS instead of wildcard")
        
        if get_secret("ENFORCE_HTTPS", "").lower() != "true":
            recommendations.append("Enable ENFORCE_HTTPS for production")
        
        if not get_secret("SENTRY_DSN"):
            recommendations.append("Configure Sentry for error monitoring")
        
        return recommendations


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

ip_rate_limiter = IPRateLimiter()
api_key_rate_limiter = APIKeyRateLimiter()
input_sanitizer = InputSanitizer()
security_audit = SecurityAudit()
csrf_protection = CSRFProtection()
request_signer = RequestSigner()
