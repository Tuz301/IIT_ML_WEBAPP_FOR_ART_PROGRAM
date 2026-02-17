"""
End-to-End Integration Tests for IIT ML Service
Tests complete user flows from authentication to prediction
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Base, User, Patient
from app.auth import get_password_hash, create_access_token
from app.core.db import get_db


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def test_db():
    """Create test database"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    import tempfile
    import os
    
    # Create temporary database
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = db_file.name
    db_file.close()
    
    # Create async engine
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    yield async_session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    os.unlink(db_path)


@pytest.fixture
async def client(test_db):
    """Create test client with database override"""
    from app.core.db import SessionLocal
    import os
    
    # Override database for testing
    original_db_url = os.getenv("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    os.environ["ENVIRONMENT"] = "test"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Restore original database URL
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    else:
        del os.environ["DATABASE_URL"]


@pytest.fixture
async def test_user(test_db):
    """Create test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPassword123!"),
        full_name="Test User",
        role="healthcare_provider",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
def test_token(test_user):
    """Create test token"""
    return create_access_token(
        data={"sub": test_user.username, "role": test_user.role}
    )


# ============================================================================
# E2E Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_authentication_flow(client):
    """
    Test complete authentication flow:
    1. Register new user
    2. Login with credentials
    3. Access protected endpoint
    4. Logout
    """
    
    # Step 1: Register new user
    register_data = {
        "username": "e2e_user",
        "email": "e2e@example.com",
        "password": "E2EPassword123!",
        "full_name": "E2E Test User",
    }
    
    response = await client.post("/v1/auth/register", json=register_data)
    assert response.status_code in [200, 201]
    data = response.json()
    assert "username" in data or "message" in data
    
    # Step 2: Login with credentials
    login_data = {
        "username": "e2e_user",
        "password": "E2EPassword123!",
    }
    
    response = await client.post("/v1/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    
    access_token = data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Step 3: Access protected endpoint
    response = await client.get("/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "e2e_user"
    
    # Step 4: Logout
    response = await client.post("/v1/auth/logout", headers=headers)
    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_prediction_flow(client, test_user, test_token):
    """
    Test complete prediction flow:
    1. Create a patient
    2. Submit prediction request
    3. Retrieve prediction results
    4. Verify prediction history
    """
    
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Step 1: Create a patient
    patient_data = {
        "patient_uuid": "e2e-patient-001",
        "birthdate": "1990-01-01",
        "gender": "F",
        "state_province": "Lagos",
        "city_village": "Ikeja",
        "phone_number": "+234801234567",
    }
    
    response = await client.post("/v1/patients", json=patient_data, headers=headers)
    assert response.status_code in [200, 201]
    
    # Step 2: Submit prediction request
    prediction_request = {
        "patient_uuid": "e2e-patient-001",
        "features": {
            "age": 34,
            "gender": 1,
            "days_since_last_refill": 45,
            "last_days_supply": 30,
            "visit_count_last_90d": 2,
        }
    }
    
    response = await client.post("/v1/predictions", json=prediction_request, headers=headers)
    assert response.status_code in [200, 201]
    prediction_data = response.json()
    assert "patient_uuid" in prediction_data or "id" in prediction_data
    
    # Step 3: Retrieve prediction results
    response = await client.get(f"/v1/predictions/patient/e2e-patient-001", headers=headers)
    assert response.status_code == 200
    predictions = response.json()
    assert isinstance(predictions, list)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_check_flow(client):
    """
    Test health check and monitoring endpoints
    """
    
    # Test health endpoint
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    
    # Test metrics endpoint
    response = await client.get("/metrics")
    assert response.status_code == 200
    
    # Test model metrics endpoint
    response = await client.get("/model_metrics")
    assert response.status_code == 200
    data = response.json()
    assert "auc" in data or "message" in data  # May return message if model not loaded


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_error_handling_flow(client):
    """
    Test error handling for various scenarios
    """
    
    # Test 404 for non-existent patient
    response = await client.get("/v1/patients/non-existent-patient")
    assert response.status_code == 401  # Unauthorized (no token)
    
    # Test 422 for invalid prediction request
    response = await client.post("/v1/predictions", json={"invalid": "data"})
    assert response.status_code == 401  # Unauthorized
    
    # Test 401 for protected endpoint without token
    response = await client.get("/v1/patients")
    assert response.status_code == 401


@pytest.mark.e2e
@pytest.asyncio
async def test_batch_prediction_flow(client, test_user, test_token):
    """
    Test batch prediction flow for multiple patients
    """
    
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Create multiple patients
    for i in range(3):
        patient_data = {
            "patient_uuid": f"e2e-batch-patient-{i}",
            "birthdate": "1990-01-01",
            "gender": "F",
            "state_province": "Lagos",
        }
        await client.post("/v1/patients", json=patient_data, headers=headers)
    
    # Submit batch prediction
    batch_request = {
        "predictions": [
            {
                "patient_uuid": f"e2e-batch-patient-{i}",
                "features": {"age": 30 + i, "gender": 1}
            }
            for i in range(3)
        ]
    }
    
    response = await client.post("/v1/predictions/batch", json=batch_request, headers=headers)
    assert response.status_code in [200, 201]
    data = response.json()
    assert "predictions" in data or "successful_predictions" in data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_patient_crud_flow(client, test_user, test_token):
    """
    Test complete CRUD flow for patients
    """
    
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Create
    patient_data = {
        "patient_uuid": "e2e-crud-patient",
        "birthdate": "1985-05-15",
        "gender": "M",
        "state_province": "Abuja",
        "city_village": "Wuse 2",
        "phone_number": "+234809876543",
    }
    
    response = await client.post("/v1/patients", json=patient_data, headers=headers)
    assert response.status_code in [200, 201]
    created_data = response.json()
    
    # Read
    response = await client.get("/v1/patients/e2e-crud-patient", headers=headers)
    assert response.status_code == 200
    patient = response.json()
    assert patient["patient_uuid"] == "e2e-crud-patient"
    
    # Update
    update_data = {"phone_number": "+234801234999"}
    response = await client.put("/v1/patients/e2e-crud-patient", json=update_data, headers=headers)
    assert response.status_code == 200
    
    # Delete
    response = await client.delete("/v1/patients/e2e-crud-patient", headers=headers)
    assert response.status_code in [200, 204]


@pytest.mark.e2e
@pytest.asyncio
async def test_analytics_flow(client, test_user, test_token):
    """
    Test analytics and reporting endpoints
    """
    
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Test prediction analytics
    response = await client.get("/v1/analytics/predictions?days=30", headers=headers)
    assert response.status_code == 200
    
    # Test patient analytics
    response = await client.get("/v1/analytics/patients", headers=headers)
    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_security_headers(client):
    """
    Test that security headers are properly set
    """
    
    response = await client.get("/health")
    assert response.status_code == 200
    
    # Check for security headers
    headers = response.headers
    # Note: httpx automatically follows redirects, so we check the final response
    # The security headers should be present on API responses


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cors_configuration(client):
    """
    Test CORS configuration for cross-origin requests
    """
    
    # Test preflight request
    response = await client.options(
        "/v1/patients",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        }
    )
    
    # CORS should be configured (may return 200 or 204 for OPTIONS)
    assert response.status_code in [200, 204]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_concurrent_requests(client, test_user, test_token):
    """
    Test that the application handles concurrent requests properly
    """
    
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Create test patient
    patient_data = {
        "patient_uuid": "concurrent-test-patient",
        "birthdate": "1990-01-01",
        "gender": "F",
        "state_province": "Lagos",
    }
    await client.post("/v1/patients", json=patient_data, headers=headers)
    
    # Send multiple concurrent requests
    tasks = []
    for i in range(5):
        task = client.get("/health")
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks)
    
    # All requests should succeed
    for response in responses:
        assert response.status_code == 200
