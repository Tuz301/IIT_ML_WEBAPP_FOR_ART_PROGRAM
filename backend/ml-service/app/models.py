"""
SQLAlchemy models for IIT ML Service database and Pydantic models for API validation
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, BigInteger, SmallInteger, ForeignKey, Index, Computed, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import JSON as SQLAlchemyJSON
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func, expression
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

# Import Base from core.db to ensure all models use the same Base
from .core.db import Base

# Custom JSON type that works with both SQLite and PostgreSQL
class UniversalJSON(TypeDecorator):
    """JSON type that uses JSONB for PostgreSQL and JSON for SQLite"""
    impl = JSON
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())

# SQLAlchemy Models
class Patient(Base):
    """Patient demographics table"""
    __tablename__ = "patients"

    patient_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    datim_id = Column(String)
    pepfar_id = Column(String)
    given_name = Column(String)
    family_name = Column(String)
    birthdate = Column(DateTime)
    gender = Column(String)
    state_province = Column(String)
    city_village = Column(String)
    phone_number = Column(String)
    phone_present = Column(Boolean, Computed("(phone_number IS NOT NULL)", persisted=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    visits = relationship("Visit", back_populates="patient", cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="patient", cascade="all, delete-orphan")
    iit_features = relationship("IITFeatures", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    iit_predictions = relationship("IITPrediction", back_populates="patient", cascade="all, delete-orphan")
    raw_json_files = relationship("RawJSONFile", back_populates="patient", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_patients_pepfar', 'pepfar_id'),
        Index('idx_patients_datim', 'datim_id'),
    )

    @validates('gender')
    def validate_gender(self, key, value):
        if value and value.upper() not in ['M', 'F', 'MALE', 'FEMALE']:
            raise ValueError("Gender must be M, F, MALE, or FEMALE")
        return value.upper() if value else value

    @validates('phone_number')
    def validate_phone_number(self, key, value):
        if value and not value.startswith('+'):
            raise ValueError("Phone number must start with +")
        return value

class Visit(Base):
    """Patient visits table"""
    __tablename__ = "visits"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    visit_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    visit_type = Column(String)
    date_started = Column(DateTime)
    date_stopped = Column(DateTime)
    location_id = Column(String)
    voided = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="visits")
    encounters = relationship("Encounter", back_populates="visit", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_visits_patient_date', 'patient_uuid', 'date_started'),
    )

    @validates('date_stopped')
    def validate_dates(self, key, value):
        if value and self.date_started and value < self.date_started:
            raise ValueError("Date stopped cannot be before date started")
        return value

class Encounter(Base):
    """Patient encounters table"""
    __tablename__ = "encounters"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    encounter_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    visit_id = Column(BigInteger, ForeignKey('visits.id'), nullable=True)
    encounter_datetime = Column(DateTime)
    encounter_type = Column(String)
    pmm_form = Column(String)
    form_id = Column(String)
    voided = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="encounters")
    visit = relationship("Visit", back_populates="encounters")
    observations = relationship("Observation", back_populates="encounter", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_encounter_uuid', 'encounter_uuid'),
        Index('idx_encounters_patient_date', 'patient_uuid', 'encounter_datetime'),
    )

class Observation(Base):
    """Clinical observations table"""
    __tablename__ = "observations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    obs_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    encounter_id = Column(BigInteger, ForeignKey('encounters.id'), nullable=False)
    concept_id = Column(String)
    variable_name = Column(String)
    value_numeric = Column(Float)
    value_text = Column(Text)
    value_coded = Column(String)
    obs_datetime = Column(DateTime)
    raw = Column(UniversalJSON)  # Store full original obs JSON
    voided = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="observations")
    encounter = relationship("Encounter", back_populates="observations")

    # Indexes
    __table_args__ = (
        Index('idx_obs_patient_time', 'patient_uuid', 'obs_datetime'),
        Index('idx_obs_varname', 'variable_name'),
        Index('idx_obs_concept', 'concept_id'),
    )

    @validates('value_numeric')
    def validate_numeric_value(self, key, value):
        if value is not None and (value < -1000000 or value > 1000000):
            raise ValueError("Numeric value out of reasonable range")
        return value

class RawJSONFile(Base):
    """Raw JSON file storage for audit and reprocessing"""
    __tablename__ = "raw_json_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    facility_datim_code = Column(String)
    filename = Column(String)
    raw_json = Column(UniversalJSON, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="raw_json_files")

    # Indexes
    __table_args__ = (
        Index('idx_rawjson_patient', 'patient_uuid'),
    )

class IITFeatures(Base):
    """Engineered features for IIT prediction (one row per patient)"""
    __tablename__ = "iit_features"

    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), primary_key=True)

    # Demographics
    age = Column(Float)
    age_group = Column(Integer)
    gender = Column(Integer)  # Encoded: 0=M, 1=F
    has_state = Column(Boolean)
    has_city = Column(Boolean)
    has_phone = Column(Boolean)

    # Pharmacy
    has_pharmacy_history = Column(Boolean)
    total_dispensations = Column(Integer)
    avg_days_supply = Column(Float)
    last_days_supply = Column(Integer)
    days_since_last_refill = Column(Integer)
    refill_frequency_3m = Column(Integer)
    refill_frequency_6m = Column(Integer)
    mmd_ratio = Column(Float)
    regimen_stability = Column(Float)
    last_regimen_complexity = Column(Integer)
    adherence_counseling_count = Column(Integer)

    # Visits
    total_visits = Column(Integer)
    visit_frequency_3m = Column(Integer)
    visit_frequency_6m = Column(Integer)
    visit_frequency_12m = Column(Integer)
    days_since_last_visit = Column(Integer)
    visit_regularity = Column(Float)
    clinical_visit_ratio = Column(Float)

    # Clinical
    who_stage = Column(Integer)
    has_vl_data = Column(Boolean)
    recent_vl_tests = Column(Integer)
    has_tb_symptoms = Column(Boolean)
    functional_status = Column(Integer)
    pregnancy_status = Column(Boolean)
    adherence_level = Column(Integer)

    # Temporal
    month = Column(SmallInteger)
    quarter = Column(SmallInteger)
    is_holiday_season = Column(Boolean)
    is_rainy_season = Column(Boolean)
    day_of_week = Column(SmallInteger)
    is_year_end = Column(Boolean)

    # Metadata
    last_feature_update = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="iit_features")

    # Indexes
    __table_args__ = (
        Index('idx_iit_features_last_update', 'last_feature_update'),
    )

    @validates('age')
    def validate_age(self, key, value):
        if value is not None and (value < 0 or value > 120):
            raise ValueError("Age must be between 0 and 120")
        return value
    
    def get_age(self) -> int:
        """Calculate patient age from birthdate"""
        if self.birthdate:
            from datetime import datetime
            today = datetime.utcnow().date()
            age = today.year - self.birthdate.year
            # Adjust if birthday hasn't occurred yet this year
            if (self.birthdate.month, self.birthdate.day) > (today.month, today.day):
                age -= 1
            return age
        return 0

    @validates('month')
    def validate_month(self, key, value):
        if value is not None and (value < 1 or value > 12):
            raise ValueError("Month must be between 1 and 12")
        return value

    @validates('day_of_week')
    def validate_day_of_week(self, key, value):
        if value is not None and (value < 0 or value > 6):
            raise ValueError("Day of week must be between 0 and 6")
        return value

class IITPrediction(Base):
    """IIT prediction audit table"""
    __tablename__ = "iit_predictions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    model_version = Column(String, nullable=False)
    prediction_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    confidence = Column(Float)
    prediction_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    features = Column(UniversalJSON)  # Snapshot of features used
    request_meta = Column(UniversalJSON)  # Request metadata

    # Relationships
    patient = relationship("Patient", back_populates="iit_predictions")

    # Indexes
    __table_args__ = (
        Index('idx_preds_patient_time', 'patient_uuid', 'prediction_timestamp'),
    )

    @validates('prediction_score')
    def validate_prediction_score(self, key, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise ValueError("Prediction score must be between 0.0 and 1.0")
        return value

    @validates('confidence')
    def validate_confidence(self, key, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return value

    @validates('risk_level')
    def validate_risk_level(self, key, value):
        if value and value.lower() not in ['low', 'medium', 'high', 'critical']:
            raise ValueError("Risk level must be low, medium, high, or critical")
        return value.lower() if value else value


# Alias for backward compatibility with explainability module
Prediction = IITPrediction


class FeatureImportance(Base):
    """Feature importance tracking table"""
    __tablename__ = "feature_importance"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_version = Column(String, nullable=False)
    feature_name = Column(String, nullable=False)
    importance_score = Column(Float, nullable=False)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_feature_imp_model_version', 'model_version'),
        Index('idx_feature_imp_calculated_at', 'calculated_at'),
    )

    @validates('importance_score')
    def validate_importance_score(self, key, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise ValueError("Importance score must be between 0.0 and 1.0")
        return value


class PredictionExplanation(Base):
    """Prediction explanation storage table"""
    __tablename__ = "prediction_explanations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    prediction_id = Column(String, nullable=False, unique=True)  # Reference to prediction
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    model_version = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    feature_contributions = Column(UniversalJSON)  # JSON array of feature contributions
    top_positive_factors = Column(UniversalJSON)  # JSON array of top positive factors
    top_negative_factors = Column(UniversalJSON)  # JSON array of top negative factors
    explanation_summary = Column(Text)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", backref="prediction_explanations")

    # Indexes
    __table_args__ = (
        Index('idx_pred_exp_prediction_id', 'prediction_id'),
        Index('idx_pred_exp_patient', 'patient_uuid'),
        Index('idx_pred_exp_model_version', 'model_version'),
        Index('idx_pred_exp_created_at', 'created_at'),
    )

    @validates('risk_score')
    def validate_risk_score(self, key, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise ValueError("Risk score must be between 0.0 and 1.0")
        return value

    @validates('confidence_score')
    def validate_confidence_score(self, key, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return value

    @validates('risk_level')
    def validate_risk_level(self, key, value):
        if value and value.lower() not in ['low', 'medium', 'high', 'critical']:
            raise ValueError("Risk level must be low, medium, high, or critical")
        return value.lower() if value else value


# Ensemble Methods Models
class EnsembleConfiguration(Base):
    """Ensemble configuration table"""
    __tablename__ = "ensemble_configurations"

    ensemble_id = Column(String, primary_key=True)
    ensemble_type = Column(String, nullable=False)
    model_ids = Column(UniversalJSON, nullable=False)
    weights = Column(UniversalJSON)
    voting_strategy = Column(String, nullable=False)
    meta_model_id = Column(String)
    threshold = Column(Float, default=0.5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_ensemble_config_created_at', 'created_at'),
    )


class EnsemblePrediction(Base):
    """Ensemble prediction audit table"""
    __tablename__ = "ensemble_predictions"

    prediction_id = Column(String, primary_key=True)
    ensemble_id = Column(String, ForeignKey('ensemble_configurations.ensemble_id'), nullable=False)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    ensemble_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    individual_predictions = Column(UniversalJSON, nullable=False)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", backref="ensemble_predictions")

    # Indexes
    __table_args__ = (
        Index('idx_ensemble_preds_patient', 'patient_uuid'),
        Index('idx_ensemble_preds_ensemble', 'ensemble_id'),
        Index('idx_ensemble_preds_created_at', 'created_at'),
    )

    @validates('ensemble_score')
    def validate_ensemble_score(self, key, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise ValueError("Ensemble score must be between 0.0 and 1.0")
        return value

    @validates('confidence_score')
    def validate_confidence_score(self, key, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return value

    @validates('risk_level')
    def validate_risk_level(self, key, value):
        if value and value.lower() not in ['low', 'medium', 'high', 'critical']:
            raise ValueError("Risk level must be low, medium, high, or critical")
        return value.lower() if value else value


# Authentication & Authorization Models
class User(Base):
    """User authentication table"""
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    roles = relationship("Role", secondary="user_roles", back_populates="users")

    # Indexes
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
    )

    @validates('email')
    def validate_email(self, key, value):
        if value and '@' not in value:
            raise ValueError("Invalid email format")
        return value.lower() if value else value

    @validates('username')
    def validate_username(self, key, value):
        if value and len(value) < 3:
            raise ValueError("Username must be at least 3 characters long")
        return value


class Role(Base):
    """User roles table"""
    __tablename__ = "roles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")

    # Indexes
    __table_args__ = (
        Index('idx_roles_name', 'name'),
    )


class Permission(Base):
    """Permissions table"""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)  # Changed from BigInteger to Integer for SQLite compatibility
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String)
    resource = Column(String, nullable=False)  # e.g., "patients", "predictions"
    action = Column(String, nullable=False)    # e.g., "read", "write", "delete"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")

    # Indexes
    __table_args__ = (
        Index('idx_permissions_name', 'name'),
        Index('idx_permissions_resource_action', 'resource', 'action'),
    )


# Association tables for many-to-many relationships
class UserRole(Base):
    """User-Role association table"""
    __tablename__ = "user_roles"

    user_id = Column(BigInteger, ForeignKey('users.id'), primary_key=True)
    role_id = Column(BigInteger, ForeignKey('roles.id'), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())


class RolePermission(Base):
    """Role-Permission association table"""
    __tablename__ = "role_permissions"

    role_id = Column(BigInteger, ForeignKey('roles.id'), primary_key=True)
    permission_id = Column(BigInteger, ForeignKey('permissions.id'), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())


# Intervention Workflow System Models
class Intervention(Base):
    """Patient intervention tracking table"""
    __tablename__ = "interventions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    intervention_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    assigned_to = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    intervention_type = Column(String, nullable=False)  # 'follow_up', 'counseling', 'referral', 'adherence_support'
    priority = Column(String, nullable=False, default='medium')  # 'low', 'medium', 'high', 'urgent'
    status = Column(String, nullable=False, default='pending')  # 'pending', 'in_progress', 'completed', 'cancelled'
    title = Column(String, nullable=False)
    description = Column(Text)
    due_date = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    outcome = Column(Text)
    notes = Column(Text)
    extra_metadata = Column(UniversalJSON)  # Additional intervention data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    patient = relationship("Patient", backref="interventions")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_interventions")
    creator = relationship("User", foreign_keys=[created_by], backref="created_interventions")
    alerts = relationship("Alert", back_populates="intervention", cascade="all, delete-orphan")
    communications = relationship("Communication", back_populates="intervention", cascade="all, delete-orphan")
    follow_ups = relationship("FollowUp", back_populates="intervention", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_interventions_patient', 'patient_uuid'),
        Index('idx_interventions_assigned_to', 'assigned_to'),
        Index('idx_interventions_status', 'status'),
        Index('idx_interventions_due_date', 'due_date'),
        Index('idx_interventions_type', 'intervention_type'),
    )

    @validates('priority')
    def validate_priority(self, key, value):
        if value and value.lower() not in ['low', 'medium', 'high', 'urgent']:
            raise ValueError("Priority must be low, medium, high, or urgent")
        return value.lower() if value else value

    @validates('status')
    def validate_status(self, key, value):
        if value and value.lower() not in ['pending', 'in_progress', 'completed', 'cancelled']:
            raise ValueError("Status must be pending, in_progress, completed, or cancelled")
        return value.lower() if value else value

    @validates('intervention_type')
    def validate_intervention_type(self, key, value):
        valid_types = ['follow_up', 'counseling', 'referral', 'adherence_support', 'clinical_review', 'pharmacy_support']
        if value and value.lower() not in valid_types:
            raise ValueError(f"Intervention type must be one of: {', '.join(valid_types)}")
        return value.lower() if value else value


class Alert(Base):
    """Risk-based alerts and notifications table"""
    __tablename__ = "alerts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    alert_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    intervention_id = Column(BigInteger, ForeignKey('interventions.id'), nullable=True)
    prediction_id = Column(BigInteger, ForeignKey('iit_predictions.id'), nullable=True)
    alert_type = Column(String, nullable=False)  # 'risk_threshold', 'missed_visit', 'adherence_drop', 'escalation'
    severity = Column(String, nullable=False, default='medium')  # 'low', 'medium', 'high', 'critical'
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, nullable=False, default='active')  # 'active', 'acknowledged', 'resolved', 'dismissed'
    acknowledged_by = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    escalation_level = Column(Integer, default=0)
    next_escalation_at = Column(DateTime(timezone=True))
    extra_metadata = Column(UniversalJSON)  # Alert-specific data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    patient = relationship("Patient", backref="alerts")
    intervention = relationship("Intervention", back_populates="alerts")
    prediction = relationship("IITPrediction", backref="alerts")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by], backref="acknowledged_alerts")

    # Indexes
    __table_args__ = (
        Index('idx_alerts_patient', 'patient_uuid'),
        Index('idx_alerts_status', 'status'),
        Index('idx_alerts_type', 'alert_type'),
        Index('idx_alerts_severity', 'severity'),
        Index('idx_alerts_created_at', 'created_at'),
    )

    @validates('severity')
    def validate_severity(self, key, value):
        if value and value.lower() not in ['low', 'medium', 'high', 'critical']:
            raise ValueError("Severity must be low, medium, high, or critical")
        return value.lower() if value else value

    @validates('status')
    def validate_status(self, key, value):
        if value and value.lower() not in ['active', 'acknowledged', 'resolved', 'dismissed']:
            raise ValueError("Status must be active, acknowledged, resolved, or dismissed")
        return value.lower() if value else value

    @validates('alert_type')
    def validate_alert_type(self, key, value):
        valid_types = ['risk_threshold', 'missed_visit', 'adherence_drop', 'escalation', 'follow_up_due', 'clinical_alert']
        if value and value.lower() not in valid_types:
            raise ValueError(f"Alert type must be one of: {', '.join(valid_types)}")
        return value.lower() if value else value


class Communication(Base):
    """Communication logs for messaging, SMS, and email"""
    __tablename__ = "communications"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    communication_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    intervention_id = Column(BigInteger, ForeignKey('interventions.id'), nullable=True)
    sent_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    communication_type = Column(String, nullable=False)  # 'sms', 'email', 'in_app_message', 'phone_call'
    channel = Column(String, nullable=False)  # 'patient', 'care_team', 'provider', 'system'
    subject = Column(String)
    message = Column(Text, nullable=False)
    recipient_contact = Column(String)  # Phone number or email address
    status = Column(String, nullable=False, default='sent')  # 'sent', 'delivered', 'failed', 'read'
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    failed_reason = Column(Text)
    extra_metadata = Column(UniversalJSON)  # Communication-specific data (delivery receipts, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    patient = relationship("Patient", backref="communications")
    intervention = relationship("Intervention", back_populates="communications")
    sender = relationship("User", foreign_keys=[sent_by], backref="sent_communications")

    # Indexes
    __table_args__ = (
        Index('idx_communications_patient', 'patient_uuid'),
        Index('idx_communications_type', 'communication_type'),
        Index('idx_communications_channel', 'channel'),
        Index('idx_communications_sent_at', 'sent_at'),
        Index('idx_communications_status', 'status'),
    )

    @validates('communication_type')
    def validate_communication_type(self, key, value):
        valid_types = ['sms', 'email', 'in_app_message', 'phone_call', 'notification']
        if value and value.lower() not in valid_types:
            raise ValueError(f"Communication type must be one of: {', '.join(valid_types)}")
        return value.lower() if value else value

    @validates('channel')
    def validate_channel(self, key, value):
        valid_channels = ['patient', 'care_team', 'provider', 'system', 'family']
        if value and value.lower() not in valid_channels:
            raise ValueError(f"Channel must be one of: {', '.join(valid_channels)}")
        return value.lower() if value else value

    @validates('status')
    def validate_status(self, key, value):
        if value and value.lower() not in ['sent', 'delivered', 'failed', 'read', 'pending']:
            raise ValueError("Status must be sent, delivered, failed, read, or pending")
        return value.lower() if value else value


class WorkflowTemplate(Base):
    """Intervention protocol templates and workflows"""
    __tablename__ = "workflow_templates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    category = Column(String, nullable=False)  # 'adherence', 'clinical', 'follow_up', 'escalation'
    trigger_conditions = Column(UniversalJSON)  # Conditions that trigger this workflow
    steps = Column(UniversalJSON)  # Ordered list of workflow steps
    is_active = Column(Boolean, default=True)
    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    version = Column(Integer, default=1)
    extra_metadata = Column(UniversalJSON)  # Template metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], backref="created_workflow_templates")

    # Indexes
    __table_args__ = (
        Index('idx_workflow_templates_category', 'category'),
        Index('idx_workflow_templates_active', 'is_active'),
    )

    @validates('category')
    def validate_category(self, key, value):
        valid_categories = ['adherence', 'clinical', 'follow_up', 'escalation', 'prevention', 'monitoring']
        if value and value.lower() not in valid_categories:
            raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        return value.lower() if value else value


class FollowUp(Base):
    """Scheduled follow-ups and reminders"""
    __tablename__ = "follow_ups"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    follow_up_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    patient_uuid = Column(UUID(as_uuid=True), ForeignKey('patients.patient_uuid'), nullable=False)
    intervention_id = Column(BigInteger, ForeignKey('interventions.id'), nullable=True)
    scheduled_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    follow_up_type = Column(String, nullable=False)  # 'phone_call', 'clinic_visit', 'home_visit', 'reminder'
    title = Column(String, nullable=False)
    description = Column(Text)
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    completed_by = Column(BigInteger, ForeignKey('users.id'), nullable=True)
    status = Column(String, nullable=False, default='scheduled')  # 'scheduled', 'completed', 'missed', 'cancelled'
    outcome = Column(Text)
    notes = Column(Text)
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime(timezone=True))
    extra_metadata = Column(UniversalJSON)  # Follow-up specific data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    patient = relationship("Patient", backref="follow_ups")
    intervention = relationship("Intervention", back_populates="follow_ups")
    scheduler = relationship("User", foreign_keys=[scheduled_by], backref="scheduled_follow_ups")
    completer = relationship("User", foreign_keys=[completed_by], backref="completed_follow_ups")

    # Indexes
    __table_args__ = (
        Index('idx_follow_ups_patient', 'patient_uuid'),
        Index('idx_follow_ups_scheduled_date', 'scheduled_date'),
        Index('idx_follow_ups_status', 'status'),
        Index('idx_follow_ups_type', 'follow_up_type'),
    )

    @validates('follow_up_type')
    def validate_follow_up_type(self, key, value):
        valid_types = ['phone_call', 'clinic_visit', 'home_visit', 'reminder', 'counseling_session', 'medication_review']
        if value and value.lower() not in valid_types:
            raise ValueError(f"Follow-up type must be one of: {', '.join(valid_types)}")
        return value.lower() if value else value

    @validates('status')
    def validate_status(self, key, value):
        if value and value.lower() not in ['scheduled', 'completed', 'missed', 'cancelled', 'rescheduled']:
            raise ValueError("Status must be scheduled, completed, missed, cancelled, or rescheduled")
        return value.lower() if value else value


class EscalationRule(Base):
    """Automated escalation rules and logic"""
    __tablename__ = "escalation_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    trigger_conditions = Column(UniversalJSON, nullable=False)  # Conditions that trigger escalation
    escalation_actions = Column(UniversalJSON, nullable=False)  # Actions to take when triggered
    priority = Column(String, nullable=False, default='medium')  # 'low', 'medium', 'high'
    is_active = Column(Boolean, default=True)
    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    last_triggered = Column(DateTime(timezone=True))
    trigger_count = Column(Integer, default=0)
    extra_metadata = Column(UniversalJSON)  # Rule-specific metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], backref="created_escalation_rules")

    # Indexes
    __table_args__ = (
        Index('idx_escalation_rules_active', 'is_active'),
        Index('idx_escalation_rules_priority', 'priority'),
    )

    @validates('priority')
    def validate_priority(self, key, value):
        if value and value.lower() not in ['low', 'medium', 'high']:
            raise ValueError("Priority must be low, medium, or high")
        return value.lower() if value else value


# Pydantic Models for API Request/Response Validation
class VisitData(BaseModel):
    """Patient visit record"""
    dateStarted: str
    voided: int = 0
    visitType: Optional[str] = None


class EncounterData(BaseModel):
    """Patient encounter record"""
    encounterUuid: str
    encounterDatetime: str
    encounterType: Optional[str] = None
    pmmForm: Optional[str] = None
    voided: int = 0


class ObservationData(BaseModel):
    """Clinical observation record"""
    obsDatetime: str
    variableName: str
    valueNumeric: Optional[float] = None
    valueText: Optional[str] = None
    valueCoded: Optional[str] = None
    encounterUuid: Optional[str] = None
    voided: int = 0


class DemographicsData(BaseModel):
    """Patient demographic information"""
    patientUuid: str
    birthdate: str
    gender: str
    stateProvince: Optional[str] = None
    cityVillage: Optional[str] = None
    phoneNumber: Optional[str] = None


class MessageData(BaseModel):
    """Complete patient message data structure"""
    demographics: DemographicsData
    visits: List[VisitData]
    encounters: List[EncounterData]
    obs: List[ObservationData]


class PatientJSON(BaseModel):
    """Complete patient JSON structure from IHVN system"""
    messageData: MessageData

    class Config:
        json_schema_extra = {
            "example": {
                "messageData": {
                    "demographics": {
                        "patientUuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "birthdate": "1985-06-15 00:00:00",
                        "gender": "F",
                        "stateProvince": "Lagos",
                        "cityVillage": "Ikeja",
                        "phoneNumber": "+234801234567"
                    },
                    "visits": [
                        {
                            "dateStarted": "2024-10-01 10:30:00",
                            "voided": 0,
                            "visitType": "CLINICAL"
                        }
                    ],
                    "encounters": [
                        {
                            "encounterUuid": "enc-uuid-123",
                            "encounterDatetime": "2024-10-01 10:30:00",
                            "pmmForm": "Pharmacy Order Form",
                            "voided": 0
                        }
                    ],
                    "obs": [
                        {
                            "obsDatetime": "2024-10-01 10:30:00",
                            "variableName": "Medication duration",
                            "valueNumeric": 90.0,
                            "voided": 0
                        }
                    ]
                }
            }
        }


class RiskLevel(str, Enum):
    """IIT risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IITPredictionResponse(BaseModel):
    """Single patient IIT prediction response"""
    patient_uuid: str
    iit_risk_score: float = Field(..., ge=0.0, le=1.0, description="Probability of IIT (0-1)")
    risk_level: RiskLevel
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    prediction_timestamp: datetime
    features_used: Dict[str, Any]
    model_version: str

    @validator('risk_level', pre=True, always=True)
    def determine_risk_level(cls, v, values):
        """Automatically determine risk level from score"""
        if 'iit_risk_score' not in values:
            return v

        score = values['iit_risk_score']
        if score >= 0.75:
            return RiskLevel.CRITICAL
        elif score >= 0.5:
            return RiskLevel.HIGH
        elif score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    class Config:
        json_schema_extra = {
            "example": {
                "patient_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "iit_risk_score": 0.68,
                "risk_level": "high",
                "confidence": 0.85,
                "prediction_timestamp": "2025-10-30T21:44:24",
                "features_used": {
                    "age": 39,
                    "days_since_last_refill": 45,
                    "last_days_supply": 30
                },
                "model_version": "1.0.0"
            }
        }


