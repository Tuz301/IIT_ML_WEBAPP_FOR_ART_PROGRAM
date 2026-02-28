"""
Alerting Integrations for Production Monitoring

Provides integration with PagerDuty and Slack for sending alerts
based on system events, metrics thresholds, and incidents.

Usage:
    from app.alerting import (
        send_pagerduty_alert,
        send_slack_notification,
        AlertManager,
        AlertSeverity
    )
    
    # Send PagerDuty alert
    send_pagerduty_alert(
        routing_key="your-pagerduty-integration-key",
        event_action="trigger",
        payload={
            "summary": "High error rate detected",
            "severity": "error",
            "source": "ml-service"
        }
    )
    
    # Send Slack notification
    send_slack_notification(
        webhook_url="your-slack-webhook-url",
        message="Deployment completed successfully",
        channel="#alerts"
    )
"""

import logging
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AlertEventType(Enum):
    """Alert event types"""
    # System events
    SYSTEM_DOWN = "system_down"
    HIGH_ERROR_RATE = "high_error_rate"
    HIGH_LATENCY = "high_latency"
    DEPLOYMENT = "deployment"
    
    # Application events
    MODEL_FAILURE = "model_failure"
    DATA_PIPELINE_FAILURE = "data_pipeline_failure"
    DATABASE_CONNECTION_ISSUE = "database_connection_issue"
    
    # Security events
    SECURITY_BREACH = "security_breach"
    AUTHENTICATION_FAILURE = "authentication_failure"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    
    # Business events
    HIGH_RISK_PREDICTION = "high_risk_prediction"
    ANOMALY_DETECTED = "anomaly_detected"


@dataclass
class Alert:
    """Alert data structure"""
    event_type: AlertEventType
    severity: AlertSeverity
    summary: str
    details: Optional[str] = None
    source: str = "ml-service"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_pagerduty_payload(self) -> Dict[str, Any]:
        """Convert to PagerDuty event payload format"""
        return {
            "routing_key": None,  # Set by send_pagerduty_alert
            "event_action": "trigger",
            "payload": {
                "summary": self.summary,
                "severity": self.severity.value,
                "source": self.source,
                "timestamp": self.timestamp.isoformat(),
                "custom_details": {
                    "event_type": self.event_type.value,
                    "details": self.details,
                    **self.metadata
                }
            },
            "dedup_key": f"{self.event_type.value}_{self.source}_{int(self.timestamp.timestamp())}"
        }
    
    def to_slack_message(self) -> str:
        """Convert to Slack message format"""
        emoji = {
            AlertSeverity.CRITICAL: ":rotating_light:",
            AlertSeverity.ERROR: ":x:",
            AlertSeverity.WARNING: ":warning:",
            AlertSeverity.INFO: ":information_source:"
        }
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji.get(self.severity, '')} {self.summary}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n{self.severity.value.upper()}"},
                    {"type": "mrkdwn", "text": f"*Source:*\n{self.source}"},
                    {"type": "mrkdwn", "text": f"*Event Type:*\n{self.event_type.value}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"}
                ]
            }
        ]
        
        if self.details:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Details:*\n{self.details}"
                }
            })
        
        if self.metadata:
            metadata_text = "\n".join([f"• *{k}*: {v}" for k, v in self.metadata.items()])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Additional Info:*\n{metadata_text}"
                }
            })
        
        return json.dumps({"blocks": blocks})


async def send_pagerduty_alert(
    routing_key: Optional[str] = None,
    event_action: str = "trigger",
    dedup_key: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    alert: Optional[Alert] = None
) -> Dict[str, Any]:
    """
    Send alert to PagerDuty using Events API v2
    
    Args:
        routing_key: PagerDuty integration key (defaults to settings)
        event_action: Action type (trigger, acknowledge, resolve)
        dedup_key: Deduplication key for updating existing alerts
        payload: Alert payload (or use alert parameter)
        alert: Alert object (alternative to payload)
        
    Returns:
        Response from PagerDuty API
    """
    routing_key = routing_key or getattr(settings, 'pagerduty_routing_key', None)
    if not routing_key:
        logger.warning("PagerDuty routing key not configured, skipping alert")
        return {"status": "skipped", "reason": "no_routing_key"}
    
    # Build payload from Alert object if provided
    if alert:
        pd_payload = alert.to_pagerduty_payload()
        pd_payload["routing_key"] = routing_key
        if dedup_key:
            pd_payload["dedup_key"] = dedup_key
    else:
        pd_payload = {
            "routing_key": routing_key,
            "event_action": event_action,
            "payload": payload or {}
        }
        if dedup_key:
            pd_payload["dedup_key"] = dedup_key
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=pd_payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            
            logger.info(f"PagerDuty alert sent: {pd_payload.get('payload', {}).get('summary')}")
            return response.json()
    
    except httpx.HTTPError as e:
        logger.error(f"Failed to send PagerDuty alert: {e}")
        return {"status": "error", "reason": str(e)}


