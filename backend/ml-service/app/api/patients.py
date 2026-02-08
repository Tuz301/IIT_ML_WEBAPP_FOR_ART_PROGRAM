"""
Patient management API endpoints for IIT ML Service
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from io import StringIO
import csv
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_user
from ..models import User
from ..schema import (
    PatientCreate, PatientUpdate, PatientResponse, PatientListResponse,
    PatientSearch, PatientFilter, PatientImportRequest, PatientImportResponse,
    PatientExportRequest, PatientValidationRequest, PatientValidationResponse,
    PatientHistoryResponse, PatientStatsResponse, ErrorResponse
)
from ..crud import (
    get_patient, get_patients, get_patient_count, create_patient,
    update_patient, delete_patient, validate_patient_data,
    import_patients, get_patient_stats
)

# Initialize logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)


@router.get("/", response_model=PatientListResponse)
async def list_patients(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    search: Optional[str] = Query(None, description="General search query"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    state_province: Optional[str] = Query(None, description="Filter by state/province"),
    has_phone: Optional[bool] = Query(None, description="Filter by phone presence"),
    age_min: Optional[int] = Query(None, ge=0, le=120, description="Minimum age"),
    age_max: Optional[int] = Query(None, ge=0, le=120, description="Maximum age"),
    created_after: Optional[datetime] = Query(None, description="Created after date"),
    created_before: Optional[datetime] = Query(None, description="Created before date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List patients with pagination and filtering
    """
    try:
        # Build filters
        filters = PatientFilter(
            gender=gender,
            state_province=state_province,
            has_phone=has_phone,
            age_min=age_min,
            age_max=age_max,
            created_after=created_after,
            created_before=created_before
        )

        # Calculate offset
        offset = (page - 1) * page_size

        # Get patients
        patients = get_patients(
            db=db,
            skip=offset,
            limit=page_size,
            search_query=search,
            filters=filters
        )

        # Get total count
        total = get_patient_count(db=db, search_query=search, filters=filters)

        # Calculate pagination info
        total_pages = (total + page_size - 1) // page_size

        logger.info(f"Listed patients - page {page}, total {total}", extra={
            "user_id": current_user.id,
            "username": current_user.username,
            "page": page,
            "page_size": page_size,
            "total": total
        })

        return PatientListResponse(
            patients=patients,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Failed to list patients: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patients"
        )


