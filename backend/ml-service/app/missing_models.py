# Missing models for explainability module
# These are imported from models.py

from .models import FeatureImportance, PredictionExplanation, IITPrediction

# Alias for backward compatibility with explainability module
Prediction = IITPrediction
