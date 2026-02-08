"""
Security API endpoints for IIT ML Service
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User
from ..crud import log_audit
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["Security"])

class SecurityConfigRequest(BaseModel):
    """Request model for security configuration"""
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 100
    rate_limit_window_seconds: int = 60

class SecurityAuditLogRequest(BaseModel):
    """Request model for audit log query"""
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return")
    offset: int = Query(0, ge=0, description="Number of logs to skip")
    event_type: Optional[str] = Query(None, description="Filter by event type")
    severity: Optional[str] = Query(None, description="Filter by severity")
    start_date: Optional[datetime] = Query(None, description="Filter logs after this date")
    end_date: Optional[datetime] = Query(None, description="Filter logs before this date")

@router.get("/audit-logs", response_model=dict)
async def get_security_audit_logs(
    request: SecurityAuditLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve security audit logs with filtering
    """
    try:
        from ..models import AuditLog
        
        query = db.query(AuditLog)
        
        if request.event_type:
            query = query.filter(AuditLog.event_type == request.event_type)
        if request.severity:
            query = query.filter(AuditLog.severity == request.severity)
        if request.start_date:
            query = query.filter(AuditLog.created_at >= request.start_date)
        if request.end_date:
            query = query.filter(AuditLog.created_at <= request.end_date)
        
        logs = query.order_by(AuditLog.created_at.desc()).offset(request.offset).limit(request.limit).all()
        
        return {
            "logs": [
                {
                    "id": log.id,
                    "event_type": log.event_type,
                    "severity": log.severity,
                    "user_id": log.user_id,
                    "details": log.details,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ],
            "total": len(logs),
            "limit": request.limit,
            "offset": request.offset
        }
    except Exception as e:
        logger.error(f"Failed to retrieve audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config", response_model=dict)
async def get_security_config(
    current_user: User = Depends(get_current_user)
):
    """
    Get current security configuration
    """
    try:
        return {
            "rate_limit_enabled": True,
            "rate_limit_requests_per_minute": 100,
            "rate_limit_window_seconds": 60,
            "security_headers_enabled": True,
            "audit_logging_enabled": True,
            "threat_detection_enabled": True,
            "updated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get security config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config", response_model=dict)
async def update_security_config(
    config: SecurityConfigRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update security configuration (admin only)
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # In production, this would update configuration in database or settings
        logger.info(f"Security config updated by {current_user.username}")
        
        return {
            "message": "Security configuration updated",
            "rate_limit_enabled": config.rate_limit_enabled,
            "rate_limit_requests_per_minute": config.rate_limit_requests_per_minute,
            "rate_limit_window_seconds": config.rate_limit_window_seconds
        }
    except HTTPException as e:
        logger.error(f"Failed to update security config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=dict)
async def get_security_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get security statistics and monitoring data
    """
    try:
        from ..models import AuditLog
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        total_events = db.query(AuditLog).filter(
            AuditLog.created_at >= cutoff_date
        ).count()
        
        # Count by severity
        high_severity = db.query(AuditLog).filter(
            AuditLog.created_at >= cutoff_date,
            AuditLog.severity == "high"
        ).count()
        
        critical_severity = db.query(AuditLog).filter(
            AuditLog.created_at >= cutoff_date,
            AuditLog.severity == "critical"
        ).count()
        
        # Count by event type
        blocked_ips = db.query(AuditLog).filter(
            AuditLog.created_at >= cutoff_date,
            AuditLog.event_type == "IP_BLOCKED"
        ).count()
        
        rate_limit_violations = db.query(AuditLog).filter(
            AuditLog.created_at >= cutoff_date,
            AuditLog.event_type == "RATE_LIMIT_EXCEEDED"
        ).count()
        
        return {
            "period_days": days,
            "total_events": total_events,
            "high_severity_count": high_severity,
            "critical_severity_count": critical_severity,
            "blocked_ips_count": blocked_ips,
            "rate_limit_violations": rate_limit_violations,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get security stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
