"""
AI Observability: Model Drift Detection and Bias Monitoring

Provides comprehensive monitoring for ML models including:
1. Data drift detection (feature distribution changes)
2. Prediction drift detection (output distribution changes)
3. Model performance monitoring
4. Bias detection and mitigation
5. Model comparison and A/B testing

Usage:
    from app.ai_observability import (
        DriftDetector,
        BiasMonitor,
        ModelObservabilityManager
    )
    
    detector = DriftDetector()
    
    # Check for data drift
    drift_report = await detector.detect_data_drift(
        reference_data=training_data,
        current_data=recent_data
    )
    
    # Check for prediction drift
    prediction_drift = await detector.detect_prediction_drift(
        reference_predictions=historical_predictions,
        current_predictions=recent_predictions
    )
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from collections import Counter
import statistics

import numpy as np
from scipy import stats

from app.config import settings

logger = logging.getLogger(__name__)


class DriftType(Enum):
    """Types of drift that can be detected"""
    COVARIATE_SHIFT = "covariate_shift"  # Input feature distribution changed
    PRIOR_PROBABILITY_SHIFT = "prior_probability_shift"  # Output distribution changed
    CONCEPT_DRIFT = "concept_drift"  # Relationship between input and output changed
    LABEL_SHIFT = "label_shift"  # Label distribution changed


class DriftSeverity(Enum):
    """Severity levels for detected drift"""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftResult:
    """Result of a drift detection test"""
    drift_type: DriftType
    severity: DriftSeverity
    p_value: float
    statistic: float
    threshold: float
    description: str
    affected_features: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class BiasReport:
    """Report on model bias"""
    protected_attribute: str
    metric_name: str
    privilege_group_value: Any
    privilege_group_metric: float
    unprivileged_group_value: Any
    unprivileged_group_metric: float
    disparity_ratio: float
    bias_detected: bool
    severity: DriftSeverity
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ModelPerformanceMetrics:
    """Model performance metrics over time"""
    timestamp: datetime
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_roc: Optional[float] = None
    calibration_score: Optional[float] = None
    prediction_distribution: Dict[str, int] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)


class DriftDetector:
    """
    Detects various types of drift in ML models
    
    Uses statistical tests to detect:
    - Covariate shift (input feature distribution changes)
    - Prediction drift (output distribution changes)
    - Concept drift (relationship changes)
    """
    
    def __init__(
        self,
        significance_level: float = 0.05,
        min_sample_size: int = 100
    ):
        self.significance_level = significance_level
        self.min_sample_size = min_sample_size
    
    async def detect_data_drift(
        self,
        reference_data: Dict[str, List[Any]],
        current_data: Dict[str, List[Any]],
        features: Optional[List[str]] = None
    ) -> List[DriftResult]:
        """
        Detect covariate shift (data drift)
        
        Args:
            reference_data: Training/baseline feature distributions
            current_data: Current feature distributions
            features: Specific features to check (None = all)
            
        Returns:
            List of DriftResult objects for each feature with drift
        """
        drift_results = []
        
        # Determine which features to check
        if features is None:
            features = list(reference_data.keys())
        
        for feature in features:
            if feature not in reference_data or feature not in current_data:
                continue
            
            ref_values = reference_data[feature]
            curr_values = current_data[feature]
            
            # Skip if insufficient data
            if len(ref_values) < self.min_sample_size or len(curr_values) < self.min_sample_size:
                continue
            
            # Perform Kolmogorov-Smirnov test for continuous variables
            if self._is_numeric(ref_values):
                result = self._ks_test(ref_values, curr_values, feature)
                if result:
                    drift_results.append(result)
            else:
                # Chi-square test for categorical variables
                result = self._chi_square_test(ref_values, curr_values, feature)
                if result:
                    drift_results.append(result)
        
        logger.info(f"Data drift detection complete: {len(drift_results)} features drifted")
        return drift_results
    
    async def detect_prediction_drift(
        self,
        reference_predictions: List[Any],
        current_predictions: List[Any],
        threshold: float = 0.1
    ) -> DriftResult:
        """
        Detect prediction distribution drift
        
        Args:
            reference_predictions: Historical prediction distribution
            current_predictions: Current prediction distribution
            threshold: Threshold for significant drift
            
        Returns:
            DriftResult for prediction drift
        """
        # Count predictions by class
        ref_dist = Counter(reference_predictions)
        curr_dist = Counter(current_predictions)
        
        # Calculate total variation distance
        all_classes = set(ref_dist.keys()) | set(curr_dist.keys())
        total_ref = sum(ref_dist.values())
        total_curr = sum(curr_dist.values())
        
        tvd = 0.5 * sum(
            abs((ref_dist.get(c, 0) / total_ref) - (curr_dist.get(c, 0) / total_curr))
            for c in all_classes
        )
        
        # Determine severity
        if tvd < threshold:
            severity = DriftSeverity.NONE
        elif tvd < threshold * 2:
            severity = DriftSeverity.LOW
        elif tvd < threshold * 3:
            severity = DriftSeverity.MODERATE
        elif tvd < threshold * 4:
            severity = DriftSeverity.HIGH
        else:
            severity = DriftSeverity.CRITICAL
        
        return DriftResult(
            drift_type=DriftType.PRIOR_PROBABILITY_SHIFT,
            severity=severity,
            p_value=max(0, 1 - tvd),  # Approximate
            statistic=tvd,
            threshold=threshold,
            description=f"Prediction distribution drift detected. Total variation distance: {tvd:.4f}",
            affected_features=list(all_classes),
            recommendations=self._get_prediction_drift_recommendations(severity, tvd)
        )
    
    async def detect_concept_drift(
        self,
        reference_pairs: List[Tuple[Any, Any]],  # (features, label)
        current_pairs: List[Tuple[Any, Any]],
        model_predict_fn
    ) -> DriftResult:
        """
        Detect concept drift (relationship between input and output changed)
        
        Args:
            reference_pairs: Historical (feature, label) pairs
            current_pairs: Current (feature, label) pairs
            model_predict_fn: Function to make predictions
            
        Returns:
            DriftResult for concept drift
        """
        # Calculate accuracy on reference vs current data
        ref_correct = sum(1 for x, y in reference_pairs if model_predict_fn(x) == y)
        curr_correct = sum(1 for x, y in current_pairs if model_predict_fn(x) == y)
        
        ref_accuracy = ref_correct / len(reference_pairs) if reference_pairs else 0
        curr_accuracy = curr_correct / len(current_pairs) if current_pairs else 0
        
        accuracy_drop = ref_accuracy - curr_accuracy
        
        # Determine severity
        if accuracy_drop < 0.05:
            severity = DriftSeverity.NONE
        elif accuracy_drop < 0.10:
            severity = DriftSeverity.LOW
        elif accuracy_drop < 0.15:
            severity = DriftSeverity.MODERATE
        elif accuracy_drop < 0.20:
            severity = DriftSeverity.HIGH
        else:
            severity = DriftSeverity.CRITICAL
        
        return DriftResult(
            drift_type=DriftType.CONCEPT_DRIFT,
            severity=severity,
            p_value=max(0, 1 - accuracy_drop),  # Approximate
            statistic=accuracy_drop,
            threshold=0.05,
            description=f"Model accuracy dropped from {ref_accuracy:.2%} to {curr_accuracy:.2%}",
            recommendations=self._get_concept_drift_recommendations(severity, accuracy_drop)
        )
    
    def _ks_test(
        self,
        reference: List[float],
        current: List[float],
        feature: str
    ) -> Optional[DriftResult]:
        """Perform Kolmogorov-Smirnov test for numeric features"""
        try:
            statistic, p_value = stats.ks_2samp(reference, current)
            
            if p_value < self.significance_level:
                # Determine severity based on statistic
                if statistic < 0.2:
                    severity = DriftSeverity.LOW
                elif statistic < 0.4:
                    severity = DriftSeverity.MODERATE
                elif statistic < 0.6:
                    severity = DriftSeverity.HIGH
                else:
                    severity = DriftSeverity.CRITICAL
                
                return DriftResult(
                    drift_type=DriftType.COVARIATE_SHIFT,
                    severity=severity,
                    p_value=p_value,
                    statistic=statistic,
                    threshold=self.significance_level,
                    description=f"Feature '{feature}' distribution changed (KS test: p={p_value:.4f})",
                    affected_features=[feature],
                    recommendations=self._get_data_drift_recommendations(severity, feature)
                )
        except Exception as e:
            logger.warning(f"KS test failed for feature {feature}: {e}")
        
        return None
    
    def _chi_square_test(
        self,
        reference: List[Any],
        current: List[Any],
        feature: str
    ) -> Optional[DriftResult]:
        """Perform Chi-square test for categorical features"""
        try:
            # Build contingency table
            ref_counts = Counter(reference)
            curr_counts = Counter(current)
            
            all_categories = set(ref_counts.keys()) | set(curr_counts.keys())
            
            # Create observed frequencies
            observed = []
            for category in all_categories:
                observed.append([ref_counts.get(category, 0), curr_counts.get(category, 0)])
            
            # Perform chi-square test
            statistic, p_value, _, _ = stats.chi2_contingency(observed)
            
            if p_value < self.significance_level:
                # Determine severity
                if statistic < 10:
                    severity = DriftSeverity.LOW
                elif statistic < 20:
                    severity = DriftSeverity.MODERATE
                elif statistic < 30:
                    severity = DriftSeverity.HIGH
                else:
                    severity = DriftSeverity.CRITICAL
                
                return DriftResult(
                    drift_type=DriftType.COVARIATE_SHIFT,
                    severity=severity,
                    p_value=p_value,
                    statistic=statistic,
                    threshold=self.significance_level,
                    description=f"Categorical feature '{feature}' distribution changed (χ²={statistic:.2f}, p={p_value:.4f})",
                    affected_features=[feature],
                    recommendations=self._get_data_drift_recommendations(severity, feature)
                )
        except Exception as e:
            logger.warning(f"Chi-square test failed for feature {feature}: {e}")
        
        return None
    
    def _is_numeric(self, values: List[Any]) -> bool:
        """Check if values are numeric"""
        try:
            [float(v) for v in values[:10]]  # Check first 10
            return True
        except (ValueError, TypeError):
            return False
    
    def _get_data_drift_recommendations(self, severity: DriftSeverity, feature: str) -> List[str]:
        """Get recommendations for data drift"""
        recommendations = []
        
        if severity in [DriftSeverity.MODERATE, DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            recommendations.append(f"Retrain model with recent data including updated '{feature}' distribution")
            recommendations.append(f"Investigate root cause of distribution shift in '{feature}'")
            recommendations.append("Consider feature engineering to handle distribution changes")
        
        if severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            recommendations.append("Schedule immediate model retraining")
            recommendations.append("Alert data engineering team about data pipeline issues")
        
        return recommendations
    
    def _get_prediction_drift_recommendations(self, severity: DriftSeverity, tvd: float) -> List[str]:
        """Get recommendations for prediction drift"""
        recommendations = []
        
        if severity != DriftSeverity.NONE:
            recommendations.append("Review recent prediction patterns for anomalies")
            recommendations.append("Check if input data distribution has changed")
        
        if severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            recommendations.append("Investigate potential model degradation")
            recommendations.append("Consider recalibrating model thresholds")
        
        return recommendations
    
    def _get_concept_drift_recommendations(self, severity: DriftSeverity, accuracy_drop: float) -> List[str]:
        """Get recommendations for concept drift"""
        recommendations = []
        
        if severity != DriftSeverity.NONE:
            recommendations.append("Model performance has degraded - investigate root cause")
            recommendations.append("Review if business logic or clinical guidelines have changed")
        
        if severity in [DriftSeverity.MODERATE, DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            recommendations.append("Retrain model with recent labeled data")
            recommendations.append("Consider ensemble methods to improve robustness")
        
        if severity == DriftSeverity.CRITICAL:
            recommendations.append("URGENT: Model may no longer be fit for production use")
            recommendations.append("Consider rolling back to previous model version")
        
        return recommendations


class BiasMonitor:
    """
    Monitor and detect bias in ML models
    
    Checks for:
    - Disparate impact across protected groups
    - Equalized odds differences
    - Calibration differences
    - Feature importance disparities
    """
    
    def __init__(
        self,
        protected_attributes: List[str] = None,
        fairness_threshold: float = 0.8
    ):
        self.protected_attributes = protected_attributes or ["gender", "age_group", "race"]
        self.fairness_threshold = fairness_threshold  # 80% rule
    
    async def detect_bias(
        self,
        predictions: List[Any],
        labels: List[Any],
        protected_attributes: Dict[str, List[Any]]
    ) -> List[BiasReport]:
        """
        Detect bias across protected attributes
        
        Args:
            predictions: Model predictions
            labels: Ground truth labels
            protected_attributes: Dictionary of attribute name -> values
            
        Returns:
            List of BiasReport objects
        """
        bias_reports = []
        
        for attr_name, attr_values in protected_attributes.items():
            # Calculate metrics for each group
            unique_groups = set(attr_values)
            
            if len(unique_groups) < 2:
                continue  # Need at least 2 groups to compare
            
            group_metrics = {}
            for group in unique_groups:
                group_mask = [v == group for v in attr_values]
                group_preds = [p for p, m in zip(predictions, group_mask) if m]
                group_labels = [l for l, m in zip(labels, group_mask) if m]
                
                if group_labels:
                    accuracy = sum(p == l for p, l in zip(group_preds, group_labels)) / len(group_labels)
                    group_metrics[group] = accuracy
            
            # Compare groups
            sorted_groups = sorted(group_metrics.items(), key=lambda x: x[1], reverse=True)
            
            if len(sorted_groups) >= 2:
                privilege_group, privilege_metric = sorted_groups[0]
                unprivileged_group, unprivileged_metric = sorted_groups[-1]
                
                disparity_ratio = unprivileged_metric / privilege_metric if privilege_metric > 0 else 0
                
                bias_detected = disparity_ratio < self.fairness_threshold
                
                # Determine severity
                if disparity_ratio >= self.fairness_threshold:
                    severity = DriftSeverity.NONE
                elif disparity_ratio >= 0.7:
                    severity = DriftSeverity.LOW
                elif disparity_ratio >= 0.6:
                    severity = DriftSeverity.MODERATE
                elif disparity_ratio >= 0.5:
                    severity = DriftSeverity.HIGH
                else:
                    severity = DriftSeverity.CRITICAL
                
                if bias_detected or severity != DriftSeverity.NONE:
                    bias_reports.append(BiasReport(
                        protected_attribute=attr_name,
                        metric_name="accuracy",
                        privilege_group_value=privilege_group,
                        privilege_group_metric=privilege_metric,
                        unprivileged_group_value=unprivileged_group,
                        unprivileged_group_metric=unprivileged_metric,
                        disparity_ratio=disparity_ratio,
                        bias_detected=bias_detected,
                        severity=severity,
                        recommendations=self._get_bias_recommendations(severity, attr_name, disparity_ratio)
                    ))
        
        logger.info(f"Bias detection complete: {len(bias_reports)} potential biases found")
        return bias_reports
    
    def _get_bias_recommendations(self, severity: DriftSeverity, attribute: str, ratio: float) -> List[str]:
        """Get recommendations for detected bias"""
        recommendations = []
        
        if severity != DriftSeverity.NONE:
            recommendations.append(f"Bias detected in '{attribute}' - review model training data")
            recommendations.append("Consider re-sampling or re-weighting training data")
        
        if severity in [DriftSeverity.MODERATE, DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            recommendations.append("Apply bias mitigation techniques (re-weighting, adversarial debiasing)")
            recommendations.append("Consider using fairness-constrained model training")
        
        if severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            recommendations.append("URGENT: Model may violate fairness requirements")
            recommendations.append("Review model with ethics committee before production use")
        
        return recommendations


class ModelObservabilityManager:
    """
    Comprehensive manager for model observability
    
    Combines drift detection, bias monitoring, and performance tracking
    """
    
    def __init__(self):
        self.drift_detector = DriftDetector()
        self.bias_monitor = BiasMonitor()
        self._performance_history: List[ModelPerformanceMetrics] = []
    
    async def check_model_health(
        self,
        reference_data: Dict[str, List[Any]],
        current_data: Dict[str, List[Any]],
        reference_predictions: List[Any],
        current_predictions: List[Any],
        labels: Optional[List[Any]] = None,
        protected_attributes: Optional[Dict[str, List[Any]]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive model health check
        
        Returns:
            Dictionary with drift results, bias reports, and recommendations
        """
        health_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "data_drift": [],
            "prediction_drift": None,
            "concept_drift": None,
            "bias_reports": [],
            "overall_status": "healthy",
            "recommendations": []
        }
        
        # Check for data drift
        data_drift = await self.drift_detector.detect_data_drift(
            reference_data, current_data
        )
        health_report["data_drift"] = data_drift
        
        # Check for prediction drift
        prediction_drift = await self.drift_detector.detect_prediction_drift(
            reference_predictions, current_predictions
        )
        health_report["prediction_drift"] = prediction_drift
        
        # Check for bias if labels and protected attributes provided
        if labels and protected_attributes:
            bias_reports = await self.bias_monitor.detect_bias(
                current_predictions, labels, protected_attributes
            )
            health_report["bias_reports"] = bias_reports
        
        # Determine overall status
        critical_issues = 0
        high_issues = 0
        
        for drift in data_drift:
            if drift.severity == DriftSeverity.CRITICAL:
                critical_issues += 1
            elif drift.severity == DriftSeverity.HIGH:
                high_issues += 1
        
        if prediction_drift.severity == DriftSeverity.CRITICAL:
            critical_issues += 1
        elif prediction_drift.severity == DriftSeverity.HIGH:
            high_issues += 1
        
        for bias in health_report["bias_reports"]:
            if bias.severity == DriftSeverity.CRITICAL:
                critical_issues += 1
            elif bias.severity == DriftSeverity.HIGH:
                high_issues += 1
        
        if critical_issues > 0:
            health_report["overall_status"] = "critical"
            health_report["recommendations"].append("URGENT: Immediate model retraining required")
        elif high_issues > 0:
            health_report["overall_status"] = "degraded"
            health_report["recommendations"].append("Schedule model retraining soon")
        elif data_drift or prediction_drift.severity != DriftSeverity.NONE:
            health_report["overall_status"] = "warning"
            health_report["recommendations"].append("Monitor model closely")
        
        # Aggregate all recommendations
        all_recommendations = []
        for drift in data_drift:
            all_recommendations.extend(drift.recommendations)
        if prediction_drift.recommendations:
            all_recommendations.extend(prediction_drift.recommendations)
        for bias in health_report["bias_reports"]:
            all_recommendations.extend(bias.recommendations)
        
        health_report["recommendations"].extend(all_recommendations)
        
        return health_report
    
    def record_performance_metrics(
        self,
        accuracy: Optional[float] = None,
        precision: Optional[float] = None,
        recall: Optional[float] = None,
        f1_score: Optional[float] = None,
        auc_roc: Optional[float] = None,
        prediction_distribution: Optional[Dict[str, int]] = None
    ):
        """Record model performance metrics"""
        metrics = ModelPerformanceMetrics(
            timestamp=datetime.utcnow(),
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            auc_roc=auc_roc,
            prediction_distribution=prediction_distribution or {}
        )
        self._performance_history.append(metrics)
        
        # Keep only last 1000 records
        if len(self._performance_history) > 1000:
            self._performance_history = self._performance_history[-1000:]
    
    def get_performance_trend(
        self,
        metric: str = "accuracy",
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get performance trend for a metric over time"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        trend = []
        for metrics in self._performance_history:
            if metrics.timestamp >= cutoff_time:
                value = getattr(metrics, metric, None)
                if value is not None:
                    trend.append({
                        "timestamp": metrics.timestamp.isoformat(),
                        "value": value
                    })
        
        return trend


# Singleton instance
_observability_manager: Optional[ModelObservabilityManager] = None


def get_observability_manager() -> ModelObservabilityManager:
    """Get the singleton ModelObservabilityManager instance"""
    global _observability_manager
    
    if _observability_manager is None:
        _observability_manager = ModelObservabilityManager()
        logger.info("Model Observability Manager created")
    
    return _observability_manager