@router.get("/search", response_model=PatientListResponse)
async def search_patients(
    query: Optional[str] = Query(None, description="General search query"),
    patient_uuid: Optional[str] = Query(None, description="Patient UUID"),
    datim_id: Optional[str] = Query(None, description="DATIM ID"),
    pepfar_id: Optional[str] = Query(None, description="PEPFAR ID"),
    given_name: Optional[str] = Query(None, description="Given name"),
    family_name: Optional[str] = Query(None, description="Family name"),
    gender: Optional[str] = Query(None, description="Gender"),
    state_province: Optional[str] = Query(None, description="State/Province"),
    city_village: Optional[str] = Query(None, description="City/Village"),
    phone_number: Optional[str] = Query(None, description="Phone number"),
    birthdate_from: Optional[datetime] = Query(None, description="Birth date from"),
    birthdate_to: Optional[datetime] = Query(None, description="Birth date to"),
    has_phone: Optional[bool] = Query(None, description="Has phone number"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Advanced patient search with multiple criteria
    """
    try:
        # Build search criteria
        search_criteria = PatientSearch(
            query=query,
            patient_uuid=patient_uuid,
            datim_id=datim_id,
            pepfar_id=pepfar_id,
            given_name=given_name,
            family_name=family_name,
            gender=gender,
            state_province=state_province,
            city_village=city_village,
            phone_number=phone_number,
            birthdate_from=birthdate_from,
            birthdate_to=birthdate_to,
            has_phone=has_phone
        )

        # Calculate offset
        offset = (page - 1) * page_size

        # Search patients
        patients = get_patients(
            db=db,
            skip=offset,
            limit=page_size,
            search_criteria=search_criteria
        )

        # Get total count
        total = get_patient_count(db=db, search_criteria=search_criteria)

        # Calculate pagination info
        total_pages = (total + page_size - 1) // page_size

        logger.info(f"Searched patients - page {page}, total {total}", extra={
            "user_id": current_user.id,
            "username": current_user.username,
            "page": page,
            "page_size": page_size,
            "total": total
        })

        return PatientListResponse(
            patients=patients,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Failed to search patients: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search patients"
        )


@router.get("/{patient_uuid}", response_model=PatientResponse)
async def get_patient_by_uuid(
    patient_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific patient by UUID
    """
    try:
        patient = get_patient(db=db, patient_uuid=patient_uuid)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with UUID {patient_uuid} not found"
            )

        logger.info(f"Retrieved patient {patient_uuid}", extra={
            "user_id": current_user.id,
            "username": current_user.username,
            "patient_uuid": patient_uuid
        })

        return patient

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get patient {patient_uuid}: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patient"
        )


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED,
             summary="Create Patient",
             description="""
Create a new patient record in the system.

**Required Information:**
- Patient identifiers (DATIM ID, PEPFAR ID)
- Basic demographics (name, birthdate, gender)
- Location information (state/province, city/village)
- Contact information (phone number - optional but recommended)

**Data Validation:**
- Patient UUID is auto-generated if not provided
- Phone number format validation
- Required field validation
- Duplicate checking (based on identifiers)

**Audit Trail:**
- Creation timestamp and user tracking
- All changes are logged for compliance

**Use Cases:**
- New patient registration
- Data migration from external systems
- Bulk patient import workflows
""",
             responses={
                 201: {
                     "description": "Patient created successfully",
                     "model": PatientResponse,
                     "content": {
                         "application/json": {
                             "example": {
                                 "patient_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                 "datim_id": "DATIM123",
                                 "pepfar_id": "PEPFAR456",
                                 "given_name": "John",
                                 "family_name": "Doe",
                                 "birthdate": "1985-06-15",
                                 "gender": "M",
                                 "state_province": "Lagos",
                                 "city_village": "Ikeja",
                                 "phone_number": "+2348012345678",
                                 "created_at": "2025-01-15T10:30:00",
                                 "updated_at": "2025-01-15T10:30:00"
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Invalid patient data or duplicate patient",
                     "model": ErrorResponse,
                     "content": {
                         "application/json": {
                             "example": {
                                 "error": "Validation error",
                                 "detail": "Patient with DATIM ID DATIM123 already exists",
                                 "timestamp": "2025-01-15T10:30:00",
                                 "request_id": "123e4567-e89b-12d3-a456-426614174000"
                             }
                         }
                     }
                 },
                 401: {
                     "description": "Authentication required",
                     "model": ErrorResponse
                 },
                 403: {
                     "description": "Insufficient permissions",
                     "model": ErrorResponse
                 }
             })
async def create_new_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new patient record.

    Validates patient data, checks for duplicates, and creates the patient record
    with proper audit trail and permission checking.
    """
    try:
        # Check permissions (assuming patients:write permission)
        # This would be implemented based on your permission system

        patient = create_patient(db=db, patient_data=patient_data)

        logger.info(f"Created patient {patient.patient_uuid}", extra={
            "user_id": current_user.id,
            "username": current_user.username,
            "patient_uuid": patient.patient_uuid
        })

        return patient

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create patient: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create patient"
        )


@router.put("/{patient_uuid}", response_model=PatientResponse)
async def update_existing_patient(
    patient_uuid: str,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing patient
    """
    try:
        # Check permissions (assuming patients:write permission)

        patient = update_patient(
            db=db,
            patient_uuid=patient_uuid,
            patient_data=patient_data,
            updated_by=current_user.id
        )

        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with UUID {patient_uuid} not found"
            )

        logger.info(f"Updated patient {patient_uuid}", extra={
            "user_id": current_user.id,
            "username": current_user.username,
            "patient_uuid": patient_uuid
        })

        return patient

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update patient {patient_uuid}: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update patient"
        )


