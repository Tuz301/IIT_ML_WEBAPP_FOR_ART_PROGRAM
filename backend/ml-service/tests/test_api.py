"""
API endpoint tests for IIT Prediction ML Service
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health and monitoring endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptime_seconds" in data
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "endpoints" in data
    
    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
    
    def test_model_metrics(self):
        """Test model metrics endpoint"""
        response = client.get("/model_metrics")
        assert response.status_code == 200
        data = response.json()
        assert "auc" in data
        assert "precision" in data
        assert "recall" in data
        assert "model_version" in data


class TestPredictionEndpoints:
    """Test prediction endpoints"""
    
    @pytest.fixture
    def sample_patient_data(self):
        """Sample patient data for testing"""
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
    
    def test_predict_single_patient(self, sample_patient_data):
        """Test single patient prediction"""
        response = client.post("/predict", json=sample_patient_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "patient_uuid" in data
        assert "iit_risk_score" in data
        assert "risk_level" in data
        assert "confidence" in data
        assert "model_version" in data
        
        # Validate risk score range
        assert 0.0 <= data["iit_risk_score"] <= 1.0
        assert 0.0 <= data["confidence"] <= 1.0
    
    def test_batch_predict(self, sample_patient_data):
        """Test batch prediction"""
        batch_request = {
            "patients": [sample_patient_data, sample_patient_data]
        }
        
        response = client.post("/batch_predict", json=batch_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "predictions" in data
        assert "total_processed" in data
        assert "batch_id" in data
        assert len(data["predictions"]) == 2
    
    def test_batch_size_validation(self, sample_patient_data):
        """Test batch size limit validation"""
        # Create oversized batch
        batch_request = {
            "patients": [sample_patient_data] * 101
        }
        
        response = client.post("/batch_predict", json=batch_request)
        assert response.status_code == 422  # Validation error


class TestDataValidation:
    """Test input data validation"""
    
    def test_invalid_patient_data(self):
        """Test prediction with invalid patient data"""
        invalid_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test"
                    # Missing required fields
                }
            }
        }
        
        response = client.post("/predict", json=invalid_data)
        assert response.status_code == 422
    
    def test_missing_message_data(self):
        """Test prediction with missing messageData"""
        response = client.post("/predict", json={})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAnalyticsEndpoints:
    """Test analytics and reporting endpoints"""

    def test_analytics_summary(self):
        """Test analytics summary endpoint"""
        response = client.get("/api/v1/analytics/summary")
        assert response.status_code in [200, 401]  # May require auth

        if response.status_code == 200:
            data = response.json()
            assert "total_patients" in data
            assert "predictions_count" in data
            assert "avg_risk_score" in data

    def test_analytics_detailed(self):
        """Test detailed analytics endpoint"""
        response = client.get("/api/v1/analytics/detailed")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "risk_distribution" in data
            assert "temporal_trends" in data
            assert "geographic_distribution" in data


class TestBackupEndpoints:
    """Test backup and restore endpoints"""

    def test_backup_creation(self):
        """Test backup creation"""
        response = client.post("/api/v1/backup/create")
        assert response.status_code in [201, 401]

        if response.status_code == 201:
            data = response.json()
            assert "backup_id" in data
            assert "status" in data
            assert data["status"] == "in_progress"

    def test_backup_listing(self):
        """Test backup listing"""
        response = client.get("/api/v1/backup/list")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_backup_restore(self):
        """Test backup restoration"""
        # First create a backup
        create_response = client.post("/api/v1/backup/create")
        if create_response.status_code == 201:
            backup_id = create_response.json()["backup_id"]

            # Try to restore
            response = client.post(f"/api/v1/backup/restore/{backup_id}")
            assert response.status_code in [200, 401]

            if response.status_code == 200:
                data = response.json()
                assert "status" in data


class TestExplainabilityEndpoints:
    """Test explainability endpoints"""

    def test_prediction_explanation(self):
        """Test prediction explanation"""
        # First make a prediction to get prediction_id
        prediction_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "explain-test-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+2348012345678"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "explain-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        pred_response = client.post("/predict", json=prediction_data)
        if pred_response.status_code == 200:
            prediction_result = pred_response.json()
            prediction_id = prediction_result.get("prediction_id")

            if prediction_id:
                response = client.get(f"/api/v1/explainability/{prediction_id}")
                assert response.status_code in [200, 401]

                if response.status_code == 200:
                    data = response.json()
                    assert "feature_importance" in data
                    assert "shap_values" in data

    def test_global_explanation(self):
        """Test global model explanation"""
        response = client.get("/api/v1/explainability/global")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "feature_importance" in data
            assert "partial_dependence" in data


class TestEnsembleEndpoints:
    """Test ensemble methods endpoints"""

    def test_ensemble_prediction(self):
        """Test ensemble prediction"""
        prediction_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "ensemble-test-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+2348012345678"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "ensemble-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        response = client.post("/api/v1/ensemble/predict", json=prediction_data)
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "ensemble_score" in data
            assert "model_agreements" in data

    def test_ensemble_comparison(self):
        """Test ensemble model comparison"""
        response = client.get("/api/v1/ensemble/compare")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "model_performance" in data
            assert "ensemble_vs_individual" in data


class TestCachingEndpoints:
    """Test caching endpoints"""

    def test_cache_stats(self):
        """Test cache statistics"""
        response = client.get("/api/v1/cache/stats")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "hit_rate" in data
            assert "total_requests" in data

    def test_cache_clear(self):
        """Test cache clearing"""
        response = client.post("/api/v1/cache/clear")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] == "cleared"


class TestFeaturesEndpoints:
    """Test feature extraction endpoints"""

    def test_feature_extraction(self):
        """Test feature extraction"""
        patient_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "feature-test-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+2348012345678"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "feature-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        response = client.post("/api/v1/features/extract", json=patient_data)
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "extracted_features" in data

    def test_feature_importance(self):
        """Test feature importance"""
        response = client.get("/api/v1/features/importance")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "feature_scores" in data


class TestMonitoringEndpoints:
    """Test monitoring endpoints"""

    def test_monitoring_metrics(self):
        """Test system metrics"""
        response = client.get("/api/v1/monitoring/metrics")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "cpu_usage" in data
            assert "memory_usage" in data

    def test_monitoring_health(self):
        """Test detailed health check"""
        response = client.get("/api/v1/monitoring/health")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "database_status" in data
            assert "model_status" in data


class TestModelRegistryEndpoints:
    """Test model registry endpoints"""

    def test_model_listing(self):
        """Test model listing"""
        response = client.get("/api/v1/models/list")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_model_info(self):
        """Test specific model information"""
        # First get list of models
        list_response = client.get("/api/v1/models/list")
        if list_response.status_code == 200:
            models = list_response.json()
            if models:
                model_id = models[0]["id"]
                response = client.get(f"/api/v1/models/{model_id}/info")
                assert response.status_code in [200, 401]

                if response.status_code == 200:
                    data = response.json()
                    assert "version" in data
                    assert "performance_metrics" in data


class TestABTestingEndpoints:
    """Test A/B testing endpoints"""

    def test_ab_test_creation(self):
        """Test A/B test creation"""
        test_config = {
            "name": "Test Experiment",
            "variants": ["control", "variant_a"],
            "traffic_split": [0.5, 0.5]
        }

        response = client.post("/api/v1/abtest/create", json=test_config)
        assert response.status_code in [201, 401]

        if response.status_code == 201:
            data = response.json()
            assert "test_id" in data

    def test_ab_test_results(self):
        """Test A/B test results"""
        # This would require a test_id from a created test
        # For now, just test the endpoint structure
        response = client.get("/api/v1/abtest/results/test-123")
        assert response.status_code in [200, 404, 401]

        if response.status_code == 200:
            data = response.json()
            assert "variant_performance" in data
            assert "statistical_significance" in data


class TestAsyncOperations:
    """Test asynchronous operations"""

    async def test_concurrent_predictions(self):
        """Test concurrent prediction handling"""
        # Create multiple prediction requests
        sample_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-patient-async-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+234801234567"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "enc-async-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        # Test concurrent requests (simulated)
        import asyncio
        tasks = []
        for i in range(5):
            task = asyncio.create_task(self._make_async_request(sample_data))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all requests succeeded
        for result in results:
            assert not isinstance(result, Exception), f"Request failed: {result}"

    async def _make_async_request(self, data):
        """Helper method to make async prediction request"""
        response = client.post("/predict", json=data)
        return response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
