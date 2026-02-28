"""
Alerting API Endpoints

Provides endpoints for sending test alerts and managing alert configurations.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.alerting import (
    AlertManager,
    Alert,
    AlertSeverity,
    AlertEventType,
    get_alert_manager,
    send_pagerduty_alert,
    send_slack_notification
)
from app.auth import get_current_active_user
from app.models import User

router = APIRouter(prefix="/alerting", tags=["Alerting"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AlertRequest(BaseModel):
    """Request model for sending an alert"""
    event_type: str = Field(..., description="Event type from AlertEventType enum")
    severity: str = Field(..., description="Severity level from AlertSeverity enum")
    summary: str = Field(..., description="Alert summary/title")
    details: Optional[str] = Field(None, description="Detailed description")
    source: str = Field("ml-service", description="Alert source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    send_pagerduty: bool = Field(True, description="Send to PagerDuty")
    send_slack: bool = Field(True, description="Send to Slack")
    force: bool = Field(False, description="Bypass rate limiting")


class TestAlertRequest(BaseModel):
    """Request model for sending a test alert"""
    channel: str = Field(..., description="Channel to test (pagerduty or slack)")
    severity: str = Field("info", description="Test alert severity")


class AlertResponse(BaseModel):
    """Response model for alert operations"""
    status: str
    message: str
    pagerduty_results: Optional[List[Dict[str, Any]]] = None
    slack_results: Optional[List[Dict[str, Any]]] = None


class AlertStatsResponse(BaseModel):
    """Response model for alert statistics"""
    total_alerts_sent: int
    alerts_by_severity: Dict[str, int]
    alerts_by_type: Dict[str, int]
    rate_limit_info: Dict[str, int]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/send", response_model=AlertResponse)
async def send_alert(
    alert_request: AlertRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send an alert through configured channels
    
    Requires authentication. Supports rate limiting based on severity.
    """
    try:
        # Validate event type and severity
        try:
            event_type = AlertEventType(alert_request.event_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event_type. Must be one of: {[e.value for e in AlertEventType]}"
            )
        
        try:
            severity = AlertSeverity(alert_request.severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity. Must be one of: {[s.value for s in AlertSeverity]}"
            )
        
        # Create alert
        alert = Alert(
            event_type=event_type,
            severity=severity,
            summary=alert_request.summary,
            details=alert_request.details,
            source=alert_request.source,
            metadata=alert_request.metadata
        )
        
        # Send alert
        manager = get_alert_manager()
        results = await manager.send_alert(
            alert=alert,
            send_pagerduty=alert_request.send_pagerduty,
            send_slack=alert_request.send_slack,
            force=alert_request.force
        )
        
        return AlertResponse(
            status="success",
            message="Alert sent successfully",
            pagerduty_results=results.get("pagerduty"),
            slack_results=results.get("slack")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send alert: {str(e)}"
        )


