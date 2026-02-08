"""
API routers for IIT ML Service
"""
from fastapi import APIRouter
from .patients import router as patients_router
from .features import router as features_router
from .predictions import router as predictions_router
from .visits import router as visits_router
from .observations import router as observations_router
from .ab_testing import router as ab_testing_router
from .explainability import router as explainability_router
from .ensemble import router as ensemble_router
from .hyperparameter_tuning import router as hyperparameter_tuning_router

# Import modules for direct access in main.py
from . import patients, observations, visits, predictions, auth, features, analytics, explainability, ensemble, backup, cache, security


# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(
    patients_router,
    prefix="/patients",
    tags=["Patients"]
)

api_router.include_router(
    features_router,
    prefix="/features",
    tags=["Features"]
)

api_router.include_router(
    predictions_router,
    prefix="/predictions",
    tags=["Predictions"]
)

api_router.include_router(
    visits_router,
    prefix="/visits",
    tags=["Visits"]
)



api_router.include_router(
    observations_router,
    prefix="/observations",
    tags=["Observations"]
)

api_router.include_router(
    ab_testing_router,
    prefix="/ab-testing",
    tags=["A/B Testing"]
)

api_router.include_router(
    explainability_router,
    prefix="/explainability",
    tags=["Explainability"]
)

api_router.include_router(
    ensemble_router,
    prefix="/ensemble",
    tags=["Ensemble Methods"]
)

api_router.include_router(
    hyperparameter_tuning_router,
    prefix="/hyperparameter-tuning",
    tags=["Hyperparameter Tuning"]
)

# api_router.include_router(
#     etl_router,
#     prefix="/etl",
#     tags=["ETL"]
# )

__all__ = ["api_router"]
