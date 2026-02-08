"""
Ensemble Methods API endpoints for IIT Prediction ML Service
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum
import logging

from ..core.db import get_db
from ..ensemble_methods import get_ensemble_engine, EnsembleType, VotingStrategy, EnsembleConfigurationData
from ..models import EnsembleConfiguration, EnsemblePrediction
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ensemble", tags=["Ensemble Methods"])


class EnsembleTypeEnum(str, Enum):
    AVERAGING = "averaging"
    WEIGHTED_AVERAGING = "weighted_averaging"
    VOTING = "voting"
    WEIGHTED_VOTING = "weighted_voting"
    STACKING = "stacking"
    BOOSTING = "boosting"


class VotingStrategyEnum(str, Enum):
    MAJORITY = "majority"
    SOFT = "soft"
    WEIGHTED = "weighted"


class EnsembleCreateRequest(BaseModel):
    """Request model for creating ensemble"""
    ensemble_type: EnsembleTypeEnum
    model_ids: List[str]
    weights: Optional[List[float]] = None
    voting_strategy: VotingStrategyEnum = VotingStrategyEnum.SOFT
    meta_model_id: Optional[str] = None
    threshold: float = 0.5


class EnsembleResponse(BaseModel):
    """Response model for ensemble"""
    ensemble_id: str
    ensemble_type: str
    model_ids: List[str]
    weights: Optional[List[float]]
    voting_strategy: str
    meta_model_id: Optional[str]
    threshold: float
    created_at: str


class EnsemblePredictionRequest(BaseModel):
    """Request model for ensemble prediction"""
    patient_uuid: str
    features: Dict[str, Any]


class EnsemblePredictionResponse(BaseModel):
    """Response model for ensemble prediction"""
    ensemble_id: str
    prediction_id: str
    patient_uuid: str
    ensemble_score: float
    risk_level: str
    individual_predictions: Dict[str, float]
    confidence_score: float
    created_at: str


@router.post("/ensembles", response_model=EnsembleResponse)
async def create_ensemble(
    request: EnsembleCreateRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Create a new ensemble configuration"""
    try:
        engine = get_ensemble_engine()

        # Convert request to configuration
        config = EnsembleConfigurationData(
            ensemble_type=EnsembleType(request.ensemble_type.value),
            model_ids=request.model_ids,
            weights=request.weights,
            voting_strategy=VotingStrategy(request.voting_strategy.value),
            meta_model_id=request.meta_model_id,
            threshold=request.threshold
        )

        # Create the ensemble
        ensemble_id = engine.create_ensemble(config, db)

        # Get the created ensemble
        ensemble = db.query(EnsembleConfiguration).filter(
            EnsembleConfiguration.ensemble_id == ensemble_id
        ).first()

        if not ensemble:
            raise HTTPException(status_code=500, detail="Failed to create ensemble")

        return EnsembleResponse(
            ensemble_id=ensemble.ensemble_id,
            ensemble_type=ensemble.ensemble_type,
            model_ids=ensemble.model_ids,
            weights=ensemble.weights,
            voting_strategy=ensemble.voting_strategy,
            meta_model_id=ensemble.meta_model_id,
            threshold=ensemble.threshold,
            created_at=ensemble.created_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to create ensemble: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ensembles", response_model=List[EnsembleResponse])
async def list_ensembles(
    ensemble_type: Optional[EnsembleTypeEnum] = Query(None, description="Filter by ensemble type"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """List all ensemble configurations"""
    try:
        query = db.query(EnsembleConfiguration)

        if ensemble_type:
            query = query.filter(EnsembleConfiguration.ensemble_type == ensemble_type.value)

        ensembles = query.order_by(EnsembleConfiguration.created_at.desc()).all()

        return [
            EnsembleResponse(
                ensemble_id=ensemble.ensemble_id,
                ensemble_type=ensemble.ensemble_type,
                model_ids=ensemble.model_ids,
                weights=ensemble.weights,
                voting_strategy=ensemble.voting_strategy,
                meta_model_id=ensemble.meta_model_id,
                threshold=ensemble.threshold,
                created_at=ensemble.created_at.isoformat()
            )
            for ensemble in ensembles
        ]

    except Exception as e:
        logger.error(f"Failed to list ensembles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ensembles/{ensemble_id}", response_model=EnsembleResponse)
async def get_ensemble(
    ensemble_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get ensemble configuration details"""
    try:
        ensemble = db.query(EnsembleConfiguration).filter(
            EnsembleConfiguration.ensemble_id == ensemble_id
        ).first()

        if not ensemble:
            raise HTTPException(status_code=404, detail="Ensemble not found")

        return EnsembleResponse(
            ensemble_id=ensemble.ensemble_id,
            ensemble_type=ensemble.ensemble_type,
            model_ids=ensemble.model_ids,
            weights=ensemble.weights,
            voting_strategy=ensemble.voting_strategy,
            meta_model_id=ensemble.meta_model_id,
            threshold=ensemble.threshold,
            created_at=ensemble.created_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ensemble {ensemble_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ensembles/{ensemble_id}/predict", response_model=EnsemblePredictionResponse)
async def predict_with_ensemble(
    ensemble_id: str,
    request: EnsemblePredictionRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Make prediction using ensemble"""
    try:
        engine = get_ensemble_engine()

        result = engine.predict_with_ensemble(
            ensemble_id=ensemble_id,
            patient_uuid=request.patient_uuid,
            features=request.features,
            db=db
        )

        if not result:
            raise HTTPException(status_code=500, detail="Ensemble prediction failed")

        return EnsemblePredictionResponse(
            ensemble_id=result.ensemble_id,
            prediction_id=result.prediction_id,
            patient_uuid=result.patient_uuid,
            ensemble_score=result.ensemble_score,
            risk_level=result.risk_level,
            individual_predictions=result.individual_predictions,
            confidence_score=result.confidence_score,
            created_at=result.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to make ensemble prediction for {ensemble_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ensembles/{ensemble_id}/predictions", response_model=List[EnsemblePredictionResponse])
async def get_ensemble_predictions(
    ensemble_id: str,
    patient_uuid: Optional[str] = Query(None, description="Filter by patient UUID"),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=1000),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get predictions made by an ensemble"""
    try:
        query = db.query(EnsemblePrediction).filter(
            EnsemblePrediction.ensemble_id == ensemble_id
        )

        if patient_uuid:
            query = query.filter(EnsemblePrediction.patient_uuid == patient_uuid)

        predictions = query.order_by(EnsemblePrediction.created_at.desc()).offset(offset).limit(limit).all()

        return [
            EnsemblePredictionResponse(
                ensemble_id=pred.ensemble_id,
                prediction_id=pred.prediction_id,
                patient_uuid=pred.patient_uuid,
                ensemble_score=pred.ensemble_score,
                risk_level=pred.risk_level,
                individual_predictions=pred.individual_predictions,
                confidence_score=pred.confidence_score,
                created_at=pred.created_at.isoformat()
            )
            for pred in predictions
        ]

    except Exception as e:
        logger.error(f"Failed to get predictions for ensemble {ensemble_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ensembles/{ensemble_id}/performance")
async def get_ensemble_performance(
    ensemble_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get performance metrics for an ensemble"""
    try:
        # Get recent predictions for the ensemble
        recent_predictions = db.query(EnsemblePrediction).filter(
            EnsemblePrediction.ensemble_id == ensemble_id
        ).order_by(EnsemblePrediction.created_at.desc()).limit(1000).all()

        if not recent_predictions:
            return {"message": "No predictions found for performance analysis"}

        # Calculate basic performance metrics
        scores = [p.ensemble_score for p in recent_predictions]
        confidence_scores = [p.confidence_score for p in recent_predictions]

        performance = {
            "total_predictions": len(recent_predictions),
            "average_score": float(sum(scores) / len(scores)),
            "score_std": float((sum((x - sum(scores)/len(scores))**2 for x in scores) / len(scores))**0.5),
            "average_confidence": float(sum(confidence_scores) / len(confidence_scores)),
            "risk_distribution": {
                "Low": sum(1 for p in recent_predictions if p.risk_level == "Low"),
                "Medium": sum(1 for p in recent_predictions if p.risk_level == "Medium"),
                "High": sum(1 for p in recent_predictions if p.risk_level == "High")
            }
        }

        return performance

    except Exception as e:
        logger.error(f"Failed to get performance for ensemble {ensemble_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ensembles/{ensemble_id}")
async def delete_ensemble(
    ensemble_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Delete an ensemble configuration"""
    try:
        ensemble = db.query(EnsembleConfiguration).filter(
            EnsembleConfiguration.ensemble_id == ensemble_id
        ).first()

        if not ensemble:
            raise HTTPException(status_code=404, detail="Ensemble not found")

        # Delete associated predictions first
        db.query(EnsemblePrediction).filter(
            EnsemblePrediction.ensemble_id == ensemble_id
        ).delete()

        # Delete the ensemble
        db.delete(ensemble)
        db.commit()

        return {"message": f"Ensemble {ensemble_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete ensemble {ensemble_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ensemble-types")
async def get_ensemble_types():
    """Get available ensemble types and their descriptions"""
    return {
        "types": [
            {
                "type": "averaging",
                "name": "Simple Averaging",
                "description": "Average predictions from all models with equal weights"
            },
            {
                "type": "weighted_averaging",
                "name": "Weighted Averaging",
                "description": "Average predictions using custom weights for each model"
            },
            {
                "type": "voting",
                "name": "Voting",
                "description": "Use voting strategy to combine model predictions"
            },
            {
                "type": "weighted_voting",
                "name": "Weighted Voting",
                "description": "Use weighted voting strategy for model combination"
            },
            {
                "type": "stacking",
                "name": "Stacking",
                "description": "Use a meta-model to combine predictions from base models"
            },
            {
                "type": "boosting",
                "name": "Boosting",
                "description": "Boost better performing models and combine predictions"
            }
        ]
    }
