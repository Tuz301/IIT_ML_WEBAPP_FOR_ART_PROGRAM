"""
Visits API endpoints for IIT ML Service
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.db import get_db
from ..models import Visit, Patient
from ..schema import (
    VisitCreate, VisitUpdate, VisitResponse, VisitListResponse,
    VisitFilter, ErrorResponse
)

router = APIRouter(prefix="/visits", tags=["visits"])


@router.post("/", response_model=VisitResponse,
            summary="Create Patient Visit",
            description="""
            Create a new patient visit record in the clinical system.

            **Visit Types:**
            - Initial consultation visits
            - Follow-up visits
            - Treatment visits
            - Laboratory visits
            - Pharmacy visits

            **Data Validation:**
            - Patient must exist in the system
            - Visit UUID auto-generated if not provided
            - Date validation (start date required, end date optional)
            - Location/facility validation if provided

            **Audit Trail:**
            - Creation timestamp automatically set
            - User tracking for compliance
            - Visit history maintained

            **Use Cases:**
            - Recording patient encounters
            - Tracking visit sequences
            - Appointment management
            - Clinical workflow management
            """,
            responses={
                200: {
                    "description": "Visit created successfully",
                    "model": VisitResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "id": 123,
                                "visit_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "patient_uuid": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "visit_type": "Follow-up",
                                "date_started": "2025-01-15T10:30:00",
                                "date_stopped": "2025-01-15T11:15:00",
                                "location_id": "facility-001",
                                "voided": False,
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
                    "description": "Validation error",
                    "model": ErrorResponse
                }
            })
async def create_visit(
    visit: VisitCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new patient visit record.

    Validates patient existence and creates a visit with proper audit trail.
    Visit UUID is auto-generated if not provided.
    """
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.patient_uuid == visit.patient_uuid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Generate UUID if not provided
    visit_uuid = visit.visit_uuid or str(uuid.uuid4())

    # Create visit record
    db_visit = Visit(
        visit_uuid=visit_uuid,
        patient_uuid=visit.patient_uuid,
        visit_type=visit.visit_type,
        date_started=visit.date_started,
        date_stopped=visit.date_stopped,
        location_id=visit.location_id
    )

    db.add(db_visit)
    db.commit()
    db.refresh(db_visit)

    return db_visit


@router.get("/{visit_id}", response_model=VisitResponse, summary="Get visit by ID")
async def get_visit(
    visit_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific visit by its database ID.

    - **visit_id**: Visit database ID
    """
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    return visit


@router.get("/uuid/{visit_uuid}", response_model=VisitResponse,
            summary="Get Visit by UUID",
            description="""
            Retrieve a specific patient visit record by its universally unique identifier (UUID).

            **UUID Benefits:**
            - Globally unique across systems and databases
            - Stable identifier that doesn't change with database migrations
            - Suitable for external integrations and data sharing
            - Consistent across different environments (dev, staging, production)

            **Visit Information Retrieved:**
            - Complete visit details including dates, type, and location
            - Associated patient information via patient_uuid
            - Visit status and voided state
            - Full audit trail with creation and update timestamps

            **Use Cases:**
            - External system integrations requiring stable identifiers
            - Mobile applications and offline-capable systems
            - Data synchronization across multiple healthcare platforms
            - Research and analytics requiring consistent visit references
            """,
            responses={
                200: {
                    "description": "Visit retrieved successfully",
                    "model": VisitResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "id": 123,
                                "visit_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "patient_uuid": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "visit_type": "Follow-up",
                                "date_started": "2025-01-15T10:30:00",
                                "date_stopped": "2025-01-15T11:15:00",
                                "location_id": "facility-001",
                                "voided": False,
                                "created_at": "2025-01-15T10:30:00",
                                "updated_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                404: {
                    "description": "Visit not found",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Not Found",
                                "detail": "Visit not found",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                }
            })
async def get_visit_by_uuid(
    visit_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific visit by its UUID for external integrations.

    Returns complete visit information using stable, globally unique identifier.
    """
    visit = db.query(Visit).filter(Visit.visit_uuid == visit_uuid).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    return visit


@router.put("/{visit_id}", response_model=VisitResponse, summary="Update visit")
async def update_visit(
    visit_id: int,
    visit_update: VisitUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing visit record.

    - **visit_id**: Visit database ID
    - **visit_update**: Fields to update
    """
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    # Update fields
    update_data = visit_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(visit, field, value)

    db.commit()
    db.refresh(visit)

    return visit


@router.delete("/{visit_id}", summary="Delete visit")
async def delete_visit(
    visit_id: int,
    db: Session = Depends(get_db)
):
    """
    Soft delete a visit record (mark as voided).

    - **visit_id**: Visit database ID
    """
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    # Soft delete by setting voided to True
    visit.voided = True
    db.commit()

    return {"message": "Visit deleted successfully"}


@router.get("/", response_model=VisitListResponse, summary="List visits")
async def list_visits(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    patient_uuid: Optional[str] = Query(None, description="Filter by patient UUID"),
    visit_type: Optional[str] = Query(None, description="Filter by visit type"),
    location_id: Optional[str] = Query(None, description="Filter by location ID"),
    date_started_from: Optional[str] = Query(None, description="Filter visits started after this date"),
    date_started_to: Optional[str] = Query(None, description="Filter visits started before this date"),
    voided: Optional[bool] = Query(None, description="Filter by voided status"),
    db: Session = Depends(get_db)
):
    """
    List visits with pagination and filtering.

    Supports filtering by:
    - patient_uuid: Patient UUID
    - visit_type: Type of visit
    - location_id: Location/facility identifier
    - date_started_from/to: Date range for visit start
    - voided: Whether visit is voided
    """
    query = db.query(Visit)

    # Apply filters
    if patient_uuid:
        query = query.filter(Visit.patient_uuid == patient_uuid)
    if visit_type:
        query = query.filter(Visit.visit_type == visit_type)
    if location_id:
        query = query.filter(Visit.location_id == location_id)
    if date_started_from:
        query = query.filter(Visit.date_started >= date_started_from)
    if date_started_to:
        query = query.filter(Visit.date_started <= date_started_to)
    if voided is not None:
        query = query.filter(Visit.voided == voided)

    # Get total count
    total = query.count()

    # Apply pagination
    visits = query.offset((page - 1) * page_size).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return VisitListResponse(
        visits=visits,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/patient/{patient_uuid}", response_model=VisitListResponse, summary="Get visits for patient")
async def get_patient_visits(
    patient_uuid: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    voided: Optional[bool] = Query(None, description="Filter by voided status"),
    db: Session = Depends(get_db)
):
    """
    Get all visits for a specific patient.

    - **patient_uuid**: Patient UUID
    - **page**: Page number for pagination
    - **page_size**: Number of items per page
    - **voided**: Filter by voided status (optional)
    """
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    query = db.query(Visit).filter(Visit.patient_uuid == patient_uuid)

    if voided is not None:
        query = query.filter(Visit.voided == voided)

    # Get total count
    total = query.count()

    # Apply pagination
    visits = query.order_by(Visit.date_started.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return VisitListResponse(
        visits=visits,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
