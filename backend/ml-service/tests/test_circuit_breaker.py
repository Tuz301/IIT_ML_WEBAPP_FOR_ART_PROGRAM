"""
Circuit Breaker Tests

Tests for the circuit breaker implementation including:
- State transitions (closed -> open -> half-open -> closed)
- Failure counting
- Recovery behavior
- Fallback functions
- Thread safety
"""

import pytest
import time
from threading import Thread
from app.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    circuit_breaker,
    get_all_circuit_breaker_states,
    CircuitState
)


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def setup_method(self):
        """Reset circuit breakers before each test"""
        CircuitBreaker.reset_all()
    
    def teardown_method(self):
        """Clean up after each test"""
        CircuitBreaker.reset_all()
    
    def test_circuit_breaker_initial_state(self):
        """Test that circuit breaker starts in closed state"""
        config = CircuitBreakerConfig(
            name="test_initial",
            failure_threshold=3,
            timeout=10.0
        )
        cb = CircuitBreaker(config)
        
        assert cb.state.state == CircuitState.CLOSED
        assert cb.state.failure_count == 0
        assert cb.state.success_count == 0
        assert cb.state.total_calls == 0
    
    def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after failure threshold is reached"""
        config = CircuitBreakerConfig(
            name="test_open",
            failure_threshold=3,
            timeout=10.0
        )
        cb = CircuitBreaker(config)
        
        def failing_function():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception):
            cb.call(failing_function)
        assert cb.state.state == CircuitState.CLOSED
        assert cb.state.failure_count == 1
        
        # Second failure
        with pytest.raises(Exception):
            cb.call(failing_function)
        assert cb.state.state == CircuitState.CLOSED
        assert cb.state.failure_count == 2
        
        # Third failure - should open circuit
        with pytest.raises(Exception):
            cb.call(failing_function)
        assert cb.state.state == CircuitState.OPEN
        assert cb.state.failure_count == 3
        assert cb.state.opened_at is not None
    
    def test_circuit_blocks_requests_when_open(self):
        """Test that requests are blocked when circuit is open"""
        config = CircuitBreakerConfig(
            name="test_block",
            failure_threshold=2,
            timeout=60.0  # Long timeout for this test
        )
        cb = CircuitBreaker(config)
        
        def failing_function():
            raise Exception("Test failure")
        
        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_function)
        
        assert cb.state.state == CircuitState.OPEN
        
        # Next call should be blocked immediately
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(failing_function)
        
        # Should not increment failure count
        assert cb.state.failure_count == 2
    
    def test_circuit_transitions_to_half_open_after_timeout(self):
        """Test that circuit transitions to half-open after timeout"""
        config = CircuitBreakerConfig(
            name="test_half_open",
            failure_threshold=2,
            timeout=0.1  # Short timeout for testing
        )
        cb = CircuitBreaker(config)
        
        def failing_function():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_function)
        
        assert cb.state.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.15)
        
        # Next call should transition to half-open
        with pytest.raises(Exception):
            cb.call(failing_function)
        
        assert cb.state.state == CircuitState.HALF_OPEN
    
    def test_circuit_closes_after_successful_recovery(self):
        """Test that circuit closes after successful calls in half-open state"""
        config = CircuitBreakerConfig(
            name="test_recovery",
            failure_threshold=2,
            success_threshold=2,
            timeout=0.1
        )
        cb = CircuitBreaker(config)
        
        def failing_function():
            raise Exception("Test failure")
        
        def success_function():
            return "success"
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_function)
        
        assert cb.state.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.15)
        
        # First success in half-open
        result = cb.call(success_function)
        assert result == "success"
        assert cb.state.state == CircuitState.HALF_OPEN
        assert cb.state.success_count == 1
        
        # Second success should close circuit
        result = cb.call(success_function)
        assert result == "success"
        assert cb.state.state == CircuitState.CLOSED
        assert cb.state.failure_count == 0
    
    def test_circuit_reopens_on_failure_in_half_open(self):
        """Test that circuit reopens if failure occurs in half-open state"""
        config = CircuitBreakerConfig(
            name="test_reopen",
            failure_threshold=2,
            success_threshold=2,
            timeout=0.1
        )
        cb = CircuitBreaker(config)
        
        def failing_function():
            raise Exception("Test failure")
        
        def success_function():
            return "success"
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_function)
        
        # Wait for timeout
        time.sleep(0.15)
        
        # First success in half-open
        cb.call(success_function)
        assert cb.state.state == CircuitState.HALF_OPEN
        
        # Failure in half-open should reopen circuit
        with pytest.raises(Exception):
            cb.call(failing_function)
        
        assert cb.state.state == CircuitState.OPEN
        assert cb.state.success_count == 0
    
    def test_fallback_function(self):
        """Test that fallback function is called when circuit is open"""
        def fallback():
            return "fallback_value"
        
        config = CircuitBreakerConfig(
            name="test_fallback",
            failure_threshold=2,
            timeout=60.0,
            fallback=fallback
        )
        cb = CircuitBreaker(config)
        
        def failing_function():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_function)
        
        # Call should use fallback
        result = cb.call(failing_function)
        assert result == "fallback_value"
    
    def test_get_state(self):
        """Test getting circuit breaker state"""
        config = CircuitBreakerConfig(
            name="test_state",
            failure_threshold=3,
            timeout=10.0
        )
        cb = CircuitBreaker(config)
        
        state = cb.get_state()
        
        assert state["name"] == "test_state"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["total_calls"] == 0
        assert state["failure_rate"] == 0
        assert "config" in state
    
    def test_reset(self):
        """Test resetting circuit breaker"""
        config = CircuitBreakerConfig(
            name="test_reset",
            failure_threshold=2,
            timeout=10.0
        )
        cb = CircuitBreaker(config)
        
        def failing_function():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_function)
        
        assert cb.state.state == CircuitState.OPEN
        
        # Reset
        cb.reset()
        
        assert cb.state.state == CircuitState.CLOSED
        assert cb.state.failure_count == 0
        assert cb.state.opened_at is None
    
    def test_decorator_usage(self):
        """Test using circuit breaker as a decorator"""
        call_count = {"success": 0, "failure": 0}
        
        @circuit_breaker("decorator_test", failure_threshold=2, timeout=1.0)
        def protected_function(should_fail=False):
            if should_fail:
                call_count["failure"] += 1
                raise Exception("Decorated function failed")
            call_count["success"] += 1
            return "success"
        
        # Successful calls
        assert protected_function() == "success"
        assert protected_function() == "success"
        assert call_count["success"] == 2
        
        # Trigger failures
        with pytest.raises(Exception):
            protected_function(should_fail=True)
        with pytest.raises(Exception):
            protected_function(should_fail=True)
        
        # Circuit should be open
        with pytest.raises(CircuitBreakerOpenError):
            protected_function()
        
        assert call_count["failure"] == 2
    
    def test_thread_safety(self):
        """Test that circuit breaker is thread-safe"""
        config = CircuitBreakerConfig(
            name="test_thread_safety",
            failure_threshold=100,  # High threshold
            timeout=10.0
        )
        cb = CircuitBreaker(config)
        
        call_count = [0]
        
        def make_calls():
            def success_function():
                call_count[0] += 1
                return "success"
            
            for _ in range(50):
                try:
                    cb.call(success_function)
                except Exception:
                    pass
        
        # Create multiple threads
        threads = [Thread(target=make_calls) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All calls should have been counted
        assert call_count[0] == 250  # 50 calls * 5 threads
        assert cb.state.total_calls == 250
    
    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly"""
        config = CircuitBreakerConfig(
            name="test_stats",
            failure_threshold=3,
            timeout=10.0
        )
        cb = CircuitBreaker(config)
        
        def success_function():
            return "success"
        
        def failing_function():
            raise Exception("Test failure")
        
        # Mix of successes and failures
        for i in range(10):
            if i < 7:
                cb.call(success_function)
            else:
                try:
                    cb.call(failing_function)
                except Exception:
                    pass
        
        state = cb.get_state()
        assert state["total_calls"] == 10
        assert state["total_successes"] == 7
        assert state["total_failures"] == 3
        assert state["failure_rate"] == 30.0


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker"""
    
    def setup_method(self):
        """Reset circuit breakers before each test"""
        CircuitBreaker.reset_all()
    
    def teardown_method(self):
        """Clean up after each test"""
        CircuitBreaker.reset_all()
    
    def test_multiple_circuit_breakers(self):
        """Test managing multiple circuit breakers"""
        # Create multiple circuit breakers
        configs = [
            CircuitBreakerConfig(name="cb1", failure_threshold=2, timeout=10.0),
            CircuitBreakerConfig(name="cb2", failure_threshold=3, timeout=20.0),
            CircuitBreakerConfig(name="cb3", failure_threshold=5, timeout=30.0),
        ]
        
        for config in configs:
            CircuitBreaker.get(config.name, config)
        
        # Get all states
        states = get_all_circuit_breaker_states()
        
        assert len(states) == 3
        assert "cb1" in states
        assert "cb2" in states
        assert "cb3" in states
    
    def test_get_existing_circuit_breaker(self):
        """Test getting existing circuit breaker"""
        config = CircuitBreakerConfig(name="test_get", failure_threshold=2, timeout=10.0)
        cb1 = CircuitBreaker.get("test_get", config)
        
        # Get same circuit breaker again
        cb2 = CircuitBreaker.get("test_get")
        
        # Should be the same instance
        assert cb1 is cb2
    
    def test_get_nonexistent_circuit_breaker(self):
        """Test getting non-existent circuit breaker without config"""
        with pytest.raises(ValueError, match="not found"):
            CircuitBreaker.get("nonexistent")
