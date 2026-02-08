"""
Model Registry for IIT Prediction ML Service
Handles model versioning, metadata storage, and model comparison
"""
import os
import json
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from .core.db import get_db
from .models import ModelVersion, ModelMetrics, ABTest, ModelComparison
from .config import get_settings
from .monitoring import MetricsManager

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ModelMetadata:
    """Model metadata structure"""
    version: str
    algorithm: str
    hyperparameters: Dict[str, Any]
    training_data_info: Dict[str, Any]
    performance_metrics: Dict[str, float]
    feature_importance: Optional[Dict[str, float]] = None
    created_at: str = None
    model_path: str = None
    is_active: bool = False
    tags: List[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.tags is None:
            self.tags = []


class ModelRegistry:
    """Central registry for managing ML model versions and metadata"""

    def __init__(self):
        self.models_dir = Path(settings.models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.active_model_version = None

    def register_model(
        self,
        model_path: str,
        metadata: ModelMetadata,
        db: Session
    ) -> str:
        """Register a new model version in the registry"""
        try:
            # Generate unique model ID
            model_id = self._generate_model_id(metadata)

            # Copy model file to registry
            registry_path = self.models_dir / f"{model_id}.model"
            shutil.copy2(model_path, registry_path)

            # Update metadata with registry path
            metadata.model_path = str(registry_path)

            # Save to database
            model_version = ModelVersion(
                model_id=model_id,
                version=metadata.version,
                algorithm=metadata.algorithm,
                hyperparameters=json.dumps(metadata.hyperparameters),
                training_data_info=json.dumps(metadata.training_data_info),
                performance_metrics=json.dumps(metadata.performance_metrics),
                feature_importance=json.dumps(metadata.feature_importance) if metadata.feature_importance else None,
                model_path=str(registry_path),
                is_active=metadata.is_active,
                tags=json.dumps(metadata.tags),
                created_at=datetime.fromisoformat(metadata.created_at)
            )

            db.add(model_version)
            db.commit()
            db.refresh(model_version)

            # Set as active if specified
            if metadata.is_active:
                self._set_active_model(model_id, db)

            logger.info(f"Model {model_id} registered successfully")
            return model_id

        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            db.rollback()
            raise

    def get_model_metadata(self, model_id: str, db: Session) -> Optional[ModelMetadata]:
        """Retrieve model metadata from registry"""
        model_version = db.query(ModelVersion).filter(ModelVersion.model_id == model_id).first()
        if not model_version:
            return None

        return ModelMetadata(
            version=model_version.version,
            algorithm=model_version.algorithm,
            hyperparameters=json.loads(model_version.hyperparameters),
            training_data_info=json.loads(model_version.training_data_info),
            performance_metrics=json.loads(model_version.performance_metrics),
            feature_importance=json.loads(model_version.feature_importance) if model_version.feature_importance else None,
            created_at=model_version.created_at.isoformat(),
            model_path=model_version.model_path,
            is_active=model_version.is_active,
            tags=json.loads(model_version.tags) if model_version.tags else []
        )

    def list_models(self, db: Session, active_only: bool = False) -> List[ModelMetadata]:
        """List all registered models"""
        query = db.query(ModelVersion)
        if active_only:
            query = query.filter(ModelVersion.is_active == True)

        model_versions = query.order_by(desc(ModelVersion.created_at)).all()

        return [
            ModelMetadata(
                version=mv.version,
                algorithm=mv.algorithm,
                hyperparameters=json.loads(mv.hyperparameters),
                training_data_info=json.loads(mv.training_data_info),
                performance_metrics=json.loads(mv.performance_metrics),
                feature_importance=json.loads(mv.feature_importance) if mv.feature_importance else None,
                created_at=mv.created_at.isoformat(),
                model_path=mv.model_path,
                is_active=mv.is_active,
                tags=json.loads(mv.tags) if mv.tags else []
            )
            for mv in model_versions
        ]

    def get_active_model(self, db: Session) -> Optional[Tuple[str, ModelMetadata]]:
        """Get the currently active model"""
        active_model = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
        if not active_model:
            return None

        metadata = ModelMetadata(
            version=active_model.version,
            algorithm=active_model.algorithm,
            hyperparameters=json.loads(active_model.hyperparameters),
            training_data_info=json.loads(active_model.training_data_info),
            performance_metrics=json.loads(active_model.performance_metrics),
            feature_importance=json.loads(active_model.feature_importance) if active_model.feature_importance else None,
            created_at=active_model.created_at.isoformat(),
            model_path=active_model.model_path,
            is_active=True,
            tags=json.loads(active_model.tags) if active_model.tags else []
        )

        return active_model.model_id, metadata

    def set_active_model(self, model_id: str, db: Session) -> bool:
        """Set a model as the active version"""
        return self._set_active_model(model_id, db)

    def _set_active_model(self, model_id: str, db: Session) -> bool:
        """Internal method to set active model"""
        try:
            # Deactivate all models
            db.query(ModelVersion).update({"is_active": False})

            # Activate the specified model
            model = db.query(ModelVersion).filter(ModelVersion.model_id == model_id).first()
            if not model:
                return False

            model.is_active = True
            db.commit()

            self.active_model_version = model_id
            logger.info(f"Model {model_id} set as active")
            return True

        except Exception as e:
            logger.error(f"Failed to set active model: {e}")
            db.rollback()
            return False

    def compare_models(
        self,
        model_ids: List[str],
        db: Session
    ) -> Dict[str, Any]:
        """Compare multiple models based on their metrics"""
        models_data = {}
        comparison_metrics = {}

        for model_id in model_ids:
            metadata = self.get_model_metadata(model_id, db)
            if metadata:
                models_data[model_id] = metadata
                comparison_metrics[model_id] = metadata.performance_metrics

        # Calculate comparison statistics
        comparison = {
            "models": models_data,
            "metrics_comparison": comparison_metrics,
            "best_performing": self._find_best_model(comparison_metrics),
            "summary": self._generate_comparison_summary(comparison_metrics)
        }

        # Save comparison to database
        self._save_comparison(model_ids, comparison, db)

        return comparison

    def _find_best_model(self, metrics_comparison: Dict[str, Dict[str, float]]) -> str:
        """Find the best performing model based on primary metric (AUC)"""
        best_model = None
        best_score = 0

        for model_id, metrics in metrics_comparison.items():
            auc_score = metrics.get('auc', 0)
            if auc_score > best_score:
                best_score = auc_score
                best_model = model_id

        return best_model

    def _generate_comparison_summary(self, metrics_comparison: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Generate summary statistics for model comparison"""
        if not metrics_comparison:
            return {}

        # Extract AUC scores
        auc_scores = [metrics.get('auc', 0) for metrics in metrics_comparison.values()]

        return {
            "total_models": len(metrics_comparison),
            "auc_range": {
                "min": min(auc_scores),
                "max": max(auc_scores),
                "avg": sum(auc_scores) / len(auc_scores)
            },
            "performance_distribution": self._calculate_performance_distribution(auc_scores)
        }

    def _calculate_performance_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate performance distribution"""
        distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}

        for score in scores:
            if score >= 0.9:
                distribution["excellent"] += 1
            elif score >= 0.8:
                distribution["good"] += 1
            elif score >= 0.7:
                distribution["fair"] += 1
            else:
                distribution["poor"] += 1

        return distribution

    def _save_comparison(self, model_ids: List[str], comparison: Dict[str, Any], db: Session):
        """Save model comparison to database"""
        try:
            comparison_record = ModelComparison(
                model_ids=json.dumps(model_ids),
                comparison_data=json.dumps(comparison),
                created_at=datetime.utcnow()
            )
            db.add(comparison_record)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save comparison: {e}")
            db.rollback()

    def delete_model(self, model_id: str, db: Session) -> bool:
        """Delete a model from the registry"""
        try:
            model = db.query(ModelVersion).filter(ModelVersion.model_id == model_id).first()
            if not model:
                return False

            # Don't allow deletion of active model
            if model.is_active:
                logger.warning(f"Cannot delete active model {model_id}")
                return False

            # Remove model file
            if os.path.exists(model.model_path):
                os.remove(model.model_path)

            # Remove from database
            db.delete(model)
            db.commit()

            logger.info(f"Model {model_id} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to delete model {model_id}: {e}")
            db.rollback()
            return False

    def _generate_model_id(self, metadata: ModelMetadata) -> str:
        """Generate unique model ID based on metadata"""
        content = f"{metadata.version}_{metadata.algorithm}_{metadata.created_at}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def get_model_path(self, model_id: str, db: Session) -> Optional[str]:
        """Get the file path for a model"""
        model = db.query(ModelVersion).filter(ModelVersion.model_id == model_id).first()
        return model.model_path if model else None


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get or create global model registry instance"""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
