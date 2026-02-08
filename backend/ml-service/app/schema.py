"""
Pydantic schemas for IIT ML Service API validation
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


# Authentication Schemas
class UserCreate(BaseModel):
    """User registration schema"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Strong password")
    full_name: Optional[str] = Field(None, description="Optional full name")

    @validator('password')
    def password_strength(cls, v):
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """User login schema"""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    roles: List[str] = []

    @validator('roles', pre=True, always=True)
    def convert_roles_to_strings(cls, v):
        """Convert Role objects to role names"""
        if v is None:
            return []
        if isinstance(v, list):
            if len(v) == 0:
                return []
            # If already a list of strings, return as-is
            if isinstance(v[0], str):
                return v
            # Convert Role objects to role names
            return [role.name if hasattr(role, 'name') else str(role) for role in v]
        return []

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class RoleResponse(BaseModel):
    """Role response schema"""
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    permissions: List[str] = []

    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    """Permission response schema"""
    id: int
    name: str
    description: Optional[str]
    resource: str
    action: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update schema"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    roles: Optional[List[str]] = None


class RoleCreate(BaseModel):
    """Role creation schema"""
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    permissions: List[str] = []


class PermissionCreate(BaseModel):
    """Permission creation schema"""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    resource: str = Field(..., min_length=2, max_length=50)
    action: str = Field(..., min_length=2, max_length=20)


# Audit Logging Schemas
class AuditLogResponse(BaseModel):
    """Audit log response schema"""
    id: int
    user_id: Optional[int]
    username: Optional[str]
    action: str
    resource: str
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime
    success: bool

    class Config:
        from_attributes = True


class AuditLogCreate(BaseModel):
    """Audit log creation schema"""
    action: str
    resource: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# Session Management Schemas
class SessionInfo(BaseModel):
    """Session information schema"""
    session_id: str
    user_id: int
    username: str
    roles: List[str]
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]


class LogoutResponse(BaseModel):
    """Logout response schema"""
    message: str
    session_terminated: bool


# Existing schemas from models.py (keeping for compatibility)
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


# Patient Management Schemas
class PatientCreate(BaseModel):
    """Patient creation schema"""
    patient_uuid: Optional[str] = Field(None, description="Optional UUID, auto-generated if not provided")
    datim_id: Optional[str] = Field(None, description="DATIM facility identifier")
    pepfar_id: Optional[str] = Field(None, description="PEPFAR patient identifier")
    given_name: Optional[str] = Field(None, description="Patient's given name")
    family_name: Optional[str] = Field(None, description="Patient's family name")
    birthdate: datetime = Field(..., description="Patient's birth date")
    gender: str = Field(..., description="Patient gender (M, F, MALE, FEMALE)")
    state_province: Optional[str] = Field(None, description="State or province")
    city_village: Optional[str] = Field(None, description="City or village")
    phone_number: Optional[str] = Field(None, description="Phone number (must start with +)")

    @validator('gender')
    def validate_gender(cls, v):
        if v and v.upper() not in ['M', 'F', 'MALE', 'FEMALE']:
            raise ValueError("Gender must be M, F, MALE, or FEMALE")
        return v.upper() if v else v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v and not v.startswith('+'):
            raise ValueError("Phone number must start with +")
        return v

    @validator('birthdate')
    def validate_birthdate(cls, v):
        if v and v > datetime.now():
            raise ValueError("Birth date cannot be in the future")
        return v


class PatientUpdate(BaseModel):
    """Patient update schema"""
    datim_id: Optional[str] = None
    pepfar_id: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    birthdate: Optional[datetime] = None
    gender: Optional[str] = None
    state_province: Optional[str] = None
    city_village: Optional[str] = None
    phone_number: Optional[str] = None

    @validator('gender')
    def validate_gender(cls, v):
        if v and v.upper() not in ['M', 'F', 'MALE', 'FEMALE']:
            raise ValueError("Gender must be M, F, MALE, or FEMALE")
        return v.upper() if v else v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v and not v.startswith('+'):
            raise ValueError("Phone number must start with +")
        return v

    @validator('birthdate')
    def validate_birthdate(cls, v):
        if v and v > datetime.now():
            raise ValueError("Birth date cannot be in the future")
        return v


