"""
LeadHunter AI - Main Application
FastAPI Backend with Security Hardening
LeadHunter AI - Main Application
FastAPI Backend with Security Hardening
LeadHunter AI - Main Application
FastAPI Backend with Security Hardening
# Reload trigger: pSEO router fix
"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path
import os
import sentry_sdk

# Load env from root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Routers
from backend.api.router import router as api_router
from backend.api.api_v1_routes import router as api_v1_router
from backend.api.analytics_routes import router as analytics_router
from backend.api.webhook_routes import router as webhook_router
from backend.api.audit_routes import router as audit_router
from backend.api.email_routes import router as email_router
from backend.api.auth_routes import router as auth_router
from backend.api.tenant_routes import router as tenant_router
from backend.api.integrations_routes import router as integrations_router
from backend.api.billing_routes import router as billing_router
from backend.api.monitoring_routes import router as monitoring_router
from backend.api.enrichment_routes import router as enrichment_router
from backend.api.search_routes import router as search_router
from backend.api.export_routes import router as export_router
from backend.api.websocket_manager import manager as ws_manager
from backend.core.migrator import DatabaseMigrator
from backend.core.secrets_manager import get_secret, get_required_secret

# Security
from backend.core.security import (
    get_cors_origins, 
    get_allowed_hosts, 
    get_security_headers,
    SecurityHeadersMiddleware,
    security_audit
)

# Rate Limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from backend.utils.limiter import limiter


# =============================================================================
# SENTRY INITIALIZATION (ONCE)
# =============================================================================

sentry_dsn = get_secret("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=get_secret("ENVIRONMENT", "development"),
        release=f"leadhunter-ai@2.0.0",
    )


# =============================================================================
# LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Run Migrations
    migrator = DatabaseMigrator()
    migrator.run_migrations()

    # Startup: Set loop for WS Manager
    ws_manager.set_loop(asyncio.get_running_loop())
    
    # Startup: Security audit
    security_status = security_audit.check_env_security()
    if not security_status.get("passed"):
        import logging
        logging.warning(f"Security audit warnings: {security_status}")
    
    yield
    # Shutdown logic if needed


# =============================================================================
# APP INITIALIZATION
# =============================================================================

API_DESCRIPTION = """
## LeadHunter AI API

All-in-One platform for Funnel Hacking, Cloning & Market Intelligence.

### Features

* **Funnel Cloner** - Clone landing pages with CSS/JS
* **Market Intelligence** - AI-powered copy analysis
* **Data Hunter** - Lead collection from Instagram/Google Maps
* **Form Hijacking** - Replace forms with your webhooks

### Authentication

Use Bearer token in Authorization header:
```
Authorization: Bearer <your_token>
```

### Rate Limits

| Tier | Daily | Per Minute |
|------|-------|------------|
| Free | 100 | 10 |
| Pro | 1,000 | 60 |
| Enterprise | 10,000 | 300 |

### Support

Contact: support@leadhunter.ai
"""

from fastapi.responses import ORJSONResponse

app = FastAPI(
    title="LeadHunter AI API",
    description=API_DESCRIPTION,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    default_response_class=ORJSONResponse,
    openapi_tags=[
        {"name": "auth", "description": "Authentication & authorization"},
        {"name": "clone", "description": "Funnel cloning operations"},
        {"name": "scrape", "description": "Data collection from social/maps"},
        {"name": "leads", "description": "Lead management"},
        {"name": "analytics", "description": "Analytics & metrics"},
        {"name": "webhooks", "description": "Webhook configuration"},
        {"name": "admin", "description": "Admin operations"},
    ]
)


# =============================================================================
# MIDDLEWARE STACK (Order matters!)
# =============================================================================

# 0. Compression (Gzip)
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 1. Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 2. Trusted Hosts (from environment, not wildcard)
allowed_hosts = get_allowed_hosts()
if allowed_hosts and allowed_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# 3. Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 3.5 Performance Caching (GET only)
from backend.core.performance import CacheMiddleware
app.add_middleware(
    CacheMiddleware, 
    ttl=60, 
    enabled_routes=[
        "/api/v1/public",  # Public data
        "/api/templates",   # Templates rarely change
        "/api/projects",    # Cache project lists
    ]
)

# 4. CORS Configuration (from environment)
cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)


# =============================================================================
# ROUTERS
# =============================================================================

app.include_router(api_router, prefix="/api")
app.include_router(api_v1_router)  # /api/v1/* routes
app.include_router(analytics_router)  # /api/analytics/* routes
app.include_router(webhook_router)  # /api/webhooks/* routes
app.include_router(audit_router)  # /api/audit/* routes
app.include_router(email_router)  # /api/email/* routes
app.include_router(auth_router)  # /api/auth/* routes
app.include_router(tenant_router)  # /api/tenant/* routes
app.include_router(integrations_router)  # /api/integrations/* routes
app.include_router(billing_router)  # /api/billing/* routes
app.include_router(monitoring_router)  # /metrics, /health/detailed
app.include_router(enrichment_router)  # /api/enrichment/* routes
app.include_router(search_router)  # /api/search/* routes
app.include_router(export_router)  # /api/export/* routes


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================

@app.get("/", tags=["health"])
def read_root():
    """Root endpoint - API status check."""
    return {
        "status": "online", 
        "message": "LeadHunter AI Backend is running 🚀",
        "version": "2.0.0"
    }


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy"}


@app.get("/security/audit", tags=["admin"])
def security_audit_endpoint():
    """Security audit endpoint (admin only in production)."""
    return security_audit.get_security_report()

@app.get("/sanity-check")
def sanity_check():
    return {"status": "alive"}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=get_secret("DEBUG", "false").lower() == "true"
    )