async def send_slack_notification(
    webhook_url: Optional[str] = None,
    message: Optional[str] = None,
    blocks: Optional[List[Dict[str, Any]]] = None,
    channel: Optional[str] = None,
    username: str = "ML Service Alerts",
    icon_emoji: str = ":robot_face:",
    alert: Optional[Alert] = None
) -> Dict[str, Any]:
    """
    Send notification to Slack using webhook
    
    Args:
        webhook_url: Slack webhook URL (defaults to settings)
        message: Plain text message
        blocks: Slack blocks for rich formatting
        channel: Override default channel
        username: Bot username
        icon_emoji: Bot icon
        alert: Alert object (will be formatted as Slack message)
        
    Returns:
        Response from Slack API
    """
    webhook_url = webhook_url or getattr(settings, 'slack_webhook_url', None)
    if not webhook_url:
        logger.warning("Slack webhook URL not configured, skipping notification")
        return {"status": "skipped", "reason": "no_webhook_url"}
    
    # Build payload
    payload = {
        "username": username,
        "icon_emoji": icon_emoji
    }
    
    if channel:
        payload["channel"] = channel
    
    if alert:
        payload.update(json.loads(alert.to_slack_message()))
    elif blocks:
        payload["blocks"] = blocks
    elif message:
        payload["text"] = message
    else:
        payload["text"] = "Notification from ML Service"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
            
            logger.info(f"Slack notification sent: {message or 'Alert notification'}")
            return {"status": "success"}
    
    except httpx.HTTPError as e:
        logger.error(f"Failed to send Slack notification: {e}")
        return {"status": "error", "reason": str(e)}


