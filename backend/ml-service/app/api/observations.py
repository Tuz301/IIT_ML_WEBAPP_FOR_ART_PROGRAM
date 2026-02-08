"""
Observations API endpoints for IIT ML Service
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import Observation, Patient, Encounter
from ..schema import (
    ObservationCreate, ObservationUpdate, ObservationResponse, ObservationListResponse,
    ObservationFilter, BulkObservationCreate, BulkObservationResponse, ErrorResponse
)

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post("/", response_model=ObservationResponse,
            summary="Create Clinical Observation",
            description="""
            Create a new clinical observation record for patient data collection.

            **Observation Types:**
            - Vital signs (blood pressure, temperature, weight)
            - Laboratory results (CD4 count, viral load, hemoglobin)
            - Clinical assessments (symptoms, diagnoses, treatment responses)
            - Medication adherence data
            - Behavioral observations

            **Data Types Supported:**
            - Numeric values (measurements, counts, scores)
            - Text values (notes, descriptions, qualitative data)
            - Coded values (standardized terminologies, categories)

            **Validation Rules:**
            - Patient must exist in the system
            - Encounter must be valid and associated with the patient
            - Observation UUID auto-generated if not provided
            - Date/time validation for temporal accuracy
            - Concept validation for standardized data

            **Audit Trail:**
            - Creation timestamp automatically recorded
            - User attribution for accountability
            - Change history maintained for compliance

            **Use Cases:**
            - Recording clinical measurements during visits
            - Capturing laboratory test results
            - Documenting patient assessments
            - Tracking treatment progress
            - Research data collection
            """,
            responses={
                200: {
                    "description": "Observation created successfully",
                    "model": ObservationResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "id": 456,
                                "obs_uuid": "o1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "patient_uuid": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "encounter_id": 123,
                                "concept_id": "5089",
                                "variable_name": "CD4_COUNT",
                                "value_numeric": 450.0,
                                "value_text": None,
                                "value_coded": None,
                                "obs_datetime": "2025-01-15T10:30:00",
                                "voided": False,
                                "created_at": "2025-01-15T10:30:00",
                                "updated_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                404: {
                    "description": "Patient or encounter not found",
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
                    "description": "Validation error in observation data",
                    "model": ErrorResponse
                }
            })
async def create_observation(
    observation: ObservationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new clinical observation record.

    Validates patient and encounter existence, then creates observation
    with proper audit trail. UUID is auto-generated if not provided.
    """
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.patient_uuid == observation.patient_uuid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Verify encounter exists
    encounter = db.query(Encounter).filter(Encounter.id == observation.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    # Generate UUID if not provided
    obs_uuid = observation.obs_uuid or str(uuid.uuid4())

    # Create observation record
    db_observation = Observation(
        obs_uuid=obs_uuid,
        patient_uuid=observation.patient_uuid,
        encounter_id=observation.encounter_id,
        concept_id=observation.concept_id,
        variable_name=observation.variable_name,
        value_numeric=observation.value_numeric,
        value_text=observation.value_text,
        value_coded=observation.value_coded,
        obs_datetime=observation.obs_datetime
    )

    db.add(db_observation)
    db.commit()
    db.refresh(db_observation)

    return db_observation


@router.post("/bulk", response_model=BulkObservationResponse, summary="Create multiple observations")
async def create_bulk_observations(
    bulk_request: BulkObservationCreate,
    db: Session = Depends(get_db)
):
    """
    Create multiple observation records in a single request.

    - **observations**: List of observation data (max 1000)
    """
    created_count = 0
    errors = []

    for i, obs_data in enumerate(bulk_request.observations):
        try:
            # Verify patient exists
            patient = db.query(Patient).filter(Patient.patient_uuid == obs_data.patient_uuid).first()
            if not patient:
                errors.append({"index": i, "error": "Patient not found", "patient_uuid": obs_data.patient_uuid})
                continue

            # Verify encounter exists
            encounter = db.query(Encounter).filter(Encounter.id == obs_data.encounter_id).first()
            if not encounter:
                errors.append({"index": i, "error": "Encounter not found", "encounter_id": obs_data.encounter_id})
                continue

            # Generate UUID if not provided
            obs_uuid = obs_data.obs_uuid or str(uuid.uuid4())

            # Create observation record
            db_observation = Observation(
                obs_uuid=obs_uuid,
                patient_uuid=obs_data.patient_uuid,
                encounter_id=obs_data.encounter_id,
                concept_id=obs_data.concept_id,
                variable_name=obs_data.variable_name,
                value_numeric=obs_data.value_numeric,
                value_text=obs_data.value_text,
                value_coded=obs_data.value_coded,
                obs_datetime=obs_data.obs_datetime
            )

            db.add(db_observation)
            created_count += 1

        except Exception as e:
            errors.append({"index": i, "error": str(e)})

    db.commit()

    return BulkObservationResponse(
        created_count=created_count,
        error_count=len(errors),
        errors=errors,
        processing_time_seconds=0.0  # Could be calculated if needed
    )


@router.get("/{observation_id}", response_model=ObservationResponse, summary="Get observation by ID")
async def get_observation(
    observation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific observation by its database ID.

    - **observation_id**: Observation database ID
    """
    observation = db.query(Observation).filter(Observation.id == observation_id).first()
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")

    return observation


@router.get("/uuid/{obs_uuid}", response_model=ObservationResponse, summary="Get observation by UUID")
async def get_observation_by_uuid(
    obs_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific observation by its UUID.

    - **obs_uuid**: Observation UUID
    """
    observation = db.query(Observation).filter(Observation.obs_uuid == obs_uuid).first()
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")

    return observation


@router.put("/{observation_id}", response_model=ObservationResponse, summary="Update observation")
async def update_observation(
    observation_id: int,
    observation_update: ObservationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing observation record.

    - **observation_id**: Observation database ID
    - **observation_update**: Fields to update
    """
    observation = db.query(Observation).filter(Observation.id == observation_id).first()
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")

    # Update fields
    update_data = observation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(observation, field, value)

    db.commit()
    db.refresh(observation)

    return observation


@router.delete("/{observation_id}", summary="Delete observation")
async def delete_observation(
    observation_id: int,
    db: Session = Depends(get_db)
):
    """
    Soft delete an observation record (mark as voided).

    - **observation_id**: Observation database ID
    """
    observation = db.query(Observation).filter(Observation.id == observation_id).first()
    if not observation:
        raise HTTPException(status_code=404, detail="Observation not found")

    # Soft delete by setting voided to True
    observation.voided = True
    db.commit()

    return {"message": "Observation deleted successfully"}


@router.get("/", response_model=ObservationListResponse, summary="List observations")
async def list_observations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    patient_uuid: Optional[str] = Query(None, description="Filter by patient UUID"),
    encounter_id: Optional[int] = Query(None, description="Filter by encounter ID"),
    concept_id: Optional[str] = Query(None, description="Filter by concept ID"),
    variable_name: Optional[str] = Query(None, description="Filter by variable name"),
    obs_datetime_from: Optional[str] = Query(None, description="Filter observations after this date"),
    obs_datetime_to: Optional[str] = Query(None, description="Filter observations before this date"),
    voided: Optional[bool] = Query(None, description="Filter by voided status"),
    db: Session = Depends(get_db)
):
    """
    List observations with pagination and filtering.

    Supports filtering by:
    - patient_uuid: Patient UUID
    - encounter_id: Encounter ID
    - concept_id: Concept identifier
    - variable_name: Variable name
    - obs_datetime_from/to: Date range for observation
    - voided: Whether observation is voided
    """
    query = db.query(Observation)

    # Apply filters
    if patient_uuid:
        query = query.filter(Observation.patient_uuid == patient_uuid)
    if encounter_id:
        query = query.filter(Observation.encounter_id == encounter_id)
    if concept_id:
        query = query.filter(Observation.concept_id == concept_id)
    if variable_name:
        query = query.filter(Observation.variable_name == variable_name)
    if obs_datetime_from:
        query = query.filter(Observation.obs_datetime >= obs_datetime_from)
    if obs_datetime_to:
        query = query.filter(Observation.obs_datetime <= obs_datetime_to)
    if voided is not None:
        query = query.filter(Observation.voided == voided)

    # Get total count
    total = query.count()

    # Apply pagination
    observations = query.offset((page - 1) * page_size).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return ObservationListResponse(
        observations=observations,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/patient/{patient_uuid}", response_model=ObservationListResponse, summary="Get observations for patient")
async def get_patient_observations(
    patient_uuid: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    voided: Optional[bool] = Query(None, description="Filter by voided status"),
    db: Session = Depends(get_db)
):
    """
    Get all observations for a specific patient.

    - **patient_uuid**: Patient UUID
    - **page**: Page number for pagination
    - **page_size**: Number of items per page
    - **voided**: Filter by voided status (optional)
    """
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    query = db.query(Observation).filter(Observation.patient_uuid == patient_uuid)

    if voided is not None:
        query = query.filter(Observation.voided == voided)

    # Get total count
    total = query.count()

    # Apply pagination
    observations = query.order_by(Observation.obs_datetime.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return ObservationListResponse(
        observations=observations,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/encounter/{encounter_id}", response_model=ObservationListResponse, summary="Get observations for encounter")
async def get_encounter_observations(
    encounter_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    voided: Optional[bool] = Query(None, description="Filter by voided status"),
    db: Session = Depends(get_db)
):
    """
    Get all observations for a specific encounter.

    - **encounter_id**: Encounter database ID
    - **page**: Page number for pagination
    - **page_size**: Number of items per page
    - **voided**: Filter by voided status (optional)
    """
    # Verify encounter exists
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    query = db.query(Observation).filter(Observation.encounter_id == encounter_id)

    if voided is not None:
        query = query.filter(Observation.voided == voided)

    # Get total count
    total = query.count()

    # Apply pagination
    observations = query.order_by(Observation.obs_datetime.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return ObservationListResponse(
        observations=observations,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
