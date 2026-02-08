"""
Predictions API endpoints for IIT risk assessment
"""
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..core.db import get_db
from ..models import IITPrediction as Prediction, Patient
from ..schema import (
    PredictionCreate, PredictionResponse, PredictionListResponse,
    PredictionSearchFilters, BatchPredictionRequest, BatchPredictionResponse,
    PredictionAnalyticsResponse, ErrorResponse
)
from ..ml_model import get_model
from ..feature_store import get_feature_store
from ..monitoring import MetricsManager
from ..dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post("/", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED,
            summary="Create IIT Risk Prediction",
            description="""
            Generate a new IIT (Interruption in Treatment) risk prediction for a patient using machine learning models.

            **Prediction Process:**
            1. **Patient Validation**: Verify patient exists in the system
            2. **Feature Extraction**: Extract relevant clinical and demographic features
            3. **Model Inference**: Run prediction using trained ML model
            4. **Risk Assessment**: Calculate risk score and determine risk level
            5. **Audit Trail**: Record prediction with full traceability

            **Risk Levels:**
            - **Low (0.0 - 0.3)**: Routine monitoring recommended
            - **Medium (0.3 - 0.5)**: Increased monitoring and preventive measures
            - **High (0.5 - 0.75)**: Immediate intervention required
            - **Critical (0.75+)**: Urgent clinical attention needed

            **Features Used:**
            - Patient demographics (age, gender, location)
            - Clinical measurements (CD4 count, viral load)
            - Treatment history (days since last refill, medication adherence)
            - Visit patterns (frequency, regularity)
            - Laboratory results (recent test values)

            **Audit Trail:**
            - Prediction timestamp and user tracking
            - Model version used for reproducibility
            - Feature values used in calculation
            - Confidence score for prediction reliability

            **Use Cases:**
            - Clinical decision support for treatment planning
            - Risk stratification for resource allocation
            - Patient monitoring and follow-up scheduling
            - Research and epidemiological studies
            """,
            responses={
                201: {
                    "description": "Prediction created successfully",
                    "model": PredictionResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "id": 123,
                                "patient_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "risk_score": 0.68,
                                "risk_level": "high",
                                "confidence": 0.85,
                                "features_used": {
                                    "age": 35,
                                    "days_since_last_refill": 45,
                                    "last_days_supply": 30,
                                    "visit_count_last_90d": 2,
                                    "cd4_count": 380
                                },
                                "model_version": "1.2.0",
                                "prediction_timestamp": "2025-01-15T10:30:00",
                                "created_by": "clinician-001",
                                "created_at": "2025-01-15T10:30:00",
                                "updated_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                404: {
                    "description": "Patient not found",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Not Found",
                                "detail": "Patient not found",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                },
                422: {
                    "description": "Validation error in prediction data",
                    "model": ErrorResponse
                },
                500: {
                    "description": "Internal server error during prediction",
                    "model": ErrorResponse
                }
            })
