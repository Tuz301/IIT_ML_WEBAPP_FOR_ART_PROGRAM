"""
Integration tests for IIT Prediction ML Service
Tests database operations and API workflows
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
import tempfile
from datetime import datetime

from app.main import app
from app.core.db import get_db
from app.models import Patient, Visit, Encounter, Observation
from app.crud import create_patient, get_patient, create_visit, create_encounter, create_observation
from app.schema import PatientCreate, VisitCreate, EncounterCreate, ObservationCreate

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session"""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Configure test database URL
    test_db_url = f"sqlite:///{db_path}"

    # Create engine and session
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    from app.models import Base
    Base.metadata.create_all(bind=engine)

    # Override get_db dependency
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal()

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


class TestDatabaseOperations:
    """Test database CRUD operations"""

    def test_patient_crud_operations(self, test_db):
        """Test complete patient CRUD workflow"""
        # Create patient
        patient_data = PatientCreate(
            given_name="John",
            family_name="Doe",
            birthdate=datetime(1985, 6, 15),
            gender="M",
            state_province="Lagos",
            city_village="Ikeja",
            phone_number="+2348012345678"
        )

        # Test create
        created_patient = create_patient(test_db, patient_data)
        assert created_patient.given_name == "John"
        assert created_patient.patient_uuid is not None

        # Test read
        retrieved_patient = get_patient(test_db, created_patient.patient_uuid)
        assert retrieved_patient is not None
        assert retrieved_patient.given_name == "John"

        # Test update (if update function exists)
        # This would require implementing update_patient in crud.py

        # Test delete (if delete function exists)
        # This would require implementing delete_patient in crud.py

    def test_visit_encounter_observation_workflow(self, test_db):
        """Test visit → encounter → observation workflow"""
        # Create patient first
        patient_data = PatientCreate(
            given_name="Jane",
            family_name="Smith",
            birthdate=datetime(1990, 3, 20),
            gender="F",
            state_province="Abuja",
            city_village="Wuse",
            phone_number="+2348023456789"
        )
        patient = create_patient(test_db, patient_data)

        # Create visit
        visit_data = VisitCreate(
            patient_uuid=patient.patient_uuid,
            visit_type="CLINICAL",
            date_started=datetime(2024, 10, 1, 10, 30),
            date_stopped=datetime(2024, 10, 1, 11, 30),
            location_id="facility-123"
        )
        visit = create_visit(test_db, visit_data)
        assert visit.patient_uuid == patient.patient_uuid

        # Create encounter
        encounter_data = EncounterCreate(
            patient_uuid=patient.patient_uuid,
            encounter_datetime=datetime(2024, 10, 1, 10, 30),
            encounter_type="PHARMACY",
            pmm_form="Pharmacy Order Form"
        )
        encounter = create_encounter(test_db, encounter_data)
        assert encounter.patient_uuid == patient.patient_uuid

        # Create observation
        obs_data = ObservationCreate(
            patient_uuid=patient.patient_uuid,
            encounter_id=encounter.id,
            variable_name="Medication duration",
            value_numeric=90.0,
            obs_datetime=datetime(2024, 10, 1, 10, 30)
        )
        observation = create_observation(test_db, obs_data)
        assert observation.value_numeric == 90.0


