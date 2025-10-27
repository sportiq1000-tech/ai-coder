"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from utils.config import settings
from utils.logger import logger
from api.middleware.rate_limiter import RateLimiterMiddleware
from api.middleware.error_handler import ErrorHandlerMiddleware
from api.routes import health, review, document, bugs, generate, admin
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimiterMiddleware, requests_per_minute=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(review.router, prefix="/api", tags=["Code Review"])
app.include_router(document.router, prefix="/api", tags=["Documentation"])
app.include_router(bugs.router, prefix="/api", tags=["Bug Prediction"])
app.include_router(generate.router, prefix="/api", tags=["Code Generation"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


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
            "metrics": "/api/admin/metrics",
            "cache_stats": "/api/admin/cache/stats",
            "cache_clear": "/api/admin/cache/clear"
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