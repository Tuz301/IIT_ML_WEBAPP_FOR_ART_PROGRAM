"""
Pytest configuration and shared fixtures for IIT ML Service testing.
This module provides comprehensive fixtures for unit, integration, and E2E tests.
"""
import pytest
import sys
import os
import asyncio
import tempfile
import json
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport

# Add app directory to path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

from app.main import app
from app.models import Base, User, Patient, Prediction
from app.auth import get_password_hash, create_access_token
from app.schema import PatientCreate, PredictionCreate


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_config():
    """Test configuration settings"""
    return {
        "test_mode": True,
        "redis_enabled": False,
        "model_path": "./tests/fixtures/mock_model.txt",
        "test_database_url": "sqlite:///./test.db",
        "test_jwt_secret": "test-secret-key",
        "test_jwt_algorithm": "HS256",
        "test_access_token_expire_minutes": 30,
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_db_file():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="function")
async def test_db(test_db_file):
    """Create test database with tables."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Create async engine for SQLite
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{test_db_file}",
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    yield async_session_maker
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_db):
    """Provide a database session for testing."""
    async with test_db() as session:
        yield session


# ============================================================================
# Mock Redis Fixtures
# ============================================================================

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    class MockRedis:
        def __init__(self):
            self._store = {}
        
        async def get(self, key):
            return self._store.get(key)
        
        async def setex(self, key, ttl, value):
            self._store[key] = value
        
        async def delete(self, key):
            self._store.pop(key, None)
        
        async def exists(self, key):
            return key in self._store
        
        async def ping(self):
            return True
        
        async def keys(self, pattern):
            return [k for k in self._store.keys() if pattern in k]
        
        async def flushdb(self):
            self._store.clear()
    
    return MockRedis()


@pytest.fixture
def mock_cache(monkeypatch):
    """Mock the cache dependency."""
    # Note: get_cache is not currently used as a dependency in the app
    # This fixture is kept for potential future use
    return mock_redis_client()


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "role": "healthcare_provider",
        "is_active": True,
    }


@pytest.fixture
def test_admin_data():
    """Sample admin user data for testing."""
    return {
        "username": "admin",
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "full_name": "System Administrator",
        "role": "admin",
        "is_active": True,
    }


@pytest.fixture
async def test_user(db_session):
    """Create a test user in the database."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPassword123!"),
        full_name="Test User",
        role="healthcare_provider",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(db_session):
    """Create a test admin user in the database."""
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPassword123!"),
        full_name="System Administrator",
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def test_token(test_user):
    """Create a valid JWT token for testing."""
    access_token = create_access_token(
        data={"sub": test_user.username, "role": test_user.role}
    )
    return access_token


@pytest.fixture
def test_admin_token(test_admin):
    """Create a valid admin JWT token for testing."""
    access_token = create_access_token(
        data={"sub": test_admin.username, "role": test_admin.role}
    )
    return access_token


@pytest.fixture
def auth_headers(test_token):
    """Headers with authentication token."""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def admin_auth_headers(test_admin_token):
    """Headers with admin authentication token."""
    return {"Authorization": f"Bearer {test_admin_token}"}


# ============================================================================
# Patient Data Fixtures
# ============================================================================

@pytest.fixture
def sample_patient_data():
    """Sample patient data for testing."""
    return {
        "patientUuid": "test-patient-123",
        "birthdate": "1985-06-15 00:00:00",
        "gender": "F",
        "stateProvince": "Lagos",
        "cityVillage": "Ikeja",
        "phoneNumber": "+234801234567",
    }


