"""
Admin endpoints for metrics and cache management
"""
from fastapi import APIRouter, HTTPException
from utils.cache import get_cache
from utils.metrics import get_metrics
from utils.logger import logger
from utils.security_monitor import security_monitor
from typing import Optional
from datetime import datetime  # Also add this if not present

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
# Add these new endpoints:

@router.get("/security/events")
async def get_security_events(
    limit: int = 100,
    attack_type: Optional[str] = None,
    endpoint: Optional[str] = None
):
    """
    Get recent security events (blocked requests)
    
    - **limit**: Number of events to return (default: 100)
    - **attack_type**: Filter by attack type (prompt_injection, secret_extraction)
    - **endpoint**: Filter by endpoint (/api/review, /api/generate, etc.)
    """
    events = security_monitor.get_events_from_file(
        limit=limit,
        attack_type=attack_type,
        endpoint=endpoint
    )
    
    return {
        "total_events": len(events),
        "events": events,
        "filters": {
            "limit": limit,
            "attack_type": attack_type,
            "endpoint": endpoint
        }
    }


@router.get("/security/stats")
async def get_security_stats():
    """Get security statistics and attack patterns"""
    stats = security_monitor.get_stats()
    analysis = security_monitor.analyze_attack_patterns()
    
    return {
        "current_session": stats,
        "historical_analysis": analysis,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/security/recent")
async def get_recent_security_events(limit: int = 50):
    """Get most recent security events from memory (fast)"""
    events = security_monitor.get_recent_events(limit=limit)
    
    return {
        "count": len(events),
        "events": events
    }