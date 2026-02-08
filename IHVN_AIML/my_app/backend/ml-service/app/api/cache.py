"""
Cache management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

from ..middleware.caching import cache_manager, redis_cache
from ..core.db import get_query_cache_stats, invalidate_cache_for_model
from ..auth import get_current_user
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])

@router.get("/stats")
async def get_cache_stats(current_user: User = Depends(get_current_user)):
    """
    Get comprehensive cache statistics

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Get API cache stats
        api_cache_stats = await cache_manager.get_cache_stats()

        # Get query cache stats
        query_cache_stats = get_query_cache_stats()

        return {
            "api_cache": api_cache_stats,
            "query_cache": query_cache_stats,
            "summary": {
                "api_cache_enabled": api_cache_stats.get("status") == "connected",
                "query_cache_enabled": query_cache_stats.get("cache", {}).get("cache_enabled", False),
                "redis_connected": redis_cache.is_connected()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@router.post("/invalidate/all")
async def invalidate_all_cache(current_user: User = Depends(get_current_user)):
    """
    Invalidate all cache entries

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Invalidate API cache
        await cache_manager.invalidate_all_cache()

        # Invalidate query cache (simplified - would need to implement in QueryCache)
        if redis_cache.is_connected():
            await redis_cache.clear_pattern("db_query:*")

        return {"message": "All cache entries invalidated successfully"}

    except Exception as e:
        logger.error(f"Failed to invalidate all cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate cache: {str(e)}")

@router.post("/invalidate/patient/{patient_uuid}")
async def invalidate_patient_cache(
    patient_uuid: str,
    current_user: User = Depends(get_current_user)
):
    """
    Invalidate cache for a specific patient

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Invalidate API cache for patient
        await cache_manager.invalidate_patient_cache(patient_uuid)

        # Invalidate query cache for patient
        invalidate_cache_for_model("Patient", [patient_uuid])

        return {"message": f"Cache invalidated for patient {patient_uuid}"}

    except Exception as e:
        logger.error(f"Failed to invalidate patient cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate patient cache: {str(e)}")

@router.post("/invalidate/endpoint/{endpoint}")
async def invalidate_endpoint_cache(
    endpoint: str,
    current_user: User = Depends(get_current_user)
):
    """
    Invalidate cache for a specific endpoint

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Invalidate API cache for endpoint
        await cache_manager.invalidate_endpoint_cache(endpoint)

        return {"message": f"Cache invalidated for endpoint {endpoint}"}

    except Exception as e:
        logger.error(f"Failed to invalidate endpoint cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate endpoint cache: {str(e)}")

@router.post("/invalidate/model/{model_name}")
async def invalidate_model_cache(
    model_name: str,
    record_ids: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Invalidate cache for a specific model

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Parse record IDs if provided
        ids_list = None
        if record_ids:
            ids_list = [id.strip() for id in record_ids.split(",") if id.strip()]

        # Invalidate query cache for model
        success = invalidate_cache_for_model(model_name, ids_list)

        if success:
            return {"message": f"Cache invalidated for model {model_name}"}
        else:
            raise HTTPException(status_code=500, detail="Cache invalidation failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invalidate model cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate model cache: {str(e)}")

@router.get("/health")
async def get_cache_health():
    """
    Get cache health status (no auth required for monitoring)
    """
    try:
        stats = await cache_manager.get_cache_stats()

        # Determine health status
        is_healthy = (
            stats.get("status") in ["connected", "disabled"] and
            stats.get("size", 0) >= 0  # Basic connectivity check
        )

        return {
            "healthy": is_healthy,
            "status": stats.get("status", "unknown"),
            "size": stats.get("size", 0),
            "hit_ratio": stats.get("hit_ratio", 0.0),
            "total_requests": stats.get("total_requests", 0)
        }

    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
        return {
            "healthy": False,
            "status": "error",
            "error": str(e)
        }

@router.post("/warmup")
async def warmup_cache(current_user: User = Depends(get_current_user)):
    """
    Warm up cache with frequently accessed data

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # This would implement cache warming logic
        # For now, just return success
        logger.info("Cache warmup requested")

        return {"message": "Cache warmup completed (placeholder implementation)"}

    except Exception as e:
        logger.error(f"Cache warmup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cache warmup failed: {str(e)}")

@router.get("/config")
async def get_cache_config(current_user: User = Depends(get_current_user)):
    """
    Get current cache configuration

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        from ..middleware.caching import cache_config

        return {
            "enabled": cache_config.enabled,
            "redis_url": cache_config.redis_url,
            "default_ttl": cache_config.default_ttl,
            "max_cache_size": cache_config.max_cache_size,
            "cacheable_methods": cache_config.cacheable_methods,
            "cacheable_status_codes": cache_config.cacheable_status_codes,
            "exclude_paths": cache_config.exclude_paths,
            "include_headers": cache_config.include_headers
        }

    except Exception as e:
        logger.error(f"Failed to get cache config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache config: {str(e)}")
