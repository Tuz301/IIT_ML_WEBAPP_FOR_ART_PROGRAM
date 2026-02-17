"""
Health check endpoints for IIT ML Service
"""
import logging
import time
from typing import Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import psutil
import os

from .dependencies import get_db
from .config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["health"],
    responses={503: {"description": "Service Unavailable"}}
)

# Track service startup time
START_TIME = time.time()


@router.get("/health", summary="Basic Health Check")
async def health_check():
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "service": "IIT ML Service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - START_TIME)
    }


@router.get("/health/detailed", summary="Detailed Health Check")
async def detailed_health_check(
    db: Session = Depends(get_db)
):
    """
    Comprehensive health check including database and external services
    """
    settings = get_settings()
    health_status = {
        "status": "healthy",
        "service": "IIT ML Service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - START_TIME),
        "checks": {}
    }

    # Database health check
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": 0  # Could measure actual response time
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Redis health check
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            socket_timeout=5
        )
        redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "host": settings.redis_host,
            "port": settings.redis_port
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Model file health check
    try:
        if os.path.exists(settings.model_path):
            model_mtime = datetime.fromtimestamp(os.path.getmtime(settings.model_path))
            health_status["checks"]["model_file"] = {
                "status": "healthy",
                "path": settings.model_path,
                "last_modified": model_mtime.isoformat()
            }
        else:
            health_status["checks"]["model_file"] = {
                "status": "unhealthy",
                "error": f"Model file not found: {settings.model_path}"
            }
            health_status["status"] = "unhealthy"
    except Exception as e:
        logger.error(f"Model file health check failed: {str(e)}")
        health_status["checks"]["model_file"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"

    # System resources check
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        health_status["checks"]["system"] = {
            "status": "healthy",
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent
            },
            "cpu_percent": psutil.cpu_percent(interval=1)
        }

        # Check if resources are critically low
        if memory.percent > 95 or disk.percent > 95:
            health_status["status"] = "unhealthy"
            health_status["checks"]["system"]["status"] = "critical"

    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        health_status["checks"]["system"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Set HTTP status code based on overall health
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


@router.get("/health/ready", summary="Readiness Probe")
async def readiness_check():
    """
    Kubernetes readiness probe - checks if service is ready to serve traffic
    """
    # For now, just return healthy if service is running
    # In production, you might check database connections, model loading, etc.
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/live", summary="Liveness Probe")
async def liveness_check():
    """
    Kubernetes liveness probe - checks if service is alive
    """
    # Simple liveness check - if this endpoint responds, service is alive
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/metrics", summary="Application Metrics")
async def application_metrics():
    """
    Application-specific metrics for monitoring
    """
    settings = get_settings()

    metrics = {
        "service": "IIT ML Service",
        "version": "1.0.0",
        "uptime_seconds": int(time.time() - START_TIME),
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "debug": settings.debug,
            "max_batch_size": settings.max_batch_size,
            "prediction_timeout": settings.prediction_timeout,
            "redis_enabled": bool(settings.redis_host),
            "metrics_enabled": settings.enable_metrics
        }
    }

    # Add system metrics
    try:
        memory = psutil.virtual_memory()
        metrics["system"] = {
            "memory_used_percent": memory.percent,
            "cpu_percent": psutil.cpu_percent(),
            "disk_used_percent": psutil.disk_usage('/').percent
        }
    except Exception as e:
        logger.warning(f"Failed to collect system metrics: {str(e)}")
        metrics["system"] = {"error": "Failed to collect system metrics"}

    return metrics
