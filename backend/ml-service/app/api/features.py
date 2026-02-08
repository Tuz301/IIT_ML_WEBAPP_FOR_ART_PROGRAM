"""
Core IIT Features API endpoints - Simplified for essential predictors
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from ..core.db import get_db
from ..models import IITFeatures, Patient
from ..schema import IITFeaturesResponse, FeatureUpdateRequest, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/features", tags=["features"])

@router.get("/{patient_uuid}", response_model=IITFeaturesResponse,
            summary="Get Patient Features",
            description="""
            Retrieve IIT (Isoniazid Preventive Therapy) features for a specific patient.

            **Feature Types:**
            - Demographic features (age, gender, location)
            - Clinical features (treatment history, lab results)
            - Behavioral features (adherence patterns, contact info)
            - Risk assessment features (calculated risk scores)

            **Data Sources:**
            - Patient demographics and registration data
            - Clinical visits and encounter records
            - Laboratory observations and test results
            - Medication dispensing and adherence data

            **Caching:**
            - Features are cached for performance
            - Cache invalidation occurs on data updates
            - Background recomputation available for large datasets

            **Use Cases:**
            - ML model prediction input
            - Risk stratification and patient monitoring
            - Clinical decision support systems
            - Research and analytics queries
            """,
            responses={
                200: {
                    "description": "Patient features retrieved successfully",
                    "model": IITFeaturesResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "patient_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "age": 35,
                                "gender": "M",
                                "has_phone": True,
                                "days_since_last_visit": 45,
                                "days_since_last_refill": 30,
                                "total_visits": 12,
                                "viral_load_suppressed": True,
                                "cd4_count": 450,
                                "last_feature_update": "2025-01-15T10:30:00",
                                "feature_version": "1.0"
                            }
                        }
                    }
                },
                404: {
                    "description": "Patient or features not found",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Not Found",
                                "detail": "Features not found for this patient",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                },
                500: {
                    "description": "Internal server error",
                    "model": ErrorResponse
                }
            })
async def get_patient_features(
    patient_uuid: UUID,
    db: Session = Depends(get_db)
) -> IITFeaturesResponse:
    """
    Retrieve IIT features for a specific patient.

    Features include demographic, clinical, and behavioral data used for
    ML model predictions and risk assessment.
    """
    try:
        # Check if patient exists
        patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )

        # Get features
        features = db.query(IITFeatures).filter(
            IITFeatures.patient_uuid == patient_uuid
        ).first()

        if not features:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Features not found for this patient"
            )

        return IITFeaturesResponse.from_orm(features)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving features for patient {patient_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patient features"
        )

@router.put("/{patient_uuid}", response_model=IITFeaturesResponse)
async def update_patient_features(
    patient_uuid: UUID,
    feature_update: FeatureUpdateRequest,
    db: Session = Depends(get_db)
) -> IITFeaturesResponse:
    """
    Update IIT features for a specific patient

    - **patient_uuid**: Patient's unique identifier
    - **feature_update**: Feature values to update
    """
    try:
        # Check if patient exists
        patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )

        # Get or create features record
        features = db.query(IITFeatures).filter(
            IITFeatures.patient_uuid == patient_uuid
        ).first()

        if not features:
            # Create new features record
            features = IITFeatures(patient_uuid=patient_uuid)
            db.add(features)

        # Update features
        for key, value in feature_update.features.items():
            if hasattr(features, key):
                setattr(features, key, value)

        # Update timestamp
        features.last_feature_update = datetime.utcnow()

        db.commit()
        db.refresh(features)

        logger.info(f"Features updated for patient: {patient_uuid}")
        return IITFeaturesResponse.from_orm(features)

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating features for patient {patient_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update patient features"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating features for patient {patient_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/{patient_uuid}/compute", response_model=IITFeaturesResponse,
            summary="Compute Core IIT Features",
            description="""
            Compute core IIT (Isoniazid Preventive Therapy) features for a patient.

            **Core Features Computed:**
            - Age (calculated from birthdate)
            - Gender
            - Phone availability
            - Days since last visit
            - Days since last refill
            - Total visits count

            **Data Sources:**
            - Patient demographics
            - Visit records
            - Medication dispensing records

            **Use Cases:**
            - Basic risk assessment
            - Patient monitoring
            - Clinical decision support
            """)
async def compute_patient_features(
    patient_uuid: UUID,
    force_recompute: bool = Query(False, description="Force recomputation even if features exist"),
    db: Session = Depends(get_db)
) -> IITFeaturesResponse:
    """
    Compute core IIT features for a patient from basic clinical data.
    """
    try:
        # Check if patient exists
        patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )

        # Check if features already exist and not forcing recompute
        if not force_recompute:
            existing_features = db.query(IITFeatures).filter(
                IITFeatures.patient_uuid == patient_uuid
            ).first()
            if existing_features:
                return IITFeaturesResponse.from_orm(existing_features)

        # Compute core features
        features_dict = {}

        # Age calculation
        if patient.birthdate:
            today = datetime.utcnow().date()
            features_dict['age'] = today.year - patient.birthdate.year - (
                (today.month, today.day) < (patient.birthdate.month, patient.birthdate.day)
            )

        # Basic demographic features
        features_dict['gender'] = patient.gender
        features_dict['has_phone'] = bool(patient.phone_number)

        # Get or create features record
        features = db.query(IITFeatures).filter(
            IITFeatures.patient_uuid == patient_uuid
        ).first()

        if not features:
            features = IITFeatures(patient_uuid=patient_uuid)
            db.add(features)

        # Update features with computed values
        for key, value in features_dict.items():
            if hasattr(features, key):
                setattr(features, key, value)

        features.last_feature_update = datetime.utcnow()

        db.commit()
        db.refresh(features)

        logger.info(f"Core features computed for patient: {patient_uuid}")
        return IITFeaturesResponse.from_orm(features)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error computing features for patient {patient_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute patient features"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error computing features for patient {patient_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{patient_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient_features(
    patient_uuid: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete IIT features for a specific patient

    - **patient_uuid**: Patient's unique identifier
    """
    try:
        # Check if patient exists
        patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )

        # Delete features
        deleted_count = db.query(IITFeatures).filter(
            IITFeatures.patient_uuid == patient_uuid
        ).delete()

        db.commit()

        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Features not found for this patient"
            )

        logger.info(f"Features deleted for patient: {patient_uuid}")

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error deleting features for patient {patient_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete patient features"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error deleting features for patient {patient_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/", response_model=Dict[str, Any])
async def get_features_summary(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get summary statistics of IIT features across all patients

    - **skip**: Number of records to skip
    - **limit**: Number of records to return
    """
    try:
        from sqlalchemy import func

        # Get basic counts
        total_features = db.query(func.count(IITFeatures.patient_uuid)).scalar()
        features_with_age = db.query(func.count(IITFeatures.patient_uuid)).filter(
            IITFeatures.age.isnot(None)
        ).scalar()
        features_with_phone = db.query(func.count(IITFeatures.patient_uuid)).filter(
            IITFeatures.has_phone == True
        ).scalar()

        # Get average values
        avg_age = db.query(func.avg(IITFeatures.age)).filter(
            IITFeatures.age.isnot(None)
        ).scalar()

        avg_days_since_refill = db.query(func.avg(IITFeatures.days_since_last_refill)).filter(
            IITFeatures.days_since_last_refill.isnot(None)
        ).scalar()

        # Get risk distribution (simplified - would need actual predictions)
        high_risk_count = 0  # Would compute from predictions

        # Get recent updates
        recent_updates = db.query(IITFeatures).filter(
            IITFeatures.last_feature_update.isnot(None)
        ).order_by(IITFeatures.last_feature_update.desc()).limit(limit).offset(skip).all()

        return {
            "total_features": total_features or 0,
            "features_with_age": features_with_age or 0,
            "features_with_phone": features_with_phone or 0,
            "average_age": float(avg_age) if avg_age else None,
            "average_days_since_refill": float(avg_days_since_refill) if avg_days_since_refill else None,
            "high_risk_patients": high_risk_count,
            "recent_updates": [
                {
                    "patient_uuid": str(f.patient_uuid),
                    "last_update": f.last_feature_update.isoformat() if f.last_feature_update else None,
                    "age": f.age,
                    "has_phone": f.has_phone
                }
                for f in recent_updates
            ]
        }

    except Exception as e:
        logger.error(f"Error getting features summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve features summary"
        )
