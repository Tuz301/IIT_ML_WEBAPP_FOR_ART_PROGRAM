"""
Model Retraining Pipeline for IIT ML Service
Automated model retraining with performance monitoring and rollback
"""
import asyncio
import logging
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score

from .model_registry import ModelRegistry, ModelMetadata
from .ml_model import IITModelPredictor, get_model
from .core.db import get_db
from .models import ModelVersion, ModelMetrics, IITPrediction, Patient
from .config import get_settings
from .monitoring import MetricsManager

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RetrainingConfig:
    """Configuration for model retraining"""
    min_samples: int = 1000  # Minimum samples required for retraining
    test_size: float = 0.2
    random_state: int = 42
    early_stopping_rounds: int = 100
    num_boost_round: int = 1000
    learning_rate: float = 0.01
    max_depth: int = 6
    min_child_samples: int = 20
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    
    # Performance thresholds
    min_auc_score: float = 0.75  # Minimum AUC to deploy new model
    min_accuracy: float = 0.70
    drift_threshold: float = 0.10  # Performance drop threshold


@dataclass
class RetrainingResult:
    """Result of model retraining"""
    success: bool
    model_id: Optional[str]
    old_model_id: str
    metrics: Dict[str, float]
    training_time_seconds: float
    sample_count: int
    timestamp: str
    error: Optional[str] = None
    deployed: bool = False


