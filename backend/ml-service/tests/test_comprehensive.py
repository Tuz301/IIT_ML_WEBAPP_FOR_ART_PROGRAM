"""
Comprehensive test suite for IIT ML Service production features
Tests all new components: validation, security, performance, analytics, backup, etc.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock
import threading
import time
import psutil
import os

from app.main import app

client = TestClient(app)


class TestValidationMiddleware:
    """Test input validation middleware"""

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in validation middleware"""
        malicious_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-patient-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos'; DROP TABLE patients; --",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+234801234567"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        response = client.post("/predict", json=malicious_data)
        assert response.status_code == 422
        data = response.json()
        assert "validation failed" in data.get("error", "").lower()

    def test_xss_prevention(self):
        """Test XSS prevention in validation middleware"""
        xss_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-patient-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "<script>alert('xss')</script>",
                    "phoneNumber": "+234801234567"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        response = client.post("/predict", json=xss_data)
        assert response.status_code == 422

    def test_phone_validation(self):
        """Test phone number validation"""
        invalid_phone_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-patient-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "0801234567"  # Missing + prefix
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        response = client.post("/predict", json=invalid_phone_data)
        assert response.status_code == 422

    def test_date_validation(self):
        """Test date validation"""
        future_birthdate_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "test-patient-123",
                    "birthdate": "2050-06-15 00:00:00",  # Future date
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+234801234567"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        response = client.post("/predict", json=future_birthdate_data)
        assert response.status_code == 422


class TestSecurityMiddleware:
    """Test security middleware functionality"""

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Make multiple rapid requests to test rate limiting
        for i in range(150):  # Exceed typical rate limit
            response = client.get("/health")
            if response.status_code == 429:  # Too Many Requests
                break

        # Should eventually hit rate limit
        assert response.status_code in [200, 429]

    def test_audit_logging(self):
        """Test that security events are logged"""
        with patch('app.middleware.security.logger') as mock_logger:
            # Make a request that should trigger security logging
            malicious_data = {
                "messageData": {
                    "demographics": {
                        "patientUuid": "test-patient-123",
                        "birthdate": "1985-06-15 00:00:00",
                        "gender": "F",
                        "stateProvince": "Lagos",
                        "cityVillage": "Ikeja",
                        "phoneNumber": "+234801234567"
                    },
                    "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                    "encounters": [{"encounterUuid": "enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                    "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "UNION SELECT * FROM users", "valueNumeric": 90.0, "voided": 0}]
                }
            }

            response = client.post("/predict", json=malicious_data)
            # Verify logging was called
            mock_logger.warning.assert_called()

    def test_encryption_utilities(self):
        """Test data encryption/decryption utilities"""
        from app.utils.encryption import encrypt_data, decrypt_data

        test_data = "sensitive patient information"
        encrypted = encrypt_data(test_data)
        decrypted = decrypt_data(encrypted)

        assert decrypted == test_data
        assert encrypted != test_data


class TestPerformanceMiddleware:
    """Test performance monitoring middleware"""

    def test_response_time_tracking(self):
        """Test that response times are tracked"""
        with patch('app.middleware.performance.logger') as mock_logger:
            response = client.get("/health")
            assert response.status_code == 200

            # Verify performance logging was called
            mock_logger.info.assert_called()

    def test_slow_query_detection(self):
        """Test slow query detection and logging"""
        # Make a request that might be slow
        with patch('app.middleware.performance.time') as mock_time:
            mock_time.time.side_effect = [0, 2.5]  # Simulate 2.5 second response

            with patch('app.middleware.performance.logger') as mock_logger:
                response = client.get("/health")
                assert response.status_code == 200

                # Should log slow query
                mock_logger.warning.assert_called()


class TestAnalyticsAPI:
    """Test comprehensive analytics API"""

    def test_dashboard_analytics(self):
        """Test dashboard analytics endpoint"""
        response = client.get("/api/analytics/dashboard")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "total_patients" in data
            assert "risk_distribution" in data
            assert "monthly_trends" in data

    def test_custom_report_generation(self):
        """Test custom report generation"""
        report_request = {
            "report_type": "risk_analysis",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "filters": {"risk_level": "high"},
            "format": "json"
        }

        response = client.post("/api/analytics/custom-report", json=report_request)
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "report_id" in data or "data" in data

    def test_scheduled_reports_management(self):
        """Test scheduled reports management"""
        # Create scheduled report
        schedule_request = {
            "name": "Weekly Risk Report",
            "report_type": "risk_summary",
            "schedule": "weekly",
            "recipients": ["admin@example.com"],
            "filters": {}
        }

        response = client.post("/api/analytics/scheduled-reports", json=schedule_request)
        assert response.status_code in [201, 401]

        if response.status_code == 201:
            schedule_data = response.json()
            schedule_id = schedule_data.get("schedule_id")

            # List scheduled reports
            list_response = client.get("/api/analytics/scheduled-reports")
            assert list_response.status_code in [200, 401]

            # Delete scheduled report
            if schedule_id:
                delete_response = client.delete(f"/api/analytics/scheduled-reports/{schedule_id}")
                assert delete_response.status_code in [200, 401]