@router.post("/test", response_model=AlertResponse)
async def send_test_alert(
    test_request: TestAlertRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a test alert to verify alerting configuration
    
    Useful for testing PagerDuty and Slack integrations.
    """
    try:
        # Validate severity
        try:
            severity = AlertSeverity(test_request.severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity. Must be one of: {[s.value for s in AlertSeverity]}"
            )
        
        # Create test alert
        alert = Alert(
            event_type=AlertEventType.DEPLOYMENT,
            severity=severity,
            summary=f"Test Alert from {test_request.channel}",
            details=f"This is a test alert sent by {current_user.username}",
            source="ml-service",
            metadata={
                "test": True,
                "user": current_user.username
            }
        )
        
        # Send to specified channel
        manager = get_alert_manager()
        results = await manager.send_alert(
            alert=alert,
            send_pagerduty=(test_request.channel == "pagerduty"),
            send_slack=(test_request.channel == "slack"),
            force=True  # Always send test alerts
        )
        
        return AlertResponse(
            status="success",
            message=f"Test alert sent to {test_request.channel}",
            pagerduty_results=results.get("pagerduty"),
            slack_results=results.get("slack")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test alert: {str(e)}"
        )


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get alert statistics and rate limit information
    
    Shows how many alerts have been sent and current rate limit settings.
    """
    manager = get_alert_manager()
    
    # Count alerts by severity and type from history
    severity_counts = {s.value: 0 for s in AlertSeverity}
    type_counts = {e.value: 0 for e in AlertEventType}
    
    for alert_key in manager._alert_history.keys():
        event_type = alert_key.split("_")[0]
        type_counts[event_type] = type_counts.get(event_type, 0) + 1
    
    return AlertStatsResponse(
        total_alerts_sent=len(manager._alert_history),
        alerts_by_severity=severity_counts,
        alerts_by_type=type_counts,
        rate_limit_info={
            s.value: manager._rate_limits.get(s, 0)
            for s in AlertSeverity
        }
    )


@router.post("/clear-history")
async def clear_alert_history(
    current_user: User = Depends(get_current_active_user)
):
    """
    Clear alert history (resets rate limiting)
    
    Useful for testing or after resolving incidents.
    """
    # Only allow superusers to clear history
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can clear alert history"
        )
    
    manager = get_alert_manager()
    manager.clear_history()
    
    return {"status": "success", "message": "Alert history cleared"}


@router.get("/event-types")
async def list_event_types():
    """List available alert event types"""
    return {
        "event_types": [e.value for e in AlertEventType],
        "descriptions": {
            AlertEventType.SYSTEM_DOWN.value: "Service or system is down",
            AlertEventType.HIGH_ERROR_RATE.value: "Error rate exceeds threshold",
            AlertEventType.HIGH_LATENCY.value: "Request latency exceeds threshold",
            AlertEventType.DEPLOYMENT.value: "Deployment event",
            AlertEventType.MODEL_FAILURE.value: "Model prediction failed",
            AlertEventType.DATA_PIPELINE_FAILURE.value: "ETL/data pipeline failed",
            AlertEventType.DATABASE_CONNECTION_ISSUE.value: "Database connection problem",
            AlertEventType.SECURITY_BREACH.value: "Security incident detected",
            AlertEventType.AUTHENTICATION_FAILURE.value: "Authentication failed repeatedly",
            AlertEventType.UNAUTHORIZED_ACCESS.value: "Unauthorized access attempt",
            AlertEventType.HIGH_RISK_PREDICTION.value: "High risk prediction generated",
            AlertEventType.ANOMALY_DETECTED.value: "Anomaly detected in data"
        }
    }


@router.get("/severities")
async def list_severities():
    """List available alert severity levels"""
    return {
        "severities": [s.value for s in AlertSeverity],
        "descriptions": {
            AlertSeverity.CRITICAL.value: "Critical - immediate action required",
            AlertSeverity.ERROR.value: "Error - needs attention",
            AlertSeverity.WARNING.value: "Warning - may need attention",
            AlertSeverity.INFO.value: "Informational - for awareness"
        },
        "rate_limits": {
            AlertSeverity.CRITICAL.value: 0,  # No rate limiting
            AlertSeverity.ERROR.value: 300,   # 5 minutes
            AlertSeverity.WARNING.value: 900,  # 15 minutes
            AlertSeverity.INFO.value: 3600    # 1 hour
        }
    }


@router.post("/pagerduty/resolve")
async def resolve_pagerduty_incident(
    dedup_key: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Resolve a PagerDuty incident using dedup key
    
    Use this to mark an incident as resolved in PagerDuty.
    """
    try:
        manager = get_alert_manager()
        result = await manager.resolve_pagerduty_incident(dedup_key)
        
        return {
            "status": "success",
            "message": "Incident resolved in PagerDuty",
            "result": result
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve incident: {str(e)}"
        )
