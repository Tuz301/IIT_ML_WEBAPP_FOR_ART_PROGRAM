"""
IIT Prediction ML Service
Production-ready ML service for predicting Interruption in Treatment (IIT) risk
"""

__version__ = "1.0.0"

# Import main app for FastAPI
from .main import app

__all__ = ['app']
