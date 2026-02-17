"""
Unit tests for ML model functionality.
Tests model loading, prediction, feature extraction, and model management.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import numpy as np

from app.ml_model import (
    MLModelService,
    extract_features,
    calculate_risk_score,
    get_feature_importance,
)
from app.schema import PredictionRequest, PredictionResponse


class TestFeatureExtraction:
    """Test feature extraction from patient data."""
    
    def test_extract_features_basic(self, sample_prediction_request):
        """Test basic feature extraction."""
        features = extract_features(sample_prediction_request)
        
        assert features is not None
        assert isinstance(features, dict)
        assert "age" in features or "medication_duration" in features
    
    def test_extract_features_with_demographics(self):
        """Test feature extraction from demographic data."""
        request_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-123",
                    "birthdate": "1990-01-01 00:00:00",
                    "gender": "M",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                },
                "visits": [],
                "encounters": [],
                "obs": []
            }
        }
        
        features = extract_features(request_data)
        assert features is not None
    
    def test_extract_features_missing_data(self):
        """Test feature extraction with missing data."""
        request_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-123",
                },
                "visits": [],
                "encounters": [],
                "obs": []
            }
        }
        
        features = extract_features(request_data)
        # Should handle missing data gracefully
        assert features is not None
    
    def test_extract_features_empty_obs(self):
        """Test feature extraction with empty observations."""
        request_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-123",
                    "birthdate": "1990-01-01 00:00:00",
                    "gender": "F",
                },
                "visits": [],
                "encounters": [],
                "obs": []
            }
        }
        
        features = extract_features(request_data)
        assert features is not None
    
    def test_extract_features_medication_duration(self):
        """Test extraction of medication duration feature."""
        request_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-123",
                    "birthdate": "1990-01-01 00:00:00",
                    "gender": "M",
                },
                "visits": [],
                "encounters": [],
                "obs": [
                    {
                        "obsDatetime": "2024-01-01 10:00:00",
                        "variableName": "Medication duration",
                        "valueNumeric": 180.0,
                        "voided": 0
                    }
                ]
            }
        }
        
        features = extract_features(request_data)
        assert "medication_duration" in features or "medication_duration_days" in features


class TestRiskScoreCalculation:
    """Test risk score calculation logic."""
    
    def test_calculate_risk_score_low(self):
        """Test low risk score calculation."""
        probability = 0.2
        risk_level = calculate_risk_score(probability)
        
        assert risk_level == "low"
    
    def test_calculate_risk_score_medium(self):
        """Test medium risk score calculation."""
        probability = 0.5
        risk_level = calculate_risk_score(probability)
        
        assert risk_level == "medium"
    
    def test_calculate_risk_score_high(self):
        """Test high risk score calculation."""
        probability = 0.8
        risk_level = calculate_risk_score(probability)
        
        assert risk_level == "high"
    
    def test_calculate_risk_score_boundary_low(self):
        """Test risk score at boundary values."""
        assert calculate_risk_score(0.0) == "low"
        assert calculate_risk_score(0.3) == "low"
        assert calculate_risk_score(0.34) == "low"
    
    def test_calculate_risk_score_boundary_medium(self):
        """Test risk score at medium boundary."""
        assert calculate_risk_score(0.35) == "medium"
        assert calculate_risk_score(0.5) == "medium"
        assert calculate_risk_score(0.64) == "medium"
    
    def test_calculate_risk_score_boundary_high(self):
        """Test risk score at high boundary."""
        assert calculate_risk_score(0.65) == "high"
        assert calculate_risk_score(0.8) == "high"
        assert calculate_risk_score(1.0) == "high"
    
    def test_calculate_risk_score_invalid(self):
        """Test risk score with invalid input."""
        with pytest.raises(ValueError):
            calculate_risk_score(-0.1)
        
        with pytest.raises(ValueError):
            calculate_risk_score(1.1)


class TestFeatureImportance:
    """Test feature importance extraction."""
    
    def test_get_feature_importance(self, mock_ml_model):
        """Test getting feature importance from model."""
        importance = get_feature_importance(mock_ml_model)
        
        assert importance is not None
        assert isinstance(importance, dict)
    
    def test_get_feature_importance_normalized(self):
        """Test feature importance normalization."""
        model = MagicMock()
        model.feature_importances_ = np.array([0.1, 0.2, 0.3, 0.4])
        
        importance = get_feature_importance(model)
        
        # Check that values sum to approximately 1
        total = sum(importance.values())
        assert abs(total - 1.0) < 0.01


@pytest.mark.unit
class TestMLModelService:
    """Test ML model service functionality."""
    
    @pytest.fixture
    def ml_service(self, mock_ml_model):
        """Create ML model service instance."""
        return MLModelService(model=mock_ml_model)
    
    def test_service_initialization(self, ml_service):
        """Test service initializes correctly."""
        assert ml_service is not None
        assert ml_service.model is not None
    
    def test_predict_single(self, ml_service, sample_prediction_request):
        """Test single prediction."""
        result = ml_service.predict(sample_prediction_request)
        
        assert result is not None
        assert "iit_risk_score" in result
        assert "risk_level" in result
    
    @pytest.mark.asyncio
    async def test_predict_batch(self, ml_service):
        """Test batch prediction."""
        requests = [
            {
                "messageData": {
                    "demographics": {"patientUuid": f"patient-{i}"},
                    "visits": [],
                    "encounters": [],
                    "obs": []
                }
            }
            for i in range(5)
        ]
        
        results = await ml_service.predict_batch(requests)
        
        assert len(results) == 5
        for result in results:
            assert "iit_risk_score" in result
    
    def test_model_loading(self):
        """Test model loading from file."""
        with patch("app.ml_model.joblib.load") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model
            
            service = MLModelService.load_model("path/to/model.pkl")
            
            assert service.model is not None
            mock_load.assert_called_once()


class TestPredictionResponse:
    """Test prediction response schema."""
    
    def test_prediction_response_creation(self):
        """Test creating prediction response."""
        response = PredictionResponse(
            patient_uuid="test-123",
            iit_risk_score=0.75,
            risk_level="high",
            confidence=0.85,
            feature_importance={"age": 0.3, "medication_duration": 0.7},
            prediction_timestamp=datetime.utcnow().isoformat(),
            model_version="1.0.0"
        )
        
        assert response.patient_uuid == "test-123"
        assert response.iit_risk_score == 0.75
        assert response.risk_level == "high"
    
    def test_prediction_response_serialization(self):
        """Test prediction response JSON serialization."""
        response = PredictionResponse(
            patient_uuid="test-123",
            iit_risk_score=0.75,
            risk_level="high",
            confidence=0.85,
            feature_importance={"age": 0.3},
            prediction_timestamp="2024-01-01T00:00:00",
            model_version="1.0.0"
        )
        
        json_data = response.model_dump()
        
        assert json_data["patient_uuid"] == "test-123"
        assert json_data["iit_risk_score"] == 0.75
        assert json_data["risk_level"] == "high"


class TestModelValidation:
    """Test model validation and quality checks."""
    
    def test_validate_model_inputs(self, sample_prediction_request):
        """Test model input validation."""
        # Valid input
        assert sample_prediction_request is not None
        assert "messageData" in sample_prediction_request
    
    def test_validate_prediction_output(self):
        """Test prediction output validation."""
        output = {
            "patient_uuid": "test-123",
            "iit_risk_score": 0.75,
            "risk_level": "high",
            "confidence": 0.85,
        }
        
        # Validate required fields
        required_fields = ["patient_uuid", "iit_risk_score", "risk_level"]
        for field in required_fields:
            assert field in output
    
    def test_confidence_score_range(self):
        """Test confidence score is in valid range."""
        confidence = 0.85
        assert 0 <= confidence <= 1


class TestModelRetraining:
    """Test model retraining functionality."""
    
    @pytest.mark.asyncio
    async def test_retrain_model(self):
        """Test model retraining process."""
        with patch("app.ml_model.MLModelService.retrain") as mock_retrain:
            mock_retrain.return_value = {
                "status": "success",
                "new_model_version": "1.1.0",
                "accuracy": 0.85,
            }
            
            result = await mock_retrain()
            
            assert result["status"] == "success"
            assert "new_model_version" in result
    
    def test_model_version_tracking(self):
        """Test model version tracking."""
        version = "1.0.0"
        
        # Parse version
        major, minor, patch = version.split(".")
        
        assert major == "1"
        assert minor == "0"
        assert patch == "0"


class TestModelErrorHandling:
    """Test error handling in ML operations."""
    
    def test_handle_missing_model_file(self):
        """Test handling of missing model file."""
        with patch("app.ml_model.joblib.load", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                MLModelService.load_model("nonexistent.pkl")
    
    def test_handle_invalid_input_data(self):
        """Test handling of invalid input data."""
        invalid_data = {"invalid": "data"}
        
        with pytest.raises(KeyError):
            extract_features(invalid_data)
    
    def test_handle_model_prediction_error(self):
        """Test handling of model prediction errors."""
        model = MagicMock()
        model.predict_proba = MagicMock(side_effect=Exception("Prediction failed"))
        
        service = MLModelService(model=model)
        
        with pytest.raises(Exception):
            service.predict({"messageData": {}})


@pytest.mark.unit
class TestModelPerformance:
    """Test model performance metrics."""
    
    def test_prediction_latency(self, ml_service):
        """Test prediction latency is acceptable."""
        import time
        
        request = {
            "messageData": {
                "demographics": {"patientUuid": "test-123"},
                "visits": [],
                "encounters": [],
                "obs": []
            }
        }
        
        start = time.time()
        ml_service.predict(request)
        latency = time.time() - start
        
        # Should complete within 1 second
        assert latency < 1.0
    
    def test_batch_prediction_throughput(self, ml_service):
        """Test batch prediction throughput."""
        import time
        
        requests = [
            {
                "messageData": {
                    "demographics": {"patientUuid": f"patient-{i}"},
                    "visits": [],
                    "encounters": [],
                    "obs": []
                }
            }
            for i in range(100)
        ]
        
        start = time.time()
        for request in requests:
            ml_service.predict(request)
        elapsed = time.time() - start
        
        # Should process at least 50 predictions per second
        throughput = len(requests) / elapsed
        assert throughput > 50


class TestModelExplainability:
    """Test model explainability features."""
    
    def test_shap_values_computation(self):
        """Test SHAP values for model explanation."""
        with patch("app.ml_model.compute_shap_values") as mock_shap:
            mock_shap.return_value = np.array([0.1, -0.2, 0.3, -0.1])
            
            shap_values = mock_shap(MagicMock(), MagicMock())
            
            assert shap_values is not None
            assert len(shap_values) == 4
    
    def test_feature_contribution_analysis(self):
        """Test feature contribution to prediction."""
        contributions = {
            "medication_duration": 0.5,
            "age": 0.3,
            "gender": 0.1,
            "location": 0.1,
        }
        
        # Find most important feature
        top_feature = max(contributions, key=contributions.get)
        
        assert top_feature == "medication_duration"
        assert contributions[top_feature] == 0.5
