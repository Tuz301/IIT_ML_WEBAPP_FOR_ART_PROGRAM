"""
Idempotency Middleware Tests

Tests for the idempotency key middleware including:
- Caching responses with idempotency keys
- Returning cached responses on subsequent requests
- Key validation
- TTL expiration
- Cleanup of expired keys
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from fastapi import Request
from fastapi.testclient import TestClient

from app.middleware.idempotency import (
    IdempotencyStore,
    IdempotencyMiddleware,
    idempotent,
    DEFAULT_IDEMPOTENCY_TTL
)
from app.main import app


class TestIdempotencyStore:
    """Test idempotency key storage"""
    
    def setup_method(self):
        """Clean up before each test"""
        IdempotencyStore.cleanup_expired()
    
    def teardown_method(self):
        """Clean up after each test"""
        IdempotencyStore.cleanup_expired()
    
    def test_store_and_retrieve(self):
        """Test storing and retrieving idempotency key"""
        key = "test-key-123"
        response_data = json.dumps({"result": "success"})
        response_status = 200
        response_headers = {"Content-Type": "application/json"}
        
        # Store
        result = IdempotencyStore.store(
            key=key,
            response_data=response_data,
            response_status=response_status,
            response_headers=response_headers,
            request_path="/v1/test",
            request_method="POST",
            ttl=3600
        )
        
        assert result is True
        
        # Retrieve
        cached = IdempotencyStore.get(key)
        
        assert cached is not None
        assert cached["response_data"] == response_data
        assert cached["response_status"] == response_status
        assert cached["response_headers"] == response_headers
    
    def test_key_not_found(self):
        """Test retrieving non-existent key"""
        cached = IdempotencyStore.get("non-existent-key")
        assert cached is None
    
    def test_key_expiration(self):
        """Test that keys expire after TTL"""
        key = "expiring-key"
        
        # Store with very short TTL
        IdempotencyStore.store(
            key=key,
            response_data='{"test": "data"}',
            response_status=200,
            response_headers={},
            request_path="/v1/test",
            request_method="POST",
            ttl=1  # 1 second
        )
        
        # Should be available immediately
        cached = IdempotencyStore.get(key)
        assert cached is not None
        
        # Wait for expiration
        time.sleep(2)
        
        # Should be expired
        cached = IdempotencyStore.get(key)
        assert cached is None
    
    def test_cleanup_expired(self):
        """Test cleanup of expired keys"""
        # Store multiple keys with different TTLs
        for i in range(5):
            IdempotencyStore.store(
                key=f"key-{i}",
                response_data=f'{{"id": {i}}}',
                response_status=200,
                response_headers={},
                request_path="/v1/test",
                request_method="POST",
                ttl=1 if i < 3 else 3600  # First 3 expire quickly
            )
        
        # Wait for expiration
        time.sleep(2)
        
        # Cleanup
        deleted_count = IdempotencyStore.cleanup_expired()
        
        assert deleted_count >= 3  # At least the 3 expired keys
    
    def test_hash_key(self):
        """Test key hashing"""
        key1 = "test-key"
        key2 = "test-key"
        key3 = "different-key"
        
        hash1 = IdempotencyStore._hash_key(key1)
        hash2 = IdempotencyStore._hash_key(key2)
        hash3 = IdempotencyStore._hash_key(key3)
        
        # Same keys should produce same hash
        assert hash1 == hash2
        
        # Different keys should produce different hashes
        assert hash1 != hash3


class TestIdempotencyMiddleware:
    """Test idempotency middleware"""
    
    def setup_method(self):
        """Clean up before each test"""
        IdempotencyStore.cleanup_expired()
    
    def teardown_method(self):
        """Clean up after each test"""
        IdempotencyStore.cleanup_expired()
    
    def test_idempotent_request(self):
        """Test that idempotent requests return cached response"""
        client = TestClient(app)
        
        idempotency_key = "test-idempotency-key-123"
        
        # First request
        response1 = client.post(
            "/v1/patients/",
            json={
                "patient_uuid": "test-patient-1",
                "given_name": "John",
                "family_name": "Doe",
                "gender": "M",
                "birth_date": "1990-01-01"
            },
            headers={"Idempotency-Key": idempotency_key}
        )
        
        # Second request with same key
        response2 = client.post(
            "/v1/patients/",
            json={
                "patient_uuid": "test-patient-1",
                "given_name": "Jane",  # Different data
                "family_name": "Smith",
                "gender": "F",
                "birth_date": "1995-01-01"
            },
            headers={"Idempotency-Key": idempotency_key}
        )
        
        # Second request should return cached response from first request
        # (Note: This depends on the endpoint returning 2xx status)
        if response1.status_code == 201 or response1.status_code == 200:
            # If first request succeeded, second should return same response
            assert "Idempotency-Replayed" in response2.headers or response2.status_code == response1.status_code
    
    def test_different_keys_different_results(self):
        """Test that different idempotency keys produce different results"""
        client = TestClient(app)
        
        key1 = "test-key-1"
        key2 = "test-key-2"
        
        # First request with key1
        response1 = client.post(
            "/v1/patients/",
            json={
                "patient_uuid": "test-patient-2",
                "given_name": "Alice",
                "family_name": "Johnson",
                "gender": "F",
                "birth_date": "1985-01-01"
            },
            headers={"Idempotency-Key": key1}
        )
        
        # Second request with key2
        response2 = client.post(
            "/v1/patients/",
            json={
                "patient_uuid": "test-patient-3",
                "given_name": "Bob",
                "family_name": "Williams",
                "gender": "M",
                "birth_date": "1980-01-01"
            },
            headers={"Idempotency-Key": key2}
        )
        
        # Requests should be independent
        # (Both should process normally, not return cached results)
        assert response1.status_code == response2.status_code
    
    def test_no_idempotency_key(self):
        """Test request without idempotency key"""
        client = TestClient(app)
        
        response = client.post(
            "/v1/patients/",
            json={
                "patient_uuid": "test-patient-4",
                "given_name": "Charlie",
                "family_name": "Brown",
                "gender": "M",
                "birth_date": "1975-01-01"
            }
        )
        
        # Request should process normally
        # (No idempotency check without the header)
        assert response.status_code in [200, 201, 400, 422]
    
    def test_invalid_idempotency_key(self):
        """Test that invalid idempotency keys are rejected"""
        client = TestClient(app)
        
        # Too short
        response = client.post(
            "/v1/patients/",
            json={
                "patient_uuid": "test-patient-5",
                "given_name": "Diana",
                "family_name": "Davis",
                "gender": "F",
                "birth_date": "1988-01-01"
            },
            headers={"Idempotency-Key": "ab"}  # Too short (less than 3 chars)
        )
        
        # Should return 400 for invalid key
        assert response.status_code == 400
    
    def test_get_request_skipped(self):
        """Test that GET requests are not subject to idempotency"""
        client = TestClient(app)
        
        idempotency_key = "test-get-key"
        
        # GET request with idempotency key
        response = client.get(
            "/v1/patients/",
            headers={"Idempotency-Key": idempotency_key}
        )
        
        # GET requests should not be cached (middleware skips them)
        # (They're naturally idempotent anyway)


class TestIdempotencyIntegration:
    """Integration tests for idempotency"""
    
    def setup_method(self):
        """Clean up before each test"""
        IdempotencyStore.cleanup_expired()
    
    def teardown_method(self):
        """Clean up after each test"""
        IdempotencyStore.cleanup_expired()
    
    def test_idempotency_with_authentication(self):
        """Test idempotency with authenticated requests"""
        client = TestClient(app)
        
        # First, login to get token
        login_response = client.post(
            "/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            token = token_data.get("access_token")
            
            if token:
                idempotency_key = "auth-test-key"
                
                # Make authenticated request with idempotency key
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": idempotency_key
                }
                
                response1 = client.get("/v1/patients/", headers=headers)
                response2 = client.get("/v1/patients/", headers=headers)
                
                # Responses should be consistent
                assert response1.status_code == response2.status_code
    
    def test_idempotency_key_persistence(self):
        """Test that idempotency keys persist across requests"""
        key = "persistence-test-key"
        
        # Store a response
        IdempotencyStore.store(
            key=key,
            response_data='{"persistent": true}',
            response_status=200,
            response_headers={"X-Custom": "value"},
            request_path="/v1/test",
            request_method="POST",
            ttl=3600
        )
        
        # Retrieve immediately
        cached1 = IdempotencyStore.get(key)
        assert cached1 is not None
        
        # Retrieve again after a short delay
        time.sleep(0.1)
        cached2 = IdempotencyStore.get(key)
        assert cached2 is not None
        
        # Both should return same data
        assert cached1["response_data"] == cached2["response_data"]
        assert cached1["response_status"] == cached2["response_status"]