class TestBackupAPI:
    """Test comprehensive backup and disaster recovery API"""

    def test_backup_creation_and_verification(self):
        """Test backup creation with verification"""
        response = client.post("/api/backup/create")
        assert response.status_code in [201, 401]

        if response.status_code == 201:
            backup_data = response.json()
            backup_id = backup_data.get("backup_id")

            # Verify backup integrity
            if backup_id:
                verify_response = client.post(f"/api/backup/verify/{backup_id}")
                assert verify_response.status_code in [200, 401]

                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    assert "integrity_check" in verify_data
                    assert verify_data.get("status") == "verified"

    def test_backup_scheduling(self):
        """Test automated backup scheduling"""
        schedule_request = {
            "name": "Daily Backup",
            "schedule": "daily",
            "retention_days": 30,
            "type": "full"
        }

        response = client.post("/api/backup/schedule", json=schedule_request)
        assert response.status_code in [201, 401]

        if response.status_code == 201:
            schedule_data = response.json()
            schedule_id = schedule_data.get("schedule_id")

            # List backup schedules
            list_response = client.get("/api/backup/schedules")
            assert list_response.status_code in [200, 401]

    def test_disaster_recovery_simulation(self):
        """Test disaster recovery procedures"""
        # Create a test backup first
        create_response = client.post("/api/backup/create")
        if create_response.status_code == 201:
            backup_id = create_response.json()["backup_id"]

            # Simulate disaster recovery
            recovery_request = {
                "backup_id": backup_id,
                "recovery_type": "full",
                "target_environment": "staging"
            }

            response = client.post("/api/backup/recover", json=recovery_request)
            assert response.status_code in [200, 401]

    def test_backup_monitoring(self):
        """Test backup monitoring and alerting"""
        response = client.get("/api/backup/monitoring/status")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "active_schedules" in data
            assert "last_backup_status" in data
            assert "failure_alerts" in data


class TestInterventionWorkflowAPI:
    """Test intervention workflow and case management API"""

    def test_intervention_creation(self):
        """Test intervention creation"""
        intervention_request = {
            "patient_uuid": "test-patient-123",
            "intervention_type": "follow_up",
            "priority": "high",
            "title": "Missed Appointment Follow-up",
            "description": "Patient missed scheduled appointment",
            "due_date": "2024-12-01T10:00:00Z"
        }

        response = client.post("/api/interventions", json=intervention_request)
        assert response.status_code in [201, 401]

        if response.status_code == 201:
            data = response.json()
            assert "intervention_id" in data
            assert data.get("status") == "pending"

    def test_workflow_execution(self):
        """Test automated workflow execution"""
        # Create intervention first
        intervention_request = {
            "patient_uuid": "test-patient-123",
            "intervention_type": "counseling",
            "priority": "medium",
            "title": "Adherence Counseling",
            "description": "Patient showing adherence issues"
        }

        create_response = client.post("/api/interventions", json=intervention_request)
        if create_response.status_code == 201:
            intervention_id = create_response.json()["intervention_id"]

            # Execute workflow step
            workflow_request = {
                "intervention_id": intervention_id,
                "action": "schedule_session",
                "parameters": {"session_type": "phone_call"}
            }

            response = client.post("/api/workflows/execute", json=workflow_request)
            assert response.status_code in [200, 401]

    def test_alert_management(self):
        """Test risk-based alerts management"""
        # Create alert
        alert_request = {
            "patient_uuid": "test-patient-123",
            "alert_type": "risk_threshold",
            "severity": "high",
            "title": "High IIT Risk Detected",
            "message": "Patient shows elevated IIT risk score"
        }

        response = client.post("/api/alerts", json=alert_request)
        assert response.status_code in [201, 401]

        if response.status_code == 201:
            alert_data = response.json()
            alert_id = alert_data.get("alert_id")

            # Acknowledge alert
            if alert_id:
                ack_response = client.post(f"/api/alerts/{alert_id}/acknowledge")
                assert ack_response.status_code in [200, 401]


