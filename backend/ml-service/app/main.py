from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import patients, observations, visits, predictions, auth, features, analytics, explainability, backup, etl, cache, security, feature_flags, queue, circuit_breakers, dlq, alerting
from .api.optional import ensemble_router

# Optional features (moved to optional/ directory)
# Uncomment to enable:
# from .optional import vector_store, rag, ai_observability, multi_tenancy, cost_monitoring, incident_response, ab_testing, ensemble_methods
from .middleware.security import SecurityMonitoringMiddleware, setup_security_headers
from .middleware.validation import create_validation_middleware
from .middleware.error_handling import setup_error_handlers
from .middleware.https import HTTPSRedirectMiddleware
from .middleware.idempotency import IdempotencyMiddleware
from .health import router as health_router
from .config import get_settings

settings = get_settings()

app = FastAPI(title="IIT ML Service", version="1.0.0", redirect_slashes=False)

# Setup custom error handlers
setup_error_handlers(app)

# CORS middleware MUST be added first to ensure headers are set correctly
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add validation middleware (fixed - no longer consumes request body)
app.middleware("http")(create_validation_middleware())

# HTTPS redirect middleware (must be added early in the middleware chain)
if settings.force_https:
    app.add_middleware(
        HTTPSRedirectMiddleware,
        force_https=settings.force_https,
        https_port=settings.https_port,
        strict_mode=settings.https_strict,
        excluded_paths=settings.https_exclude_paths
    )

# Idempotency middleware (for safe retries)
if settings.idempotency_enabled:
    app.add_middleware(
        IdempotencyMiddleware,
        enabled=settings.idempotency_enabled,
        ttl=settings.idempotency_ttl,
        header_name=settings.idempotency_header
    )

# Include routers (must be done before security middleware wraps the app)
app.include_router(health_router, tags=["health"])
app.include_router(patients.router, prefix="/v1", tags=["patients"])
app.include_router(observations.router, prefix="/v1", tags=["observations"])  # Fixed: added /v1 prefix
app.include_router(visits.router, prefix="/v1", tags=["visits"])  # Fixed: added /v1 prefix
app.include_router(predictions.router, prefix="/v1", tags=["predictions"])
app.include_router(auth.router, prefix="/v1", tags=["auth"])
app.include_router(features.router, prefix="/v1", tags=["features"])
app.include_router(analytics.router, prefix="/v1", tags=["analytics"])
app.include_router(explainability.router, prefix="/v1", tags=["explainability"])
app.include_router(ensemble_router, prefix="/v1", tags=["ensemble"])
app.include_router(backup.router, prefix="/v1", tags=["backup"])
app.include_router(etl.router, prefix="/v1", tags=["etl"])  # Fixed: added missing ETL router
app.include_router(cache.router, prefix="/v1", tags=["cache"])  # Fixed: added missing cache router
app.include_router(security.router, prefix="/v1", tags=["security"])  # Fixed: added missing security router
app.include_router(feature_flags.router, prefix="/v1", tags=["feature-flags"])  # Feature flags management
app.include_router(queue.router, prefix="/v1", tags=["queue"])  # Queue management
app.include_router(circuit_breakers.router, tags=["circuit-breakers"])  # Circuit breaker monitoring
app.include_router(dlq.router, tags=["dead-letter-queue"])  # Dead letter queue management
app.include_router(alerting.router, prefix="/v1", tags=["alerting"])  # Alerting and notifications

# Security headers middleware (preserves CORS headers)
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    # Only add security headers, don't override CORS headers
    setup_security_headers(response)
    # Ensure CORS headers are preserved
    if "access_control_allow_origin" not in response.headers:
        # This shouldn't happen if CORS middleware is working, but as a fallback
        origin = request.headers.get("origin")
        if origin:
            response.headers["access_control_allow_origin"] = origin
    return response

# Startup event handler
@app.on_event("startup")
async def startup_event():
    """Initialize database, ML model, and telemetry on startup"""
    from .core.db import init_database
    from .ml_model import get_model
    from .telemetry import init_telemetry, instrument_fastapi
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Initialize telemetry
    try:
        if settings.telemetry_enabled:
            init_telemetry(
                service_name="iit-ml-service",
                jaeger_endpoint=settings.jaeger_endpoint,
                jaeger_agent_host_name=settings.jaeger_agent_host,
                jaeger_agent_port=settings.jaeger_agent_port,
                enable_console_export=settings.telemetry_console_export,
                sample_rate=settings.telemetry_sample_rate
            )
            logger.info("OpenTelemetry initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")
    
    # Initialize database tables
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Pre-load ML model
    try:
        model = get_model()
        logger.info(f"ML model loaded: {model is not None}")
    except Exception as e:
        logger.error(f"Failed to load ML model: {e}")


# Enhanced security monitoring middleware (ASGI middleware - wraps the app AFTER everything else is registered)
# This MUST be last so that all decorators and event handlers are registered on the FastAPI app first
if settings.security_enabled:
    app = SecurityMonitoringMiddleware(
        app,
        exclude_paths=settings.security_exclude_paths
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
