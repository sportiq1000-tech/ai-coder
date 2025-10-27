"""
Admin endpoints for metrics and cache management
"""
from fastapi import APIRouter, HTTPException
from utils.cache import get_cache
from utils.metrics import get_metrics
from utils.logger import logger

router = APIRouter()


@router.get("/metrics")
async def get_metrics_stats(last_n: int = 100):
    """
    Get usage metrics and statistics
    
    - **last_n**: Number of recent requests to analyze (default: 100)
    """
    try:
        metrics = get_metrics()
        stats = metrics.get_stats(last_n=last_n)
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """Get detailed cache statistics"""
    try:
        cache = get_cache()
        stats = await cache.get_stats()
        
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cache"""
    try:
        cache = get_cache()
        await cache.clear()
        logger.info("Cache cleared via admin endpoint")
        return {
            "status": "success",
            "message": "Cache cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))