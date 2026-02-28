"""
Tests for Retry Mechanism
"""
import pytest
import time
from unittest.mock import Mock, patch
from tenacity import RetryError

from app.utils.retry import (
    database_retry,
    api_retry,
    redis_retry,
    retry_on_transient,
    TransientError,
    RetryableError,
)


class TestDatabaseRetry:
    """Test database retry decorator"""
    
    def test_successful_database_call(self):
        """Test successful database call without retry"""
        call_count = [0]
        
        @database_retry(max_attempts=3)
        def mock_db_call():
            call_count[0] += 1
            return "success"
        
        result = mock_db_call()
        
        assert result == "success"
        assert call_count[0] == 1
    
    @patch('app.utils.retry.time.sleep')
    def test_database_retry_on_failure(self, mock_sleep):
        """Test database retry on failure"""
        call_count = [0]
        
        @database_retry(max_attempts=3, wait_min=0.1, wait_max=0.1)
        def mock_db_call():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Connection error")
            return "success"
        
        result = mock_db_call()
        
        assert result == "success"
        assert call_count[0] == 2
        assert mock_sleep.call_count == 1
    
    @patch('app.utils.retry.time.sleep')
    def test_database_retry_exhausted(self, mock_sleep):
        """Test database retry exhausted"""
        @database_retry(max_attempts=2, wait_min=0.1, wait_max=0.1, reraise=True)
        def mock_db_call():
            raise Exception("Connection error")
        
        with pytest.raises(Exception) as exc_info:
            mock_db_call()
        
        assert str(exc_info.value) == "Connection error"
        assert mock_sleep.call_count == 1


class TestAPIRetry:
    """Test API retry decorator"""
    
    def test_successful_api_call(self):
        """Test successful API call without retry"""
        @api_retry()
        def mock_api_call():
            return {"status": "ok"}
        
        result = mock_api_call()
        
        assert result["status"] == "ok"
    
    @patch('app.utils.retry.time.sleep')
    def test_api_retry_on_failure(self, mock_sleep):
        """Test API retry on failure"""
        call_count = [0]
        
        @api_retry(max_attempts=3, wait_min=0.1, wait_max=0.1)
        def mock_api_call():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Network error")
            return {"status": "ok"}
        
        result = mock_api_call()
        
        assert result["status"] == "ok"
        assert call_count[0] == 2
    
    @patch('app.utils.retry.time.sleep')
    def test_api_retry_on_503_status(self, mock_sleep):
        """Test API retry on HTTP 503 status"""
        call_count = [0]
        
        # Mock response object
        class MockResponse:
            def __init__(self, status_code):
                self.status_code = status_code
        
        @api_retry(max_attempts=3, wait_min=0.1, wait_max=0.1)
        def mock_api_call():
            call_count[0] += 1
            if call_count[0] < 2:
                return MockResponse(503)
            return MockResponse(200)
        
        result = mock_api_call()
        
        assert result.status_code == 200
        assert call_count[0] == 2
    
    @patch('app.utils.retry.time.sleep')
    def test_api_retry_exhausted(self, mock_sleep):
        """Test API retry exhausted"""
        @api_retry(max_attempts=2, wait_min=0.1, wait_max=0.1, reraise=True)
        def mock_api_call():
            raise Exception("Network error")
        
        with pytest.raises(Exception) as exc_info:
            mock_api_call()
        
        assert str(exc_info.value) == "Network error"


class TestRedisRetry:
    """Test Redis retry decorator"""
    
    def test_successful_redis_call(self):
        """Test successful Redis call without retry"""
        @redis_retry()
        def mock_redis_call():
            return "ok"
        
        result = mock_redis_call()
        
        assert result == "ok"
    
    @patch('app.utils.retry.time.sleep')
    def test_redis_retry_on_connection_error(self, mock_sleep):
        """Test Redis retry on connection error"""
        call_count = [0]
        
        @redis_retry(max_attempts=3, wait_min=0.1, wait_max=0.1)
        def mock_redis_call():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Connection timeout")
            return "ok"
        
        result = mock_redis_call()
        
        assert result == "ok"
        assert call_count[0] == 2
    
    @patch('app.utils.retry.time.sleep')
    def test_redis_retry_no_retry_on_other_errors(self, mock_sleep):
        """Test Redis retry doesn't retry on non-connection errors"""
        @redis_retry(max_attempts=3, wait_min=0.1, wait_max=0.1, reraise=True)
        def mock_redis_call():
            raise ValueError("Invalid key format")
        
        with pytest.raises(ValueError) as exc_info:
            mock_redis_call()
        
        assert str(exc_info.value) == "Invalid key format"
        assert mock_sleep.call_count == 0  # Should not sleep


class TestRetryOnTransient:
    """Test retry on transient errors"""
    
    def test_successful_call(self):
        """Test successful call without retry"""
        @retry_on_transient()
        def mock_call():
            return "success"
        
        result = mock_call()
        
        assert result == "success"
    
    @patch('app.utils.retry.time.sleep')
    def test_retry_on_transient_error(self, mock_sleep):
        """Test retry on TransientError"""
        call_count = [0]
        
        @retry_on_transient(max_attempts=3, wait_min=0.1, wait_max=0.1)
        def mock_call():
            call_count[0] += 1
            if call_count[0] < 2:
                raise TransientError("Temporary error")
            return "success"
        
        result = mock_call()
        
        assert result == "success"
        assert call_count[0] == 2
    
    @patch('app.utils.retry.time.sleep')
    def test_no_retry_on_non_transient_error(self, mock_sleep):
        """Test no retry on non-transient errors"""
        @retry_on_transient(max_attempts=3, reraise=True)
        def mock_call():
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError) as exc_info:
            mock_call()
        
        assert str(exc_info.value) == "Permanent error"
        assert mock_sleep.call_count == 0


class TestRetryableErrors:
    """Test retryable error classes"""
    
    def test_transient_error_is_retryable(self):
        """Test TransientError is a RetryableError"""
        error = TransientError("Temporary issue")
        
        assert isinstance(error, RetryableError)
    
    def test_custom_retryable_error(self):
        """Test custom retryable error"""
        class CustomRetryableError(RetryableError):
            pass
        
        error = CustomRetryableError("Custom issue")
        
        assert isinstance(error, RetryableError)


class TestRetryConfiguration:
    """Test retry configuration"""
    
    @patch('app.utils.retry.settings')
    def test_default_configuration(self, mock_settings):
        """Test default retry configuration from settings"""
        mock_settings.retry_max_attempts = 3
        mock_settings.retry_wait_min = 1.0
        mock_settings.retry_wait_max = 10.0
        
        from app.utils.retry import _get_retry_config
        
        attempts, min_wait, max_wait = _get_retry_config()
        
        assert attempts == 3
        assert min_wait == 1.0
        assert max_wait == 10.0
    
    @patch('app.utils.retry.settings')
    def test_custom_configuration(self, mock_settings):
        """Test custom retry configuration overrides defaults"""
        mock_settings.retry_max_attempts = 3
        mock_settings.retry_wait_min = 1.0
        mock_settings.retry_wait_max = 10.0
        
        from app.utils.retry import _get_retry_config
        
        attempts, min_wait, max_wait = _get_retry_config(
            max_attempts=5,
            wait_min=0.5,
            wait_max=5.0
        )
        
        assert attempts == 5
        assert min_wait == 0.5
        assert max_wait == 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
