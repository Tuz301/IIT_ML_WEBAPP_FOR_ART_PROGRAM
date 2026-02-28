"""
Dead Letter Queue Management API

Provides endpoints for monitoring and managing failed jobs in the dead letter queue.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.auth import get_current_active_user
from app.models import User
from app.queue.dead_letter_queue import get_dlq
from app.monitoring import MetricsManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dlq", tags=["Dead Letter Queue"])


@router.get("", response_model=Dict[str, Any])
async def list_dlq_jobs(
    resolved: bool = Query(False, description="Include resolved jobs"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum jobs to return"),
    current_user: User = Depends(get_current_active_user)
):
    """
    List dead letter queue jobs
    
    Requires authentication.
    
    Args:
        resolved: Include resolved jobs
        limit: Maximum number of jobs to return
        
    Returns:
        Dictionary with DLQ jobs list
    """
    try:
        dlq = get_dlq()
        jobs = dlq.get_dlq_jobs(resolved=resolved, limit=limit)
        
        # Get queue size
        queue_size = len(jobs)
        
        return {
            "total": queue_size,
            "resolved": resolved,
            "jobs": jobs,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error listing DLQ jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve DLQ jobs"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_dlq_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get dead letter queue statistics
    
    Returns summary statistics for DLQ.
    """
    try:
        dlq = get_dlq()
        
        # Get unresolved jobs
        unresolved_jobs = dlq.get_dlq_jobs(resolved=False, limit=10000)
        resolved_jobs = dlq.get_dlq_jobs(resolved=True, limit=10000)
        
        # Calculate statistics
        total_unresolved = len(unresolved_jobs)
        total_resolved = len(resolved_jobs)
        
        # Count by failure reason
        failure_reasons: Dict[str, int] = {}
        for job in unresolved_jobs:
            reason = job.get("failure_reason", "unknown")
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        # Count by job type
        job_types: Dict[str, int] = {}
        for job in unresolved_jobs:
            job_type = job.get("job_func", "unknown")
            job_types[job_type] = job_types.get(job_type, 0) + 1
        
        return {
            "summary": {
                "total_unresolved": total_unresolved,
                "total_resolved": total_resolved,
                "total": total_unresolved + total_resolved
            },
            "failure_reasons": failure_reasons,
            "job_types": job_types,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting DLQ stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve DLQ statistics"
        )


@router.post("/retry/{original_job_id}", response_model=Dict[str, str])
async def retry_dlq_job(
    original_job_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Retry a job from dead letter queue
    
    Args:
        original_job_id: Original job ID to retry
        
    Returns:
        Confirmation message
    """
    try:
        dlq = get_dlq()
        success = dlq.retry_dlq_job(original_job_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DLQ job '{original_job_id}' not found or already resolved"
            )
        
        logger.info(f"DLQ job '{original_job_id}' retried by user {current_user.username}")
        
        # Record metric
        MetricsManager.record_dlq_job_resolved("manual_retry")
        
        return {
            "message": f"Job '{original_job_id}' has been scheduled for retry",
            "original_job_id": original_job_id,
            "retried_by": current_user.username,
            "retried_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying DLQ job {original_job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job '{original_job_id}'"
        )


@router.post("/cleanup", response_model=Dict[str, Any])
async def cleanup_dlq(
    older_than_days: int = Query(30, ge=1, le=365, description="Clean up jobs older than this many days"),
    dry_run: bool = Query(False, description="If true, don't actually delete, just report"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Clean up old resolved DLQ jobs
    
    **WARNING**: This permanently deletes old DLQ records.
    
    Args:
        older_than_days: Only clean up jobs older than this
        dry_run: If true, report what would be deleted without deleting
        
    Returns:
        Cleanup results
    """
    try:
        from app.utils.database import DatabaseManager
        
        db = DatabaseManager()
        
        # Count jobs that would be deleted
        count_query = """
        SELECT COUNT(*) FROM dead_letter_jobs
        WHERE resolved = 1
        AND resolved_at < datetime('now', '-' || ? || ' days');
        """
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(count_query, (older_than_days,))
            count = cursor.fetchone()[0]
        
        if dry_run:
            return {
                "message": "Dry run - no jobs deleted",
                "would_delete": count,
                "older_than_days": older_than_days,
                "dry_run": True
            }
        
        # Delete old resolved jobs
        delete_query = """
        DELETE FROM dead_letter_jobs
        WHERE resolved = 1
        AND resolved_at < datetime('now', '-' || ? || ' days');
        """
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(delete_query, (older_than_days,))
            deleted_count = cursor.rowcount
            conn.commit()
        
        logger.info(f"Cleaned up {deleted_count} DLQ jobs older than {older_than_days} days")
        
        return {
            "message": f"Cleaned up {deleted_count} old DLQ jobs",
            "deleted_count": deleted_count,
            "older_than_days": older_than_days,
            "cleaned_by": current_user.username,
            "cleaned_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up DLQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup DLQ"
        )


@router.get("/job/{original_job_id}", response_model=Dict[str, Any])
async def get_dlq_job(
    original_job_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get details of a specific DLQ job
    
    Args:
        original_job_id: Original job ID
        
    Returns:
        DLQ job details
    """
    try:
        from app.utils.database import DatabaseManager
        
        db = DatabaseManager()
        
        query = """
        SELECT * FROM dead_letter_jobs
        WHERE original_job_id = ?
        LIMIT 1;
        """
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (original_job_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"DLQ job '{original_job_id}' not found"
                )
            
            columns = [desc[0] for desc in cursor.description]
            job_data = dict(zip(columns, row))
            
            return job_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DLQ job {original_job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve DLQ job '{original_job_id}'"
        )
