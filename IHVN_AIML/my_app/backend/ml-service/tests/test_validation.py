"""
Data validation tests for IIT Prediction ML Service
"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from datetime import datetime, timedelta

from app.main import app
from app.schema import (
    PatientCreate, PatientUpdate, PatientJSON,
    VisitCreate, EncounterCreate, ObservationCreate,
    BatchPredictionRequest
)

client = TestClient(app)


class TestPatientValidation:
    """Test patient data validation"""

    def test_valid_patient_creation(self):
        """Test creating a patient with valid data"""
        patient_data = PatientCreate(
            given_name="John",
            family_name="Doe",
            birthdate=datetime(1985, 6, 15),
            gender="M",
            state_province="Lagos",
            city_village="Ikeja",
            phone_number="+2348012345678"
        )
        # This should not raise an exception
        assert patient_data.given_name == "John"
        assert patient_data.phone_number == "+2348012345678"

    def test_invalid_gender(self):
        """Test patient creation with invalid gender"""
        with pytest.raises(ValidationError):
            PatientCreate(
                given_name="John",
                family_name="Doe",
                birthdate=datetime(1985, 6, 15),
                gender="INVALID",  # Invalid gender
                state_province="Lagos"
            )

    def test_invalid_phone_number(self):
        """Test patient creation with invalid phone number"""
        with pytest.raises(ValidationError):
            PatientCreate(
                given_name="John",
                family_name="Doe",
                birthdate=datetime(1985, 6, 15),
                gender="M",
                phone_number="1234567890"  # Missing + prefix
            )

    def test_future_birthdate(self):
        """Test patient creation with future birthdate"""
        future_date = datetime.now() + timedelta(days=365)
        with pytest.raises(ValidationError):
            PatientCreate(
                given_name="John",
                family_name="Doe",
                birthdate=future_date,
                gender="M"
            )

    def test_invalid_age_range(self):
        """Test patient creation with invalid age constraints"""
        # Test age minimum
        with pytest.raises(ValidationError):
            PatientCreate(
                given_name="John",
                family_name="Doe",
                birthdate=datetime(1880, 6, 15),  # Too old
                gender="M"
            )


class TestVisitValidation:
    """Test visit data validation"""

    def test_valid_visit_creation(self):
        """Test creating a visit with valid data"""
        visit_data = VisitCreate(
            patient_uuid="test-uuid-123",
            visit_type="CLINICAL",
            date_started=datetime(2024, 10, 1, 10, 30),
            date_stopped=datetime(2024, 10, 1, 11, 30),
            location_id="facility-123"
        )
        assert visit_data.patient_uuid == "test-uuid-123"

    def test_invalid_date_order(self):
        """Test visit creation with invalid date order"""
        with pytest.raises(ValidationError):
            VisitCreate(
                patient_uuid="test-uuid-123",
                date_started=datetime(2024, 10, 1, 11, 30),
                date_stopped=datetime(2024, 10, 1, 10, 30)  # Before start
            )


class TestEncounterValidation:
    """Test encounter data validation"""

    def test_valid_encounter_creation(self):
        """Test creating an encounter with valid data"""
        encounter_data = EncounterCreate(
            patient_uuid="test-uuid-123",
            encounter_datetime=datetime(2024, 10, 1, 10, 30),
            encounter_type="PHARMACY",
            pmm_form="Pharmacy Order Form"
        )
        assert encounter_data.patient_uuid == "test-uuid-123"

    def test_future_encounter_datetime(self):
        """Test encounter creation with future datetime"""
        future_datetime = datetime.now() + timedelta(hours=1)
        with pytest.raises(ValidationError):
            EncounterCreate(
                patient_uuid="test-uuid-123",
                encounter_datetime=future_datetime
            )


class TestObservationValidation:
    """Test observation data validation"""

    def test_valid_observation_creation(self):
        """Test creating an observation with valid data"""
        obs_data = ObservationCreate(
            patient_uuid="test-uuid-123",
            encounter_id=1,
            variable_name="Blood Pressure",
            value_numeric=120.5,
            obs_datetime=datetime(2024, 10, 1, 10, 30)
        )
        assert obs_data.value_numeric == 120.5

    def test_future_observation_datetime(self):
        """Test observation creation with future datetime"""
        future_datetime = datetime.now() + timedelta(hours=1)
        with pytest.raises(ValidationError):
            ObservationCreate(
                patient_uuid="test-uuid-123",
                encounter_id=1,
                variable_name="Blood Pressure",
                obs_datetime=future_datetime
            )

    def test_invalid_numeric_range(self):
        """Test observation creation with out-of-range numeric value"""
        with pytest.raises(ValidationError):
            ObservationCreate(
                patient_uuid="test-uuid-123",
                encounter_id=1,
                variable_name="Blood Pressure",
                value_numeric=1000000,  # Too large
                obs_datetime=datetime(2024, 10, 1, 10, 30)
            )


class TestBatchValidation:
    """Test batch operation validation"""

    def test_valid_batch_prediction(self):
        """Test batch prediction with valid data"""
        sample_patient = PatientJSON(
            messageData={
                "demographics": {
                    "patientUuid": "test-uuid-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja"
                },
                "visits": [],
                "encounters": [],
                "obs": []
            }
        )

        batch_request = BatchPredictionRequest(patients=[sample_patient])
        assert len(batch_request.patients) == 1

    def test_batch_size_limit(self):
        """Test batch size limit validation"""
        sample_patient = PatientJSON(
            messageData={
                "demographics": {
                    "patientUuid": "test-uuid-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja"
                },
                "visits": [],
                "encounters": [],
                "obs": []
            }
        )

        # Create oversized batch
        oversized_batch = [sample_patient] * 101
        with pytest.raises(ValidationError):
            BatchPredictionRequest(patients=oversized_batch)


class TestAPIValidation:
    """Test API-level validation"""

    def test_patient_api_validation(self):
        """Test patient API input validation"""
        # Test missing required fields
        invalid_patient = {
            "given_name": "John"
            # Missing birthdate and gender
        }

        response = client.post("/api/v1/patients/", json=invalid_patient)
        assert response.status_code == 422  # Validation error

    def test_visit_api_validation(self):
        """Test visit API input validation"""
        # Test invalid date order
        invalid_visit = {
            "patient_uuid": "test-uuid-123",
            "date_started": "2024-10-01T11:30:00",
            "date_stopped": "2024-10-01T10:30:00"  # Before start
        }

        response = client.post("/api/v1/visits/", json=invalid_visit)
        assert response.status_code == 422

    def test_observation_api_validation(self):
        """Test observation API input validation"""
        # Test invalid numeric value
        invalid_obs = {
            "patient_uuid": "test-uuid-123",
            "encounter_id": 1,
            "variable_name": "Test",
            "value_numeric": 10000000,  # Too large
            "obs_datetime": "2024-10-01T10:30:00"
        }

        response = client.post("/api/v1/observations/", json=invalid_obs)
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
