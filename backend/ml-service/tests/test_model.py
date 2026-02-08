"""
Unit tests for ML model wrapper and feature extraction
"""
import pytest
from datetime import datetime
import pandas as pd
import numpy as np

from app.ml_model import IITModelPredictor


class TestFeatureExtraction:
    """Test feature extraction logic"""
    
    @pytest.fixture
    def predictor(self):
        """Create predictor instance"""
        return IITModelPredictor()
    
    @pytest.fixture
    def sample_patient_json(self):
        """Sample patient JSON for testing"""
        return {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "M",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+234801234567"
                },
                "visits": [
                    {
                        "dateStarted": "2024-10-01 10:30:00",
                        "voided": 0
                    },
                    {
                        "dateStarted": "2024-09-01 10:30:00",
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
                        "encounterUuid": "enc-123",
                        "voided": 0
                    },
                    {
                        "obsDatetime": "2024-10-01 10:30:00",
                        "variableName": "Viral Load",
                        "valueNumeric": 50.0,
                        "voided": 0
                    }
                ]
            }
        }
    
    def test_extract_demographic_features(self, predictor, sample_patient_json):
        """Test demographic feature extraction"""
        features = predictor.extract_features_from_json(sample_patient_json)
        
        assert "age" in features
        assert "gender" in features
        assert "has_state" in features
        assert "has_phone" in features
        
        assert features["gender"] == 1  # Male
        assert features["has_state"] == 1
        assert features["has_phone"] == 1
        assert features["age"] > 0
    
    def test_extract_pharmacy_features(self, predictor, sample_patient_json):
        """Test pharmacy feature extraction"""
        features = predictor.extract_features_from_json(sample_patient_json)
        
        assert "has_pharmacy_history" in features
        assert "total_dispensations" in features
        assert "last_days_supply" in features
        assert "days_since_last_refill" in features
        
        assert features["has_pharmacy_history"] == 1
        assert features["last_days_supply"] == 90
    
    def test_extract_visit_features(self, predictor, sample_patient_json):
        """Test visit feature extraction"""
        features = predictor.extract_features_from_json(sample_patient_json)
        
        assert "total_visits" in features
        assert "visit_frequency_3m" in features
        assert "days_since_last_visit" in features
        
        assert features["total_visits"] >= 2
    
    def test_extract_clinical_features(self, predictor, sample_patient_json):
        """Test clinical feature extraction"""
        features = predictor.extract_features_from_json(sample_patient_json)
        
        assert "has_vl_data" in features
        assert "recent_vl_tests" in features
        assert "who_stage" in features
        
        assert features["has_vl_data"] == 1
        assert features["recent_vl_tests"] >= 1
    
    def test_extract_temporal_features(self, predictor, sample_patient_json):
        """Test temporal feature extraction"""
        features = predictor.extract_features_from_json(sample_patient_json)
        
        assert "month" in features
        assert "quarter" in features
        assert "day_of_week" in features
        
        assert 1 <= features["month"] <= 12
        assert 0 <= features["quarter"] <= 3
    
    def test_missing_data_handling(self, predictor):
        """Test handling of missing/incomplete data"""
        incomplete_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-456",
                    "birthdate": "1990-01-01 00:00:00",
                    "gender": "F"
                },
                "visits": [],
                "encounters": [],
                "obs": []
            }
        }
        
        features = predictor.extract_features_from_json(incomplete_data)
        
        # Should still extract features with defaults
        assert "age" in features
        assert "has_pharmacy_history" in features
        assert features["has_pharmacy_history"] == 0


class TestModelPrediction:
    """Test model prediction functionality"""
    
    @pytest.fixture
    def predictor(self):
        """Create predictor with loaded model"""
        pred = IITModelPredictor()
        try:
            pred.load_model()
        except:
            pass  # Model may not be present in test environment
        return pred
    
    def test_prediction_output_range(self, predictor):
        """Test prediction output is in valid range"""
        # Create sample feature DataFrame
        sample_features = pd.DataFrame({
            'age': [35],
            'gender': [1],
            'days_since_last_refill': [45],
            'last_days_supply': [30]
        })
        
        predictions = predictor.predict(sample_features)
        
        assert len(predictions) == 1
        assert 0.0 <= predictions[0] <= 1.0
    
    def test_batch_prediction(self, predictor):
        """Test batch prediction"""
        sample_features = pd.DataFrame({
            'age': [35, 42, 28],
            'gender': [1, 0, 1],
            'days_since_last_refill': [45, 20, 60],
            'last_days_supply': [30, 90, 30]
        })
        
        predictions = predictor.predict(sample_features)
        
        assert len(predictions) == 3
        assert all(0.0 <= p <= 1.0 for p in predictions)


class TestModelMetrics:
    """Test model metrics retrieval"""
    
    def test_get_model_metrics(self):
        """Test model metrics retrieval"""
        predictor = IITModelPredictor()
        metrics = predictor.get_model_metrics()
        
        assert "auc" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "model_version" in metrics
        
        # Check metric ranges
        assert 0.0 <= metrics["auc"] <= 1.0
        assert 0.0 <= metrics["precision"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
