"""
Optional API Routers for IIT ML Service

This directory contains API endpoints for advanced features.

Ensemble router has been re-enabled for production use.
"""

# Export ensemble router for main app
from .ensemble import router as ensemble_router

# AB Testing router remains optional (uncomment to enable)
# from .ab_testing import router as ab_testing_router

__all__ = ['ensemble_router']