class AlertManager:
    """
    Manager for handling alerts with routing rules and rate limiting
    """
    
    def __init__(self):
        self._alert_history: Dict[str, datetime] = {}
        self._rate_limits: Dict[AlertSeverity, int] = {
            AlertSeverity.CRITICAL: 0,  # No rate limiting for critical
            AlertSeverity.ERROR: 300,   # 5 minutes
            AlertSeverity.WARNING: 900,  # 15 minutes
            AlertSeverity.INFO: 3600    # 1 hour
        }
    
    def _should_send_alert(self, alert: Alert) -> bool:
        """Check if alert should be sent based on rate limiting"""
        alert_key = f"{alert.event_type.value}_{alert.source}"
        last_sent = self._alert_history.get(alert_key)
        rate_limit = self._rate_limits.get(alert.severity, 0)
        
        if last_sent is None:
            return True
        
        time_since_last = (datetime.utcnow() - last_sent).total_seconds()
        return time_since_last >= rate_limit
    
    async def send_alert(
        self,
        alert: Alert,
        send_pagerduty: bool = True,
        send_slack: bool = True,
        force: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Send alert through configured channels
        
        Args:
            alert: Alert object to send
            send_pagerduty: Send to PagerDuty
            send_slack: Send to Slack
            force: Bypass rate limiting
            
        Returns:
            Dictionary with results from each channel
        """
        results = {
            "pagerduty": [],
            "slack": []
        }
        
        # Check rate limiting
        if not force and not self._should_send_alert(alert):
            logger.info(f"Alert rate limited: {alert.summary}")
            return {
                "pagerduty": [{"status": "rate_limited"}],
                "slack": [{"status": "rate_limited"}]
            }
        
        # Send to PagerDuty for critical and error alerts
        if send_pagerduty and alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.ERROR]:
            result = await send_pagerduty_alert(alert=alert)
            results["pagerduty"].append(result)
        
        # Send to Slack for all alerts
        if send_slack:
            result = await send_slack_notification(alert=alert)
            results["slack"].append(result)
        
        # Update alert history
        alert_key = f"{alert.event_type.value}_{alert.source}"
        self._alert_history[alert_key] = datetime.utcnow()
        
        return results
    
    async def resolve_pagerduty_incident(
        self,
        dedup_key: str,
        routing_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve a PagerDuty incident"""
        return await send_pagerduty_alert(
            routing_key=routing_key,
            event_action="resolve",
            dedup_key=dedup_key
        )
    
    def clear_history(self):
        """Clear alert history (useful for testing)"""
        self._alert_history.clear()


# Singleton instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the singleton AlertManager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


# Convenience functions for common alert scenarios
async def alert_high_error_rate(error_rate: float, threshold: float, window: str = "5m"):
    """Send alert for high error rate"""
    alert = Alert(
        event_type=AlertEventType.HIGH_ERROR_RATE,
        severity=AlertSeverity.ERROR if error_rate > threshold * 2 else AlertSeverity.WARNING,
        summary=f"High error rate detected: {error_rate:.1f}%",
        details=f"Error rate of {error_rate:.1f}% exceeds threshold of {threshold:.1f}% over {window}",
        metadata={"error_rate": error_rate, "threshold": threshold, "window": window}
    )
    return await get_alert_manager().send_alert(alert)


async def alert_high_latency(p95_latency: float, threshold: float, endpoint: str):
    """Send alert for high latency"""
    alert = Alert(
        event_type=AlertEventType.HIGH_LATENCY,
        severity=AlertSeverity.WARNING,
        summary=f"High latency on {endpoint}",
        details=f"P95 latency of {p95_latency:.0f}ms exceeds threshold of {threshold:.0f}ms",
        metadata={"p95_latency": p95_latency, "threshold": threshold, "endpoint": endpoint}
    )
    return await get_alert_manager().send_alert(alert)


async def alert_system_down(service: str, error: str):
    """Send alert for system down"""
    alert = Alert(
        event_type=AlertEventType.SYSTEM_DOWN,
        severity=AlertSeverity.CRITICAL,
        summary=f"{service} is down",
        details=error,
        metadata={"service": service}
    )
    return await get_alert_manager().send_alert(alert)


async def alert_deployment_status(status: str, version: str, environment: str):
    """Send notification for deployment status"""
    severity = AlertSeverity.INFO if status == "success" else AlertSeverity.ERROR
    alert = Alert(
        event_type=AlertEventType.DEPLOYMENT,
        severity=severity,
        summary=f"Deployment {status}: v{version} to {environment}",
        metadata={"version": version, "environment": environment, "status": status}
    )
    return await get_alert_manager().send_alert(alert, send_pagerduty=False)


async def alert_model_failure(model_name: str, error: str, patient_id: Optional[str] = None):
    """Send alert for model prediction failure"""
    alert = Alert(
        event_type=AlertEventType.MODEL_FAILURE,
        severity=AlertSeverity.ERROR,
        summary=f"Model failure: {model_name}",
        details=error,
        metadata={"model_name": model_name, "patient_id": patient_id}
    )
    return await get_alert_manager().send_alert(alert)


async def alert_security_breach(event_type: str, details: str, user_id: Optional[str] = None):
    """Send alert for security breach"""
    alert = Alert(
        event_type=AlertEventType.SECURITY_BREACH,
        severity=AlertSeverity.CRITICAL,
        summary=f"Security breach: {event_type}",
        details=details,
        metadata={"event_type": event_type, "user_id": user_id}
    )
    return await get_alert_manager().send_alert(alert)


async def alert_high_risk_prediction(patient_id: str, risk_score: float, risk_factors: List[str]):
    """Send alert for high risk prediction"""
    alert = Alert(
        event_type=AlertEventType.HIGH_RISK_PREDICTION,
        severity=AlertSeverity.WARNING,
        summary=f"High risk prediction for patient {patient_id}",
        details=f"Risk score: {risk_score:.2f}. Key factors: {', '.join(risk_factors)}",
        metadata={"patient_id": patient_id, "risk_score": risk_score, "risk_factors": risk_factors}
    )
    return await get_alert_manager().send_alert(alert, send_pagerduty=False)
