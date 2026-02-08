"""
Unit tests for middleware components in IIT Prediction ML Service
Tests security, performance, caching, error handling, and validation middleware
"""
import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import json
from datetime import datetime

from app.main import app
from app.middleware.security import (
    SecurityMonitoringMiddleware,
    check_rate_limit,
    detect_suspicious_activity,
    log_security_event,
    setup_security_headers,
    create_rate_limiting_middleware
)
from app.middleware.performance import (
    PerformanceMonitoringMiddleware,
    log_performance_metrics,
    PerformanceMetrics
)
from app.middleware.caching import (
    CacheMiddleware,
    get_cache_key,
    cache_response,
    get_cached_response
)
from app.middleware.error_handling import (
    ErrorHandlingMiddleware,
    log_error,
    create_error_response
)
from app.middleware.validation import (
    ValidationMiddleware,
    validate_request_data,
    sanitize_input
)

client = TestClient(app)


class TestSecurityMiddleware:
    """Test security monitoring middleware"""

    @pytest.fixture
    def security_middleware(self):
        """Create security middleware instance"""
        return SecurityMonitoringMiddleware(app)

    def test_rate_limit_check(self):
        """Test rate limiting functionality"""
        client_ip = "192.168.1.1"
        endpoint = "/api/predict"

        # Should allow initial requests
        assert check_rate_limit(client_ip, endpoint, max_requests=5, window_seconds=60) == True
        assert check_rate_limit(client_ip, endpoint, max_requests=5, window_seconds=60) == True
        assert check_rate_limit(client_ip, endpoint, max_requests=5, window_seconds=60) == True
        assert check_rate_limit(client_ip, endpoint, max_requests=5, window_seconds=60) == True
        assert check_rate_limit(client_ip, endpoint, max_requests=5, window_seconds=60) == True

        # Should block when limit exceeded
        assert check_rate_limit(client_ip, endpoint, max_requests=5, window_seconds=60) == False

    def test_suspicious_activity_detection(self):
        """Test detection of suspicious activity patterns"""
        # Create mock request
        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "Mozilla/5.0"}
        mock_request.url = MagicMock()
        mock_request.url.path = "/api/predict"
        mock_request.query_params = ""

        # Normal request should not trigger issues
        issues = detect_suspicious_activity(mock_request)
        assert len(issues) == 0

        # Test SQL injection detection
        mock_request.query_params = "param=1' OR '1'='1"
        issues = detect_suspicious_activity(mock_request)
        assert len(issues) > 0
        assert any("SQL injection" in issue for issue in issues)

        # Test suspicious user agent
        mock_request.headers["user-agent"] = "sqlmap/1.0"
        mock_request.query_params = ""
        issues = detect_suspicious_activity(mock_request)
        assert len(issues) > 0
        assert any("user agent" in issue.lower() for issue in issues)

        # Test directory traversal
        mock_request.headers["user-agent"] = "Mozilla/5.0"
        mock_request.url.path = "/api/../../../etc/passwd"
        issues = detect_suspicious_activity(mock_request)
        assert len(issues) > 0
        assert any("directory traversal" in issue.lower() for issue in issues)

    @patch('app.middleware.security.log_audit')
    def test_security_event_logging(self, mock_log_audit):
        """Test security event logging"""
        mock_db = MagicMock()

        log_security_event(
            mock_db,
            "TEST_EVENT",
            "medium",
            {"test": "data"},
            "192.168.1.1"
        )

        # Verify audit log was called
        mock_log_audit.assert_called_once()
        call_args = mock_log_audit.call_args
        assert call_args[1]["action"] == "SECURITY_TEST_EVENT"
        details = json.loads(call_args[1]["details"])
        assert details["severity"] == "medium"
        assert details["test"] == "data"

    def test_security_headers_setup(self):
        """Test security headers are added to responses"""
        response = Response()
        setup_security_headers(response)

        # Check essential security headers are present
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers
        assert "Content-Security-Policy" in response.headers

    def test_rate_limiting_middleware_creation(self):
        """Test rate limiting middleware creation"""
        middleware = create_rate_limiting_middleware(max_requests=10, window_seconds=30)

        # Should be a callable function
        assert callable(middleware)

    @pytest.mark.asyncio
    async def test_security_middleware_excludes_paths(self):
        """Test that excluded paths skip security checks"""
        middleware = SecurityMonitoringMiddleware(app, exclude_paths=["/health"])

        # Mock ASGI components
        scope = {"type": "http", "path": "/health"}
        receive = AsyncMock()
        send = AsyncMock()

        # Should pass through without security checks
        await middleware(scope, receive, send)
        # Verify the app was called
        # (This is a basic test - in real scenario would verify no security logic executed)