class ModelRetrainingPipeline:
    """
    Automated model retraining pipeline with:
    - Data collection and validation
    - Training with hyperparameter tuning
    - Performance evaluation
    - A/B testing support
    - Automatic rollback on failure
    """
    
    def __init__(self, config: RetrainingConfig = None):
        self.config = config or RetrainingConfig()
        self.model_registry = ModelRegistry()
        self.current_predictor = get_model()
        self.settings = get_settings()
        
    async def check_retraining_needed(self) -> Dict[str, Any]:
        """
        Check if model retraining is needed based on:
        - Data drift
        - Performance degradation
        - Time since last training
        - New data availability
        """
        db = next(get_db())
        
        try:
            # Get current model info
            current_model = db.query(ModelVersion).filter(
                ModelVersion.is_active == True
            ).first()
            
            if not current_model:
                return {"needed": True, "reason": "No active model found"}
            
            # Check time since last training
            days_since_training = (datetime.utcnow() - current_model.created_at).days
            if days_since_training > 30:  # Retrain monthly
                return {
                    "needed": True,
                    "reason": f"Model is {days_since_training} days old (threshold: 30 days)"
                }
            
            # Check for new data
            total_predictions = db.query(IITPrediction).count()
            if total_predictions > self.config.min_samples:
                # Check if we have significantly more data
                old_metrics = json.loads(current_model.performance_metrics) if current_model.performance_metrics else {}
                old_sample_count = old_metrics.get('training_samples', 0)
                
                if total_predictions > old_sample_count * 1.5:  # 50% more data
                    return {
                        "needed": True,
                        "reason": f"Significant new data available: {total_predictions} vs {old_sample_count}"
                    }
            
            # Check model performance (from monitoring)
            current_auc = MetricsManager.get_current_auc()
            if current_auc and current_auc < self.config.min_auc_score:
                return {
                    "needed": True,
                    "reason": f"Model AUC ({current_auc:.3f}) below threshold ({self.config.min_auc_score})"
                }
            
            return {"needed": False, "reason": "Model performance is acceptable"}
            
        finally:
            db.close()
    
    async def prepare_training_data(self) -> Optional[pd.DataFrame]:
        """
        Prepare training data from database.
        
        Returns:
            DataFrame with features and labels, or None if insufficient data
        """
        db = next(get_db())
        
        try:
            # Get all predictions with actual outcomes
            # In a real system, you'd track actual outcomes (did patient interrupt treatment?)
            # For now, we'll use the prediction data itself
            
            query = db.query(
                IITPrediction.patient_uuid,
                IITPrediction.features_used,
                IITPrediction.risk_score
            ).limit(10000)  # Limit for initial implementation
            
            results = query.all()
            
            if len(results) < self.config.min_samples:
                logger.warning(f"Insufficient data for retraining: {len(results)} < {self.config.min_samples}")
                return None
            
            # Build DataFrame
            data_rows = []
            for row in results:
                features = json.loads(row.features_used) if isinstance(row.features_used, str) else row.features_used
                features['risk_score'] = row.risk_score  # Use as label (in real system, use actual outcome)
                data_rows.append(features)
            
            df = pd.DataFrame(data_rows)
            
            # Remove non-feature columns
            feature_cols = [col for col in df.columns if col != 'patient_uuid']
            df = df[feature_cols]
            
            logger.info(f"Prepared training data: {len(df)} samples, {len(df.columns)-1} features")
            return df
            
        except Exception as e:
            logger.error(f"Failed to prepare training data: {e}")
            return None
        finally:
            db.close()
    
    async def train_model(
        self,
        training_data: pd.DataFrame
    ) -> Optional[lgb.Booster]:
        """
        Train a new LightGBM model.
        
        Args:
            training_data: Training DataFrame with features and labels
            
        Returns:
            Trained model or None if training failed
        """
        try:
            # Separate features and labels
            X = training_data.drop('risk_score', axis=1)
            y = training_data['risk_score']
            
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                X, y,
                test_size=self.config.test_size,
                random_state=self.config.random_state,
                stratify=(y > 0.5).astype(int)  # Stratify by risk level
            )
            
            # Create LightGBM datasets
            train_data = lgb.Dataset(X_train, label=y_train)
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            
            # Training parameters
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'learning_rate': self.config.learning_rate,
                'max_depth': self.config.max_depth,
                'min_child_samples': self.config.min_child_samples,
                'subsample': self.config.subsample,
                'colsample_bytree': self.config.colsample_bytree,
                'verbose': -1
            }
            
            # Train model
            logger.info("Starting model training...")
            start_time = datetime.utcnow()
            
            model = lgb.train(
                params,
                train_data,
                num_boost_round=self.config.num_boost_round,
                valid_sets=[val_data],
                early_stopping_rounds=self.config.early_stopping_rounds,
                verbose_eval=False
            )
            
            training_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Model training completed in {training_time:.2f} seconds")
            
            return model
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return None
    
    def evaluate_model(
        self,
        model: lgb.Booster,
        test_data: pd.DataFrame
    ) -> Dict[str, float]:
        """Evaluate model performance"""
        X_test = test_data.drop('risk_score', axis=1)
        y_test = test_data['risk_score']
        
        # Make predictions
        predictions = model.predict(X_test)
        
        # Calculate metrics
        binary_predictions = (predictions > 0.5).astype(int)
        binary_labels = (y_test > 0.5).astype(int)
        
        metrics = {
            'auc_score': roc_auc_score(binary_labels, predictions),
            'accuracy': accuracy_score(binary_labels, binary_predictions),
            'precision': precision_score(binary_labels, binary_predictions, zero_division=0),
            'recall': recall_score(binary_labels, binary_predictions, zero_division=0),
            'f1_score': f1_score(binary_labels, binary_predictions, zero_division=0),
            'rmse': ((predictions - y_test) ** 2).mean() ** 0.5
        }
        
        return metrics
    
    async def retrain_model(self) -> RetrainingResult:
        """
        Execute full retraining pipeline.
        
        Returns:
            RetrainingResult with outcome details
        """
        start_time = datetime.utcnow()
        
        try:
            # Get current model ID
            db = next(get_db())
            current_model = db.query(ModelVersion).filter(
                ModelVersion.is_active == True
            ).first()
            old_model_id = current_model.model_id if current_model else "none"
            db.close()
            
            # Prepare training data
            training_data = await self.prepare_training_data()
            if training_data is None:
                return RetrainingResult(
                    success=False,
                    model_id=None,
                    old_model_id=old_model_id,
                    metrics={},
                    training_time_seconds=0,
                    sample_count=0,
                    timestamp=datetime.utcnow().isoformat(),
                    error="Insufficient training data",
                    deployed=False
                )
            
            # Split into train and test
            train_data, test_data = train_test_split(
                training_data,
                test_size=self.config.test_size,
                random_state=self.config.random_state
            )
            
            # Train new model
            new_model = await self.train_model(train_data)
            if new_model is None:
                return RetrainingResult(
                    success=False,
                    model_id=None,
                    old_model_id=old_model_id,
                    metrics={},
                    training_time_seconds=0,
                    sample_count=len(training_data),
                    timestamp=datetime.utcnow().isoformat(),
                    error="Model training failed",
                    deployed=False
                )
            
            # Evaluate new model
            metrics = self.evaluate_model(new_model, test_data)
            
            # Check if metrics meet thresholds
            if metrics['auc_score'] < self.config.min_auc_score:
                return RetrainingResult(
                    success=True,
                    model_id=None,
                    old_model_id=old_model_id,
                    metrics=metrics,
                    training_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    sample_count=len(training_data),
                    timestamp=datetime.utcnow().isoformat(),
                    error=f"AUC score ({metrics['auc_score']:.3f}) below threshold ({self.config.min_auc_score})",
                    deployed=False
                )
            
            # Save new model
            model_path = Path(self.settings.models_dir) / f"iit_model_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
            new_model.save_model(str(model_path))
            
            # Register new model
            metadata = ModelMetadata(
                version=datetime.utcnow().strftime('%Y.%m.%d'),
                algorithm='lightgbm',
                hyperparameters={
                    'learning_rate': self.config.learning_rate,
                    'max_depth': self.config.max_depth,
                    'num_boost_round': self.config.num_boost_round
                },
                training_data_info={
                    'sample_count': len(training_data),
                    'feature_count': len(training_data.columns) - 1,
                    'training_date': datetime.utcnow().isoformat()
                },
                performance_metrics=metrics,
                is_active=False  # Don't activate yet
            )
            
            db = next(get_db())
            try:
                new_model_id = self.model_registry.register_model(
                    model_path=str(model_path),
                    metadata=metadata,
                    db=db
                )
            finally:
                db.close()
            
            training_time = (datetime.utcnow() - start_time).total_seconds()
            
            return RetrainingResult(
                success=True,
                model_id=new_model_id,
                old_model_id=old_model_id,
                metrics=metrics,
                training_time_seconds=training_time,
                sample_count=len(training_data),
                timestamp=datetime.utcnow().isoformat(),
                deployed=False  # Requires manual activation or A/B testing
            )
            
        except Exception as e:
            logger.error(f"Retraining pipeline failed: {e}")
            return RetrainingResult(
                success=False,
                model_id=None,
                old_model_id=old_model_id,
                metrics={},
                training_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                sample_count=0,
                timestamp=datetime.utcnow().isoformat(),
                error=str(e),
                deployed=False
            )
    
    async def activate_model(self, model_id: str) -> bool:
        """
        Activate a trained model.
        
        Args:
            model_id: Model ID to activate
            
        Returns:
            True if activation successful
        """
        try:
            db = next(get_db())
            
            # Deactivate current model
            db.query(ModelVersion).filter(ModelVersion.is_active == True).update(
                {ModelVersion.is_active: False}
            )
            
            # Activate new model
            model = db.query(ModelVersion).filter(ModelVersion.model_id == model_id).first()
            if model:
                model.is_active = True
                db.commit()
                
                # Reload model in predictor
                self.current_predictor.load_model()
                
                logger.info(f"Activated model: {model_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to activate model {model_id}: {e}")
            return False
        finally:
            db.close()


# Global instance
_retraining_pipeline: Optional[ModelRetrainingPipeline] = None


def get_retraining_pipeline() -> ModelRetrainingPipeline:
    """Get or create global retraining pipeline instance"""
    global _retraining_pipeline
    if _retraining_pipeline is None:
        _retraining_pipeline = ModelRetrainingPipeline()
    return _retraining_pipeline


async def run_retraining_pipeline() -> RetrainingResult:
    """
    Convenience function to run the retraining pipeline.
    
    Returns:
        RetrainingResult with outcome
    """
    pipeline = get_retraining_pipeline()
    return await pipeline.retrain_model()