async def create_prediction(
    prediction_data: PredictionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new IIT risk prediction for a patient.

    Validates patient existence, extracts features, runs ML model prediction,
    and stores results with full audit trail and metrics tracking.
    """
    try:
        # Check if patient exists
        patient = db.query(Patient).filter(Patient.patient_uuid == prediction_data.patient_uuid).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )

        # Get model and feature store
        model = get_model()
        feature_store = await get_feature_store()

        # Extract features (all 32 features required by the model)
        features = {
            "age": prediction_data.features.get("age", 30),
            "age_group": prediction_data.features.get("age_group", 3),
            "gender": prediction_data.features.get("gender", 1),
            "has_state": prediction_data.features.get("has_state", 1),
            "has_city": prediction_data.features.get("has_city", 1),
            "has_phone": prediction_data.features.get("has_phone", 1),
            "has_pharmacy_history": prediction_data.features.get("has_pharmacy_history", 1),
            "total_dispensations": prediction_data.features.get("total_dispensations", 5),
            "avg_days_supply": prediction_data.features.get("avg_days_supply", 30),
            "last_days_supply": prediction_data.features.get("last_days_supply", 30),
            "days_since_last_refill": prediction_data.features.get("days_since_last_refill", 30),
            "refill_frequency_3m": prediction_data.features.get("refill_frequency_3m", 2),
            "refill_frequency_6m": prediction_data.features.get("refill_frequency_6m", 4),
            "mmd_ratio": prediction_data.features.get("mmd_ratio", 0.5),
            "regimen_stability": prediction_data.features.get("regimen_stability", 1),
            "last_regimen_complexity": prediction_data.features.get("last_regimen_complexity", 0),
            "adherence_counseling_count": prediction_data.features.get("adherence_counseling_count", 1),
            "total_visits": prediction_data.features.get("total_visits", 5),
            "visit_frequency_3m": prediction_data.features.get("visit_frequency_3m", 2),
            "visit_frequency_6m": prediction_data.features.get("visit_frequency_6m", 4),
            "visit_frequency_12m": prediction_data.features.get("visit_frequency_12m", 8),
            "days_since_last_visit": prediction_data.features.get("days_since_last_visit", 30),
            "visit_regularity": prediction_data.features.get("visit_regularity", 0.7),
            "clinical_visit_ratio": prediction_data.features.get("clinical_visit_ratio", 0.8),
            "who_stage": prediction_data.features.get("who_stage", 1),
            "has_vl_data": prediction_data.features.get("has_vl_data", 1),
            "recent_vl_tests": prediction_data.features.get("recent_vl_tests", 2),
            "has_tb_symptoms": prediction_data.features.get("has_tb_symptoms", 0),
            "functional_status": prediction_data.features.get("functional_status", 0),
            "pregnancy_status": prediction_data.features.get("pregnancy_status", 0),
            "adherence_level": prediction_data.features.get("adherence_level", 2),
            "month": prediction_data.features.get("month", 1),
            "quarter": prediction_data.features.get("quarter", 0),
            "is_holiday_season": prediction_data.features.get("is_holiday_season", 0),
            "is_rainy_season": prediction_data.features.get("is_rainy_season", 0),
            "day_of_week": prediction_data.features.get("day_of_week", 0),
            "is_year_end": prediction_data.features.get("is_year_end", 0)
        }

        # Make prediction
        import pandas as pd
        feature_df = pd.DataFrame([features])
        risk_score = float(model.predict(feature_df)[0])

        # Determine risk level
        if risk_score >= 0.75:
            risk_level = "critical"
        elif risk_score >= 0.5:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Calculate confidence
        confidence = min(abs(risk_score - 0.5) * 2, 1.0)

        # Create prediction record
        prediction = Prediction(
            patient_uuid=prediction_data.patient_uuid,
            prediction_score=risk_score,
            risk_level=risk_level,
            confidence=confidence,
            features=features,
            model_version=model.model_version
        )

        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        # Record metrics
        MetricsManager.record_prediction(
            risk_level=risk_level,
            model_version=model.model_version
        )

        logger.info(f"Prediction created for patient {prediction_data.patient_uuid}")

        return PredictionResponse.from_orm(prediction)

    except Exception as e:
        logger.error(f"Failed to create prediction: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create prediction: {str(e)}"
        )


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific prediction by ID
    """
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )

    return PredictionResponse.from_orm(prediction)


