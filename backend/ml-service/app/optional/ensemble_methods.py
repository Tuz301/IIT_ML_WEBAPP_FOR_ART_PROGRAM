"""
Ensemble Methods for IIT Prediction ML Service
Implements model stacking, boosting, and ensemble prediction strategies
"""
import json
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

import numpy as np
import pandas as pd

from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..core.db import get_db
from ..models import EnsembleConfiguration, EnsemblePrediction
from ..ml_model import get_model
from ..model_registry import get_model_registry, ModelMetadata
from ..monitoring import MetricsManager

logger = logging.getLogger(__name__)


class EnsembleType(Enum):
    """Types of ensemble methods"""
    AVERAGING = "averaging"
    WEIGHTED_AVERAGING = "weighted_averaging"
    VOTING = "voting"
    WEIGHTED_VOTING = "weighted_voting"
    STACKING = "stacking"
    BOOSTING = "boosting"


class VotingStrategy(Enum):
    """Voting strategies for classification"""
    MAJORITY = "majority"
    SOFT = "soft"
    WEIGHTED = "weighted"


@dataclass
class EnsembleConfigurationData:
    """Configuration for ensemble methods"""
    ensemble_type: EnsembleType
    model_ids: List[str]
    weights: Optional[List[float]] = None
    voting_strategy: VotingStrategy = VotingStrategy.SOFT
    meta_model_id: Optional[str] = None
    threshold: float = 0.5


@dataclass
class EnsemblePredictionResult:
    """Result of ensemble prediction"""
    ensemble_id: str
    prediction_id: str
    patient_uuid: str
    ensemble_score: float
    risk_level: str
    individual_predictions: Dict[str, float]
    confidence_score: float
    created_at: str


class EnsembleEngine:
    """Engine for managing ensemble predictions"""

    def __init__(self):
        self.model = get_model()
        self.registry = get_model_registry()

    def create_ensemble(
        self,
        config: EnsembleConfigurationData,
        db: Session
    ) -> str:
        """Create a new ensemble configuration"""
        try:
            # Validate configuration
            self._validate_ensemble_config(config, db)

            # Generate ensemble ID
            ensemble_id = str(uuid.uuid4())

            # Store configuration
            ensemble_config = EnsembleConfiguration(
                ensemble_id=ensemble_id,
                ensemble_type=config.ensemble_type.value,
                model_ids=json.dumps(config.model_ids),
                weights=json.dumps(config.weights) if config.weights else None,
                voting_strategy=config.voting_strategy.value,
                meta_model_id=config.meta_model_id,
                threshold=config.threshold,
                created_at=datetime.utcnow()
            )

            db.add(ensemble_config)
            db.commit()

            logger.info(f"Created ensemble {ensemble_id} with type {config.ensemble_type.value}")
            return ensemble_id

        except Exception as e:
            logger.error(f"Failed to create ensemble: {e}")
            db.rollback()
            raise

    def predict_with_ensemble(
        self,
        ensemble_id: str,
        patient_uuid: str,
        features: Dict[str, Any],
        db: Session
    ) -> Optional[EnsemblePredictionResult]:
        """Make prediction using ensemble"""
        try:
            # Get ensemble configuration
            ensemble_config = db.query(EnsembleConfiguration).filter(
                EnsembleConfiguration.ensemble_id == ensemble_id
            ).first()

            if not ensemble_config:
                return None

            # Parse configuration
            config = EnsembleConfigurationData(
                ensemble_type=EnsembleType(ensemble_config.ensemble_type),
                model_ids=json.loads(ensemble_config.model_ids),
                weights=json.loads(ensemble_config.weights) if ensemble_config.weights else None,
                voting_strategy=VotingStrategy(ensemble_config.voting_strategy),
                meta_model_id=ensemble_config.meta_model_id,
                threshold=ensemble_config.threshold
            )

            # Get individual model predictions
            individual_predictions = {}
            for model_id in config.model_ids:
                try:
                    prediction = self._get_model_prediction(model_id, features)
                    individual_predictions[model_id] = prediction
                except Exception as e:
                    logger.warning(f"Failed to get prediction from model {model_id}: {e}")
                    individual_predictions[model_id] = 0.5  # Default

            # Apply ensemble method
            ensemble_score = self._apply_ensemble_method(
                config, individual_predictions, features
            )

            # Determine risk level
            risk_level = self._score_to_risk_level(ensemble_score)

            # Calculate confidence
            confidence_score = self._calculate_ensemble_confidence(
                ensemble_score, list(individual_predictions.values())
            )

            # Create result
            result = EnsemblePredictionResult(
                ensemble_id=ensemble_id,
                prediction_id=str(uuid.uuid4()),
                patient_uuid=patient_uuid,
                ensemble_score=ensemble_score,
                risk_level=risk_level,
                individual_predictions=individual_predictions,
                confidence_score=confidence_score,
                created_at=datetime.utcnow().isoformat()
            )

            # Store prediction
            self._store_ensemble_prediction(result, db)

            # Record metrics
            MetricsManager.record_ensemble_prediction(
                config.ensemble_type.value,
                ensemble_config.meta_model_id or config.model_ids[0]
            )

            return result

        except Exception as e:
            logger.error(f"Failed to make ensemble prediction: {e}")
            return None

    def _validate_ensemble_config(
        self,
        config: EnsembleConfigurationData,
        db: Session
    ):
        """Validate ensemble configuration"""
        if not config.model_ids:
            raise ValueError("At least one model ID required")

        # Check if models exist
        for model_id in config.model_ids:
            if not self.registry.get_model_metadata(model_id, db):
                raise ValueError(f"Model {model_id} not found")

        # Validate weights
        if config.weights and len(config.weights) != len(config.model_ids):
            raise ValueError("Weights length must match model IDs length")

        # Validate meta model for stacking
        if config.ensemble_type == EnsembleType.STACKING and not config.meta_model_id:
            raise ValueError("Meta model required for stacking")

    def _get_model_prediction(self, model_id: str, features: Dict[str, Any]) -> float:
        """Get prediction from individual model"""
        # This is a simplified implementation
        # In practice, this would load the specific model and make prediction
        return np.random.uniform(0, 1)  # Placeholder

    def _apply_ensemble_method(
        self,
        config: EnsembleConfigurationData,
        predictions: Dict[str, float],
        features: Dict[str, Any]
    ) -> float:
        """Apply the specified ensemble method"""
        prediction_values = list(predictions.values())

        if config.ensemble_type == EnsembleType.AVERAGING:
            return np.mean(prediction_values)

        elif config.ensemble_type == EnsembleType.WEIGHTED_AVERAGING:
            if config.weights:
                return np.average(prediction_values, weights=config.weights)
            else:
                return np.mean(prediction_values)

        elif config.ensemble_type == EnsembleType.VOTING:
            return self._apply_voting(config, predictions)

        elif config.ensemble_type == EnsembleType.WEIGHTED_VOTING:
            return self._apply_weighted_voting(config, predictions)

        elif config.ensemble_type == EnsembleType.STACKING:
            return self._apply_stacking(config, predictions, features)

        elif config.ensemble_type == EnsembleType.BOOSTING:
            return self._apply_boosting(config, predictions)

        else:
            # Default to averaging
            return np.mean(prediction_values)

    def _apply_voting(self, config: EnsembleConfigurationData, predictions: Dict[str, float]) -> float:
        """Apply voting ensemble method"""
        if config.voting_strategy == VotingStrategy.SOFT:
            # Soft voting - average probabilities
            return np.mean(list(predictions.values()))

        elif config.voting_strategy == VotingStrategy.MAJORITY:
            # Majority voting - convert to classes and vote
            risk_levels = [self._score_to_risk_level(score) for score in predictions.values()]
            # Convert back to scores for averaging
            score_map = {"Low": 0.2, "Medium": 0.5, "High": 0.8}
            scores = [score_map.get(level, 0.5) for level in risk_levels]
            return np.mean(scores)

        else:
            return np.mean(list(predictions.values()))

    def _apply_weighted_voting(self, config: EnsembleConfigurationData, predictions: Dict[str, float]) -> float:
        """Apply weighted voting ensemble method"""
        if config.weights:
            return np.average(list(predictions.values()), weights=config.weights)
        else:
            return np.mean(list(predictions.values()))

    def _apply_stacking(self, config: EnsembleConfigurationData, predictions: Dict[str, float], features: Dict[str, Any]) -> float:
        """Apply stacking ensemble method"""
        try:
            if config.meta_model_id:
                # Prepare features for meta model
                meta_features = list(predictions.values()) + list(features.values())

                # Get prediction from meta model
                meta_prediction = self._get_model_prediction(config.meta_model_id, {"stacked_features": meta_features})
                return meta_prediction
            else:
                # Fallback to averaging
                return np.mean(list(predictions.values()))
        except Exception as e:
            logger.warning(f"Stacking failed, falling back to averaging: {e}")
            return np.mean(list(predictions.values()))

    def _apply_boosting(self, config: EnsembleConfigurationData, predictions: Dict[str, float]) -> float:
        """Apply boosting ensemble method"""
        try:
            # Simple boosting - weight better models higher
            sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)

            # Assign weights: 0.5, 0.3, 0.2, etc.
            weights = []
            remaining_weight = 1.0
            for i, (model_id, score) in enumerate(sorted_predictions):
                if i == 0:
                    weight = 0.5
                elif i == 1:
                    weight = 0.3
                else:
                    weight = remaining_weight
                weights.append(weight)
                remaining_weight -= weight
                if remaining_weight <= 0:
                    break

            # Apply weights
            weighted_scores = [score * weight for (model_id, score), weight in zip(sorted_predictions, weights)]
            return sum(weighted_scores) / sum(weights) if weights else np.mean(list(predictions.values()))

        except Exception as e:
            logger.warning(f"Boosting failed, falling back to averaging: {e}")
            return np.mean(list(predictions.values()))

    def _score_to_risk_level(self, score: float) -> str:
        """Convert score to risk level"""
        if score >= 0.7:
            return "High"
        elif score >= 0.3:
            return "Medium"
        else:
            return "Low"

    def _calculate_ensemble_confidence(self, ensemble_score: float, individual_scores: List[float]) -> float:
        """Calculate confidence score for ensemble prediction"""
        if not individual_scores:
            return 0.0

        # Calculate agreement between models
        mean_score = np.mean(individual_scores)
        std_score = np.std(individual_scores)

        # Higher confidence if models agree (low std) and score is not borderline
        agreement_confidence = max(0, 1 - std_score)
        position_confidence = 1 - abs(ensemble_score - 0.5) * 2  # Lower confidence near 0.5

        return (agreement_confidence + position_confidence) / 2

    def _store_ensemble_prediction(self, result: EnsemblePredictionResult, db: Session):
        """Store ensemble prediction in database"""
        try:
            prediction_record = EnsemblePrediction(
                prediction_id=result.prediction_id,
                ensemble_id=result.ensemble_id,
                patient_uuid=result.patient_uuid,
                ensemble_score=result.ensemble_score,
                risk_level=result.risk_level,
                individual_predictions=json.dumps(result.individual_predictions),
                confidence_score=result.confidence_score,
                created_at=datetime.fromisoformat(result.created_at)
            )

            db.add(prediction_record)
            db.commit()

        except Exception as e:
            logger.error(f"Failed to store ensemble prediction: {e}")
            db.rollback()


# Global ensemble engine instance
_ensemble_engine: Optional[EnsembleEngine] = None


def get_ensemble_engine() -> EnsembleEngine:
    """Get or create global ensemble engine instance"""
    global _ensemble_engine
    if _ensemble_engine is None:
        _ensemble_engine = EnsembleEngine()
    return _ensemble_engine
