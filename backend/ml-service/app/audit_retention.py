"""
Audit Log Retention Management for IIT ML Service
Automated cleanup and archival of audit logs based on retention policies
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .core.db import get_db
from .models import AuditLog
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuditLogRetention:
    """
    Manages audit log retention policies and cleanup.
    
    Retention Policies:
    - Security events: 365 days (1 year)
    - Authentication events: 180 days (6 months)
    - Data modifications: 90 days (3 months)
    - General activity: 30 days (1 month)
    - Failed operations: 180 days (6 months)
    """
    
    # Retention periods in days
    RETENTION_POLICIES = {
        'SECURITY': 365,  # Security incidents
        'AUTH': 180,  # Authentication events
        'DATA_CREATE': 90,  # Data creation
        'DATA_UPDATE': 90,  # Data updates
        'DATA_DELETE': 90,  # Data deletions
        'HTTP_POST': 30,  # General POST requests
        'HTTP_GET': 30,  # General GET requests
        'FAILED': 180,  # Failed operations
        'DEFAULT': 30  # Default retention
    }
    
    def __init__(self):
        self.settings = get_settings()
        
    def get_retention_days(self, action: str) -> int:
        """Get retention period for a specific action type"""
        action_upper = action.upper()
        
        # Check for specific action patterns
        for pattern, days in self.RETENTION_POLICIES.items():
            if pattern in action_upper:
                return days
        
        return self.RETENTION_POLICIES['DEFAULT']
    
    def get_logs_to_delete(self, db: Session, dry_run: bool = False) -> Dict[str, Any]:
        """
        Identify logs eligible for deletion based on retention policies.
        
        Args:
            db: Database session
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dictionary with deletion statistics
        """
        cutoff_date = datetime.utcnow()
        total_to_delete = 0
        breakdown = {}
        
        for action, retention_days in self.RETENTION_POLICIES.items():
            action_cutoff = cutoff_date - timedelta(days=retention_days)
            
            # Count logs matching this action type and older than cutoff
            query = db.query(func.count(AuditLog.id)).filter(
                and_(
                    AuditLog.action.like(f'%{action}%'),
                    AuditLog.timestamp < action_cutoff
                )
            )
            
            count = query.scalar() or 0
            total_to_delete += count
            breakdown[action] = {
                'retention_days': retention_days,
                'cutoff_date': action_cutoff.isoformat(),
                'count': count
            }
        
        return {
            'total_to_delete': total_to_delete,
            'breakdown': breakdown,
            'dry_run': dry_run
        }
    
    def delete_old_logs(
        self,
        db: Session,
        dry_run: bool = False,
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Delete audit logs older than retention period.
        
        Args:
            db: Database session
            dry_run: If True, only report what would be deleted
            batch_size: Number of records to delete per batch
            
        Returns:
            Dictionary with deletion results
        """
        if dry_run:
            return self.get_logs_to_delete(db, dry_run=True)
        
        cutoff_date = datetime.utcnow()
        total_deleted = 0
        deletion_results = {}
        
        for action, retention_days in self.RETENTION_POLICIES.items():
            action_cutoff = cutoff_date - timedelta(days=retention_days)
            
            # Delete in batches to avoid locking issues
            while True:
                # Find and delete a batch
                deleted = db.query(AuditLog).filter(
                    and_(
                        AuditLog.action.like(f'%{action}%'),
                        AuditLog.timestamp < action_cutoff
                    )
                ).limit(batch_size).delete(synchronize_session=False)
                
                if deleted == 0:
                    break
                
                db.commit()
                total_deleted += deleted
                logger.info(f"Deleted {deleted} audit logs for action {action}")
            
            deletion_results[action] = {
                'retention_days': retention_days,
                'deleted': total_deleted
            }
        
        return {
            'total_deleted': total_deleted,
            'breakdown': deletion_results,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def archive_old_logs(
        self,
        db: Session,
        archive_path: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Archive old audit logs to file before deletion.
        
        Args:
            db: Database session
            archive_path: Path to save archive file
            dry_run: If True, only report what would be archived
            
        Returns:
            Dictionary with archival results
        """
        import json
        from pathlib import Path
        
        cutoff_date = datetime.utcnow() - timedelta(days=30)  # Archive everything older than 30 days
        
        # Query logs to archive
        logs_to_archive = db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff_date
        ).all()
        
        if dry_run:
            return {
                'would_archive': len(logs_to_archive),
                'archive_path': archive_path,
                'dry_run': True
            }
        
        # Convert to JSON
        archive_data = []
        for log in logs_to_archive:
            archive_data.append({
                'id': log.id,
                'user_id': log.user_id,
                'username': log.username,
                'action': log.action,
                'resource': log.resource,
                'resource_id': log.resource_id,
                'details': log.details,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'timestamp': log.timestamp.isoformat(),
                'success': log.success
            })
        
        # Write to file
        archive_file = Path(archive_path)
        archive_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(archive_file, 'w') as f:
            json.dump({
                'archived_at': datetime.utcnow().isoformat(),
                'record_count': len(archive_data),
                'records': archive_data
            }, f, indent=2)
        
        logger.info(f"Archived {len(archive_data)} audit logs to {archive_path}")
        
        return {
            'archived': len(archive_data),
            'archive_path': str(archive_file),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_retention_stats(self, db: Session) -> Dict[str, Any]:
        """
        Get statistics about current audit log storage.
        
        Returns:
            Dictionary with retention statistics
        """
        # Total log count
        total_logs = db.query(func.count(AuditLog.id)).scalar()
        
        # Logs by action type
        action_counts = db.query(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).group_by(AuditLog.action).all()
        
        action_breakdown = {
            action: count for action, count in action_counts
        }
        
        # Logs by date range
        today = datetime.utcnow().date()
        date_ranges = {
            'last_24h': db.query(func.count(AuditLog.id)).filter(
                AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
            ).scalar(),
            'last_7d': db.query(func.count(AuditLog.id)).filter(
                AuditLog.timestamp >= datetime.utcnow() - timedelta(days=7)
            ).scalar(),
            'last_30d': db.query(func.count(AuditLog.id)).filter(
                AuditLog.timestamp >= datetime.utcnow() - timedelta(days=30)
            ).scalar(),
            'older_30d': db.query(func.count(AuditLog.id)).filter(
                AuditLog.timestamp < datetime.utcnow() - timedelta(days=30)
            ).scalar(),
        }
        
        # Estimate storage (rough calculation)
        avg_log_size = 500  # bytes (rough estimate)
        estimated_storage_bytes = total_logs * avg_log_size
        
        return {
            'total_logs': total_logs,
            'action_breakdown': action_breakdown,
            'date_ranges': date_ranges,
            'estimated_storage_mb': round(estimated_storage_bytes / (1024 * 1024), 2),
            'retention_policies': self.RETENTION_POLICIES
        }


# Global instance
_audit_retention: Optional[AuditLogRetention] = None


def get_audit_retention() -> AuditLogRetention:
    """Get or create global audit retention instance"""
    global _audit_retention
    if _audit_retention is None:
        _audit_retention = AuditLogRetention()
    return _audit_retention


async def run_audit_cleanup(dry_run: bool = False) -> Dict[str, Any]:
    """
    Run audit log cleanup based on retention policies.
    
    Args:
        dry_run: If True, only report what would be deleted
        
    Returns:
        Dictionary with cleanup results
    """
    retention = get_audit_retention()
    db = next(get_db())
    
    try:
        return retention.delete_old_logs(db, dry_run=dry_run)
    finally:
        db.close()


async def get_audit_stats() -> Dict[str, Any]:
    """
    Get audit log storage statistics.
    
    Returns:
        Dictionary with retention statistics
    """
    retention = get_audit_retention()
    db = next(get_db())
    
    try:
        return retention.get_retention_stats(db)
    finally:
        db.close()