@router.get("/", response_model=PredictionListResponse)
async def list_predictions(
    skip: int = 0,
    limit: int = 100,
    patient_uuid: Optional[UUID] = None,
    risk_level: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List predictions with optional filtering
    """
    query = db.query(Prediction)

    if patient_uuid:
        query = query.filter(Prediction.patient_uuid == patient_uuid)
    if risk_level:
        query = query.filter(Prediction.risk_level == risk_level)
    if start_date:
        query = query.filter(Prediction.created_at >= start_date)
    if end_date:
        query = query.filter(Prediction.created_at <= end_date)

    total = query.count()
    predictions = query.order_by(desc(Prediction.created_at)).offset(skip).limit(limit).all()

    return PredictionListResponse(
        predictions=[PredictionResponse.from_orm(p) for p in predictions],
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/batch", response_model=BatchPredictionResponse)
async def batch_predictions(
    batch_request: BatchPredictionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create batch predictions for multiple patients
    """
    if len(batch_request.predictions) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size cannot exceed 100 predictions"
        )

    successful_predictions = []
    failed_predictions = []

    model = get_model()

    for prediction_data in batch_request.predictions:
        try:
            # Check if patient exists
            patient = db.query(Patient).filter(Patient.patient_uuid == prediction_data.patient_uuid).first()
            if not patient:
                failed_predictions.append({
                    "patient_uuid": str(prediction_data.patient_uuid),
                    "error": "Patient not found"
                })
                continue

            # Extract features (all 32 features required by the model)
            features = {
                "age": prediction_data.features.get("age", 30),
                "age_group": prediction_data.features.get("age_group", 3),
                "gender": prediction_data.features.get("gender", 1),
                "has_state": prediction_data.features.get("has_state", 1),
                "has_city": prediction_data.features.get("has_city", 1),
                "has_phone": prediction_data.features.get("has_phone", 1),
                "has_pharmacy_history": prediction_data.features.get("has_pharmacy_history", 1),
                "total_dispensations": prediction_data.features.get("total_dispensations", 5),
                "avg_days_supply": prediction_data.features.get("avg_days_supply", 30),
                "last_days_supply": prediction_data.features.get("last_days_supply", 30),
                "days_since_last_refill": prediction_data.features.get("days_since_last_refill", 30),
                "refill_frequency_3m": prediction_data.features.get("refill_frequency_3m", 2),
                "refill_frequency_6m": prediction_data.features.get("refill_frequency_6m", 4),
                "mmd_ratio": prediction_data.features.get("mmd_ratio", 0.5),
                "regimen_stability": prediction_data.features.get("regimen_stability", 1),
                "last_regimen_complexity": prediction_data.features.get("last_regimen_complexity", 0),
                "adherence_counseling_count": prediction_data.features.get("adherence_counseling_count", 1),
                "total_visits": prediction_data.features.get("total_visits", 5),
                "visit_frequency_3m": prediction_data.features.get("visit_frequency_3m", 2),
                "visit_frequency_6m": prediction_data.features.get("visit_frequency_6m", 4),
                "visit_frequency_12m": prediction_data.features.get("visit_frequency_12m", 8),
                "days_since_last_visit": prediction_data.features.get("days_since_last_visit", 30),
                "visit_regularity": prediction_data.features.get("visit_regularity", 0.7),
                "clinical_visit_ratio": prediction_data.features.get("clinical_visit_ratio", 0.8),
                "who_stage": prediction_data.features.get("who_stage", 1),
                "has_vl_data": prediction_data.features.get("has_vl_data", 1),
                "recent_vl_tests": prediction_data.features.get("recent_vl_tests", 2),
                "has_tb_symptoms": prediction_data.features.get("has_tb_symptoms", 0),
                "functional_status": prediction_data.features.get("functional_status", 0),
                "pregnancy_status": prediction_data.features.get("pregnancy_status", 0),
                "adherence_level": prediction_data.features.get("adherence_level", 2),
                "month": prediction_data.features.get("month", 1),
                "quarter": prediction_data.features.get("quarter", 0),
                "is_holiday_season": prediction_data.features.get("is_holiday_season", 0),
                "is_rainy_season": prediction_data.features.get("is_rainy_season", 0),
                "day_of_week": prediction_data.features.get("day_of_week", 0),
                "is_year_end": prediction_data.features.get("is_year_end", 0)
            }

            # Make prediction
            import pandas as pd
            feature_df = pd.DataFrame([features])
            risk_score = float(model.predict(feature_df)[0])

            # Determine risk level
            if risk_score >= 0.75:
                risk_level = "critical"
            elif risk_score >= 0.5:
                risk_level = "high"
            elif risk_score >= 0.3:
                risk_level = "medium"
            else:
                risk_level = "low"

            confidence = min(abs(risk_score - 0.5) * 2, 1.0)

            # Create prediction record
            prediction = Prediction(
                patient_uuid=prediction_data.patient_uuid,
                prediction_score=risk_score,
                risk_level=risk_level,
                confidence=confidence,
                features=features,
                model_version=model.model_version
            )

            db.add(prediction)
            db.commit()
            db.refresh(prediction)

            successful_predictions.append(PredictionResponse.from_orm(prediction))

            # Record metrics
            MetricsManager.record_prediction(
                risk_level=risk_level,
                model_version=model.model_version
            )

        except Exception as e:
            db.rollback()
            failed_predictions.append({
                "patient_uuid": str(prediction_data.patient_uuid),
                "error": str(e)
            })

    return BatchPredictionResponse(
        successful_predictions=successful_predictions,
        failed_predictions=failed_predictions,
        total_processed=len(successful_predictions),
        total_failed=len(failed_predictions)
    )


@router.delete("/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a prediction record
    """
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )

    db.delete(prediction)
    db.commit()

    logger.info(f"Prediction {prediction_id} deleted")


@router.get("/analytics/overview", response_model=PredictionAnalyticsResponse)
async def get_prediction_analytics(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get prediction analytics overview
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Risk distribution
    risk_counts = db.query(
        Prediction.risk_level,
        func.count(Prediction.id).label('count')
    ).filter(
        Prediction.created_at >= start_date
    ).group_by(Prediction.risk_level).all()

    risk_distribution = {risk: count for risk, count in risk_counts}

    # Trend data (daily counts)
    trend_data = db.query(
        func.date(Prediction.created_at).label('date'),
        func.count(Prediction.id).label('count')
    ).filter(
        Prediction.created_at >= start_date
    ).group_by(func.date(Prediction.created_at)).order_by(func.date(Prediction.created_at)).all()

    trend = [{"date": str(date), "count": count} for date, count in trend_data]

    # Performance metrics
    total_predictions = db.query(func.count(Prediction.id)).filter(
        Prediction.created_at >= start_date
    ).scalar()

    avg_confidence = db.query(func.avg(Prediction.confidence)).filter(
        Prediction.created_at >= start_date
    ).scalar() or 0

    return PredictionAnalyticsResponse(
        total_predictions=total_predictions,
        risk_distribution=risk_distribution,
        trend_data=trend,
        average_confidence=float(avg_confidence),
        period_days=days
    )
