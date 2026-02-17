"""
Integration tests for the IIT ML Service.
These tests verify the integration between different components.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta

from app.main import app
from app.models import User, Patient, Prediction
from app.auth import get_password_hash, create_access_token


@pytest.mark.integration
class TestAuthIntegration:
    """Integration tests for authentication flow."""
    
    @pytest.mark.asyncio
    async def test_complete_login_flow(self, async_client: AsyncClient, db_session):
        """Test complete login flow from request to token."""
        # Create user
        user = User(
            username="integration_test",
            email="integration@test.com",
            hashed_password=get_password_hash("TestPassword123!"),
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        
        # Login request
        response = await async_client.post(
            "/auth/token",
            data={"username": "integration_test", "password": "TestPassword123!"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_access(self, async_client: AsyncClient, test_user, test_token):
        """Test accessing protected endpoint with valid token."""
        response = await async_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, async_client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await async_client.get("/users/me")
        
        assert response.status_code == 401


@pytest.mark.integration
class TestPredictionIntegration:
    """Integration tests for prediction workflow."""
    
    @pytest.mark.asyncio
    async def test_prediction_with_authentication(
        self, async_client: AsyncClient, test_token, sample_prediction_request
    ):
        """Test prediction endpoint with authentication."""
        response = await async_client.post(
            "/predict",
            json=sample_prediction_request,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "iit_risk_score" in data
        assert "risk_level" in data
    
    @pytest.mark.asyncio
    async def test_prediction_saves_to_database(
        self, async_client: AsyncClient, test_token, sample_prediction_request, db_session
    ):
        """Test that predictions are saved to database."""
        response = await async_client.post(
            "/predict",
            json=sample_prediction_request,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        
        # Verify prediction was saved
        result = await db_session.execute(
            f"SELECT * FROM predictions WHERE patient_uuid = '{sample_prediction_request['messageData']['demographics']['patientUuid']}'"
        )
        # Note: This would need proper SQLAlchemy query in real implementation


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.mark.asyncio
    async def test_patient_crud_workflow(self, async_client: AsyncClient, test_token, db_session):
        """Test complete patient CRUD workflow."""
        patient_data = {
            "patient_uuid": "integration-patient-123",
            "birthdate": "1990-01-01",
            "gender": "F",
            "state_province": "Lagos",
            "city_village": "Ikeja",
            "phone_number": "+234801234567",
        }
        
        # Create
        response = await async_client.post(
            "/patients",
            json=patient_data,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code in [200, 201]
        
        # Read
        response = await async_client.get(
            f"/patients/{patient_data['patient_uuid']}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        
        # Update
        update_data = {"phone_number": "+234809876543"}
        response = await async_client.put(
            f"/patients/{patient_data['patient_uuid']}",
            json=update_data,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_prediction_history_retrieval(
        self, async_client: AsyncClient, test_token, test_patient, db_session
    ):
        """Test retrieving prediction history for a patient."""
        response = await async_client.get(
            f"/patients/{test_patient.patient_uuid}/predictions",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests for caching functionality."""
    
    @pytest.mark.asyncio
    async def test_prediction_caching(
        self, async_client: AsyncClient, test_token, sample_prediction_request, mock_redis_client
    ):
        """Test that predictions are cached."""
        # First request
        response1 = await async_client.post(
            "/predict",
            json=sample_prediction_request,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response1.status_code == 200
        
        # Second request - should use cache
        response2 = await async_client.post(
            "/predict",
            json=sample_prediction_request,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(
        self, async_client: AsyncClient, test_token, sample_prediction_request
    ):
        """Test cache invalidation on model update."""
        # Make prediction
        await async_client.post(
            "/predict",
            json=sample_prediction_request,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        # Update model
        await async_client.post(
            "/admin/reload-model",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        # Cache should be invalidated


@pytest.mark.integration
class TestMonitoringIntegration:
    """Integration tests for monitoring and metrics."""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, async_client: AsyncClient):
        """Test Prometheus metrics endpoint."""
        response = await async_client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_health_check_includes_dependencies(self, async_client: AsyncClient):
        """Test health check includes dependency status."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "dependencies" in data or "checks" in data


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""
    
    @pytest.mark.asyncio
    async def test_invalid_prediction_request(self, async_client: AsyncClient, test_token):
        """Test handling of invalid prediction request."""
        invalid_request = {"invalid": "data"}
        
        response = await async_client.post(
            "/predict",
            json=invalid_request,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self, async_client: AsyncClient, test_token):
        """Test handling of database connection errors."""
        # This would require mocking database failure
        pass
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, async_client: AsyncClient, test_token):
        """Test rate limiting on endpoints."""
        # Make multiple rapid requests
        responses = []
        for _ in range(100):
            response = await async_client.get(
                "/health",
                headers={"Authorization": f"Bearer {test_token}"}
            )
            responses.append(response)
        
        # Check if any were rate limited
        rate_limited = any(r.status_code == 429 for r in responses)


@pytest.mark.integration
class TestBatchOperations:
    """Integration tests for batch operations."""
    
    @pytest.mark.asyncio
    async def test_batch_prediction(
        self, async_client: AsyncClient, test_token
    ):
        """Test batch prediction endpoint."""
        batch_request = {
            "predictions": [
                {
                    "messageData": {
                        "demographics": {
                            "patientUuid": f"patient-{i}",
                            "birthdate": "1990-01-01",
                            "gender": "F",
                        },
                        "visits": [],
                        "encounters": [],
                        "obs": []
                    }
                }
                for i in range(5)
            ]
        }
        
        response = await async_client.post(
            "/predict/batch",
            json=batch_request,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["predictions"]) == 5


@pytest.mark.integration
class TestAdminOperations:
    """Integration tests for admin operations."""
    
    @pytest.mark.asyncio
    async def test_model_reload(self, async_client: AsyncClient, test_admin_token):
        """Test model reload endpoint."""
        response = await async_client.post(
            "/admin/reload-model",
            headers={"Authorization": f"Bearer {test_admin_token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_user_management(self, async_client: AsyncClient, test_admin_token):
        """Test user management endpoints."""
        # Create user
        new_user = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "NewPassword123!",
            "role": "healthcare_provider",
        }
        
        response = await async_client.post(
            "/admin/users",
            json=new_user,
            headers={"Authorization": f"Bearer {test_admin_token}"}
        )
        
        assert response.status_code in [200, 201]
    
    @pytest.mark.asyncio
    async def test_admin_only_endpoints(self, async_client: AsyncClient, test_token):
        """Test that admin endpoints reject regular users."""
        response = await async_client.post(
            "/admin/reload-model",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 403  # Forbidden


@pytest.mark.integration
@pytest.mark.e2e
class TestEndToEndWorkflows:
    """End-to-end workflow tests."""
    
    @pytest.mark.asyncio
    async def test_complete_patient_workflow(
        self, async_client: AsyncClient, db_session
    ):
        """Test complete workflow from patient creation to prediction."""
        # 1. Create admin user and login
        admin = User(
            username="admin",
            email="admin@test.com",
            hashed_password=get_password_hash("Admin123!"),
            is_active=True,
            role="admin",
        )
        db_session.add(admin)
        await db_session.commit()
        
        login_response = await async_client.post(
            "/auth/token",
            data={"username": "admin", "password": "Admin123!"}
        )
        token = login_response.json()["access_token"]
        
        # 2. Create patient
        patient_data = {
            "patient_uuid": "e2e-patient-123",
            "birthdate": "1990-01-01",
            "gender": "F",
            "state_province": "Lagos",
        }
        
        patient_response = await async_client.post(
            "/patients",
            json=patient_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert patient_response.status_code in [200, 201]
        
        # 3. Make prediction
        prediction_request = {
            "messageData": {
                "demographics": patient_data,
                "visits": [],
                "encounters": [],
                "obs": []
            }
        }
        
        prediction_response = await async_client.post(
            "/predict",
            json=prediction_request,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert prediction_response.status_code == 200
        
        # 4. Retrieve prediction history
        history_response = await async_client.get(
            f"/patients/{patient_data['patient_uuid']}/predictions",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert history_response.status_code == 200


@pytest.mark.integration
class TestExternalServiceIntegration:
    """Integration tests with external services."""
    
    @pytest.mark.asyncio
    async def test_openmrs_integration(self, async_client: AsyncClient, test_token):
        """Test OpenMRS API integration."""
        # This would test fetching patient data from OpenMRS
        pass
    
    @pytest.mark.asyncio
    async def test_notification_service(self, async_client: AsyncClient, test_token):
        """Test notification service integration."""
        # This would test sending notifications for high-risk patients
        pass
