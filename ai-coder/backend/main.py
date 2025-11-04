"""
Main FastAPI application
"""
from fastapi import FastAPI, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from utils.config import settings
from utils.logger import logger
from api.middleware.rate_limiter import RateLimiterMiddleware
from api.middleware.error_handler import ErrorHandlerMiddleware
from api.routes import health, review, document, bugs, generate, admin
from api.middleware.auth import verify_api_key, verify_admin_api_key
from api.middleware.versioning import APIVersionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from datetime import datetime
import json

# SECURITY FIX - Phase 2C: Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Monkey-patch FastAPI's JSON response to use our encoder
original_jsonresponse_render = JSONResponse.render

def custom_render(self, content) -> bytes:
    return json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
        cls=DateTimeEncoder,  # Use our custom encoder
    ).encode("utf-8")

JSONResponse.render = custom_render

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize cache
    from utils.cache import get_cache
    cache = get_cache()
    
    yield
    
    # Shutdown - close cache connections
    logger.info(f"Shutting down {settings.APP_NAME}")
    await cache.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Driven Software Engineering Assistant API",
    debug=settings.DEBUG,
    lifespan=lifespan
)  # ← Close FastAPI() here

# Mount static files (AFTER creating app)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at root for web interface
@app.get("/ui")
async def serve_ui():
    """Serve the web interface"""
    return FileResponse("static/index.html")

# Add middleware
app.add_middleware(APIVersionMiddleware)  # VERSIONING: Add version middleware first
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimiterMiddleware, requests_per_minute=60)
# SECURITY FIX - Phase 1: Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # SECURITY: Restrict methods
    allow_headers=["Content-Type", "X-API-Key"],  # SECURITY: Restrict headers
)

# VERSIONING: Create v1 API router
v1_router = APIRouter(prefix="/api/v1")

# SECURITY FIX - Phase 1: Include routers with conditional authentication
# Health endpoint - no auth required (for monitoring)
v1_router.include_router(health.router, tags=["Health"])

if settings.AUTH_ENABLED:
    logger.info("🔒 Authentication ENABLED for API endpoints")
    
    # Regular endpoints
    v1_router.include_router(
        review.router,
        tags=["Code Review"],
        dependencies=[Depends(verify_api_key)]
    )
    v1_router.include_router(
        document.router,
        tags=["Documentation"],
        dependencies=[Depends(verify_api_key)]
    )
    v1_router.include_router(
        bugs.router,
        tags=["Bug Prediction"],
        dependencies=[Depends(verify_api_key)]
    )
    v1_router.include_router(
        generate.router,
        tags=["Code Generation"],
        dependencies=[Depends(verify_api_key)]
    )
    
    # SECURITY FIX - Phase 2C: Admin endpoints require admin role
    admin_router = APIRouter(prefix="/admin")
    admin_router.include_router(
        admin.router,
        tags=["Admin"],
        dependencies=[Depends(verify_admin_api_key)]
    )
    v1_router.include_router(admin_router)
    
else:
    logger.warning("⚠️  Authentication DISABLED - do not use in production!")
    v1_router.include_router(review.router, tags=["Code Review"])
    v1_router.include_router(document.router, tags=["Documentation"])
    v1_router.include_router(bugs.router, tags=["Bug Prediction"])
    v1_router.include_router(generate.router, tags=["Code Generation"])
    
    admin_router = APIRouter(prefix="/admin")
    admin_router.include_router(admin.router, tags=["Admin"])
    v1_router.include_router(admin_router)

# VERSIONING: Mount v1 router to app
app.include_router(v1_router)

logger.info("✅ API v1 routes registered at /api/v1/")
logger.info("⚠️  Legacy /api/ routes supported (deprecated)")


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "features": [
            "Code Review",
            "Documentation Generation",
            "Bug Prediction",
            "Code Generation"
        ],
        "admin": {
            "metrics": "/api/v1/admin/metrics",
            "cache_stats": "/api/v1/admin/cache/stats",
            "cache_clear": "/api/v1/admin/cache/clear"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )