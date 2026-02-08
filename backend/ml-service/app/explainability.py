"""
Explainability Features for IIT Prediction ML Service
Provides feature importance calculation, prediction explanations, and interpretability tools
"""
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session
from sqlalchemy import desc

from .core.db import get_db
from .models import Prediction, FeatureImportance, PredictionExplanation
from .ml_model import get_model
from .model_registry import get_model_registry, ModelMetadata
from .monitoring import MetricsManager

logger = logging.getLogger(__name__)


@dataclass
class FeatureContribution:
    """Feature contribution to a prediction"""
    feature_name: str
    contribution: float
    feature_value: Any
    importance_rank: int


@dataclass
class PredictionExplanationData:
    """Complete prediction explanation"""
    prediction_id: str
    patient_uuid: str
    risk_score: float
    risk_level: str
    model_version: str
    feature_contributions: List[FeatureContribution]
    top_positive_factors: List[FeatureContribution]
    top_negative_factors: List[FeatureContribution]
    explanation_summary: str
    confidence_score: float
    created_at: str


class ExplainabilityEngine:
    """Engine for generating model explanations and feature importance"""

    def __init__(self):
        self.model = get_model()
        self.registry = get_model_registry()

    def calculate_feature_importance(
        self,
        model_id: str,
        db: Session,
        sample_size: int = 1000
    ) -> Dict[str, float]:
        """Calculate global feature importance for a model"""
        try:
            # Get recent predictions for importance calculation
            recent_predictions = db.query(Prediction).filter(
                Prediction.model_version == model_id
            ).order_by(desc(Prediction.created_at)).limit(sample_size).all()

            if not recent_predictions:
                logger.warning(f"No predictions found for model {model_id}")
                return {}

            # Extract features and predictions
            features_list = []
            predictions = []

            for pred in recent_predictions:
                if pred.features_used:
                    features = json.loads(pred.features_used)
                    features_list.append(features)
                    predictions.append(pred.iit_risk_score)

            if not features_list:
                return {}

            # Calculate feature importance using permutation importance
            try:
                feature_importance = self._calculate_permutation_importance(
                    features_list, predictions
                )

                # Store in database
                self._store_feature_importance(model_id, feature_importance, db)

                return feature_importance
            except Exception as e:
                logger.error(f"Failed to calculate permutation importance: {e}")
                return {}

        except Exception as e:
            logger.error(f"Failed to calculate feature importance: {e}")
            return {}

    def explain_prediction(
        self,
        prediction_id: str,
        db: Session
    ) -> Optional[PredictionExplanationData]:
        """Generate explanation for a specific prediction"""
        try:
            # Get prediction details
            prediction = db.query(Prediction).filter(
                Prediction.prediction_id == prediction_id
            ).first()

            if not prediction:
                return None

            # Parse features
            if not prediction.features_used:
                return None

            features = json.loads(prediction.features_used)

            # Calculate feature contributions
            contributions = self._calculate_feature_contributions(
                features, prediction.iit_risk_score
            )

            # Sort contributions
            sorted_contributions = sorted(
                contributions,
                key=lambda x: abs(x.contribution),
                reverse=True
            )

            # Add importance ranks
            for i, contrib in enumerate(sorted_contributions):
                contrib.importance_rank = i + 1

            # Get top positive and negative factors
            top_positive = [c for c in sorted_contributions if c.contribution > 0][:5]
            top_negative = [c for c in sorted_contributions if c.contribution < 0][:5]

            # Generate explanation summary
            explanation_summary = self._generate_explanation_summary(
                prediction.iit_risk_score,
                top_positive,
                top_negative
            )

            # Calculate confidence score
            confidence_score = self._calculate_explanation_confidence(sorted_contributions)

            explanation_data = PredictionExplanationData(
                prediction_id=prediction_id,
                patient_uuid=prediction.patient_uuid,
                risk_score=prediction.iit_risk_score,
                risk_level=prediction.iit_risk_level,
                model_version=prediction.model_version,
                feature_contributions=sorted_contributions,
                top_positive_factors=top_positive,
                top_negative_factors=top_negative,
                explanation_summary=explanation_summary,
                confidence_score=confidence_score,
                created_at=datetime.utcnow().isoformat()
            )

            # Store explanation
            self._store_prediction_explanation(explanation_data, db)

            # Record metrics
            MetricsManager.record_explainability_request("prediction_explanation")

            return explanation_data

        except Exception as e:
            logger.error(f"Failed to explain prediction {prediction_id}: {e}")
            return None

    def get_model_interpretability_report(
        self,
        model_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Generate comprehensive interpretability report for a model"""
        try:
            # Get feature importance
            feature_importance = self._get_stored_feature_importance(model_id, db)

            # Get recent explanations
            recent_explanations = db.query(PredictionExplanation).filter(
                PredictionExplanation.model_version == model_id
            ).order_by(desc(PredictionExplanation.created_at)).limit(100).all()

            # Analyze explanation patterns
            explanation_patterns = self._analyze_explanation_patterns(recent_explanations)

            # Generate report
            report = {
                "model_id": model_id,
                "feature_importance": feature_importance,
                "explanation_patterns": explanation_patterns,
                "interpretability_metrics": self._calculate_interpretability_metrics(recent_explanations),
                "generated_at": datetime.utcnow().isoformat()
            }

            return report

        except Exception as e:
            logger.error(f"Failed to generate interpretability report for {model_id}: {e}")
            return {}

    def _calculate_permutation_importance(
        self,
        features_list: List[Dict[str, Any]],
        predictions: List[float]
    ) -> Dict[str, float]:
        """Calculate permutation feature importance"""
        try:
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(features_list)

            # Get baseline score (simplified - using mean prediction as baseline)
            baseline_score = np.mean(predictions)

            importance_scores = {}

            # For each feature, calculate importance
            for feature in df.columns:
                if df[feature].dtype in ['int64', 'float64']:
                    # Permute numeric features
                    permuted_values = np.random.permutation(df[feature].values)
                    permuted_df = df.copy()
                    permuted_df[feature] = permuted_values

                    # Calculate score drop (simplified)
                    permuted_predictions = self._predict_with_features(permuted_df.to_dict('records'))
                    permuted_score = np.mean(permuted_predictions)

                    importance = abs(baseline_score - permuted_score)
                    importance_scores[feature] = importance

            # Normalize importance scores
            if importance_scores:
                max_importance = max(importance_scores.values())
                if max_importance > 0:
                    importance_scores = {
                        k: v / max_importance for k, v in importance_scores.items()
                    }

            return importance_scores

        except Exception as e:
            logger.error(f"Failed to calculate permutation importance: {e}")
            return {}

    def _calculate_feature_contributions(
        self,
        features: Dict[str, Any],
        prediction_score: float
    ) -> List[FeatureContribution]:
        """Calculate individual feature contributions to prediction"""
        contributions = []

        try:
            # Get feature importance from model registry
            active_model = self.registry.get_active_model(get_db())
            if active_model:
                model_id, metadata = active_model
                feature_importance = metadata.feature_importance or {}

                for feature_name, value in features.items():
                    importance = feature_importance.get(feature_name, 0.1)  # Default importance

                    # Calculate contribution (simplified approach)
                    # In practice, this would use SHAP or LIME values
                    contribution = importance * (value if isinstance(value, (int, float)) else 1.0)

                    contributions.append(FeatureContribution(
                        feature_name=feature_name,
                        contribution=contribution,
                        feature_value=value,
                        importance_rank=0  # Will be set later
                    ))

        except Exception as e:
            logger.error(f"Failed to calculate feature contributions: {e}")

        return contributions

    def _predict_with_features(self, features_list: List[Dict[str, Any]]) -> List[float]:
        """Get predictions for feature sets (simplified)"""
        # This is a placeholder - in practice would use the actual model
        return [0.5] * len(features_list)

    def _generate_explanation_summary(
        self,
        risk_score: float,
        top_positive: List[FeatureContribution],
        top_negative: List[FeatureContribution]
    ) -> str:
        """Generate human-readable explanation summary"""
        risk_level = "High" if risk_score > 0.7 else "Medium" if risk_score > 0.3 else "Low"

        summary_parts = [f"The patient has a {risk_level.lower()} IIT risk score of {risk_score:.3f}."]

        if top_positive:
            positive_factors = [f"{c.feature_name} ({c.contribution:.3f})" for c in top_positive[:3]]
            summary_parts.append(f"Key risk factors include: {', '.join(positive_factors)}.")

        if top_negative:
            negative_factors = [f"{c.feature_name} ({abs(c.contribution):.3f})" for c in top_negative[:3]]
            summary_parts.append(f"Protective factors include: {', '.join(negative_factors)}.")

        return " ".join(summary_parts)

    def _calculate_explanation_confidence(self, contributions: List[FeatureContribution]) -> float:
        """Calculate confidence score for the explanation"""
        if not contributions:
            return 0.0

        # Simple confidence based on contribution distribution
        total_contribution = sum(abs(c.contribution) for c in contributions)
        top_contributions = sum(abs(c.contribution) for c in contributions[:5])

        if total_contribution > 0:
            return min(top_contributions / total_contribution, 1.0)
        return 0.0

    def _store_feature_importance(
        self,
        model_id: str,
        importance: Dict[str, float],
        db: Session
    ):
        """Store feature importance in database"""
        try:
            for feature_name, importance_score in importance.items():
                feature_imp = FeatureImportance(
                    model_version=model_id,
                    feature_name=feature_name,
                    importance_score=importance_score,
                    calculated_at=datetime.utcnow()
                )
                db.add(feature_imp)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to store feature importance: {e}")
            db.rollback()

    def _store_prediction_explanation(
        self,
        explanation: PredictionExplanationData,
        db: Session
    ):
        """Store prediction explanation in database"""
        try:
            exp_record = PredictionExplanation(
                prediction_id=explanation.prediction_id,
                patient_uuid=explanation.patient_uuid,
                model_version=explanation.model_version,
                risk_score=explanation.risk_score,
                risk_level=explanation.risk_level,
                feature_contributions=json.dumps([asdict(c) for c in explanation.feature_contributions]),
                top_positive_factors=json.dumps([asdict(c) for c in explanation.top_positive_factors]),
                top_negative_factors=json.dumps([asdict(c) for c in explanation.top_negative_factors]),
                explanation_summary=explanation.explanation_summary,
                confidence_score=explanation.confidence_score,
                created_at=datetime.fromisoformat(explanation.created_at)
            )
            db.add(exp_record)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to store prediction explanation: {e}")
            db.rollback()

    def _get_stored_feature_importance(self, model_id: str, db: Session) -> Dict[str, float]:
        """Retrieve stored feature importance"""
        try:
            importance_records = db.query(FeatureImportance).filter(
                FeatureImportance.model_version == model_id
            ).order_by(desc(FeatureImportance.calculated_at)).all()

            return {rec.feature_name: rec.importance_score for rec in importance_records}
        except Exception as e:
            logger.error(f"Failed to get stored feature importance: {e}")
            return {}

    def _analyze_explanation_patterns(self, explanations: List[PredictionExplanation]) -> Dict[str, Any]:
        """Analyze patterns in prediction explanations"""
        if not explanations:
            return {}

        try:
            # Extract common patterns
            risk_levels = [exp.risk_level for exp in explanations]
            confidence_scores = [exp.confidence_score for exp in explanations]

            return {
                "total_explanations": len(explanations),
                "risk_level_distribution": pd.Series(risk_levels).value_counts().to_dict(),
                "average_confidence": np.mean(confidence_scores),
                "confidence_distribution": {
                    "high": sum(1 for c in confidence_scores if c > 0.8),
                    "medium": sum(1 for c in confidence_scores if 0.5 <= c <= 0.8),
                    "low": sum(1 for c in confidence_scores if c < 0.5)
                }
            }
        except Exception as e:
            logger.error(f"Failed to analyze explanation patterns: {e}")
            return {}

    def _calculate_interpretability_metrics(self, explanations: List[PredictionExplanation]) -> Dict[str, float]:
        """Calculate interpretability metrics"""
        if not explanations:
            return {}

        try:
            confidence_scores = [exp.confidence_score for exp in explanations]

            return {
                "average_explanation_confidence": np.mean(confidence_scores),
                "explanation_stability": np.std(confidence_scores),
                "total_features_explained": len(set(
                    feature for exp in explanations
                    for contrib in json.loads(exp.feature_contributions or '[]')
                    for feature in [contrib.get('feature_name')]
                ))
            }
        except Exception as e:
            logger.error(f"Failed to calculate interpretability metrics: {e}")
            return {}


# Global explainability engine instance
_explainability_engine: Optional[ExplainabilityEngine] = None


def get_explainability_engine() -> ExplainabilityEngine:
    """Get or create global explainability engine instance"""
    global _explainability_engine
    if _explainability_engine is None:
        _explainability_engine = ExplainabilityEngine()
    return _explainability_engine