class PatientResponse(BaseModel):
    """Patient response schema"""
    patient_uuid: str
    datim_id: Optional[str]
    pepfar_id: Optional[str]
    given_name: Optional[str]
    family_name: Optional[str]
    birthdate: Optional[datetime]
    gender: Optional[str]
    state_province: Optional[str]
    city_village: Optional[str]
    phone_number: Optional[str]
    phone_present: Optional[bool]
    created_at: datetime
    updated_at: datetime

    @validator('patient_uuid', pre=True, always=True)
    def convert_uuid_to_string(cls, v):
        """Convert UUID object to string"""
        if v and hasattr(v, '__str__'):
            return str(v)
        return v

    class Config:
        from_attributes = True


class PatientSearch(BaseModel):
    """Patient search schema"""
    query: Optional[str] = Field(None, description="General search query")
    patient_uuid: Optional[str] = None
    datim_id: Optional[str] = None
    pepfar_id: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    gender: Optional[str] = None
    state_province: Optional[str] = None
    city_village: Optional[str] = None
    phone_number: Optional[str] = None
    birthdate_from: Optional[datetime] = None
    birthdate_to: Optional[datetime] = None
    has_phone: Optional[bool] = None


class PatientFilter(BaseModel):
    """Patient filtering schema"""
    gender: Optional[str] = None
    state_province: Optional[str] = None
    has_phone: Optional[bool] = None
    age_min: Optional[int] = Field(None, ge=0, le=120)
    age_max: Optional[int] = Field(None, ge=0, le=120)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class PatientListResponse(BaseModel):
    """Patient list response with pagination"""
    patients: List[PatientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PatientImportRequest(BaseModel):
    """Patient import request schema"""
    patients: List[PatientCreate] = Field(..., max_length=1000)
    deduplicate: bool = Field(True, description="Whether to check for duplicates")
    validate_data: bool = Field(True, description="Whether to validate data quality")


class PatientImportResponse(BaseModel):
    """Patient import response schema"""
    imported_count: int
    duplicate_count: int
    error_count: int
    errors: List[Dict[str, Any]]
    processing_time_seconds: float


class PatientExportRequest(BaseModel):
    """Patient export request schema"""
    filters: Optional[PatientFilter] = None
    format: str = Field("json", description="Export format: json, csv, excel")
    include_related: bool = Field(False, description="Include visits, encounters, observations")


class PatientValidationRequest(BaseModel):
    """Patient data validation request schema"""
    patient: PatientCreate
    strict: bool = Field(True, description="Whether to use strict validation rules")


class PatientValidationResponse(BaseModel):
    """Patient data validation response schema"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class PatientHistoryResponse(BaseModel):
    """Patient history response schema"""
    patient_uuid: str
    changes: List[Dict[str, Any]]
    total_changes: int


class PatientStatsResponse(BaseModel):
    """Patient statistics response schema"""
    total_patients: int
    gender_distribution: Dict[str, int]
    state_distribution: Dict[str, int]
    phone_coverage: float
    average_age: Optional[float]
    age_distribution: Dict[str, int]


# Visit Management Schemas
class VisitCreate(BaseModel):
    """Visit creation schema"""
    visit_uuid: Optional[str] = Field(None, description="Optional UUID, auto-generated if not provided")
    patient_uuid: str = Field(..., description="Patient UUID")
    visit_type: Optional[str] = Field(None, description="Type of visit")
    date_started: datetime = Field(..., description="Visit start date and time")
    date_stopped: Optional[datetime] = Field(None, description="Visit end date and time")
    location_id: Optional[str] = Field(None, description="Location/facility identifier")

    @validator('date_stopped')
    def validate_dates(cls, v, values):
        if v and 'date_started' in values and v < values['date_started']:
            raise ValueError("Date stopped cannot be before date started")
        return v


class VisitUpdate(BaseModel):
    """Visit update schema"""
    visit_type: Optional[str] = None
    date_started: Optional[datetime] = None
    date_stopped: Optional[datetime] = None
    location_id: Optional[str] = None
    voided: Optional[bool] = None

    @validator('date_stopped')
    def validate_dates(cls, v, values):
        if v and 'date_started' in values and values['date_started'] and v < values['date_started']:
            raise ValueError("Date stopped cannot be before date started")
        return v
    
class VisitResponse(BaseModel):
    """Visit response schema"""
    id: int
    visit_uuid: str
    patient_uuid: str
    visit_type: Optional[str]
    date_started: Optional[datetime]
    date_stopped: Optional[datetime]
    location_id: Optional[str]
    voided: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VisitListResponse(BaseModel):
    """Visit list response with pagination"""
    visits: List[VisitResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VisitFilter(BaseModel):
    """Visit filtering schema"""
    patient_uuid: Optional[str] = None
    visit_type: Optional[str] = None
    location_id: Optional[str] = None
    date_started_from: Optional[datetime] = None
    date_started_to: Optional[datetime] = None
    voided: Optional[bool] = None


# Encounter Management Schemas
class EncounterCreate(BaseModel):
    """Encounter creation schema"""
    encounter_uuid: Optional[str] = Field(None, description="Optional UUID, auto-generated if not provided")
    patient_uuid: str = Field(..., description="Patient UUID")
    visit_id: Optional[int] = Field(None, description="Associated visit ID")
    encounter_datetime: datetime = Field(..., description="Encounter date and time")
    encounter_type: Optional[str] = Field(None, description="Type of encounter")
    pmm_form: Optional[str] = Field(None, description="PMM form name")
    form_id: Optional[str] = Field(None, description="Form identifier")

    @validator('encounter_datetime')
    def validate_datetime(cls, v):
        if v > datetime.now():
            raise ValueError("Encounter datetime cannot be in the future")
        return v


class EncounterUpdate(BaseModel):
    """Encounter update schema"""
    visit_id: Optional[int] = None
    encounter_datetime: Optional[datetime] = None
    encounter_type: Optional[str] = None
    pmm_form: Optional[str] = None
    form_id: Optional[str] = None
    voided: Optional[bool] = None

    @validator('encounter_datetime')
    def validate_datetime(cls, v):
        if v and v > datetime.now():
            raise ValueError("Encounter datetime cannot be in the future")
        return v


class EncounterResponse(BaseModel):
    """Encounter response schema"""
    id: int
    encounter_uuid: str
    patient_uuid: str
    visit_id: Optional[int]
    encounter_datetime: Optional[datetime]
    encounter_type: Optional[str]
    pmm_form: Optional[str]
    form_id: Optional[str]
    voided: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EncounterListResponse(BaseModel):
    """Encounter list response with pagination"""
    encounters: List[EncounterResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EncounterFilter(BaseModel):
    """Encounter filtering schema"""
    patient_uuid: Optional[str] = None
    visit_id: Optional[int] = None
    encounter_type: Optional[str] = None
    pmm_form: Optional[str] = None
    encounter_datetime_from: Optional[datetime] = None
    encounter_datetime_to: Optional[datetime] = None
    voided: Optional[bool] = None


# Observation Management Schemas
class ObservationCreate(BaseModel):
    """Observation creation schema"""
    obs_uuid: Optional[str] = Field(None, description="Optional UUID, auto-generated if not provided")
    patient_uuid: str = Field(..., description="Patient UUID")
    encounter_id: int = Field(..., description="Associated encounter ID")
    concept_id: Optional[str] = Field(None, description="Concept identifier")
    variable_name: str = Field(..., description="Variable name")
    value_numeric: Optional[float] = Field(None, description="Numeric value")
    value_text: Optional[str] = Field(None, description="Text value")
    value_coded: Optional[str] = Field(None, description="Coded value")
    obs_datetime: datetime = Field(..., description="Observation date and time")

    @validator('obs_datetime')
    def validate_datetime(cls, v):
        if v > datetime.now():
            raise ValueError("Observation datetime cannot be in the future")
        return v

    @validator('value_numeric')
    def validate_numeric_value(cls, v):
        if v is not None and (v < -1000000 or v > 1000000):
            raise ValueError("Numeric value out of reasonable range")
        return v


class ObservationUpdate(BaseModel):
    """Observation update schema"""
    concept_id: Optional[str] = None
    variable_name: Optional[str] = None
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    value_coded: Optional[str] = None
    obs_datetime: Optional[datetime] = None
    voided: Optional[bool] = None

    @validator('obs_datetime')
    def validate_datetime(cls, v):
        if v and v > datetime.now():
            raise ValueError("Observation datetime cannot be in the future")
        return v

    @validator('value_numeric')
    def validate_numeric_value(cls, v):
        if v is not None and (v < -1000000 or v > 1000000):
            raise ValueError("Numeric value out of reasonable range")
        return v


class ObservationResponse(BaseModel):
    """Observation response schema"""
    id: int
    obs_uuid: str
    patient_uuid: str
    encounter_id: int
    concept_id: Optional[str]
    variable_name: Optional[str]
    value_numeric: Optional[float]
    value_text: Optional[str]
    value_coded: Optional[str]
    obs_datetime: Optional[datetime]
    voided: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ObservationListResponse(BaseModel):
    """Observation list response with pagination"""
    observations: List[ObservationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ObservationFilter(BaseModel):
    """Observation filtering schema"""
    patient_uuid: Optional[str] = None
    encounter_id: Optional[int] = None
    concept_id: Optional[str] = None
    variable_name: Optional[str] = None
    obs_datetime_from: Optional[datetime] = None
    obs_datetime_to: Optional[datetime] = None
    voided: Optional[bool] = None


class BulkObservationCreate(BaseModel):
    """Bulk observation creation schema"""
    observations: List[ObservationCreate] = Field(..., max_length=1000)

    @validator('observations')
    def validate_batch_size(cls, v):
        if len(v) > 1000:
            raise ValueError("Batch size cannot exceed 1000 observations")
        return v


class BulkObservationResponse(BaseModel):
    """Bulk observation creation response schema"""
    created_count: int
    error_count: int
    errors: List[Dict[str, Any]]
    processing_time_seconds: float


# Analytics Schemas
class PatientAnalyticsResponse(BaseModel):
    """Patient analytics response schema"""
    total_patients: int
    active_patients: int
    new_patients_last_30_days: int
    patients_by_gender: Dict[str, int]
    patients_by_state: Dict[str, int]
    average_age: Optional[float]
    phone_coverage_rate: float


class PredictionAnalyticsResponse(BaseModel):
    """Prediction analytics response schema"""
    total_predictions: int
    predictions_last_30_days: int
    risk_distribution: Dict[str, int]
    average_confidence: float
    model_versions: List[str]


class SystemHealthResponse(BaseModel):
    """System health response schema"""
    database_status: str
    redis_status: str
    model_status: str
    uptime_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float


class DatabaseHealthResponse(BaseModel):
    """Database health response schema"""
    status: str
    connection_count: int
    active_connections: int
    total_tables: int
    database_size_mb: float


class ModelHealthResponse(BaseModel):
    """Model health response schema"""
    status: str
    model_version: str
    last_loaded: Optional[datetime]
    prediction_count: int
    average_response_time_ms: float


# Advanced Analytics Schemas
class CohortAnalysisRequest(BaseModel):
    """Cohort analysis request schema"""
    cohort_definition: Dict[str, Any] = Field(..., description="Cohort definition criteria")
    time_period: str = Field("monthly", description="Analysis time period: daily, weekly, monthly")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metrics: List[str] = Field(["retention", "risk_trend"], description="Metrics to analyze")

class ModelHealthResponse(BaseModel):
    """Model health response schema"""
    status: str
    model_version: str
    last_loaded: Optional[datetime]
    prediction_count: int
    average_response_time_ms: float

# Advanced Analytics Schemas
class CohortAnalysisRequest(BaseModel):
    """Cohort analysis request schema"""
    cohort_definition: Dict[str, Any] = Field(..., description="Cohort definition criteria")
    time_period: str = Field("monthly", description="Time period for analysis: daily, weekly, monthly")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metrics: List[str] = Field(["retention", "risk_trend"], description="Metrics to analyze")


class CohortAnalysisResponse(BaseModel):
    """Cohort analysis response schema"""
    cohort_id: str
    cohort_size: int
    retention_rates: Dict[str, float]
    risk_score_trends: Dict[str, float]
    intervention_effectiveness: Optional[Dict[str, Any]]
    time_period: str
    analysis_date: datetime


class PredictiveTrendRequest(BaseModel):
    """Predictive trend analysis request schema"""
    target_metric: str = Field(..., description="Metric to predict: risk_score, patient_count, etc.")
    forecast_periods: int = Field(30, description="Number of periods to forecast")
    model_type: str = Field("linear", description="Forecasting model: linear, exponential, arima")
    confidence_interval: float = Field(0.95, description="Confidence interval for predictions")


class PredictiveTrendResponse(BaseModel):
    """Predictive trend analysis response schema"""
    target_metric: str
    historical_data: List[Dict[str, Any]]
    predictions: List[Dict[str, Any]]
    confidence_intervals: Dict[str, List[float]]
    model_accuracy: float
    forecast_periods: int
    generated_at: datetime


class RiskFactorCorrelationRequest(BaseModel):
    """Risk factor correlation analysis request schema"""
    risk_factors: List[str] = Field(..., description="Risk factors to analyze")
    correlation_method: str = Field("pearson", description="Correlation method: pearson, spearman, kendall")
    min_sample_size: int = Field(30, description="Minimum sample size for analysis")
    significance_level: float = Field(0.05, description="Statistical significance level")


class RiskFactorCorrelationResponse(BaseModel):
    """Risk factor correlation analysis response schema"""
    correlations: Dict[str, Dict[str, float]]
    p_values: Dict[str, Dict[str, float]]
    significant_correlations: List[Dict[str, Any]]
    sample_size: int
    method_used: str
    analysis_date: datetime


class CustomReportRequest(BaseModel):
    """Custom report builder request schema"""
    report_name: str = Field(..., description="Name of the custom report")
    filters: Dict[str, Any] = Field(..., description="Report filters")
    group_by: List[str] = Field(..., description="Fields to group by")
    aggregations: Dict[str, str] = Field(..., description="Aggregation functions")
    date_range: Dict[str, datetime] = Field(..., description="Date range for report")
    include_charts: bool = Field(True, description="Whether to include chart data")


class CustomReportResponse(BaseModel):
    """Custom report builder response schema"""
    report_id: str
    report_name: str
    data: List[Dict[str, Any]]
    summary: Dict[str, Any]
    charts: Optional[Dict[str, Any]]
    generated_at: datetime
    filters_applied: Dict[str, Any]


class InterventionEffectivenessRequest(BaseModel):
    """Intervention effectiveness analysis request schema"""
    intervention_type: str = Field(..., description="Type of intervention")
    patient_cohort: Dict[str, Any] = Field(..., description="Patient cohort criteria")
    time_period: str = Field("before_after", description="Analysis time period: before_after, trend")
    metrics: List[str] = Field(["risk_reduction", "retention"], description="Metrics to evaluate")


class InterventionEffectivenessResponse(BaseModel):
    """Intervention effectiveness analysis response schema"""
    intervention_type: str
    cohort_size: int
    effectiveness_metrics: Dict[str, Any]
    statistical_significance: Dict[str, float]
    confidence_intervals: Dict[str, List[float]]
    analysis_period: str
    report_date: datetime


class ComplianceAuditRequest(BaseModel):
    """Compliance and audit report request schema"""
    audit_type: str = Field(..., description="Type of audit: data_quality, access_control, prediction_accuracy")
    time_range: Dict[str, datetime] = Field(..., description="Time range for audit")
    severity_filter: Optional[str] = Field(None, description="Filter by severity level")
    department_filter: Optional[str] = Field(None, description="Filter by department")


class ComplianceAuditResponse(BaseModel):
    """Compliance and audit report response schema"""
    audit_id: str
    audit_type: str
    findings: List[Dict[str, Any]]
    compliance_score: float
    critical_issues: int
    recommendations: List[str]
    audit_period: Dict[str, datetime]
    generated_at: datetime


class DataExportRequest(BaseModel):
    """Data export request schema"""
    export_type: str = Field(..., description="Export type: csv, excel, pdf, json")
    data_source: str = Field(..., description="Data source: patients, predictions, analytics")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Export filters")
    include_headers: bool = Field(True, description="Include column headers")
    date_format: str = Field("YYYY-MM-DD", description="Date format for export")


class DataExportResponse(BaseModel):
    """Data export response schema"""
    export_id: str
    file_url: str
    file_size: int
    record_count: int
    export_format: str
    generated_at: datetime
    expires_at: datetime


class ScheduledReportRequest(BaseModel):
    """Scheduled report request schema"""
    report_type: str = Field(..., description="Type of report to schedule")
    schedule: str = Field(..., description="Cron schedule expression")
    recipients: List[str] = Field(..., description="Email recipients")
    report_config: Dict[str, Any] = Field(..., description="Report configuration")
    is_active: bool = Field(True, description="Whether the schedule is active")


class ScheduledReportResponse(BaseModel):
    """Scheduled report response schema"""
    schedule_id: str
    report_type: str
    schedule_expression: str
    next_run: datetime
    recipients: List[str]
    is_active: bool
    created_at: datetime
    last_run: Optional[datetime]


class DashboardAnalyticsResponse(BaseModel):
    """Enhanced dashboard analytics response"""
    total_predictions: int
    high_risk_patients: int
    any_risk_cases: int
    predictions_today: int
    risk_distribution: List[Dict[str, Any]]
    recent_predictions: List[Dict[str, Any]]
    trend_data: List[Dict[str, Any]]
    period_days: int
    intervention_effectiveness: Optional[Dict[str, Any]]
    compliance_score: Optional[float]


class RiskDistributionResponse(BaseModel):
    """Risk distribution response schema"""
    distribution: List[Dict[str, Any]]
    total_patients: int
    period_days: int
    risk_trends: Optional[Dict[str, Any]]


class TrendAnalysisResponse(BaseModel):
    """Trend analysis response schema"""
    trends: List[Dict[str, Any]]
    interval: str
    period_days: int
    predictions: Optional[List[Dict[str, Any]]]


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response schema"""
    total_predictions: int
    average_confidence: float
    average_risk_score: float
    risk_distribution: Dict[str, int]
    average_processing_time: float
    period_days: int
    model_drift_score: Optional[float]


class PatientAnalyticsResponse(BaseModel):
    """Patient analytics response schema"""
    patient_uuid: str
    total_predictions: int
    current_risk_level: str
    previous_risk_level: str
    average_risk_score: float
    max_risk_score: float
    min_risk_score: float
    risk_trend: List[Dict[str, Any]]
    visit_count: int
    period_days: int
    intervention_history: Optional[List[Dict[str, Any]]]



# Features Management Schemas
class IITFeaturesResponse(BaseModel):
    """IIT features response schema"""
    patient_uuid: str
    age: Optional[int] = None
    gender: Optional[str] = None
    has_phone: Optional[bool] = None
    days_since_last_visit: Optional[int] = None
    days_since_last_refill: Optional[int] = None
    total_visits: Optional[int] = None
    viral_load_suppressed: Optional[bool] = None
    cd4_count: Optional[float] = None
    last_feature_update: Optional[datetime] = None
    feature_version: Optional[str] = None

    class Config:
        from_attributes = True


class FeatureUpdateRequest(BaseModel):
    """Feature update request schema"""
    features: Dict[str, Any] = Field(..., description="Features to update")


class FeatureUpdateResponse(BaseModel):
    """Feature update response schema"""
    patient_uuid: str
    updated_features: List[str]
    update_timestamp: datetime


class PredictionCreate(BaseModel):
    """Request model for creating a new IIT prediction"""
    patient_uuid: str
    features: Dict[str, Any] = Field(..., description="Feature values for prediction")

    class Config:
        json_schema_extra = {
            "example": {
                "patient_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "features": {
                    "age": 35,
                    "days_since_last_refill": 45,
                    "last_days_supply": 30,
                    "visit_count_last_90d": 2,
                    "cd4_count": 380
                }
            }
        }


