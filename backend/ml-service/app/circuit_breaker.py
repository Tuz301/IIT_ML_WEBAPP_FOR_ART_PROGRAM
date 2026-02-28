"""
Circuit Breaker Implementation for Production Resilience

Implements the Circuit Breaker pattern to prevent cascading failures
when external dependencies (APIs, databases, services) are unavailable
or experiencing issues.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit is tripped, requests fail immediately
- HALF_OPEN: Testing if service has recovered

Usage:
    @circuit_breaker("external_api")
    def call_external_api():
        # Your API call here
        pass
"""

import time
import threading
from typing import Callable, Optional, Any, Dict
from functools import wraps
from enum import Enum
from dataclasses import dataclass, field

from app.config import settings
from app.monitoring import MetricsManager


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit tripped, fail fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for a single circuit breaker"""
    name: str
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 2          # Successes to close from half-open
    timeout: float = 60.0               # Seconds before attempting recovery
    expected_exception: Exception = Exception
    fallback: Optional[Callable] = None
    
    def __post_init__(self):
        """Validate configuration"""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")
        if self.timeout < 1:
            raise ValueError("timeout must be >= 1")


@dataclass
class CircuitBreakerState:
    """Runtime state of a circuit breaker"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state: CircuitState = CircuitState.CLOSED
    opened_at: Optional[float] = None
    
    # Statistics
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit Breaker implementation
    
    Tracks failures and opens the circuit when threshold is exceeded.
    Automatically attempts recovery after timeout period.
    """
    
    _instances: Dict[str, 'CircuitBreaker'] = {}
    _lock = threading.Lock()
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState()
        self._lock = threading.RLock()
        
        # Register metrics
        self._init_metrics()
    
    def _init_metrics(self):
        """Initialize Prometheus metrics for this circuit breaker"""
        self.metrics = MetricsManager
        
        # Register circuit-specific metrics
        self.metrics.register_circuit_breaker(
            name=self.config.name,
            failure_threshold=self.config.failure_threshold,
            timeout=self.config.timeout
        )
    
    @classmethod
    def get(cls, name: str, config: Optional[CircuitBreakerConfig] = None) -> 'CircuitBreaker':
        """Get or create circuit breaker instance"""
        with cls._lock:
            if name not in cls._instances:
                if config is None:
                    raise ValueError(f"Circuit breaker '{name}' not found and no config provided")
                cls._instances[name] = cls(config)
            return cls._instances[name]
    
    @classmethod
    def reset_all(cls):
        """Reset all circuit breakers (useful for testing)"""
        with cls._lock:
            for cb in cls._instances.values():
                cb.reset()
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        with self._lock:
            self.state = CircuitBreakerState()
            self._log_state_change("reset")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.state.opened_at is None:
            return False
        
        elapsed = time.time() - self.state.opened_at
        return elapsed >= self.config.timeout
    
    def _log_state_change(self, action: str, **kwargs):
        """Log state changes for monitoring"""
        import logging
        logger = logging.getLogger(__name__)
        
        log_data = {
            "circuit_breaker": self.config.name,
            "action": action,
            "state": self.state.state.value,
            "failure_count": self.state.failure_count,
            "total_calls": self.state.total_calls,
            **kwargs
        }
        
        if action in ["opened", "failed_in_half_open"]:
            logger.warning(f"Circuit breaker event: {action}", extra=log_data)
        else:
            logger.info(f"Circuit breaker event: {action}", extra=log_data)
    
    def _record_success(self):
        """Record a successful call"""
        with self._lock:
            self.state.success_count += 1
            self.state.total_successes += 1
            self.state.last_success_time = time.time()
            
            if self.state.state == CircuitState.HALF_OPEN:
                if self.state.success_count >= self.config.success_threshold:
                    # Circuit recovered, close it
                    old_state = self.state.state
                    self.state.state = CircuitState.CLOSED
                    self.state.failure_count = 0
                    self.state.success_count = 0
                    self.state.opened_at = None
                    self._log_state_change("closed", previous_state=old_state.value)
    
    def _record_failure(self, exception: Exception):
        """Record a failed call"""
        with self._lock:
            self.state.failure_count += 1
            self.state.total_failures += 1
            self.state.last_failure_time = time.time()
            
            if self.state.state == CircuitState.CLOSED:
                if self.state.failure_count >= self.config.failure_threshold:
                    # Open the circuit
                    self.state.state = CircuitState.OPEN
                    self.state.opened_at = time.time()
                    self._log_state_change(
                        "opened",
                        failure_count=self.state.failure_count,
                        threshold=self.config.failure_threshold
                    )
            
            elif self.state.state == CircuitState.HALF_OPEN:
                # Failed during recovery, reopen
                self.state.state = CircuitState.OPEN
                self.state.opened_at = time.time()
                self.state.success_count = 0
                self._log_state_change("failed_in_half_open")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function return value
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        self.state.total_calls += 1
        
        # Check circuit state
        with self._lock:
            if self.state.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    # Transition to half-open for testing
                    self.state.state = CircuitState.HALF_OPEN
                    self.state.success_count = 0
                    self._log_state_change("half_open")
                else:
                    # Circuit is still open
                    self.metrics.record_circuit_breaker_blocked(self.config.name)
                    raise CircuitBreakerOpenError(
                        f"Circuit '{self.config.name}' is OPEN. "
                        f"Opened {time.time() - self.state.opened_at:.1f}s ago. "
                        f"Timeout: {self.config.timeout}s"
                    )
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            self.metrics.record_circuit_breaker_success(self.config.name)
            return result
            
        except self.config.expected_exception as e:
            self._record_failure(e)
            self.metrics.record_circuit_breaker_failure(self.config.name, type(e).__name__)
            
            # Try fallback if available
            if self.config.fallback:
                return self.config.fallback(*args, **kwargs)
            
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state for monitoring"""
        with self._lock:
            return {
                "name": self.config.name,
                "state": self.state.state.value,
                "failure_count": self.state.failure_count,
                "success_count": self.state.success_count,
                "total_calls": self.state.total_calls,
                "total_failures": self.state.total_failures,
                "total_successes": self.state.total_successes,
                "failure_rate": (
                    self.state.total_failures / self.state.total_calls * 100
                    if self.state.total_calls > 0 else 0
                ),
                "last_failure_time": self.state.last_failure_time,
                "last_success_time": self.state.last_success_time,
                "opened_at": self.state.opened_at,
                "time_since_open": (
                    time.time() - self.state.opened_at
                    if self.state.opened_at else None
                ),
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout,
                }
            }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit is open and requests are blocked"""
    pass


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout: float = 60.0,
    expected_exception: Exception = Exception,
    fallback: Optional[Callable] = None
):
    """
    Decorator for circuit breaker protection
    
    Args:
        name: Unique name for this circuit breaker
        failure_threshold: Number of failures before opening circuit
        success_threshold: Number of successes needed to close circuit
        timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type that counts as failure
        fallback: Optional fallback function when circuit is open
    
    Usage:
        @circuit_breaker("external_api", failure_threshold=3, timeout=30)
        def call_external_api():
            return requests.get("https://api.example.com")
    
        @circuit_breaker("database", fallback=lambda: cached_data)
        def get_from_db():
            return db.query(...)
    """
    config = CircuitBreakerConfig(
        name=name,
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timeout,
        expected_exception=expected_exception,
        fallback=fallback
    )
    cb = CircuitBreaker.get(name, config)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        return wrapper
    
    return decorator


# Predefined circuit breakers for common services
def get_database_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for database operations"""
    return CircuitBreaker.get("database", CircuitBreakerConfig(
        name="database",
        failure_threshold=5,
        success_threshold=2,
        timeout=30.0,
        expected_exception=Exception  # Will be refined to specific DB exceptions
    ))


def get_redis_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for Redis operations"""
    return CircuitBreaker.get("redis", CircuitBreakerConfig(
        name="redis",
        failure_threshold=10,
        success_threshold=3,
        timeout=20.0,
        expected_exception=Exception
    ))


def get_external_api_circuit_breaker(api_name: str) -> CircuitBreaker:
    """Get circuit breaker for external API calls"""
    return CircuitBreaker.get(f"external_api_{api_name}", CircuitBreakerConfig(
        name=f"external_api_{api_name}",
        failure_threshold=3,
        success_threshold=2,
        timeout=60.0,
        expected_exception=Exception
    ))


def get_all_circuit_breaker_states() -> Dict[str, Dict[str, Any]]:
    """Get state of all circuit breakers for monitoring endpoint"""
    return {
        name: cb.get_state()
        for name, cb in CircuitBreaker._instances.items()
    }
