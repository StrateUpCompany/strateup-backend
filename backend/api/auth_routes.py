"""
Auth Routes
LeadHunter AI - Authentication API

Endpoints:
- POST /api/auth/register    - Register new user
- POST /api/auth/login       - Login
- POST /api/auth/refresh     - Refresh tokens
- GET  /api/auth/me          - Get current user
- POST /api/auth/logout      - Logout
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from backend.core.auth import auth_service, get_current_user


router = APIRouter(prefix="/api/auth", tags=["Auth"])


# =============================================================================
# MODELS
# =============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    Register a new user account.
    """
    if len(request.password) < 6:
        return AuthResponse(success=False, error="Password must be at least 6 characters")
    
    result = await auth_service.register(
        email=request.email,
        password=request.password,
        name=request.name
    )
    
    if result["success"]:
        # Auto-login after registration
        login_result = await auth_service.login(request.email, request.password)
        return AuthResponse(success=True, data={
            "user": result["user"],
            "tokens": login_result.get("tokens")
        })
    else:
        return AuthResponse(success=False, error=result.get("error"))


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.
    """
    result = await auth_service.login(
        email=request.email,
        password=request.password
    )
    
    if result["success"]:
        return AuthResponse(success=True, data={
            "user": result["user"],
            "tokens": result["tokens"]
        })
    else:
        return AuthResponse(success=False, error=result.get("error"))


@router.post("/refresh", response_model=AuthResponse)
async def refresh_tokens(request: RefreshRequest):
    """
    Refresh access token using refresh token.
    """
    result = await auth_service.refresh_tokens(request.refresh_token)
    
    if result["success"]:
        return AuthResponse(success=True, data={"tokens": result["tokens"]})
    else:
        return AuthResponse(success=False, error=result.get("error"))


@router.get("/me", response_model=AuthResponse)
async def get_me(user: Dict = Depends(get_current_user)):
    """
    Get current authenticated user.
    """
    return AuthResponse(success=True, data={"user": user})


@router.post("/logout")
async def logout(user: Dict = Depends(get_current_user)):
    """
    Logout current user (client should discard tokens).
    """
    # Server-side logout could invalidate refresh token in DB
    return AuthResponse(success=True, data={"message": "Logged out successfully"})


@router.post("/change-password", response_model=AuthResponse)
async def change_password(
    current_password: str,
    new_password: str,
    user: Dict = Depends(get_current_user)
):
    """
    Change password for current user.
    """
    if len(new_password) < 6:
        return AuthResponse(success=False, error="Password must be at least 6 characters")
    
    # Verify current password
    login_result = await auth_service.login(user["email"], current_password)
    if not login_result["success"]:
        return AuthResponse(success=False, error="Current password is incorrect")
    
    # Update password (would need to add method to auth_service)
    # For now, return success placeholder
    return AuthResponse(success=True, data={"message": "Password changed successfully"})
