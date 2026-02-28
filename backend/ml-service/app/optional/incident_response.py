"""
Incident Response Runbooks and Procedures

Provides structured runbooks for handling common incidents:
1. Service outages
2. High error rates
3. Performance degradation
4. Data quality issues
5. Security incidents
6. Model failures

Usage:
    from app.incident_response import (
        Runbook,
        IncidentManager,
        execute_runbook
    )
    
    # Execute runbook for incident type
    result = await execute_runbook(
        incident_type="high_error_rate",
        context={"error_rate": 15.5, "threshold": 5.0}
    )
"""

import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels"""
    P1 = "P1"  # Critical - total outage
    P2 = "P2"  # High - major impact
    P3 = "P3"  # Medium - partial impact
    P4 = "P4"  # Low - minimal impact


class IncidentStatus(Enum):
    """Incident status"""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    POSTMORTEM = "postmortem"


class IncidentType(Enum):
    """Types of incidents"""
    SERVICE_DOWN = "service_down"
    HIGH_ERROR_RATE = "high_error_rate"
    HIGH_LATENCY = "high_latency"
    DATABASE_ISSUE = "database_issue"
    MODEL_FAILURE = "model_failure"
    DATA_QUALITY = "data_quality"
    SECURITY_BREACH = "security_breach"
    AUTHENTICATION_FAILURE = "authentication_failure"
    QUEUE_BACKLOG = "queue_backlog"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    BUDGET_EXCEEDED = "budget_exceeded"


@dataclass
class Incident:
    """Incident record"""
    id: str
    type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus
    title: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_summary: Optional[str] = None


@dataclass
class RunbookStep:
    """A single step in a runbook"""
    order: int
    title: str
    description: str
    action: Optional[Callable] = None
    expected_duration_minutes: int = 5
    requires_escalation: bool = False
    success_criteria: Optional[str] = None


@dataclass
class Runbook:
    """Incident response runbook"""
    incident_type: IncidentType
    title: str
    description: str
    steps: List[RunbookStep]
    escalation_contacts: List[str] = field(default_factory=list)
    estimated_resolution_time_minutes: int = 30
    related_runbooks: List[str] = field(default_factory=list)


class IncidentManager:
    """
    Manager for incident response
    
    Handles:
    - Incident detection and classification
    - Runbook execution
    - Escalation procedures
    - Post-incident analysis
    """
    
    def __init__(self):
        self._active_incidents: Dict[str, Incident] = {}
        self._runbooks: Dict[IncidentType, Runbook] = {}
        self._initialize_runbooks()
    
    def _initialize_runbooks(self):
        """Initialize standard runbooks"""
        
        # Service Down Runbook
        self._runbooks[IncidentType.SERVICE_DOWN] = Runbook(
            incident_type=IncidentType.SERVICE_DOWN,
            title="Service Outage Response",
            description="Runbook for handling complete service outages",
            steps=[
                RunbookStep(
                    order=1,
                    title="Verify Service Status",
                    description="Check if service is actually down or if it's a network/routing issue",
                    action=self._verify_service_status,
                    expected_duration_minutes=2
                ),
                RunbookStep(
                    order=2,
                    title="Check Recent Deployments",
                    description="Verify if a recent deployment caused the outage",
                    action=self._check_recent_deployments,
                    expected_duration_minutes=3
                ),
                RunbookStep(
                    order=3,
                    title="Review Application Logs",
                    description="Check for errors or crashes in application logs",
                    action=self._review_application_logs,
                    expected_duration_minutes=5
                ),
                RunbookStep(
                    order=4,
                    title="Check Infrastructure Health",
                    description="Verify database, cache, and other dependencies",
                    action=self._check_infrastructure_health,
                    expected_duration_minutes=5
                ),
                RunbookStep(
                    order=5,
                    title="Attempt Service Restart",
                    description="Restart the service if appropriate",
                    action=self._attempt_service_restart,
                    expected_duration_minutes=5,
                    requires_escalation=True
                ),
                RunbookStep(
                    order=6,
                    title="Rollback if Needed",
                    description="Rollback recent deployment if it caused the issue",
                    action=self._rollback_deployment,
                    expected_duration_minutes=10
                )
            ],
            escalation_contacts=["oncall-engineer", "engineering-lead"],
            estimated_resolution_time_minutes=30
        )
        
        # High Error Rate Runbook
        self._runbooks[IncidentType.HIGH_ERROR_RATE] = Runbook(
            incident_type=IncidentType.HIGH_ERROR_RATE,
            title="High Error Rate Response",
            description="Runbook for handling elevated error rates",
            steps=[
                RunbookStep(
                    order=1,
                    title="Confirm Error Rate",
                    description="Verify the error rate is actually elevated",
                    action=self._confirm_error_rate,
                    expected_duration_minutes=2
                ),
                RunbookStep(
                    order=2,
                    title="Identify Error Patterns",
                    description="Analyze which endpoints/errors are most common",
                    action=self._identify_error_patterns,
                    expected_duration_minutes=5
                ),
                RunbookStep(
                    order=3,
                    title="Check Recent Changes",
                    description="Review recent code/config changes",
                    action=self._check_recent_changes,
                    expected_duration_minutes=5
                ),
                RunbookStep(
                    order=4,
                    title="Check Dependencies",
                    description="Verify external services are healthy",
                    action=self._check_dependencies,
                    expected_duration_minutes=5
                ),
                RunbookStep(
                    order=5,
                    title="Enable Circuit Breakers",
                    description="Open circuit breakers for failing services",
                    action=self._enable_circuit_breakers,
                    expected_duration_minutes=3
                ),
                RunbookStep(
                    order=6,
                    title="Scale Resources",
                    description="Scale up if issue is resource-related",
                    action=self._scale_resources,
                    expected_duration_minutes=10
                )
            ],
            escalation_contacts=["oncall-engineer"],
            estimated_resolution_time_minutes=30
        )
        
        # Model Failure Runbook
        self._runbooks[IncidentType.MODEL_FAILURE] = Runbook(
            incident_type=IncidentType.MODEL_FAILURE,
            title="ML Model Failure Response",
            description="Runbook for handling model prediction failures",
            steps=[
                RunbookStep(
                    order=1,
                    title="Verify Model Status",
                    description="Check if model file exists and is loadable",
                    action=self._verify_model_status,
                    expected_duration_minutes=3
                ),
                RunbookStep(
                    order=2,
                    title="Check Input Data",
                    description="Verify input data format and values",
                    action=self._check_input_data,
                    expected_duration_minutes=5
                ),
                RunbookStep(
                    order=3,
                    title="Switch to Backup Model",
                    description="Use ensemble or fallback model if available",
                    action=self._switch_to_backup_model,
                    expected_duration_minutes=5
                ),
                RunbookStep(
                    order=4,
                    title="Reload Model",
                    description="Attempt to reload the model from disk",
                    action=self._reload_model,
                    expected_duration_minutes=10
                ),
                RunbookStep(
                    order=5,
                    title="Retrain Model",
                    description="Initiate model retraining if data drift detected",
                    action=self._retrain_model,
                    expected_duration_minutes=60,
                    requires_escalation=True
                )
            ],
            escalation_contacts=["ml-engineer", "data-science-lead"],
            estimated_resolution_time_minutes=90
        )
        
        # Database Issue Runbook
        self._runbooks[IncidentType.DATABASE_ISSUE] = Runbook(
            incident_type=IncidentType.DATABASE_ISSUE,
            title="Database Issue Response",
            description="Runbook for handling database connectivity/performance issues",
            steps=[
                RunbookStep(
                    order=1,
                    title="Check Database Connectivity",
                    description="Verify database server is reachable",
                    action=self._check_database_connectivity,
                    expected_duration_minutes=2
                ),
                RunbookStep(
                    order=2,
                    title="Check Connection Pool",
                    description="Verify connection pool status",
                    action=self._check_connection_pool,
                    expected_duration_minutes=3
                ),
                RunbookStep(
                    order=3,
                    title="Review Slow Queries",
                    description="Identify slow or blocking queries",
                    action=self._review_slow_queries,
                    expected_duration_minutes=5
                ),
                RunbookStep(
                    order=4,
                    title="Check Database Resources",
                    description="Verify CPU, memory, disk usage",
                    action=self._check_database_resources,
                    expected_duration_minutes=3
                ),
                RunbookStep(
                    order=5,
                    title="Enable Read Replica",
                    description="Route reads to replica if available",
                    action=self._enable_read_replica,
                    expected_duration_minutes=5
                ),
                RunbookStep(
                    order=6,
                    title="Scale Database",
                    description="Increase database resources",
                    action=self._scale_database,
                    expected_duration_minutes=15,
                    requires_escalation=True
                )
            ],
            escalation_contacts=["oncall-engineer", "dba"],
            estimated_resolution_time_minutes=45
        )
        
        # Security Breach Runbook
        self._runbooks[IncidentType.SECURITY_BREACH] = Runbook(
            incident_type=IncidentType.SECURITY_BREACH,
            title="Security Incident Response",
            description="Runbook for handling security incidents",
            steps=[
                RunbookStep(
                    order=1,
                    title="Contain the Breach",
                    description="Isolate affected systems and prevent further damage",
                    action=self._contain_breach,
                    expected_duration_minutes=5,
                    requires_escalation=True
                ),
                RunbookStep(
                    order=2,
                    title="Activate Security Team",
                    description="Notify security team and CTO",
                    action=self._activate_security_team,
                    expected_duration_minutes=2,
                    requires_escalation=True
                ),
                RunbookStep(
                    order=3,
                    title="Preserve Evidence",
                    description="Collect logs and evidence for investigation",
                    action=self._preserve_evidence,
                    expected_duration_minutes=10
                ),
                RunbookStep(
                    order=4,
                    title="Identify Affected Users",
                    description="Determine which users/data were compromised",
                    action=self._identify_affected_users,
                    expected_duration_minutes=15
                ),
                RunbookStep(
                    order=5,
                    title="Reset Credentials",
                    description="Force password resets for affected users",
                    action=self._reset_credentials,
                    expected_duration_minutes=10
                ),
                RunbookStep(
                    order=6,
                    title="Notify Stakeholders",
                    description="Inform management, legal, and affected users",
                    action=self._notify_stakeholders,
                    expected_duration_minutes=30
                )
            ],
            escalation_contacts=["ciso", "cto", "legal"],
            estimated_resolution_time_minutes=120
        )
    
    async def create_incident(
        self,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        title: str,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Incident:
        """Create a new incident"""
        incident_id = f"inc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        incident = Incident(
            id=incident_id,
            type=incident_type,
            severity=severity,
            status=IncidentStatus.DETECTED,
            title=title,
            description=description,
            context=context or {}
        )
        
        self._active_incidents[incident_id] = incident
        
        # Send alert
        from app.alerting import alert_system_down, AlertEventType, AlertSeverity
        await alert_system_down(
            service=title,
            error=description
        )
        
        logger.critical(f"Incident created: {incident_id} - {title}")
        return incident
    
    async def execute_runbook(
        self,
        incident: Incident
    ) -> Dict[str, Any]:
        """Execute the appropriate runbook for an incident"""
        runbook = self._runbooks.get(incident.type)
        
        if not runbook:
            logger.warning(f"No runbook found for incident type: {incident.type}")
            return {"status": "no_runbook", "message": "No runbook available for this incident type"}
        
        logger.info(f"Executing runbook for incident {incident.id}: {runbook.title}")
        
        results = {
            "incident_id": incident.id,
            "runbook": runbook.title,
            "steps_completed": [],
            "steps_failed": [],
            "escalated": False
        }
        
        # Update incident status
        incident.status = IncidentStatus.INVESTIGATING
        incident.updated_at = datetime.utcnow()
        
        # Execute each step
        for step in runbook.steps:
            logger.info(f"Executing step {step.order}: {step.title}")
            
            try:
                # Execute the step action
                if step.action:
                    result = await step.action(incident)
                    
                    # Check if step succeeded
                    if result.get("success", True):
                        results["steps_completed"].append({
                            "order": step.order,
                            "title": step.title,
                            "result": result
                        })
                    else:
                        results["steps_failed"].append({
                            "order": step.order,
                            "title": step.title,
                            "error": result.get("error", "Unknown error")
                        })
                        
                        # Escalate if required
                        if step.requires_escalation:
                            await self._escalate_incident(incident, step)
                            results["escalated"] = True
                else:
                    results["steps_completed"].append({
                        "order": step.order,
                        "title": step.title,
                        "result": {"message": "Manual step completed"}
                    })
                
                # Small delay between steps
                await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Step {step.order} failed: {e}")
                results["steps_failed"].append({
                    "order": step.order,
                    "title": step.title,
                    "error": str(e)
                })
                
                if step.requires_escalation:
                    await self._escalate_incident(incident, step)
                    results["escalated"] = True
        
        # Update incident status
        if not results["steps_failed"]:
            incident.status = IncidentStatus.RESOLVED
            incident.resolved_at = datetime.utcnow()
        else:
            incident.status = IncidentStatus.MITIGATING
        
        incident.updated_at = datetime.utcnow()
        
        return results
    
    async def _escalate_incident(self, incident: Incident, step: RunbookStep):
        """Escalate incident to appropriate contacts"""
        runbook = self._runbooks.get(incident.type)
        
        if runbook and runbook.escalation_contacts:
            from app.alerting import alert_system_down, AlertEventType, AlertSeverity
            
            for contact in runbook.escalation_contacts:
                # Send alert to escalation contact
                logger.critical(f"Escalating incident {incident.id} to {contact}")
                
                # Would send actual notification here
                # await send_alert_to_contact(contact, incident)
    
    # Runbook step actions
    async def _verify_service_status(self, incident: Incident) -> Dict[str, Any]:
        """Verify if service is actually down"""
        # Implementation would check health endpoint
        return {"success": True, "status": "verified"}
    
    async def _check_recent_deployments(self, incident: Incident) -> Dict[str, Any]:
        """Check for recent deployments"""
        # Implementation would check deployment history
        return {"success": True, "recent_deployment": None}
    
    async def _review_application_logs(self, incident: Incident) -> Dict[str, Any]:
        """Review application logs for errors"""
        # Implementation would aggregate recent logs
        return {"success": True, "errors_found": []}
    
    async def _check_infrastructure_health(self, incident: Incident) -> Dict[str, Any]:
        """Check infrastructure health"""
        # Implementation would check database, cache, etc.
        return {"success": True, "infrastructure_status": "healthy"}
    
    async def _attempt_service_restart(self, incident: Incident) -> Dict[str, Any]:
        """Attempt to restart the service"""
        # Implementation would trigger service restart
        return {"success": True, "restarted": True}
    
    async def _rollback_deployment(self, incident: Incident) -> Dict[str, Any]:
        """Rollback recent deployment"""
        # Implementation would trigger rollback
        return {"success": True, "rollback_complete": True}
    
    async def _confirm_error_rate(self, incident: Incident) -> Dict[str, Any]:
        """Confirm elevated error rate"""
        error_rate = incident.context.get("error_rate", 0)
        threshold = incident.context.get("threshold", 5)
        return {"success": True, "confirmed": error_rate > threshold}
    
    async def _identify_error_patterns(self, incident: Incident) -> Dict[str, Any]:
        """Identify which endpoints are failing"""
        return {"success": True, "patterns": []}
    
    async def _check_recent_changes(self, incident: Incident) -> Dict[str, Any]:
        """Check for recent code/config changes"""
        return {"success": True, "changes": []}
    
    async def _check_dependencies(self, incident: Incident) -> Dict[str, Any]:
        """Check external service health"""
        return {"success": True, "dependencies": "healthy"}
    
    async def _enable_circuit_breakers(self, incident: Incident) -> Dict[str, Any]:
        """Enable circuit breakers for failing services"""
        return {"success": True, "circuit_breakers_enabled": True}
    
    async def _scale_resources(self, incident: Incident) -> Dict[str, Any]:
        """Scale up resources"""
        return {"success": True, "scaled": True}
    
    async def _verify_model_status(self, incident: Incident) -> Dict[str, Any]:
        """Verify model file exists and is loadable"""
        return {"success": True, "model_status": "ok"}
    
    async def _check_input_data(self, incident: Incident) -> Dict[str, Any]:
        """Check input data format and values"""
        return {"success": True, "data_valid": True}
    
    async def _switch_to_backup_model(self, incident: Incident) -> Dict[str, Any]:
        """Switch to backup/ensemble model"""
        return {"success": True, "backup_model_active": True}
    
    async def _reload_model(self, incident: Incident) -> Dict[str, Any]:
        """Reload model from disk"""
        return {"success": True, "model_reloaded": True}
    
    async def _retrain_model(self, incident: Incident) -> Dict[str, Any]:
        """Initiate model retraining"""
        return {"success": True, "retraining_initiated": True}
    
    async def _check_database_connectivity(self, incident: Incident) -> Dict[str, Any]:
        """Check database connectivity"""
        return {"success": True, "database_reachable": True}
    
    async def _check_connection_pool(self, incident: Incident) -> Dict[str, Any]:
        """Check connection pool status"""
        return {"success": True, "pool_status": "healthy"}
    
    async def _review_slow_queries(self, incident: Incident) -> Dict[str, Any]:
        """Review slow queries"""
        return {"success": True, "slow_queries": []}
    
    async def _check_database_resources(self, incident: Incident) -> Dict[str, Any]:
        """Check database resource usage"""
        return {"success": True, "resources": "ok"}
    
    async def _enable_read_replica(self, incident: Incident) -> Dict[str, Any]:
        """Enable read replica routing"""
        return {"success": True, "read_replica_enabled": True}
    
    async def _scale_database(self, incident: Incident) -> Dict[str, Any]:
        """Scale database resources"""
        return {"success": True, "database_scaled": True}
    
    async def _contain_breach(self, incident: Incident) -> Dict[str, Any]:
        """Contain security breach"""
        return {"success": True, "contained": True}
    
    async def _activate_security_team(self, incident: Incident) -> Dict[str, Any]:
        """Activate security team"""
        return {"success": True, "team_notified": True}
    
    async def _preserve_evidence(self, incident: Incident) -> Dict[str, Any]:
        """Preserve evidence for investigation"""
        return {"success": True, "evidence_preserved": True}
    
    async def _identify_affected_users(self, incident: Incident) -> Dict[str, Any]:
        """Identify affected users"""
        return {"success": True, "affected_users": []}
    
    async def _reset_credentials(self, incident: Incident) -> Dict[str, Any]:
        """Reset user credentials"""
        return {"success": True, "credentials_reset": True}
    
    async def _notify_stakeholders(self, incident: Incident) -> Dict[str, Any]:
        """Notify stakeholders"""
        return {"success": True, "stakeholders_notified": True}


# Singleton instance
_incident_manager: Optional[IncidentManager] = None


def get_incident_manager() -> IncidentManager:
    """Get the singleton IncidentManager instance"""
    global _incident_manager
    if _incident_manager is None:
        _incident_manager = IncidentManager()
        logger.info("Incident Manager created")
    return _incident_manager


async def execute_runbook(
    incident_type: str,
    context: Optional[Dict[str, Any]] = None,
    severity: str = "P2"
) -> Dict[str, Any]:
    """
    Execute a runbook for a given incident type
    
    Convenience function for quick runbook execution.
    
    Args:
        incident_type: Type of incident (e.g., "high_error_rate")
        context: Additional context about the incident
        severity: Incident severity (P1, P2, P3, P4)
    
    Returns:
        Results of runbook execution
    """
    manager = get_incident_manager()
    
    # Map string to enum
    try:
        inc_type = IncidentType(incident_type)
        inc_severity = IncidentSeverity(severity)
    except ValueError:
        return {"status": "error", "message": f"Invalid incident type or severity"}
    
    # Create incident
    incident = await manager.create_incident(
        incident_type=inc_type,
        severity=inc_severity,
        title=f"{incident_type.replace('_', ' ').title()} Detected",
        description=f"Automated incident: {incident_type}",
        context=context or {}
    )
    
    # Execute runbook
    return await manager.execute_runbook(incident)