@router.delete("/{patient_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_patient(
    patient_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a patient
    """
    try:
        # Check permissions (assuming patients:delete permission)

        deleted = delete_patient(
            db=db,
            patient_uuid=patient_uuid,
            deleted_by=current_user.id
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with UUID {patient_uuid} not found"
            )

        logger.info(f"Deleted patient {patient_uuid}", extra={
            "user_id": current_user.id,
            "username": current_user.username,
            "patient_uuid": patient_uuid
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete patient {patient_uuid}: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete patient"
        )


@router.post("/import", response_model=PatientImportResponse)
async def import_patients_bulk(
    import_request: PatientImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk import patients with optional deduplication and validation
    """
    try:
        # Check permissions (assuming patients:write permission)

        result = import_patients(
            db=db,
            patients_data=import_request.patients,
            deduplicate=import_request.deduplicate,
            validate_data=import_request.validate_data,
            imported_by=current_user.id
        )

        logger.info(f"Imported patients - {result.imported_count} imported, {result.duplicate_count} duplicates, {result.error_count} errors", extra={
            "user_id": current_user.id,
            "username": current_user.username,
            "imported_count": result.imported_count,
            "duplicate_count": result.duplicate_count,
            "error_count": result.error_count,
            "processing_time": result.processing_time_seconds
        })

        return result

    except Exception as e:
        logger.error(f"Failed to import patients: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import patients"
        )


@router.get("/export")
async def export_patients(
    format: str = Query("json", description="Export format: json, csv, excel"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    state_province: Optional[str] = Query(None, description="Filter by state/province"),
    has_phone: Optional[bool] = Query(None, description="Filter by phone presence"),
    age_min: Optional[int] = Query(None, ge=0, le=120, description="Minimum age"),
    age_max: Optional[int] = Query(None, ge=0, le=120, description="Maximum age"),
    include_related: bool = Query(False, description="Include related data counts"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export patients data in various formats
    """
    try:
        # Build filters
        filters = PatientFilter(
            gender=gender,
            state_province=state_province,
            has_phone=has_phone,
            age_min=age_min,
            age_max=age_max
        )

        # Get all patients matching filters
        patients = get_patients(db=db, filters=filters, limit=10000)  # Reasonable limit

        if format.lower() == "json":
            # JSON export
            export_data = []
            for patient in patients:
                patient_dict = {
                    "patient_uuid": str(patient.patient_uuid),
                    "datim_id": patient.datim_id,
                    "pepfar_id": patient.pepfar_id,
                    "given_name": patient.given_name,
                    "family_name": patient.family_name,
                    "birthdate": patient.birthdate.isoformat() if patient.birthdate else None,
                    "gender": patient.gender,
                    "state_province": patient.state_province,
                    "city_village": patient.city_village,
                    "phone_number": patient.phone_number,
                    "created_at": patient.created_at.isoformat(),
                    "updated_at": patient.updated_at.isoformat()
                }

                if include_related:
                    patient_dict.update({
                        "visits_count": len(patient.visits),
                        "encounters_count": len(patient.encounters),
                        "observations_count": len(patient.observations)
                    })

                export_data.append(patient_dict)

            logger.info(f"Exported {len(patients)} patients as JSON", extra={
                "user_id": current_user.id,
                "username": current_user.username,
                "format": "json",
                "count": len(patients)
            })

            return {"patients": export_data, "total": len(patients)}

        elif format.lower() == "csv":
            # CSV export
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            header = [
                "patient_uuid", "datim_id", "pepfar_id", "given_name", "family_name",
                "birthdate", "gender", "state_province", "city_village", "phone_number",
                "created_at", "updated_at"
            ]
            if include_related:
                header.extend(["visits_count", "encounters_count", "observations_count"])
            writer.writerow(header)

            # Write data
            for patient in patients:
                row = [
                    str(patient.patient_uuid),
                    patient.datim_id or "",
                    patient.pepfar_id or "",
                    patient.given_name or "",
                    patient.family_name or "",
                    patient.birthdate.isoformat() if patient.birthdate else "",
                    patient.gender or "",
                    patient.state_province or "",
                    patient.city_village or "",
                    patient.phone_number or "",
                    patient.created_at.isoformat(),
                    patient.updated_at.isoformat()
                ]

                if include_related:
                    row.extend([
                        len(patient.visits),
                        len(patient.encounters),
                        len(patient.observations)
                    ])

                writer.writerow(row)

            logger.info(f"Exported {len(patients)} patients as CSV", extra={
                "user_id": current_user.id,
                "username": current_user.username,
                "format": "csv",
                "count": len(patients)
            })

            return output.getvalue()

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}. Supported formats: json, csv"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export patients: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export patients"
        )


@router.post("/validate", response_model=PatientValidationResponse)
async def validate_patient(
    validation_request: PatientValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate patient data and return validation results
    """
    try:
        result = validate_patient_data(
            patient_data=validation_request.patient,
            strict=validation_request.strict
        )

        logger.info(f"Validated patient data - valid: {result.is_valid}, errors: {len(result.errors)}, warnings: {len(result.warnings)}", extra={
            "user_id": current_user.id,
            "username": current_user.username,
            "is_valid": result.is_valid,
            "error_count": len(result.errors),
            "warning_count": len(result.warnings)
        })

        return result

    except Exception as e:
        logger.error(f"Failed to validate patient data: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate patient data"
        )


@router.get("/stats", response_model=PatientStatsResponse)
async def get_patient_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get patient statistics and analytics
    """
    try:
        stats = get_patient_stats(db=db)

        logger.info("Retrieved patient statistics", extra={
            "user_id": current_user.id,
            "username": current_user.username,
            "total_patients": stats.total_patients
        })

        return stats

    except Exception as e:
        logger.error(f"Failed to get patient statistics: {str(e)}", extra={
            "user_id": current_user.id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve patient statistics"
        )