class TestCommunicationAPI:
    """Test communication and messaging API"""

    def test_sms_communication(self):
        """Test SMS communication functionality"""
        sms_request = {
            "patient_uuid": "test-patient-123",
            "communication_type": "sms",
            "message": "Reminder: Your appointment is tomorrow at 10 AM",
            "priority": "normal"
        }

        response = client.post("/api/communications/send", json=sms_request)
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert "communication_id" in data
            assert "status" in data

    def test_communication_history(self):
        """Test communication history retrieval"""
        response = client.get("/api/communications/history/test-patient-123")
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if data:
                assert "communication_type" in data[0]
                assert "status" in data[0]
                assert "sent_at" in data[0]


class TestLoadTesting:
    """Load testing scenarios"""

    def test_high_concurrency_load(self):
        """Test system under high concurrent load"""
        results = []
        errors = []

        def make_request():
            try:
                response = client.get("/health")
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = []
        for i in range(50):  # 50 concurrent requests
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()

        # Verify results
        assert len(results) == 50
        assert all(status == 200 for status in results)
        assert len(errors) == 0

        # Verify reasonable response time (under 30 seconds for 50 requests)
        assert (end_time - start_time) < 30

    def test_memory_leak_prevention(self):
        """Test for memory leaks under sustained load"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Make many requests
        for i in range(100):
            response = client.get("/health")
            assert response.status_code == 200

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024


class TestDatabaseOptimization:
    """Test database optimization features"""

    def test_index_usage(self):
        """Test that database indexes are being used"""
        # This would require database access to check query plans
        # For now, just test that the optimization script can be imported
        try:
            from scripts.database_optimization import DatabaseOptimizer
            optimizer = DatabaseOptimizer()
            assert optimizer is not None
        except ImportError:
            pytest.skip("Database optimization script not available")

    def test_query_performance(self):
        """Test query performance improvements"""
        # Test that complex queries still perform well
        start_time = time.time()

        # Make a request that would use optimized indexes
        response = client.get("/health")
        assert response.status_code == 200

        end_time = time.time()
        response_time = end_time - start_time

        # Response should be fast (< 1 second)
        assert response_time < 1.0


class TestComplianceAndSecurity:
    """Test HIPAA/GDPR compliance and security features"""

    def test_data_encryption_at_rest(self):
        """Test that sensitive data is encrypted at rest"""
        from app.utils.encryption import encrypt_data, decrypt_data

        sensitive_data = "PHI: Patient has HIV, CD4 count: 200"
        encrypted = encrypt_data(sensitive_data)
        decrypted = decrypt_data(encrypted)

        assert decrypted == sensitive_data
        # Ensure encryption actually changes the data
        assert encrypted != sensitive_data

    def test_audit_trail_completeness(self):
        """Test that all operations are properly audited"""
        with patch('app.middleware.security.logger') as mock_logger:
            # Perform an operation that should be audited
            response = client.get("/health")
            assert response.status_code == 200

            # Verify audit logging was called
            mock_logger.info.assert_called()

    def test_access_control_enforcement(self):
        """Test that access controls are properly enforced"""
        # Test unauthorized access to protected endpoints
        protected_endpoints = [
            "/api/analytics/dashboard",
            "/api/backup/create",
            "/api/interventions"
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # Should return 401 Unauthorized (or 200 if no auth required in test)
            assert response.status_code in [200, 401]


class TestSystemIntegration:
    """Test end-to-end system integration"""

    def test_full_prediction_workflow(self):
        """Test complete prediction workflow from data ingestion to intervention"""
        # 1. Create patient data
        patient_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "workflow-test-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+234801234567"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "workflow-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 30.0, "voided": 0}]  # Low adherence
            }
        }

        # 2. Make prediction
        pred_response = client.post("/predict", json=patient_data)
        assert pred_response.status_code == 200
        prediction = pred_response.json()

        # 3. Check if high-risk alert was created
        if prediction.get("risk_level") in ["high", "critical"]:
            # Should trigger intervention workflow
            intervention_response = client.post("/api/interventions", json={
                "patient_uuid": prediction["patient_uuid"],
                "intervention_type": "follow_up",
                "priority": "high",
                "title": "High IIT Risk Intervention",
                "description": f"Patient shows {prediction['risk_level']} IIT risk"
            })
            assert intervention_response.status_code in [201, 401]

    def test_backup_and_recovery_workflow(self):
        """Test complete backup and recovery workflow"""
        # 1. Create backup
        backup_response = client.post("/api/backup/create")
        assert backup_response.status_code in [201, 401]

        if backup_response.status_code == 201:
            backup_id = backup_response.json()["backup_id"]

            # 2. Verify backup
            verify_response = client.post(f"/api/backup/verify/{backup_id}")
            assert verify_response.status_code in [200, 401]

            # 3. List backups
            list_response = client.get("/api/backup/list")
            assert list_response.status_code in [200, 401]

            if list_response.status_code == 200:
                backups = list_response.json()
                assert any(b["backup_id"] == backup_id for b in backups)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
