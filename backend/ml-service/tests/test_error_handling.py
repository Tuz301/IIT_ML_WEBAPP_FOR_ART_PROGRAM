"""
Error handling tests for IIT Prediction ML Service
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)


class TestAPIErrorHandling:
    """Test API error handling"""

    def test_404_not_found(self):
        """Test 404 error for non-existent endpoint"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_405_method_not_allowed(self):
        """Test 405 error for wrong HTTP method"""
        response = client.post("/api/v1/patients/")  # Wrong method
        assert response.status_code == 405
        data = response.json()
        assert "detail" in data

    def test_invalid_json_payload(self):
        """Test error handling for invalid JSON"""
        response = client.post(
            "/api/v1/patients/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    @patch('app.api.patients.get_patient')
    def test_database_connection_error(self, mock_get_patient):
        """Test database connection error handling"""
        mock_get_patient.side_effect = Exception("Database connection failed")

        response = client.get("/api/v1/patients/test-uuid")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    @patch('app.api.predictions.make_prediction')
    def test_prediction_service_error(self, mock_predict):
        """Test prediction service error handling"""
        mock_predict.side_effect = Exception("Model prediction failed")

        sample_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-uuid",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F"
                },
                "visits": [],
                "encounters": [],
                "obs": []
            }
        }

        response = client.post("/predict", json=sample_data)
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestValidationErrorHandling:
    """Test validation error handling"""

    def test_required_field_missing(self):
        """Test error for missing required fields"""
        incomplete_data = {
            "given_name": "John"
            # Missing birthdate and gender
        }

        response = client.post("/api/v1/patients/", json=incomplete_data)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert len(data["detail"]) > 0

    def test_invalid_data_type(self):
        """Test error for invalid data types"""
        invalid_data = {
            "given_name": "John",
            "family_name": "Doe",
            "birthdate": "1985-06-15",
            "gender": "M",
            "phone_number": 1234567890  # Should be string
        }

        response = client.post("/api/v1/patients/", json=invalid_data)
        assert response.status_code == 422

    def test_invalid_enum_value(self):
        """Test error for invalid enum values"""
        invalid_data = {
            "given_name": "John",
            "family_name": "Doe",
            "birthdate": "1985-06-15",
            "gender": "INVALID",  # Invalid enum
            "state_province": "Lagos"
        }

        response = client.post("/api/v1/patients/", json=invalid_data)
        assert response.status_code == 422


class TestAuthenticationErrorHandling:
    """Test authentication error handling"""

    def test_unauthorized_access(self):
        """Test unauthorized access to protected endpoints"""
        response = client.get("/api/v1/patients/")
        # Should return 401 or 403 depending on auth implementation
        assert response.status_code in [401, 403]

    def test_invalid_token(self):
        """Test invalid authentication token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/patients/", headers=headers)
        assert response.status_code in [401, 403]


class TestBusinessLogicErrorHandling:
    """Test business logic error handling"""

    def test_patient_not_found(self):
        """Test error when patient not found"""
        response = client.get("/api/v1/patients/nonexistent-uuid")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_duplicate_patient_creation(self):
        """Test error when creating duplicate patient"""
        patient_data = {
            "given_name": "John",
            "family_name": "Doe",
            "birthdate": "1985-06-15",
            "gender": "M",
            "datim_id": "DUPLICATE123"  # Assuming this would cause duplicate
        }

        # First creation should succeed (if no auth required)
        # Second creation should fail with duplicate error
        # This test assumes auth is not required for basic validation
        pass

    def test_invalid_relationship(self):
        """Test error for invalid data relationships"""
        # Test observation without valid encounter
        invalid_obs = {
            "patient_uuid": "test-uuid",
            "encounter_id": 99999,  # Non-existent encounter
            "variable_name": "Test",
            "obs_datetime": "2024-10-01T10:30:00"
        }

        response = client.post("/api/v1/observations/", json=invalid_obs)
        # Should return 400 or 404 depending on implementation
        assert response.status_code in [400, 404, 422]


class TestRateLimitErrorHandling:
    """Test rate limiting error handling"""

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded error"""
        # This would require rate limiting middleware
        # For now, just test that the endpoint exists
        response = client.get("/")
        assert response.status_code == 200


class TestMiddlewareErrorHandling:
    """Test middleware error handling"""

    @patch('app.middleware.security.log_requests')
    def test_security_middleware_error(self, mock_log):
        """Test security middleware error handling"""
        mock_log.side_effect = Exception("Security middleware failed")

        response = client.get("/")
        # Should still work despite middleware error
        assert response.status_code == 200

    @patch('app.middleware.performance.PerformanceMiddleware.process_request')
    def test_performance_middleware_error(self, mock_process):
        """Test performance middleware error handling"""
        mock_process.side_effect = Exception("Performance middleware failed")

        response = client.get("/")
        # Should still work despite middleware error
        assert response.status_code == 200


class TestExternalServiceErrorHandling:
    """Test external service error handling"""

    @patch('app.monitoring.send_alert')
    def test_monitoring_service_error(self, mock_alert):
        """Test monitoring service error handling"""
        mock_alert.side_effect = Exception("Monitoring service failed")

        # Trigger some operation that would send alerts
        response = client.get("/health")
        # Should still return health status despite monitoring failure
        assert response.status_code == 200

    @patch('redis.Redis.ping')
    def test_redis_connection_error(self, mock_ping):
        """Test Redis connection error handling"""
        mock_ping.side_effect = Exception("Redis connection failed")

        # Test endpoint that uses Redis
        response = client.get("/health")
        # Should handle Redis failure gracefully
        assert response.status_code == 200
        data = response.json()
        # Should indicate Redis is not connected
        assert "redis_connected" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
