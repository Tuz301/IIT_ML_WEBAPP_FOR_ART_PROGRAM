"""
CRUD operations for IIT ML Service
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from .models import Patient, User, Visit, Encounter, Observation
from .schema import (
    PatientCreate, PatientUpdate, PatientFilter, PatientSearch,
    PatientImportRequest, PatientValidationResponse, PatientStatsResponse,
    VisitCreate, EncounterCreate, ObservationCreate
)

logger = logging.getLogger(__name__)


def get_patient(db: Session, patient_uuid: str) -> Optional[Patient]:
    """Get a patient by UUID"""
    return db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()


def get_patients(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search_query: Optional[str] = None,
    filters: Optional[PatientFilter] = None,
    search_criteria: Optional[PatientSearch] = None
) -> List[Patient]:
    """Get patients with optional filtering and search"""
    query = db.query(Patient)

    # Apply search query
    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            or_(
                Patient.given_name.ilike(search_filter),
                Patient.family_name.ilike(search_filter),
                Patient.datim_id.ilike(search_filter),
                Patient.pepfar_id.ilike(search_filter),
                Patient.phone_number.ilike(search_filter)
            )
        )

    # Apply filters
    if filters:
        if filters.gender:
            query = query.filter(Patient.gender == filters.gender)
        if filters.state_province:
            query = query.filter(Patient.state_province == filters.state_province)
        if filters.has_phone is not None:
            if filters.has_phone:
                query = query.filter(Patient.phone_number.isnot(None))
            else:
                query = query.filter(Patient.phone_number.is_(None))
        if filters.age_min is not None or filters.age_max is not None:
            # Calculate age from birthdate
            current_year = datetime.now().year
            if filters.age_min is not None:
                min_birth_year = current_year - filters.age_max if filters.age_max else 0
                query = query.filter(func.extract('year', Patient.birthdate) <= min_birth_year)
            if filters.age_max is not None:
                max_birth_year = current_year - filters.age_min if filters.age_min else current_year
                query = query.filter(func.extract('year', Patient.birthdate) >= max_birth_year)
        if filters.created_after:
            query = query.filter(Patient.created_at >= filters.created_after)
        if filters.created_before:
            query = query.filter(Patient.created_at <= filters.created_before)

    # Apply search criteria
    if search_criteria:
        if search_criteria.patient_uuid:
            query = query.filter(Patient.patient_uuid == search_criteria.patient_uuid)
        if search_criteria.datim_id:
            query = query.filter(Patient.datim_id == search_criteria.datim_id)
        if search_criteria.pepfar_id:
            query = query.filter(Patient.pepfar_id == search_criteria.pepfar_id)
        if search_criteria.given_name:
            query = query.filter(Patient.given_name.ilike(f"%{search_criteria.given_name}%"))
        if search_criteria.family_name:
            query = query.filter(Patient.family_name.ilike(f"%{search_criteria.family_name}%"))
        if search_criteria.gender:
            query = query.filter(Patient.gender == search_criteria.gender)
        if search_criteria.state_province:
            query = query.filter(Patient.state_province == search_criteria.state_province)
        if search_criteria.city_village:
            query = query.filter(Patient.city_village == search_criteria.city_village)
        if search_criteria.phone_number:
            query = query.filter(Patient.phone_number.ilike(f"%{search_criteria.phone_number}%"))
        if search_criteria.birthdate_from:
            query = query.filter(Patient.birthdate >= search_criteria.birthdate_from)
        if search_criteria.birthdate_to:
            query = query.filter(Patient.birthdate <= search_criteria.birthdate_to)
        if search_criteria.has_phone is not None:
            if search_criteria.has_phone:
                query = query.filter(Patient.phone_number.isnot(None))
            else:
                query = query.filter(Patient.phone_number.is_(None))

    return query.offset(skip).limit(limit).all()


def get_patient_count(
    db: Session,
    search_query: Optional[str] = None,
    filters: Optional[PatientFilter] = None,
    search_criteria: Optional[PatientSearch] = None
) -> int:
    """Get total count of patients with optional filtering"""
    query = db.query(func.count(Patient.patient_uuid))

    # Apply same filters as get_patients
    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            or_(
                Patient.given_name.ilike(search_filter),
                Patient.family_name.ilike(search_filter),
                Patient.datim_id.ilike(search_filter),
                Patient.pepfar_id.ilike(search_filter),
                Patient.phone_number.ilike(search_filter)
            )
        )

    if filters:
        if filters.gender:
            query = query.filter(Patient.gender == filters.gender)
        if filters.state_province:
            query = query.filter(Patient.state_province == filters.state_province)
        if filters.has_phone is not None:
            if filters.has_phone:
                query = query.filter(Patient.phone_number.isnot(None))
            else:
                query = query.filter(Patient.phone_number.is_(None))
        if filters.created_after:
            query = query.filter(Patient.created_at >= filters.created_after)
        if filters.created_before:
            query = query.filter(Patient.created_at <= filters.created_before)

    if search_criteria:
        if search_criteria.patient_uuid:
            query = query.filter(Patient.patient_uuid == search_criteria.patient_uuid)
        if search_criteria.datim_id:
            query = query.filter(Patient.datim_id == search_criteria.datim_id)
        if search_criteria.pepfar_id:
            query = query.filter(Patient.pepfar_id == search_criteria.pepfar_id)
        if search_criteria.given_name:
            query = query.filter(Patient.given_name.ilike(f"%{search_criteria.given_name}%"))
        if search_criteria.family_name:
            query = query.filter(Patient.family_name.ilike(f"%{search_criteria.family_name}%"))
        if search_criteria.gender:
            query = query.filter(Patient.gender == search_criteria.gender)
        if search_criteria.state_province:
            query = query.filter(Patient.state_province == search_criteria.state_province)
        if search_criteria.city_village:
            query = query.filter(Patient.city_village == search_criteria.city_village)
        if search_criteria.phone_number:
            query = query.filter(Patient.phone_number.ilike(f"%{search_criteria.phone_number}%"))
        if search_criteria.birthdate_from:
            query = query.filter(Patient.birthdate >= search_criteria.birthdate_from)
        if search_criteria.birthdate_to:
            query = query.filter(Patient.birthdate <= search_criteria.birthdate_to)
        if search_criteria.has_phone is not None:
            if search_criteria.has_phone:
                query = query.filter(Patient.phone_number.isnot(None))
            else:
                query = query.filter(Patient.phone_number.is_(None))

    return query.scalar()


def create_patient(db: Session, patient_data: PatientCreate) -> Patient:
    """Create a new patient"""
    # Check for duplicates
    if patient_data.datim_id:
        existing = db.query(Patient).filter(Patient.datim_id == patient_data.datim_id).first()
        if existing:
            raise ValueError(f"Patient with DATIM ID {patient_data.datim_id} already exists")

    if patient_data.pepfar_id:
        existing = db.query(Patient).filter(Patient.pepfar_id == patient_data.pepfar_id).first()
        if existing:
            raise ValueError(f"Patient with PEPFAR ID {patient_data.pepfar_id} already exists")

    patient = Patient(**patient_data.dict())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update_patient(
    db: Session,
    patient_uuid: str,
    patient_data: PatientUpdate,
    updated_by: Optional[int] = None
) -> Optional[Patient]:
    """Update an existing patient"""
    patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
    if not patient:
        return None

    update_data = patient_data.dict(exclude_unset=True)
    if updated_by:
        update_data['updated_by'] = updated_by

    for field, value in update_data.items():
        setattr(patient, field, value)

    patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(patient)
    return patient


def delete_patient(db: Session, patient_uuid: str, deleted_by: Optional[int] = None) -> bool:
    """Delete a patient"""
    patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
    if not patient:
        return False

    db.delete(patient)
    db.commit()
    return True


def validate_patient_data(patient_data: Dict[str, Any], strict: bool = True) -> PatientValidationResponse:
    """Validate patient data"""
    errors = []
    warnings = []

    # Required fields validation
    required_fields = ['given_name', 'family_name', 'birthdate', 'gender']
    for field in required_fields:
        if not patient_data.get(field):
            errors.append(f"Missing required field: {field}")

    # Gender validation
    if patient_data.get('gender'):
        if patient_data['gender'] not in ['M', 'F', 'O']:
            errors.append("Gender must be 'M', 'F', or 'O'")

    # Phone number validation
    if patient_data.get('phone_number'):
        if not patient_data['phone_number'].startswith('+'):
            warnings.append("Phone number should start with country code (e.g., +234)")

    # Age validation
    if patient_data.get('birthdate'):
        try:
            birthdate = datetime.fromisoformat(patient_data['birthdate'])
            age = (datetime.now() - birthdate).days / 365.25
            if age < 0:
                errors.append("Birthdate cannot be in the future")
            elif age > 120:
                warnings.append("Patient age seems unusually high (>120 years)")
        except ValueError:
            errors.append("Invalid birthdate format")

    return PatientValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def import_patients(
    db: Session,
    patients_data: List[Dict[str, Any]],
    deduplicate: bool = True,
    validate_data: bool = True,
    imported_by: Optional[int] = None
) -> Dict[str, Any]:
    """Import patients in bulk"""
    imported_count = 0
    duplicate_count = 0
    error_count = 0
    errors = []

    for i, patient_dict in enumerate(patients_data):
        try:
            # Validate data if requested
            if validate_data:
                validation = validate_patient_data(patient_dict, strict=False)
                if not validation.is_valid:
                    error_count += 1
                    errors.append(f"Row {i+1}: {', '.join(validation.errors)}")
                    continue

            # Check for duplicates if requested
            if deduplicate:
                if patient_dict.get('datim_id'):
                    existing = db.query(Patient).filter(Patient.datim_id == patient_dict['datim_id']).first()
                    if existing:
                        duplicate_count += 1
                        continue
                if patient_dict.get('pepfar_id'):
                    existing = db.query(Patient).filter(Patient.pepfar_id == patient_dict['pepfar_id']).first()
                    if existing:
                        duplicate_count += 1
                        continue

            # Create patient
            patient_data = PatientCreate(**patient_dict)
            create_patient(db, patient_data)
            imported_count += 1

        except Exception as e:
            error_count += 1
            errors.append(f"Row {i+1}: {str(e)}")

    return {
        'imported_count': imported_count,
        'duplicate_count': duplicate_count,
        'error_count': error_count,
        'errors': errors,
        'processing_time_seconds': 0.0  # Would need to track actual time
    }


def get_patient_stats(db: Session) -> PatientStatsResponse:
    """Get patient statistics"""
    total_patients = db.query(func.count(Patient.patient_uuid)).scalar()

    # Gender distribution
    gender_stats = db.query(
        Patient.gender,
        func.count(Patient.patient_uuid).label('count')
    ).group_by(Patient.gender).all()

    gender_distribution = {gender: count for gender, count in gender_stats}

    # State/province distribution
    state_stats = db.query(
        Patient.state_province,
        func.count(Patient.patient_uuid).label('count')
    ).filter(Patient.state_province.isnot(None)).group_by(Patient.state_province).all()

    state_distribution = {state: count for state, count in state_stats}

    # Age distribution
    current_year = datetime.now().year
    age_stats = db.query(
        func.extract('year', Patient.birthdate).label('birth_year')
    ).filter(Patient.birthdate.isnot(None)).all()

    age_groups = {'0-17': 0, '18-34': 0, '35-54': 0, '55-74': 0, '75+': 0}
    for row in age_stats:
        if row.birth_year:
            age = current_year - int(row.birth_year)
            if age <= 17:
                age_groups['0-17'] += 1
            elif age <= 34:
                age_groups['18-34'] += 1
            elif age <= 54:
                age_groups['35-54'] += 1
            elif age <= 74:
                age_groups['55-74'] += 1
            else:
                age_groups['75+'] += 1

    # Phone number stats
    with_phone = db.query(func.count(Patient.patient_uuid)).filter(Patient.phone_number.isnot(None)).scalar()
    without_phone = total_patients - with_phone

    return PatientStatsResponse(
        total_patients=total_patients,
        gender_distribution=gender_distribution,
        state_distribution=state_distribution,
        age_distribution=age_groups,
        phone_stats={
            'with_phone': with_phone,
            'without_phone': without_phone,
            'phone_percentage': (with_phone / total_patients * 100) if total_patients > 0 else 0
        }
    )


def create_visit(db: Session, visit_data: VisitCreate) -> Visit:
    """Create a new visit"""
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.patient_uuid == visit_data.patient_uuid).first()
    if not patient:
        raise ValueError(f"Patient with UUID {visit_data.patient_uuid} not found")

    # Generate UUID if not provided
    import uuid
    visit_uuid = visit_data.visit_uuid or str(uuid.uuid4())

    # Create visit record
    visit = Visit(
        visit_uuid=visit_uuid,
        patient_uuid=visit_data.patient_uuid,
        visit_type=visit_data.visit_type,
        date_started=visit_data.date_started,
        date_stopped=visit_data.date_stopped,
        location_id=visit_data.location_id
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


def create_encounter(db: Session, encounter_data: EncounterCreate) -> Encounter:
    """Create a new encounter"""
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.patient_uuid == encounter_data.patient_uuid).first()
    if not patient:
        raise ValueError(f"Patient with UUID {encounter_data.patient_uuid} not found")

    # Generate UUID if not provided
    import uuid
    encounter_uuid = encounter_data.encounter_uuid or str(uuid.uuid4())

    # Create encounter record
    encounter = Encounter(
        encounter_uuid=encounter_uuid,
        patient_uuid=encounter_data.patient_uuid,
        encounter_datetime=encounter_data.encounter_datetime,
        encounter_type=encounter_data.encounter_type,
        pmm_form=encounter_data.pmm_form
    )

    db.add(encounter)
    db.commit()
    db.refresh(encounter)
    return encounter


def create_observation(db: Session, observation_data: ObservationCreate) -> Observation:
    """Create a new observation"""
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.patient_uuid == observation_data.patient_uuid).first()
    if not patient:
        raise ValueError(f"Patient with UUID {observation_data.patient_uuid} not found")

    # Create observation record
    observation = Observation(
        patient_uuid=observation_data.patient_uuid,
        encounter_id=observation_data.encounter_id,
        variable_name=observation_data.variable_name,
        value_numeric=observation_data.value_numeric,
        value_text=observation_data.value_text,
        obs_datetime=observation_data.obs_datetime
    )

    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


def log_audit(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """Log audit events for security monitoring"""
    # This would typically insert into an audit log table
    # For now, we'll just log to the application logger
    audit_data = {
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'user_id': user_id,
        'details': details or {},
        'ip_address': ip_address,
        'user_agent': user_agent,
        'timestamp': datetime.utcnow().isoformat()
    }

    logger.info(f"AUDIT: {audit_data}")