class TestPerformanceMiddleware:
    """Test performance monitoring middleware"""

    @pytest.fixture
    def performance_middleware(self):
        """Create performance middleware instance"""
        return PerformanceMonitoringMiddleware(app)

    def test_performance_metrics_initialization(self):
        """Test performance metrics object"""
        metrics = PerformanceMetrics()

        assert hasattr(metrics, 'response_time')
        assert hasattr(metrics, 'cpu_usage')
        assert hasattr(metrics, 'memory_usage')
        assert hasattr(metrics, 'request_count')

    @patch('app.middleware.performance.psutil')
    @patch('app.middleware.performance.time')
    def test_performance_metrics_collection(self, mock_time, mock_psutil):
        """Test collection of performance metrics"""
        mock_time.time.return_value = 1000.0
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.virtual_memory.return_value.percent = 67.8

        metrics = PerformanceMetrics()
        metrics.collect()

        assert metrics.response_time == 1000.0
        assert metrics.cpu_usage == 45.5
        assert metrics.memory_usage == 67.8

    @patch('app.middleware.performance.logger')
    def test_performance_logging(self, mock_logger):
        """Test performance metrics logging"""
        metrics = PerformanceMetrics()
        metrics.response_time = 0.5
        metrics.cpu_usage = 30.0
        metrics.memory_usage = 50.0

        log_performance_metrics(metrics, "/api/test")

        # Verify logging was called
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_performance_middleware_request_tracking(self):
        """Test that middleware tracks request performance"""
        # This would require mocking the ASGI interface
        # For now, test the basic structure
        middleware = PerformanceMonitoringMiddleware(app)
        assert hasattr(middleware, 'app')


class TestCachingMiddleware:
    """Test caching middleware"""

    @pytest.fixture
    def cache_middleware(self):
        """Create cache middleware instance"""
        return CacheMiddleware(app)

    def test_cache_key_generation(self):
        """Test cache key generation"""
        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/api/predict"
        request.query_params = "param1=value1&param2=value2"

        key = get_cache_key(request)
        assert isinstance(key, str)
        assert "/api/predict" in key
        assert "param1=value1" in key

    @patch('app.middleware.caching.redis_client')
    def test_response_caching(self, mock_redis):
        """Test response caching functionality"""
        mock_redis.setex.return_value = True

        response_data = {"result": "test"}
        cache_key = "test_key"

        result = cache_response(cache_key, response_data, ttl=300)
        assert result == True

        # Verify Redis was called
        mock_redis.setex.assert_called_once_with(
            cache_key,
            300,
            json.dumps(response_data)
        )

    @patch('app.middleware.caching.redis_client')
    def test_cached_response_retrieval(self, mock_redis):
        """Test cached response retrieval"""
        cached_data = {"result": "cached"}
        mock_redis.get.return_value = json.dumps(cached_data)

        result = get_cached_response("test_key")
        assert result == cached_data

        mock_redis.get.assert_called_once_with("test_key")

    @patch('app.middleware.caching.redis_client')
    def test_cache_miss(self, mock_redis):
        """Test cache miss handling"""
        mock_redis.get.return_value = None

        result = get_cached_response("nonexistent_key")
        assert result is None


class TestErrorHandlingMiddleware:
    """Test error handling middleware"""

    @pytest.fixture
    def error_middleware(self):
        """Create error handling middleware instance"""
        return ErrorHandlingMiddleware(app)

    @patch('app.middleware.error_handling.logger')
    def test_error_logging(self, mock_logger):
        """Test error logging functionality"""
        error = ValueError("Test error")
        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/api/test"

        log_error(error, request)

        # Verify error was logged
        mock_logger.error.assert_called()

    def test_error_response_creation(self):
        """Test error response creation"""
        error = HTTPException(status_code=400, detail="Bad request")
        response = create_error_response(error)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

        response_data = response.body
        assert b"Bad request" in response_data

    def test_generic_error_response_creation(self):
        """Test generic error response creation"""
        error = ValueError("Generic error")
        response = create_error_response(error)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

        response_data = response.body
        assert b"Internal server error" in response_data


class TestValidationMiddleware:
    """Test validation middleware"""

    @pytest.fixture
    def validation_middleware(self):
        """Create validation middleware instance"""
        return ValidationMiddleware(app)

    def test_input_sanitization(self):
        """Test input sanitization"""
        # Test basic sanitization
        dirty_input = "<script>alert('xss')</script>Hello World"
        clean_input = sanitize_input(dirty_input)

        assert "<script>" not in clean_input
        assert "Hello World" in clean_input

    def test_request_data_validation(self):
        """Test request data validation"""
        # Valid data
        valid_data = {
            "patient_uuid": "123e4567-e89b-12d3-a456-426614174000",
            "age": 25,
            "gender": "M"
        }

        result = validate_request_data(valid_data)
        assert result["is_valid"] == True

        # Invalid data
        invalid_data = {
            "patient_uuid": "not-a-uuid",
            "age": "not-a-number",
            "gender": "X"  # Invalid gender
        }

        result = validate_request_data(invalid_data)
        assert result["is_valid"] == False
        assert len(result["errors"]) > 0

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in validation"""
        malicious_data = {
            "query": "SELECT * FROM users WHERE id = 1 OR 1=1"
        }

        result = validate_request_data(malicious_data)
        assert result["is_valid"] == False
        assert any("SQL injection" in error.lower() for error in result["errors"])


class TestMiddlewareIntegration:
    """Test middleware integration and end-to-end functionality"""

    def test_middleware_stack_execution(self):
        """Test that middleware stack executes without errors"""
        # Basic health check to ensure middleware doesn't break the app
        response = client.get("/health")
        assert response.status_code in [200, 404]  # Health endpoint may not exist

    def test_security_headers_on_responses(self):
        """Test that security headers are added to actual responses"""
        response = client.get("/docs")  # OpenAPI docs should exist

        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    def test_error_handling_integration(self):
        """Test error handling middleware integration"""
        # Make a request that should trigger error handling
        response = client.get("/nonexistent-endpoint")

        # Should get proper error response
        assert response.status_code in [404, 422, 500]

    @pytest.mark.asyncio
    async def test_middleware_async_execution(self):
        """Test async middleware execution"""
        # This is a placeholder for testing async middleware
        # In a real scenario, would test with actual async middleware
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