@pytest.fixture
def sample_prediction_request():
    """Sample prediction request data."""
    return {
        "messageData": {
            "demographics": {
                "patientUuid": "test-patient-123",
                "birthdate": "1985-06-15 00:00:00",
                "gender": "F",
                "stateProvince": "Lagos",
                "cityVillage": "Ikeja",
                "phoneNumber": "+234801234567"
            },
            "visits": [
                {
                    "dateStarted": "2024-10-01 10:30:00",
                    "voided": 0
                }
            ],
            "encounters": [
                {
                    "encounterUuid": "enc-123",
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


@pytest.fixture
async def test_patient(db_session, sample_patient_data):
    """Create a test patient in the database."""
    patient = Patient(
        patient_uuid=sample_patient_data["patientUuid"],
        birthdate=datetime.strptime(sample_patient_data["birthdate"], "%Y-%m-%d %H:%M:%S"),
        gender=sample_patient_data["gender"],
        state_province=sample_patient_data["stateProvince"],
        city_village=sample_patient_data["cityVillage"],
        phone_number=sample_patient_data["phoneNumber"],
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


# ============================================================================
# ML Model Fixtures
# ============================================================================

@pytest.fixture
def mock_ml_model():
    """Mock ML model for testing."""
    model = MagicMock()
    model.predict_proba = MagicMock(return_value=[[0.3, 0.7]])
    model.predict = MagicMock(return_value=[1])
    model.feature_importances_ = [0.1, 0.2, 0.3, 0.4]
    return model


@pytest.fixture
def mock_model_response():
    """Mock model prediction response."""
    return {
        "patient_uuid": "test-patient-123",
        "iit_risk_score": 0.75,
        "risk_level": "high",
        "confidence": 0.85,
        "feature_importance": {
            "medication_duration": 0.35,
            "age": 0.25,
            "gender": 0.15,
            "location": 0.25
        },
        "prediction_timestamp": datetime.utcnow().isoformat(),
        "model_version": "1.0.0"
    }


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sync_client():
    """Synchronous test client for FastAPI."""
    from fastapi.testclient import TestClient
    return TestClient(app)


# ============================================================================
# Mock External Services
# ============================================================================

@pytest.fixture
def mock_openmrs_api():
    """Mock OpenMRS API client."""
    with patch("app.ml_model.OpenMRSClient") as mock:
        client = MagicMock()
        client.get_patient_data = AsyncMock(return_value={
            "uuid": "test-patient-123",
            "identifiers": [{"identifier": "PAT-001"}],
        })
        mock.return_value = client
        yield client


@pytest.fixture
def mock_external_api():
    """Mock external API calls."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "ok", "data": {}}
        )
        yield mock_get


# ============================================================================
# Time-based Fixtures
# ============================================================================

@pytest.fixture
def freeze_time(monkeypatch):
    """Freeze time for testing."""
    frozen_time = datetime(2024, 1, 1, 12, 0, 0)
    
    class FrozenDateTime:
        @classmethod
        def now(cls, tz=None):
            return frozen_time
        
        @classmethod
        def utcnow(cls):
            return frozen_time
    
    monkeypatch.setattr("datetime.datetime", FrozenDateTime)
    return frozen_time


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def benchmark_data():
    """Generate benchmark data for performance testing."""
    try:
        from faker import Faker  # type: ignore
    except ImportError:
        # Faker is optional for testing
        from unittest.mock import MagicMock
        Faker = MagicMock()
    fake = Faker()
    
    patients = []
    for i in range(100):
        patients.append({
            "patientUuid": f"patient-{i}",
            "birthdate": fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%Y-%m-%d %H:%M:%S"),
            "gender": fake.random_element(["M", "F"]),
            "stateProvince": fake.state(),
            "cityVillage": fake.city(),
            "phoneNumber": fake.phone_number(),
        })
    
    return patients


# ============================================================================
# Error Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_database_error():
    """Mock database error for testing error handling."""
    from sqlalchemy.exc import SQLAlchemyError
    error = SQLAlchemyError("Database connection failed")
    return error


@pytest.fixture
def mock_api_timeout():
    """Mock API timeout error."""
    import asyncio
    return asyncio.TimeoutError("API request timed out")


# ============================================================================
# Logging Fixtures
# ============================================================================

@pytest.fixture
def log_capture(caplog):
    """Capture log messages for testing."""
    with caplog.at_level("DEBUG"):
        yield caplog


# ============================================================================
# Test Data Generators
# ============================================================================

@pytest.fixture
def generate_patient_data():
    """Factory for generating patient test data."""
    try:
        from faker import Faker  # type: ignore
    except ImportError:
        # Faker is optional for testing
        from unittest.mock import MagicMock
        Faker = MagicMock()
    fake = Faker()
    
    def _generate(**overrides):
        data = {
            "patientUuid": fake.uuid4(),
            "birthdate": fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%Y-%m-%d %H:%M:%S"),
            "gender": fake.random_element(["M", "F"]),
            "stateProvince": fake.state(),
            "cityVillage": fake.city(),
            "phoneNumber": fake.phone_number(),
        }
        data.update(overrides)
        return data
    
    return _generate
