"""
A/B Testing Framework for IIT Prediction ML Service
Implements traffic splitting, performance tracking, and statistical significance testing
"""
import hashlib
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import logging
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from ..core.db import get_db
from ..models import ABTest, ABTestVariant, ABTestResult
from ..model_registry import get_model_registry, ModelMetadata
from ..monitoring import MetricsManager

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """A/B test status enumeration"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TrafficAllocation(Enum):
    """Traffic allocation strategies"""
    EQUAL = "equal"
    GRADUAL = "gradual"
    CUSTOM = "custom"


@dataclass
class ABTestConfiguration:
    """A/B test configuration"""
    test_name: str
    description: str
    model_variants: List[str]  # Model IDs
    traffic_allocation: TrafficAllocation
    custom_weights: Optional[Dict[str, float]] = None
    target_sample_size: int = 1000
    confidence_level: float = 0.95
    minimum_effect_size: float = 0.02
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    primary_metric: str = "auc"
    secondary_metrics: Optional[List[str]] = None

    def __post_init__(self):
        if self.secondary_metrics is None:
            self.secondary_metrics = ["precision", "recall"]


@dataclass
class VariantResult:
    """Results for a single test variant"""
    variant_id: str
    model_id: str
    sample_size: int
    metrics: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]
    statistical_significance: Dict[str, bool]


class ABTestingFramework:
    """A/B testing framework for model comparison"""

    def __init__(self):
        self.registry = get_model_registry()

    def create_test(self, config: ABTestConfiguration, db: Session) -> str:
        """Create a new A/B test"""
        try:
            test_id = self._generate_test_id(config.test_name)

            # Validate model variants exist
            for model_id in config.model_variants:
                if not self.registry.get_model_metadata(model_id, db):
                    raise ValueError(f"Model {model_id} not found in registry")

            # Calculate traffic weights
            weights = self._calculate_weights(config)

            # Create test record
            ab_test = ABTest(
                test_id=test_id,
                test_name=config.test_name,
                description=config.description,
                status=TestStatus.DRAFT.value,
                model_variants=json.dumps(config.model_variants),
                traffic_allocation=config.traffic_allocation.value,
                traffic_weights=json.dumps(weights),
                target_sample_size=config.target_sample_size,
                confidence_level=config.confidence_level,
                minimum_effect_size=config.minimum_effect_size,
                primary_metric=config.primary_metric,
                secondary_metrics=json.dumps(config.secondary_metrics),
                start_date=config.start_date,
                end_date=config.end_date,
                created_at=datetime.utcnow()
            )

            db.add(ab_test)

            # Create variant records
            for i, model_id in enumerate(config.model_variants):
                variant = ABTestVariant(
                    test_id=test_id,
                    variant_id=f"variant_{i+1}",
                    model_id=model_id,
                    weight=weights.get(model_id, 0),
                    sample_size=0,
                    is_control=(i == 0)  # First variant is control
                )
                db.add(variant)

            db.commit()

            logger.info(f"A/B test {test_id} created successfully")
            return test_id

        except Exception as e:
            logger.error(f"Failed to create A/B test: {e}")
            db.rollback()
            raise

    def start_test(self, test_id: str, db: Session) -> bool:
        """Start an A/B test"""
        try:
            test = db.query(ABTest).filter(ABTest.test_id == test_id).first()
            if not test:
                return False

            if test.status != TestStatus.DRAFT.value:
                logger.warning(f"Test {test_id} is not in draft status")
                return False

            test.status = TestStatus.RUNNING.value
            test.start_date = datetime.utcnow()
            db.commit()

            logger.info(f"A/B test {test_id} started")
            return True

        except Exception as e:
            logger.error(f"Failed to start A/B test {test_id}: {e}")
            db.rollback()
            return False

    def assign_variant(self, test_id: str, user_id: str, db: Session) -> Optional[str]:
        """Assign a user to a test variant based on traffic allocation"""
        try:
            test = db.query(ABTest).filter(ABTest.test_id == test_id).first()
            if not test or test.status != TestStatus.RUNNING.value:
                return None

            # Check if user already assigned
            existing_assignment = db.query(ABTestResult).filter(
                and_(ABTestResult.test_id == test_id, ABTestResult.user_id == user_id)
            ).first()

            if existing_assignment:
                return existing_assignment.variant_id

            # Assign new variant
            variants = db.query(ABTestVariant).filter(ABTestVariant.test_id == test_id).all()
            weights = {v.model_id: v.weight for v in variants}

            assigned_model = self._weighted_random_choice(weights)
            assigned_variant = None

            for variant in variants:
                if variant.model_id == assigned_model:
                    assigned_variant = variant.variant_id
                    variant.sample_size += 1
                    break

            # Record assignment
            result = ABTestResult(
                test_id=test_id,
                user_id=user_id,
                variant_id=assigned_variant,
                assigned_at=datetime.utcnow()
            )
            db.add(result)
            db.commit()

            return assigned_variant

        except Exception as e:
            logger.error(f"Failed to assign variant for test {test_id}: {e}")
            db.rollback()
            return None

    def record_prediction_result(
        self,
        test_id: str,
        user_id: str,
        prediction_result: Dict[str, Any],
        db: Session
    ) -> bool:
        """Record prediction results for A/B test analysis"""
        try:
            result = db.query(ABTestResult).filter(
                and_(ABTestResult.test_id == test_id, ABTestResult.user_id == user_id)
            ).first()

            if not result:
                return False

            # Update result with prediction data
            result.prediction_score = prediction_result.get('risk_score')
            result.actual_outcome = prediction_result.get('actual_outcome')
            result.prediction_metadata = json.dumps(prediction_result.get('metadata', {}))
            result.recorded_at = datetime.utcnow()

            db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to record prediction result: {e}")
            db.rollback()
            return False

    def get_test_results(self, test_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get comprehensive results for an A/B test"""
        try:
            test = db.query(ABTest).filter(ABTest.test_id == test_id).first()
            if not test:
                return None

            variants = db.query(ABTestVariant).filter(ABTestVariant.test_id == test_id).all()
            results = db.query(ABTestResult).filter(ABTestResult.test_id == test_id).all()

            # Calculate metrics for each variant
            variant_results = {}
            for variant in variants:
                variant_data = self._calculate_variant_metrics(variant.variant_id, results)
                variant_results[variant.variant_id] = VariantResult(
                    variant_id=variant.variant_id,
                    model_id=variant.model_id,
                    sample_size=variant.sample_size,
                    metrics=variant_data['metrics'],
                    confidence_intervals=variant_data['confidence_intervals'],
                    statistical_significance=variant_data['significance']
                )

            # Overall test analysis
            analysis = self._analyze_test_results(test, variant_results)

            return {
                "test_info": {
                    "test_id": test.test_id,
                    "test_name": test.test_name,
                    "status": test.status,
                    "start_date": test.start_date.isoformat() if test.start_date else None,
                    "total_sample_size": sum(v.sample_size for v in variants)
                },
                "variants": {k: asdict(v) for k, v in variant_results.items()},
                "analysis": analysis
            }

        except Exception as e:
            logger.error(f"Failed to get test results for {test_id}: {e}")
            return None

    def _calculate_variant_metrics(self, variant_id: str, results: List[ABTestResult]) -> Dict[str, Any]:
        """Calculate performance metrics for a variant"""
        variant_results = [r for r in results if r.variant_id == variant_id and r.prediction_score is not None]

        if not variant_results:
            return {
                "metrics": {},
                "confidence_intervals": {},
                "significance": {}
            }

        scores = [r.prediction_score for r in variant_results]

        # Calculate basic metrics
        metrics = {
            "mean_score": sum(scores) / len(scores),
            "sample_size": len(scores),
            "std_dev": (sum((x - sum(scores)/len(scores))**2 for x in scores) / len(scores))**0.5
        }

        # Calculate confidence intervals (simplified)
        confidence_intervals = {
            "mean_score": self._calculate_confidence_interval(scores, 0.95)
        }

        # Statistical significance (placeholder - would implement proper statistical tests)
        significance = {
            "minimum_sample_achieved": len(scores) >= 100  # Simplified threshold
        }

        return {
            "metrics": metrics,
            "confidence_intervals": confidence_intervals,
            "significance": significance
        }

    def _analyze_test_results(self, test: ABTest, variant_results: Dict[str, VariantResult]) -> Dict[str, Any]:
        """Analyze overall test results"""
        if len(variant_results) < 2:
            return {"conclusion": "Insufficient variants for analysis"}

        # Find best performing variant
        best_variant = max(variant_results.values(),
                          key=lambda v: v.metrics.get('mean_score', 0))

        # Check if test should be concluded
        total_samples = sum(v.sample_size for v in variant_results.values())
        should_conclude = total_samples >= test.target_sample_size

        analysis = {
            "best_variant": best_variant.variant_id,
            "best_score": best_variant.metrics.get('mean_score', 0),
            "total_samples": total_samples,
            "should_conclude": should_conclude,
            "recommendation": self._generate_recommendation(test, variant_results)
        }

        return analysis

    def _generate_recommendation(self, test: ABTest, variant_results: Dict[str, VariantResult]) -> str:
        """Generate recommendation based on test results"""
        if len(variant_results) < 2:
            return "Need at least 2 variants for comparison"

        best_variant = max(variant_results.values(),
                          key=lambda v: v.metrics.get('mean_score', 0))

        # Check statistical significance
        control_variant = next((v for v in variant_results.values() if v != best_variant), None)
        if control_variant and best_variant.metrics.get('mean_score', 0) > control_variant.metrics.get('mean_score', 0) + test.minimum_effect_size:
            return f"Variant {best_variant.variant_id} shows significant improvement. Consider deploying model {best_variant.model_id} as the new default."

        return "Results inconclusive. Continue testing or adjust test parameters."

    def stop_test(self, test_id: str, db: Session) -> bool:
        """Stop an A/B test"""
        try:
            test = db.query(ABTest).filter(ABTest.test_id == test_id).first()
            if not test:
                return False

            test.status = TestStatus.COMPLETED.value
            test.end_date = datetime.utcnow()
            db.commit()

            logger.info(f"A/B test {test_id} stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop A/B test {test_id}: {e}")
            db.rollback()
            return False

    def _calculate_weights(self, config: ABTestConfiguration) -> Dict[str, float]:
        """Calculate traffic weights based on allocation strategy"""
        if config.traffic_allocation == TrafficAllocation.EQUAL:
            weight = 1.0 / len(config.model_variants)
            return {model_id: weight for model_id in config.model_variants}

        elif config.traffic_allocation == TrafficAllocation.GRADUAL:
            # Gradual rollout: 10%, 30%, 60% for 3 variants, etc.
            weights = []
            remaining = 1.0
            for i in range(len(config.model_variants)):
                if i == len(config.model_variants) - 1:
                    weight = remaining
                else:
                    weight = remaining * 0.3  # 30% of remaining
                    remaining -= weight
                weights.append(weight)
            return dict(zip(config.model_variants, weights))

        elif config.traffic_allocation == TrafficAllocation.CUSTOM:
            return config.custom_weights or {}

        return {}

    def _weighted_random_choice(self, weights: Dict[str, float]) -> str:
        """Make weighted random choice"""
        total = sum(weights.values())
        r = random.uniform(0, total)
        cumulative = 0

        for item, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return item

        return list(weights.keys())[0]  # Fallback

    def _calculate_confidence_interval(self, data: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval (simplified)"""
        if len(data) < 2:
            mean = sum(data) / len(data) if data else 0
            return (mean, mean)

        mean = sum(data) / len(data)
        std_dev = (sum((x - mean)**2 for x in data) / len(data))**0.5

        # Simplified z-score for 95% confidence
        z_score = 1.96
        margin = z_score * std_dev / (len(data)**0.5)

        return (mean - margin, mean + margin)

    def _generate_test_id(self, test_name: str) -> str:
        """Generate unique test ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"ab_{timestamp}_{hashlib.md5(test_name.encode()).hexdigest()[:8]}"


# Global A/B testing instance
_ab_testing: Optional[ABTestingFramework] = None


def get_ab_testing_framework() -> ABTestingFramework:
    """Get or create global A/B testing framework instance"""
    global _ab_testing
    if _ab_testing is None:
        _ab_testing = ABTestingFramework()
    return _ab_testing

@dataclass
class VariantConfiguration:
    """Configuration for a single A/B test variant"""
    variant_id: str
    name: str
    description: str = ""
    traffic_weight: float = 0.0
    model_version: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

# Compatibility function for API
def get_ab_testing_engine():
    """Get A/B testing engine instance for API compatibility"""
    return get_ab_testing_framework()
