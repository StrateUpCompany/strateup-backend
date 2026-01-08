"""
Authentication Service
LeadHunter AI - JWT + OAuth

Features:
- JWT access/refresh tokens
- Password hashing
- OAuth (Google, GitHub)
- Session management
"""
import os
import secrets
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import jwt
from pydantic import BaseModel, EmailStr
from backend.utils.logger import logger
from backend.core.secrets_manager import get_secret
from backend.core.cache_manager import cache

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

JWT_SECRET = get_secret("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


# =============================================================================
# MODELS
# =============================================================================

class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    ENTERPRISE = "enterprise"


class TokenPayload(BaseModel):
    sub: str  # user_id
    email: str
    role: str
    exp: datetime
    type: str  # "access" or "refresh"


class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None


# =============================================================================
# AUTH SERVICE
# =============================================================================

class AuthService:
    """
    JWT + OAuth authentication service.
    
    Usage:
        auth = AuthService()
        
        # Register
        user = await auth.register("user@example.com", "password123", "John")
        
        # Login
        tokens = await auth.login("user@example.com", "password123")
        
        # Verify token
        payload = auth.verify_token(tokens["access_token"])
    """
    
    _instance = None
    _memory_users: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._memory_users = {}
        self._supabase: Optional[Client] = None
        
        if SUPABASE_AVAILABLE:
            self._connect_supabase()
    
    def _connect_supabase(self):
        """Connect to Supabase"""
        url = get_secret("SUPABASE_URL")
        key = get_secret("SUPABASE_KEY")
        
        if url and key:
            try:
                self._supabase = create_client(url, key)
                logger.info("Connected to Supabase for auth")
            except Exception as e:
                logger.warning(f"Supabase connection failed: {e}")
    
    # =========================================================================
    # PASSWORD UTILITIES
    # =========================================================================
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000
        ).hex()
        return f"{salt}:{pwd_hash}"
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            salt, pwd_hash = hashed.split(":")
            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                100000
            ).hex()
            return new_hash == pwd_hash
        except:
            return False
    
    # =========================================================================
    # TOKEN UTILITIES
    # =========================================================================
    
    def create_access_token(self, user_id: str, email: str, role: str) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": expire,
            "type": "access"
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "exp": expire,
            "type": "refresh"
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def create_tokens(self, user_id: str, email: str, role: str) -> Dict[str, str]:
        """Create access + refresh token pair"""
        return {
            "access_token": self.create_access_token(user_id, email, role),
            "refresh_token": self.create_refresh_token(user_id),
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================
    
    async def register(
        self,
        email: str,
        password: str,
        name: str,
        role: UserRole = UserRole.USER
    ) -> Dict[str, Any]:
        """
        Register a new user.
        
        Returns:
            {"success": bool, "user": dict or None, "error": str or None}
        """
        # Check if user exists
        existing = await self._get_user_by_email(email)
        if existing:
            return {"success": False, "error": "Email already registered"}
        
        user_id = secrets.token_urlsafe(16)
        now = datetime.utcnow().isoformat()
        
        user_data = {
            "id": user_id,
            "email": email,
            "password_hash": self._hash_password(password),
            "name": name,
            "role": role.value,
            "is_active": True,
            "created_at": now,
            "last_login": None
        }
        
        # Store in Supabase
        if self._supabase:
            try:
                self._supabase.table("users").insert(user_data).execute()
                logger.info(f"User registered: {email}")
            except Exception as e:
                logger.error(f"Registration failed: {e}")
                self._memory_users[user_id] = user_data
        else:
            self._memory_users[user_id] = user_data
        
        # Return user without password
        user_data.pop("password_hash")
        return {"success": True, "user": user_data}
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login user and return tokens.
        
        Returns:
            {"success": bool, "tokens": dict or None, "user": dict or None, "error": str or None}
        """
        user = await self._get_user_by_email(email)
        
        if not user:
            return {"success": False, "error": "Invalid credentials"}
        
        if not self._verify_password(password, user.get("password_hash", "")):
            return {"success": False, "error": "Invalid credentials"}
        
        if not user.get("is_active", True):
            return {"success": False, "error": "Account disabled"}
        
        # Update last login
        await self._update_last_login(user["id"])
        
        # Create tokens
        tokens = self.create_tokens(
            user["id"],
            user["email"],
            user.get("role", "user")
        )
        
        # Return user without password
        user.pop("password_hash", None)
        
        return {"success": True, "tokens": tokens, "user": user}
    
    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        """
        payload = self.verify_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            return {"success": False, "error": "Invalid refresh token"}
        
        user = await self._get_user_by_id(payload["sub"])
        if not user:
            return {"success": False, "error": "User not found"}
        
        tokens = self.create_tokens(
            user["id"],
            user["email"],
            user.get("role", "user")
        )
        
        return {"success": True, "tokens": tokens}
    
    async def get_current_user(self, token: str) -> Optional[Dict]:
        """Get current user from access token"""
        payload = self.verify_token(token)
        
        if not payload or payload.get("type") != "access":
            return None
        
        user = await self._get_user_by_id(payload["sub"])
        if user:
            user.pop("password_hash", None)
        
        return user
    
    # =========================================================================
    # OAUTH
    # =========================================================================
    
    async def oauth_login(
        self,
        provider: str,
        provider_id: str,
        email: str,
        name: str
    ) -> Dict[str, Any]:
        """
        Login or register via OAuth provider.
        """
        # Check existing user
        user = await self._get_user_by_email(email)
        
        if not user:
            # Register new OAuth user
            user_id = secrets.token_urlsafe(16)
            now = datetime.utcnow().isoformat()
            
            user = {
                "id": user_id,
                "email": email,
                "name": name,
                "role": "user",
                "is_active": True,
                "created_at": now,
                "oauth_provider": provider,
                "oauth_id": provider_id
            }
            
            if self._supabase:
                try:
                    self._supabase.table("users").insert(user).execute()
                except:
                    self._memory_users[user_id] = user
            else:
                self._memory_users[user_id] = user
        
        # Update last login
        await self._update_last_login(user["id"])
        
        tokens = self.create_tokens(
            user["id"],
            user["email"],
            user.get("role", "user")
        )
        
        return {"success": True, "tokens": tokens, "user": user}
    
    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================
    
    async def _get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        if self._supabase:
            try:
                result = self._supabase.table("users").select("*").eq("email", email).execute()
                if result.data:
                    return result.data[0]
            except:
                pass
        
        for user in self._memory_users.values():
            if user.get("email") == email:
                return user
        
        return None
    
    async def _get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID with caching"""
        # Check cache
        cache_key = f"user:{user_id}"
        cached_user = cache.get(cache_key)
        if cached_user:
            return cached_user
            
        if self._supabase:
            try:
                result = self._supabase.table("users").select("*").eq("id", user_id).execute()
                if result.data:
                    user = result.data[0]
                    # Cache for 5 minutes
                    cache.set(cache_key, user, ttl=300)
                    return user
            except:
                pass
        
        return self._memory_users.get(user_id)
    
    async def _update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        now = datetime.utcnow().isoformat()
        
        if self._supabase:
            try:
                self._supabase.table("users").update({"last_login": now}).eq("id", user_id).execute()
            except:
                pass
        
        if user_id in self._memory_users:
            self._memory_users[user_id]["last_login"] = now


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

auth_service = AuthService()


# =============================================================================
# FASTAPI DEPENDENCIES
# =============================================================================

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """FastAPI dependency to get current authenticated user"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = await auth_service.get_current_user(credentials.credentials)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict]:
    """Optional auth - returns None if not authenticated"""
    if not credentials:
        return None
    
    return await auth_service.get_current_user(credentials.credentials)


def require_role(role: str):
    """Dependency factory to require specific role"""
    async def role_checker(user: Dict = Depends(get_current_user)) -> Dict:
        if user.get("role") != role and user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required"
            )
        return user
    return role_checker