class TestAPIWorkflows:
    """Test complete API workflows"""

    def test_patient_registration_workflow(self, test_db):
        """Test complete patient registration workflow"""
        patient_data = {
            "given_name": "Alice",
            "family_name": "Johnson",
            "birthdate": "1988-12-25",
            "gender": "F",
            "state_province": "Kano",
            "city_village": "Sabon Gari",
            "phone_number": "+2348034567890"
        }

        # Register patient
        response = client.post("/api/v1/patients/", json=patient_data)
        assert response.status_code == 201
        patient_response = response.json()
        patient_uuid = patient_response["patient_uuid"]

        # Verify patient was created
        response = client.get(f"/api/v1/patients/{patient_uuid}")
        assert response.status_code == 200
        retrieved_patient = response.json()
        assert retrieved_patient["given_name"] == "Alice"

    def test_prediction_workflow(self, test_db):
        """Test prediction workflow with database integration"""
        # First create a patient in database
        patient_data = PatientCreate(
            given_name="Bob",
            family_name="Wilson",
            birthdate=datetime(1982, 8, 10),
            gender="M",
            state_province="Port Harcourt",
            city_village="GRA",
            phone_number="+2348045678901"
        )
        patient = create_patient(test_db, patient_data)

        # Create prediction request
        prediction_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": str(patient.patient_uuid),
                    "birthdate": "1982-08-10 00:00:00",
                    "gender": "M",
                    "stateProvince": "Port Harcourt",
                    "cityVillage": "GRA",
                    "phoneNumber": "+2348045678901"
                },
                "visits": [
                    {
                        "dateStarted": "2024-10-01 10:30:00",
                        "voided": 0
                    }
                ],
                "encounters": [
                    {
                        "encounterUuid": "enc-test-123",
                        "encounterDatetime": "2024-10-01 10:30:00",
                        "pmmForm": "Pharmacy Order Form",
                        "voided": 0
                    }
                ],
                "obs": [
                    {
                        "obsDatetime": "2024-10-01 10:30:00",
                        "variableName": "Medication duration",
                        "valueNumeric": 60.0,
                        "voided": 0
                    }
                ]
            }
        }

        # Make prediction
        response = client.post("/predict", json=prediction_data)
        assert response.status_code == 200
        prediction_result = response.json()
        assert "iit_risk_score" in prediction_result
        assert "risk_level" in prediction_result
        assert 0.0 <= prediction_result["iit_risk_score"] <= 1.0

    def test_batch_prediction_workflow(self, test_db):
        """Test batch prediction workflow"""
        # Create multiple patients
        patients_data = []
        for i in range(3):
            patient = PatientCreate(
                given_name=f"Patient{i}",
                family_name="Test",
                birthdate=datetime(1980 + i, 1, 1),
                gender="F" if i % 2 == 0 else "M",
                state_province="Lagos",
                city_village="Ikeja",
                phone_number=f"+23480{i}1234567"
            )
            created_patient = create_patient(test_db, patient)

            patient_json = {
                "messageData": {
                    "demographics": {
                        "patientUuid": str(created_patient.patient_uuid),
                        "birthdate": f"198{i}-01-01 00:00:00",
                        "gender": "F" if i % 2 == 0 else "M",
                        "stateProvince": "Lagos",
                        "cityVillage": "Ikeja",
                        "phoneNumber": f"+23480{i}1234567"
                    },
                    "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                    "encounters": [{"encounterUuid": f"enc-{i}", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                    "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
                }
            }
            patients_data.append(patient_json)

        # Batch prediction
        batch_request = {"patients": patients_data}
        response = client.post("/batch_predict", json=batch_request)
        assert response.status_code == 200
        batch_result = response.json()
        assert "predictions" in batch_result
        assert len(batch_result["predictions"]) == 3


class TestDataIntegrity:
    """Test data integrity across operations"""

    def test_transaction_rollback_on_failure(self, test_db):
        """Test that failed operations don't leave partial data"""
        # This would test transaction handling
        # Implementation depends on transaction management in the app
        pass

    def test_foreign_key_constraints(self, test_db):
        """Test foreign key relationships are maintained"""
        # Create patient
        patient = create_patient(test_db, PatientCreate(
            given_name="Test",
            family_name="Constraints",
            birthdate=datetime(1990, 1, 1),
            gender="M",
            state_province="Test",
            city_village="Test"
        ))

        # Try to create observation with invalid patient_uuid
        # This should fail due to foreign key constraint
        invalid_obs = ObservationCreate(
            patient_uuid="nonexistent-uuid",  # Invalid UUID
            encounter_id=1,
            variable_name="Test",
            obs_datetime=datetime(2024, 10, 1, 10, 30)
        )

        with pytest.raises(Exception):  # Should raise integrity error
            create_observation(test_db, invalid_obs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
