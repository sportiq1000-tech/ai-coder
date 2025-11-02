"""
Health check endpoint
"""
from fastapi import APIRouter, Depends
from schemas.response_schemas import HealthResponse
from core.models.model_router import get_model_router, ModelRouter
from utils.config import settings
import time

router = APIRouter()

# Track startup time
startup_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    router: ModelRouter = Depends(get_model_router)
):
    """
    Health check endpoint
    Returns system status and model availability
    """
    # Check model availability
    models_status = await router.health_check()
    
    # SECURITY FIX - Phase 1: Remove Bytez from health check (disabled)
    # Remove bytez since it's not currently used
    if 'bytez' in models_status:
        del models_status['bytez']
    
    # Calculate uptime
    uptime = time.time() - startup_time
    
    # Determine overall status (only check active providers)
    all_healthy = all(models_status.values())
    status = "healthy" if all_healthy else "degraded"
    
    return HealthResponse(
        status=status,
        version=settings.APP_VERSION,
        uptime_seconds=uptime,
        models_available=models_status
    )


@router.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"status": "ok", "message": "pong"}