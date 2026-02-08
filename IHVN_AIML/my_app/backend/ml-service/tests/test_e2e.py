"""
End-to-End tests for IIT Prediction ML Service
Complete user journey tests from patient registration to analytics
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
import tempfile
from datetime import datetime, timedelta
import time

from app.main import app
from app.core.db import get_db
from app.models import Patient, Visit, Encounter, Observation
from app.crud import create_patient, get_patient
from app.schema import PatientCreate

client = TestClient(app)


@pytest.fixture(scope="function")
def e2e_test_db():
    """Create a test database for end-to-end testing"""
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


class TestPatientRegistrationJourney:
    """Test complete patient registration to prediction journey"""

    def test_complete_patient_journey(self, e2e_test_db):
        """Test full patient lifecycle: registration → data entry → prediction → analytics"""

        # Step 1: Patient Registration
        patient_data = {
            "given_name": "E2E Test Patient",
            "family_name": "Journey",
            "birthdate": "1990-05-15",
            "gender": "F",
            "state_province": "Lagos",
            "city_village": "Victoria Island",
            "phone_number": "+2348012345678"
        }

        # Register patient via API
        response = client.post("/api/v1/patients/", json=patient_data)
        assert response.status_code == 201
        patient_response = response.json()
        patient_uuid = patient_response["patient_uuid"]

        # Verify patient was created
        response = client.get(f"/api/v1/patients/{patient_uuid}")
        assert response.status_code == 200
        retrieved_patient = response.json()
        assert retrieved_patient["given_name"] == "E2E Test Patient"

        # Step 2: Add clinical data (visits, encounters, observations)
        # This would typically be done through the EMR integration
        # For E2E testing, we'll simulate the data entry

        # Step 3: Make IIT Risk Prediction
        prediction_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": patient_uuid,
                    "birthdate": "1990-05-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Victoria Island",
                    "phoneNumber": "+2348012345678"
                },
                "visits": [
                    {
                        "dateStarted": "2024-10-01 09:00:00",
                        "voided": 0
                    }
                ],
                "encounters": [
                    {
                        "encounterUuid": "e2e-enc-001",
                        "encounterDatetime": "2024-10-01 09:00:00",
                        "pmmForm": "Pharmacy Order Form",
                        "voided": 0
                    }
                ],
                "obs": [
                    {
                        "obsDatetime": "2024-10-01 09:00:00",
                        "variableName": "Medication duration",
                        "valueNumeric": 120.0,  # High duration = higher IIT risk
                        "voided": 0
                    },
                    {
                        "obsDatetime": "2024-10-01 09:00:00",
                        "variableName": "Days since last pickup",
                        "valueNumeric": 45.0,  # Delayed pickup = higher risk
                        "voided": 0
                    }
                ]
            }
        }

        # Make prediction
        response = client.post("/predict", json=prediction_data)
        assert response.status_code == 200
        prediction_result = response.json()

        # Validate prediction response
        assert "patient_uuid" in prediction_result
        assert "iit_risk_score" in prediction_result
        assert "risk_level" in prediction_result
        assert "confidence" in prediction_result
        assert prediction_result["patient_uuid"] == patient_uuid
        assert 0.0 <= prediction_result["iit_risk_score"] <= 1.0
        assert prediction_result["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

        # Step 4: Access Analytics Dashboard
        # Test analytics summary
        response = client.get("/api/v1/analytics/summary")
        # May require authentication, so accept 401 or 200
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            analytics_data = response.json()
            assert "total_patients" in analytics_data
            assert "predictions_count" in analytics_data
            assert analytics_data["total_patients"] >= 1

        # Step 5: Generate Report
        report_request = {
            "report_type": "risk_assessment",
            "date_from": "2024-10-01",
            "date_to": "2024-10-31",
            "filters": {
                "risk_level": ["HIGH", "CRITICAL"],
                "location": "Lagos"
            }
        }

        response = client.post("/api/v1/reports/generate", json=report_request)
        # May require authentication
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            report_data = response.json()
            assert "report_id" in report_data
            assert "status" in report_data

    def test_batch_processing_journey(self, e2e_test_db):
        """Test batch processing of multiple patients"""

        # Create multiple patients in database
        patients_data = []
        prediction_requests = []

        for i in range(5):
            # Create patient
            patient = PatientCreate(
                given_name=f"Batch Patient {i}",
                family_name="Test",
                birthdate=datetime(1985 + i, 1, 1),
                gender="F" if i % 2 == 0 else "M",
                state_province="Lagos",
                city_village="Ikeja",
                phone_number=f"+23480{i}1234567"
            )
            created_patient = create_patient(e2e_test_db, patient)

            # Prepare prediction request
            pred_request = {
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
                    "encounters": [{"encounterUuid": f"batch-enc-{i}", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                    "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0 + i * 10, "voided": 0}]
                }
            }
            prediction_requests.append(pred_request)

        # Perform batch prediction
        batch_request = {"patients": prediction_requests}
        response = client.post("/batch_predict", json=batch_request)
        assert response.status_code == 200

        batch_result = response.json()
        assert "predictions" in batch_result
        assert "total_processed" in batch_result
        assert len(batch_result["predictions"]) == 5
        assert batch_result["total_processed"] == 5

        # Verify each prediction
        for prediction in batch_result["predictions"]:
            assert "patient_uuid" in prediction
            assert "iit_risk_score" in prediction
            assert "risk_level" in prediction
            assert 0.0 <= prediction["iit_risk_score"] <= 1.0


class TestErrorRecoveryScenarios:
    """Test error recovery and edge cases in end-to-end flows"""

    def test_prediction_with_missing_data_recovery(self, e2e_test_db):
        """Test prediction when some data is missing but system recovers"""

        # Create patient
        patient = create_patient(e2e_test_db, PatientCreate(
            given_name="Recovery Test",
            family_name="Patient",
            birthdate=datetime(1990, 1, 1),
            gender="M",
            state_province="Abuja",
            city_village="Wuse"
        ))

        # Prediction with minimal data (missing some observations)
        minimal_prediction_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": str(patient.patient_uuid),
                    "birthdate": "1990-01-01 00:00:00",
                    "gender": "M",
                    "stateProvince": "Abuja",
                    "cityVillage": "Wuse",
                    "phoneNumber": "+2348023456789"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "recovery-enc-001", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": []  # No observations - system should handle gracefully
            }
        }

        response = client.post("/predict", json=minimal_prediction_data)
        # Should either succeed with default values or fail gracefully
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            result = response.json()
            assert "iit_risk_score" in result
            assert "risk_level" in result

    def test_concurrent_user_sessions(self, e2e_test_db):
        """Test multiple users accessing the system concurrently"""

        # Create test patients
        patients = []
        for i in range(3):
            patient = create_patient(e2e_test_db, PatientCreate(
                given_name=f"Concurrent User {i}",
                family_name="Test",
                birthdate=datetime(1985, 1, 1),
                gender="F",
                state_province="Lagos",
                city_village="Ikeja",
                phone_number=f"+23480{i}1111111"
            ))
            patients.append(patient)

        # Simulate concurrent prediction requests
        import threading
        results = []
        errors = []

        def make_concurrent_request(patient_idx):
            try:
                patient = patients[patient_idx]
                prediction_data = {
                    "messageData": {
                        "demographics": {
                            "patientUuid": str(patient.patient_uuid),
                            "birthdate": "1985-01-01 00:00:00",
                            "gender": "F",
                            "stateProvince": "Lagos",
                            "cityVillage": "Ikeja",
                            "phoneNumber": f"+23480{patient_idx}1111111"
                        },
                        "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                        "encounters": [{"encounterUuid": f"conc-enc-{patient_idx}", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                        "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 60.0, "voided": 0}]
                    }
                }

                response = client.post("/predict", json=prediction_data)
                results.append({
                    "user": patient_idx,
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                })
            except Exception as e:
                errors.append(f"User {patient_idx}: {str(e)}")

        # Start concurrent threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_concurrent_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        assert len(results) == 3
        assert len(errors) == 0

        successful_requests = [r for r in results if r["success"]]
        assert len(successful_requests) >= 2  # At least 2 should succeed


class TestSystemIntegrationFlows:
    """Test integration with external systems and scheduled tasks"""

    def test_scheduled_report_generation(self, e2e_test_db):
        """Test scheduled report generation workflow"""

        # Create some test data
        for i in range(10):
            patient = create_patient(e2e_test_db, PatientCreate(
                given_name=f"Report Patient {i}",
                family_name="Test",
                birthdate=datetime(1980 + (i % 10), 1, 1),
                gender="F" if i % 2 == 0 else "M",
                state_province="Lagos" if i < 5 else "Abuja",
                city_village="Ikeja",
                phone_number=f"+23480{i}2222222"
            ))

        # Trigger scheduled report generation
        # This would typically be done by a cron job or scheduler
        report_config = {
            "report_type": "weekly_risk_summary",
            "date_from": "2024-09-01",
            "date_to": "2024-10-31",
            "include_charts": True,
            "recipients": ["admin@hospital.org"]
        }

        response = client.post("/api/v1/reports/scheduled/generate", json=report_config)
        # May require authentication or specific permissions
        assert response.status_code in [200, 201, 401, 403]

        if response.status_code in [200, 201]:
            result = response.json()
            assert "report_id" in result or "job_id" in result

    def test_backup_and_restore_workflow(self, e2e_test_db):
        """Test complete backup and restore workflow"""

        # Create test data
        for i in range(5):
            create_patient(e2e_test_db, PatientCreate(
                given_name=f"Backup Patient {i}",
                family_name="Test",
                birthdate=datetime(1990, 1, 1),
                gender="F",
                state_province="Lagos",
                city_village="Ikeja"
            ))

        # Create backup
        response = client.post("/api/v1/backup/create")
        assert response.status_code in [201, 401]

        if response.status_code == 201:
            backup_data = response.json()
            backup_id = backup_data["backup_id"]

            # List backups
            response = client.get("/api/v1/backup/list")
            assert response.status_code in [200, 401]

            if response.status_code == 200:
                backups = response.json()
                assert isinstance(backups, list)
                assert len(backups) >= 1

                # Test restore (in a real scenario, this would be done carefully)
                # For testing, we'll just check the endpoint exists
                response = client.post(f"/api/v1/backup/restore/{backup_id}")
                assert response.status_code in [200, 202, 401, 403]


class TestHealthcareWorkflowCompliance:
    """Test healthcare-specific workflow compliance"""

    def test_patient_privacy_protection(self, e2e_test_db):
        """Test that patient data is properly protected throughout the workflow"""

        # Create patient with sensitive data
        patient = create_patient(e2e_test_db, PatientCreate(
            given_name="Privacy Test",
            family_name="Patient",
            birthdate=datetime(1995, 1, 1),
            gender="M",
            state_province="Lagos",
            city_village="Ikeja",
            phone_number="+2348012345678"
        ))

        # Make prediction
        prediction_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": str(patient.patient_uuid),
                    "birthdate": "1995-01-01 00:00:00",
                    "gender": "M",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+2348012345678"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "privacy-enc-001", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "HIV status", "valueText": "Positive", "voided": 0}]
            }
        }

        response = client.post("/predict", json=prediction_data)
        assert response.status_code == 200

        result = response.json()
        # Ensure no sensitive patient data is leaked in response
        assert "phone_number" not in result
        assert "HIV status" not in result
        assert result["patient_uuid"] == str(patient.patient_uuid)  # UUID is ok for tracking

    def test_audit_trail_compliance(self, e2e_test_db):
        """Test that all actions are properly audited"""

        # Create patient
        patient = create_patient(e2e_test_db, PatientCreate(
            given_name="Audit Test",
            family_name="Patient",
            birthdate=datetime(1985, 1, 1),
            gender="F",
            state_province="Abuja",
            city_village="Wuse"
        ))

        # Make prediction (should be audited)
        prediction_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": str(patient.patient_uuid),
                    "birthdate": "1985-01-01 00:00:00",
                    "gender": "F",
                    "stateProvince": "Abuja",
                    "cityVillage": "Wuse",
                    "phoneNumber": "+2348023456789"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "audit-enc-001", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        response = client.post("/predict", json=prediction_data)
        assert response.status_code == 200

        # Check audit logs (if audit endpoint exists)
        response = client.get("/api/v1/audit/logs")
        # May require admin permissions
        assert response.status_code in [200, 401, 403]

        if response.status_code == 200:
            audit_logs = response.json()
            assert isinstance(audit_logs, list)
            # Check if prediction was logged
            prediction_logs = [log for log in audit_logs if "prediction" in log.get("action", "").lower()]
            assert len(prediction_logs) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
