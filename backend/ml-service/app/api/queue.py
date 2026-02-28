"""
Queue Management API endpoints for IHVN ML Service

Provides REST API for managing background jobs:
- Queue statistics
- Job status queries
- Job cancellation
- Worker status
- Scheduled jobs management
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..auth import get_current_active_user, get_current_superuser
from ..models import User
from ..queue.worker import (
    get_queue_stats,
    get_job_status,
    cancel_job,
    enqueue_job,
    get_all_workers,
)

# Optional scheduler imports (may not be available due to compatibility issues)
try:
    from ..queue.scheduler import (
        list_scheduled_jobs,
        cancel_scheduled_job,
        get_scheduler_status,
        schedule_daily_cleanup,
        schedule_weekly_report,
        schedule_monthly_model_retraining,
    )
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    # Create stub functions for when scheduler is not available
    list_scheduled_jobs = None
    cancel_scheduled_job = None
    get_scheduler_status = None
    schedule_daily_cleanup = None
    schedule_weekly_report = None
    schedule_monthly_model_retraining = None

from ..queue.jobs import (
    process_etl_job,
    batch_prediction_job,
    generate_report_job,
    cleanup_old_data_job,
    send_notifications_job,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/queue", tags=["Queue"])


# Pydantic models for request/response
class QueueStatsResponse(BaseModel):
    """Queue statistics response"""
    name: str
    queued: int
    failed: int
    started: int
    finished: int
    workers: int


class JobStatusResponse(BaseModel):
    """Job status response"""
    id: str
    status: str
    created_at: Optional[str]
    started_at: Optional[str]
    ended_at: Optional[str]
    exc_info: Optional[str]
    result: Optional[Dict[str, Any]]


class EnqueueETLRequest(BaseModel):
    """Request to enqueue ETL job"""
    source_file_path: str = Field(..., description="Path to source data file")
    batch_size: int = Field(100, ge=1, le=1000, description="Batch size for processing")


class EnqueueBatchPredictionRequest(BaseModel):
    """Request to enqueue batch prediction job"""
    patient_uuids: List[str] = Field(..., min_length=1, description="List of patient UUIDs")
    model_version: Optional[str] = Field(None, description="Model version to use")


class EnqueueReportRequest(BaseModel):
    """Request to enqueue report generation job"""
    report_type: str = Field(..., description="Type of report to generate")
    start_date: str = Field(..., description="Start date (ISO format)")
    end_date: str = Field(..., description="End date (ISO format)")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters")


class EnqueueCleanupRequest(BaseModel):
    """Request to enqueue cleanup job"""
    days_to_keep: int = Field(90, ge=1, description="Days of data to keep")
    dry_run: bool = Field(True, description="If True, only report what would be deleted")


class EnqueueNotificationsRequest(BaseModel):
    """Request to enqueue notifications job"""
    notification_type: str = Field(..., description="Type of notification")
    recipients: List[str] = Field(..., min_length=1, description="List of recipients")
    message: str = Field(..., description="Message content")


class JobEnqueuedResponse(BaseModel):
    """Response when job is enqueued"""
    job_id: str
    status: str
    message: str


class WorkerInfo(BaseModel):
    """Worker information"""
    name: str
    state: str
    current_job: Optional[str]
    queues: List[str]


class ScheduledJobInfo(BaseModel):
    """Scheduled job information"""
    id: str
    func_name: str
    scheduled_time: Optional[str]
    interval: Optional[int]
    timeout: int


class ScheduleCleanupRequest(BaseModel):
    """Request to schedule daily cleanup"""
    hour: int = Field(2, ge=0, le=23, description="Hour to run (0-23)")
    minute: int = Field(0, ge=0, le=59, description="Minute to run (0-59)")
    days_to_keep: int = Field(90, ge=1, description="Days of data to keep")


class ScheduleReportRequest(BaseModel):
    """Request to schedule weekly report"""
    day_of_week: int = Field(0, ge=0, le=6, description="Day of week (0=Monday)")
    hour: int = Field(8, ge=0, le=23, description="Hour to run")
    minute: int = Field(0, ge=0, le=59, description="Minute to run")
    report_type: str = Field("predictions", description="Type of report")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None


@router.get(
    "/stats",
    response_model=QueueStatsResponse,
    summary="Get Queue Statistics",
    description="""
    Get current statistics for the job queue.
    
    **Returns:**
    - Number of queued jobs
    - Number of failed jobs
    - Number of started jobs
    - Number of finished jobs
    - Number of active workers
    
    **Permissions:**
    - Requires active user authentication
    """
)
async def get_queue_statistics(
    current_user: User = Depends(get_current_active_user)
) -> QueueStatsResponse:
    """Get queue statistics"""
    try:
        stats = get_queue_stats()
        return QueueStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue statistics: {str(e)}"
        )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get Job Status",
    description="""
    Get the status of a specific job by ID.
    
    **Parameters:**
    - job_id: The ID of the job to query
    
    **Returns:**
    - Job status (queued, started, finished, failed)
    - Timestamps for job lifecycle
    - Result or error information
    
    **Error:**
    - 404: Job not found
    """
)
async def get_job_status_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
) -> JobStatusResponse:
    """Get job status"""
    status_data = get_job_status(job_id)
    
    if status_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )
    
    return JobStatusResponse(**status_data)


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel Job",
    description="""
    Cancel a queued job by ID.
    
    **Note:** Only jobs that are still queued can be cancelled.
    Jobs that are already started or finished cannot be cancelled.
    
    **Error:**
    - 404: Job not found
    - 400: Job cannot be cancelled (already started/finished)
    """
)
async def cancel_job_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_superuser)
) -> None:
    """Cancel a job"""
    success = cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel job '{job_id}'. Job may not exist or cannot be cancelled."
        )


@router.post(
    "/jobs/etl",
    response_model=JobEnqueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue ETL Job",
    description="""
    Enqueue an ETL data processing job for background execution.
    
    **Parameters:**
    - source_file_path: Path to the source data file
    - batch_size: Number of records to process per batch (default: 100)
    
    **Returns:**
    - Job ID for tracking
    
    **Use Case:**
    - Process large data files asynchronously
    - Avoid blocking API responses during ETL
    """
)
async def enqueue_etl_job(
    request: EnqueueETLRequest,
    current_user: User = Depends(get_current_active_user)
) -> JobEnqueuedResponse:
    """Enqueue ETL job"""
    try:
        job = enqueue_job(
            process_etl_job,
            request.source_file_path,
            request.batch_size,
            user_id=current_user.username,
        )
        
        if job:
            logger.info(f"ETL job {job.id} enqueued by {current_user.username}")
            return JobEnqueuedResponse(
                job_id=job.id,
                status="queued",
                message="ETL job enqueued successfully"
            )
        else:
            return JobEnqueuedResponse(
                job_id="sync",
                status="completed",
                message="Job executed synchronously (queue disabled)"
            )
    
    except Exception as e:
        logger.error(f"Failed to enqueue ETL job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue ETL job: {str(e)}"
        )


@router.post(
    "/jobs/batch-prediction",
    response_model=JobEnqueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue Batch Prediction Job",
    description="""
    Enqueue a batch prediction job for multiple patients.
    
    **Parameters:**
    - patient_uuids: List of patient UUIDs to predict
    - model_version: Optional model version to use
    
    **Returns:**
    - Job ID for tracking
    
    **Use Case:**
    - Generate predictions for multiple patients asynchronously
    - Process large batches without blocking
    """
)
async def enqueue_batch_prediction_job_endpoint(
    request: EnqueueBatchPredictionRequest,
    current_user: User = Depends(get_current_active_user)
) -> JobEnqueuedResponse:
    """Enqueue batch prediction job"""
    try:
        job = enqueue_job(
            batch_prediction_job,
            request.patient_uuids,
            request.model_version,
            user_id=current_user.username,
        )
        
        if job:
            logger.info(f"Batch prediction job {job.id} enqueued by {current_user.username}")
            return JobEnqueuedResponse(
                job_id=job.id,
                status="queued",
                message="Batch prediction job enqueued successfully"
            )
        else:
            return JobEnqueuedResponse(
                job_id="sync",
                status="completed",
                message="Job executed synchronously (queue disabled)"
            )
    
    except Exception as e:
        logger.error(f"Failed to enqueue batch prediction job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue batch prediction job: {str(e)}"
        )


@router.post(
    "/jobs/report",
    response_model=JobEnqueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue Report Generation Job",
    description="""
    Enqueue a report generation job.
    
    **Parameters:**
    - report_type: Type of report (predictions, patients, analytics)
    - start_date: Start date for report period (ISO format)
    - end_date: End date for report period (ISO format)
    - filters: Optional filters for the report
    
    **Returns:**
    - Job ID for tracking
    
    **Use Case:**
    - Generate large reports asynchronously
    - Schedule periodic report generation
    """
)
async def enqueue_report_job_endpoint(
    request: EnqueueReportRequest,
    current_user: User = Depends(get_current_active_user)
) -> JobEnqueuedResponse:
    """Enqueue report generation job"""
    try:
        job = enqueue_job(
            generate_report_job,
            request.report_type,
            request.start_date,
            request.end_date,
            request.filters,
            user_id=current_user.username,
        )
        
        if job:
            logger.info(f"Report generation job {job.id} enqueued by {current_user.username}")
            return JobEnqueuedResponse(
                job_id=job.id,
                status="queued",
                message="Report generation job enqueued successfully"
            )
        else:
            return JobEnqueuedResponse(
                job_id="sync",
                status="completed",
                message="Job executed synchronously (queue disabled)"
            )
    
    except Exception as e:
        logger.error(f"Failed to enqueue report generation job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue report generation job: {str(e)}"
        )


@router.post(
    "/jobs/cleanup",
    response_model=JobEnqueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue Cleanup Job",
    description="""
    Enqueue a data cleanup job.
    
    **Parameters:**
    - days_to_keep: Number of days of data to keep
    - dry_run: If True, only report what would be deleted
    
    **Returns:**
    - Job ID for tracking
    
    **Use Case:**
    - Schedule periodic data cleanup
    - Remove old data asynchronously
    """
)
async def enqueue_cleanup_job_endpoint(
    request: EnqueueCleanupRequest,
    current_user: User = Depends(get_current_superuser)
) -> JobEnqueuedResponse:
    """Enqueue cleanup job"""
    try:
        job = enqueue_job(
            cleanup_old_data_job,
            request.days_to_keep,
            request.dry_run,
            user_id=current_user.username,
        )
        
        if job:
            logger.info(f"Cleanup job {job.id} enqueued by {current_user.username}")
            return JobEnqueuedResponse(
                job_id=job.id,
                status="queued",
                message="Cleanup job enqueued successfully"
            )
        else:
            return JobEnqueuedResponse(
                job_id="sync",
                status="completed",
                message="Job executed synchronously (queue disabled)"
            )
    
    except Exception as e:
        logger.error(f"Failed to enqueue cleanup job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue cleanup job: {str(e)}"
        )


@router.get(
    "/workers",
    response_model=List[WorkerInfo],
    summary="Get All Workers",
    description="""
    Get information about all active workers.
    
    **Returns:**
    - List of worker information including:
      - Worker name
      - Current state
      - Current job (if any)
      - Queues being processed
    
    **Permissions:**
    - Requires active user authentication
    """
)
async def get_workers_endpoint(
    current_user: User = Depends(get_current_active_user)
) -> List[WorkerInfo]:
    """Get all workers"""
    try:
        workers = get_all_workers()
        return [WorkerInfo(**w) for w in workers]
    except Exception as e:
        logger.error(f"Failed to get workers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workers: {str(e)}"
        )


@router.get(
    "/scheduled",
    response_model=list[ScheduledJobInfo],
    summary="Get Scheduled Jobs",
    description="""
    Get all scheduled jobs.
    
    **Returns:**
    - List of scheduled job information
    
    **Permissions:**
    - Requires active user authentication
    """
)
async def get_scheduled_jobs_endpoint(
    current_user: User = Depends(get_current_active_user)
) -> list[ScheduledJobInfo]:
    """Get scheduled jobs"""
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Scheduler is not available due to dependency compatibility issues"
        )
    try:
        jobs = list_scheduled_jobs()
        return [ScheduledJobInfo(**j) for j in jobs]
    except Exception as e:
        logger.error(f"Failed to get scheduled jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduled jobs: {str(e)}"
        )


@router.delete(
    "/scheduled/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel Scheduled Job",
    description="""
    Cancel a scheduled job by ID.
    
    **Error:**
    - 404: Scheduled job not found
    - 400: Failed to cancel job
    
    **Permissions:**
    - Requires superuser privileges
    """
)
async def cancel_scheduled_job_endpoint(
    job_id: str,
    current_user: User = Depends(get_current_superuser)
) -> None:
    """Cancel scheduled job"""
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Scheduler is not available due to dependency compatibility issues"
        )
    success = cancel_scheduled_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel scheduled job '{job_id}'"
        )


@router.post(
    "/schedule/cleanup",
    response_model=JobEnqueuedResponse,
    summary="Schedule Daily Cleanup",
    description="""
    Schedule a daily data cleanup job.
    
    **Parameters:**
    - hour: Hour to run (0-23, default: 2)
    - minute: Minute to run (0-59, default: 0)
    - days_to_keep: Days of data to keep (default: 90)
    
    **Returns:**
    - Scheduled job ID
    
    **Permissions:**
    - Requires superuser privileges
    """
)
async def schedule_cleanup_endpoint(
    request: ScheduleCleanupRequest,
    current_user: User = Depends(get_current_superuser)
) -> JobEnqueuedResponse:
    """Schedule daily cleanup"""
    if not SCHEDULER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Scheduler is not available due to dependency compatibility issues"
        )
    try:
        job_id = schedule_daily_cleanup(
            hour=request.hour,
            minute=request.minute,
            days_to_keep=request.days_to_keep
        )
        
        logger.info(f"Daily cleanup scheduled by {current_user.username}: {job_id}")
        return JobEnqueuedResponse(
            job_id=job_id,
            status="scheduled",
            message="Daily cleanup job scheduled successfully"
        )
    
    except Exception as e:
        logger.error(f"Failed to schedule cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule cleanup: {str(e)}"
        )


@router.get(
    "/scheduler/status",
    response_model=Dict[str, Any],
    summary="Get Scheduler Status",
    description="""
    Get the current status of the scheduler.
    
    **Returns:**
    - Scheduler running status
    - Total scheduled jobs
    - Queue name
    - Check interval
    
    **Permissions:**
    - Requires active user authentication
    """
)
async def get_scheduler_status_endpoint(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get scheduler status"""
    if not SCHEDULER_AVAILABLE:
        return {
            "available": False,
            "message": "Scheduler is not available due to dependency compatibility issues"
        }
    try:
        status_data = get_scheduler_status()
        return status_data
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}"
        )