class BatchPredictionRequest(BaseModel):
    """Batch prediction request"""
    patients: List[PatientJSON] = Field(..., max_length=100)

    @validator('patients')
    def validate_batch_size(cls, v):
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100 patients")
        return v


class BatchPrediction(BaseModel):
    """Batch prediction response"""
    predictions: List[IITPredictionResponse]
    total_processed: int
    failed_count: int
    processing_time_seconds: float
    batch_id: str


class ModelMetrics(BaseModel):
    """Current model performance metrics"""
    model_version: str
    auc: float
    precision: float
    recall: float
    f1: float
    brier_score: float
    sensitivity: float
    specificity: float
    last_trained: Optional[datetime] = None
    total_predictions: int
    drift_detected: bool = False


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    model_loaded: bool
    redis_connected: bool
    uptime_seconds: float


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
    request_id: Optional[str] = None


# A/B Testing Models
class ABTest(Base):
    """A/B test configuration and metadata"""
    __tablename__ = "ab_tests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    test_id = Column(String, unique=True, nullable=False, index=True)
    test_name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, nullable=False, default='draft')  # draft, running, paused, completed, cancelled
    model_variants = Column(UniversalJSON, nullable=False)  # List of model IDs
    traffic_allocation = Column(String, nullable=False, default='equal')  # equal, gradual, custom
    traffic_weights = Column(UniversalJSON)  # Model ID to weight mapping
    target_sample_size = Column(Integer, default=1000)
    confidence_level = Column(Float, default=0.95)
    minimum_effect_size = Column(Float, default=0.02)
    primary_metric = Column(String, default='auc')
    secondary_metrics = Column(UniversalJSON)  # List of secondary metrics
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    variants = relationship("ABTestVariant", back_populates="test", cascade="all, delete-orphan")
    results = relationship("ABTestResult", back_populates="test", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_ab_tests_status', 'status'),
        Index('idx_ab_tests_start_date', 'start_date'),
    )


