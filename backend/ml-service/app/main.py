from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import patients, observations, visits, predictions, auth, features, analytics, explainability, ensemble, backup, etl, cache, security
from .middleware.security import SecurityMonitoringMiddleware, setup_security_headers
from .middleware.validation import create_validation_middleware
from .middleware.error_handling import setup_error_handlers
from .health import router as health_router
from .config import get_settings

settings = get_settings()

app = FastAPI(title="IIT ML Service", version="1.0.0")

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

# Add validation middleware (disabled due to body consumption issue)
# app.middleware("http")(create_validation_middleware())

# Enhanced security monitoring middleware (ASGI middleware - wraps the app)
if settings.security_enabled:
    app = SecurityMonitoringMiddleware(
        app,
        exclude_paths=settings.security_exclude_paths
    )

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(patients.router, prefix="/v1", tags=["patients"])
app.include_router(observations.router, prefix="/v1", tags=["observations"])  # Fixed: added /v1 prefix
app.include_router(visits.router, prefix="/v1", tags=["visits"])  # Fixed: added /v1 prefix
app.include_router(predictions.router, prefix="/v1", tags=["predictions"])
app.include_router(auth.router, prefix="/v1", tags=["auth"])
app.include_router(features.router, prefix="/v1", tags=["features"])
app.include_router(analytics.router, prefix="/v1", tags=["analytics"])
app.include_router(explainability.router, prefix="/v1", tags=["explainability"])
app.include_router(ensemble.router, prefix="/v1", tags=["ensemble"])
app.include_router(backup.router, prefix="/v1", tags=["backup"])
app.include_router(etl.router, prefix="/v1", tags=["etl"])  # Fixed: added missing ETL router
app.include_router(cache.router, prefix="/v1", tags=["cache"])  # Fixed: added missing cache router
app.include_router(security.router, prefix="/v1", tags=["security"])  # Fixed: added missing security router

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