class PredictionResponse(BaseModel):
    """Response model for prediction results"""
    id: int
    patient_uuid: str
    prediction_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: RiskLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    features: Dict[str, Any]
    model_version: str
    prediction_timestamp: datetime

    @validator('patient_uuid', pre=True, always=True)
    def convert_uuid_to_string(cls, v):
        """Convert UUID object to string"""
        if v and hasattr(v, '__str__'):
            return str(v)
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 123,
                "patient_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "risk_score": 0.68,
                "risk_level": "high",
                "confidence": 0.85,
                "features_used": {
                    "age": 35,
                    "days_since_last_refill": 45,
                    "last_days_supply": 30
                },
                "model_version": "1.2.0",
                "prediction_timestamp": "2025-01-15T10:30:00",
                "created_by": "clinician-001",
                "created_at": "2025-01-15T10:30:00",
                "updated_at": "2025-01-15T10:30:00"
            }
        }


class PredictionListResponse(BaseModel):
    """Response model for prediction list endpoints"""
    predictions: List[PredictionResponse]
    total: int
    skip: int
    limit: int


class PredictionSearchFilters(BaseModel):
    """Filters for prediction search"""
    patient_uuid: Optional[str] = None
    risk_level: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_confidence: Optional[float] = None


class BatchPredictionRequest(BaseModel):
    """Request model for batch predictions"""
    predictions: List[PredictionCreate] = Field(..., max_length=100)


class BatchPredictionResponse(BaseModel):
    """Response model for batch predictions"""
    successful_predictions: List[PredictionResponse]
    failed_predictions: List[Dict[str, Any]]
    total_processed: int
    total_failed: int


class PredictionAnalyticsResponse(BaseModel):
    """Response model for prediction analytics"""
    total_predictions: int
    risk_distribution: Dict[str, int]
    trend_data: List[Dict[str, Any]]
    average_confidence: float
    period_days: int
