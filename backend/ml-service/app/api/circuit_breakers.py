"""
Circuit Breaker Monitoring API

Provides endpoints for monitoring and managing circuit breakers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.circuit_breaker import (
    get_all_circuit_breaker_states,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError
)
from app.auth import get_current_active_user
from app.models import User
from app.monitoring import MetricsManager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/circuit-breakers", tags=["Circuit Breakers"])


@router.get("", response_model=Dict[str, Any])
async def list_circuit_breakers(
    current_user: User = Depends(get_current_active_user)
):
    """
    List all circuit breakers and their states
    
    Requires authentication.
    
    Returns:
        Dictionary with circuit breaker states and statistics
    """
    try:
        states = get_all_circuit_breaker_states()
        
        # Add summary statistics
        total = len(states)
        open_count = sum(1 for s in states.values() if s["state"] == "open")
        half_open_count = sum(1 for s in states.values() if s["state"] == "half_open")
        closed_count = total - open_count - half_open_count
        
        return {
            "summary": {
                "total": total,
                "open": open_count,
                "half_open": half_open_count,
                "closed": closed_count,
                "health_status": "healthy" if open_count == 0 else "degraded"
            },
            "circuit_breakers": states,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error listing circuit breakers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve circuit breaker states"
        )


@router.get("/{name}", response_model=Dict[str, Any])
async def get_circuit_breaker(
    name: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed state of a specific circuit breaker
    
    Args:
        name: Circuit breaker name
        
    Returns:
        Detailed circuit breaker state
    """
    try:
        states = get_all_circuit_breaker_states()
        
        if name not in states:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Circuit breaker '{name}' not found"
            )
        
        cb_state = states[name]
        
        # Add health assessment
        health = "healthy"
        if cb_state["state"] == "open":
            health = "unhealthy"
        elif cb_state["state"] == "half_open":
            health = "recovering"
        elif cb_state["failure_rate"] > 10:
            health = "degraded"
        
        cb_state["health"] = health
        
        return cb_state
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting circuit breaker {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve circuit breaker '{name}'"
        )


@router.post("/{name}/reset", response_model=Dict[str, str])
async def reset_circuit_breaker(
    name: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Reset a circuit breaker to closed state
    
    **WARNING**: Only use this when the underlying service has been fixed.
    Manual reset during ongoing issues will cause the circuit to open again.
    
    Args:
        name: Circuit breaker name
        
    Returns:
        Confirmation message
    """
    try:
        states = get_all_circuit_breaker_states()
        
        if name not in states:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Circuit breaker '{name}' not found"
            )
        
        # Get and reset the circuit breaker
        cb = CircuitBreaker.get(name)
        cb.reset()
        
        logger.info(f"Circuit breaker '{name}' reset by user {current_user.username}")
        
        return {
            "message": f"Circuit breaker '{name}' has been reset to closed state",
            "name": name,
            "reset_by": current_user.username,
            "reset_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting circuit breaker {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker '{name}'"
        )


@router.get("/metrics/summary", response_model=Dict[str, Any])
async def get_circuit_breaker_metrics(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get circuit breaker metrics from Prometheus
    
    Returns aggregated metrics for all circuit breakers.
    """
    try:
        states = get_all_circuit_breaker_states()
        
        metrics = {
            "total_circuit_breakers": len(states),
            "open_circuits": 0,
            "half_open_circuits": 0,
            "closed_circuits": 0,
            "total_calls": 0,
            "total_failures": 0,
            "total_successes": 0,
            "average_failure_rate": 0.0,
            "circuit_breakers": {}
        }
        
        failure_rates = []
        
        for name, state in states.items():
            metrics["circuit_breakers"][name] = {
                "state": state["state"],
                "failure_rate": state["failure_rate"],
                "total_calls": state["total_calls"],
                "total_failures": state["total_failures"],
                "total_successes": state["total_successes"]
            }
            
            # Update counters
            if state["state"] == "open":
                metrics["open_circuits"] += 1
            elif state["state"] == "half_open":
                metrics["half_open_circuits"] += 1
            else:
                metrics["closed_circuits"] += 1
            
            metrics["total_calls"] += state["total_calls"]
            metrics["total_failures"] += state["total_failures"]
            metrics["total_successes"] += state["total_successes"]
            
            if state["total_calls"] > 0:
                failure_rates.append(state["failure_rate"])
        
        # Calculate average failure rate
        if failure_rates:
            metrics["average_failure_rate"] = sum(failure_rates) / len(failure_rates)
        
        metrics["generated_at"] = datetime.utcnow().isoformat()
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting circuit breaker metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve circuit breaker metrics"
        )


@router.post("/test", response_model=Dict[str, Any])
async def test_circuit_breaker(
    name: str,
    failure_threshold: int = 3,
    timeout: float = 10.0,
    current_user: User = Depends(get_current_active_user)
):
    """
    Test circuit breaker behavior
    
    Creates a temporary circuit breaker and simulates failures
    to demonstrate circuit breaker behavior.
    
    **WARNING**: This is for testing/demonstration only.
    
    Args:
        name: Unique name for test circuit breaker
        failure_threshold: Failures before opening
        timeout: Recovery timeout in seconds
        
    Returns:
        Test results
    """
    import time
    
    # Create test circuit breaker
    config = CircuitBreakerConfig(
        name=f"test_{name}",
        failure_threshold=failure_threshold,
        success_threshold=2,
        timeout=timeout
    )
    cb = CircuitBreaker(config)
    
    results = {
        "test_name": name,
        "config": {
            "failure_threshold": failure_threshold,
            "timeout": timeout
        },
        "steps": []
    }
    
    def failing_function():
        raise Exception("Simulated failure")
    
    def success_function():
        return "success"
    
    # Step 1: Normal operation
    try:
        result = cb.call(success_function)
        results["steps"].append({
            "step": 1,
            "action": "successful_call",
            "result": "success",
            "state": cb.state.state.value
        })
    except Exception as e:
        results["steps"].append({
            "step": 1,
            "action": "successful_call",
            "error": str(e),
            "state": cb.state.state.value
        })
    
    # Step 2: Trigger failures
    for i in range(failure_threshold):
        try:
            cb.call(failing_function)
        except CircuitBreakerOpenError:
            results["steps"].append({
                "step": 2 + i,
                "action": f"failure_{i+1}",
                "result": "circuit_opened",
                "state": cb.state.state.value
            })
            break
        except Exception:
            results["steps"].append({
                "step": 2 + i,
                "action": f"failure_{i+1}",
                "result": "failure_recorded",
                "state": cb.state.state.value,
                "failure_count": cb.state.failure_count
            })
    
    # Step 3: Try to call while open
    try:
        cb.call(success_function)
        results["steps"].append({
            "step": 2 + failure_threshold,
            "action": "call_while_open",
            "result": "unexpected_success",
            "state": cb.state.state.value
        })
    except CircuitBreakerOpenError as e:
        results["steps"].append({
            "step": 2 + failure_threshold,
            "action": "call_while_open",
            "result": "blocked_as_expected",
            "state": cb.state.state.value,
            "error": str(e)
        })
    
    # Clean up test circuit breaker
    del CircuitBreaker._instances[f"test_{name}"]
    
    results["final_state"] = cb.get_state()
    results["test_completed_at"] = datetime.utcnow().isoformat()
    
    return results