class ABTestVariant(Base):
    """A/B test variant configuration"""
    __tablename__ = "ab_test_variants"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    test_id = Column(String, ForeignKey('ab_tests.test_id'), nullable=False)
    variant_id = Column(String, nullable=False)  # variant_1, variant_2, etc.
    model_id = Column(String, nullable=False)
    weight = Column(Float, default=0.0)  # Traffic weight (0-1)
    sample_size = Column(Integer, default=0)
    is_control = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    test = relationship("ABTest", back_populates="variants")

    # Indexes
    __table_args__ = (
        Index('idx_ab_test_variants_test_id', 'test_id'),
        Index('idx_ab_test_variants_variant_id', 'variant_id'),
    )


class ABTestResult(Base):
    """A/B test prediction results and assignments"""
    __tablename__ = "ab_test_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    test_id = Column(String, ForeignKey('ab_tests.test_id'), nullable=False)
    user_id = Column(String, nullable=False)  # Patient UUID or user identifier
    variant_id = Column(String, nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    prediction_score = Column(Float)
    actual_outcome = Column(Float)  # Ground truth when available
    prediction_metadata = Column(UniversalJSON)  # Additional prediction data
    recorded_at = Column(DateTime(timezone=True))

    # Relationships
    test = relationship("ABTest", back_populates="results")

    # Indexes
    __table_args__ = (
        Index('idx_ab_test_results_test_id', 'test_id'),
        Index('idx_ab_test_results_user_id', 'user_id'),
        Index('idx_ab_test_results_variant_id', 'variant_id'),
        Index('idx_ab_test_results_assigned_at', 'assigned_at'),
    )


# Model Registry Models
class ModelVersion(Base):
    """Model version and metadata storage"""
    __tablename__ = "model_versions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_id = Column(String, unique=True, nullable=False, index=True)
    version = Column(String, nullable=False)
    algorithm = Column(String, nullable=False)
    hyperparameters = Column(UniversalJSON, nullable=False)
    training_data_info = Column(UniversalJSON, nullable=False)
    performance_metrics = Column(UniversalJSON, nullable=False)
    feature_importance = Column(UniversalJSON)
    model_path = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    tags = Column(UniversalJSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_model_versions_active', 'is_active'),
        Index('idx_model_versions_created_at', 'created_at'),
    )


class ModelMetrics(Base):
    """Model performance metrics tracking"""
    __tablename__ = "model_metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_id = Column(String, ForeignKey('model_versions.model_id'), nullable=False)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    extra_metadata = Column(UniversalJSON)

    # Relationships
    model = relationship("ModelVersion", backref="metrics")

    # Indexes
    __table_args__ = (
        Index('idx_model_metrics_model_id', 'model_id'),
        Index('idx_model_metrics_name', 'metric_name'),
        Index('idx_model_metrics_recorded_at', 'recorded_at'),
    )


class ModelComparison(Base):
    """Model comparison results storage"""
    __tablename__ = "model_comparisons"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_ids = Column(UniversalJSON, nullable=False)  # List of model IDs being compared
    comparison_data = Column(UniversalJSON, nullable=False)  # Full comparison results
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_model_comparisons_created_at', 'created_at'),
    )
