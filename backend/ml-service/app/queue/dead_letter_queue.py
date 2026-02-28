"""
Dead Letter Queue (DLQ) for RQ

Handles failed jobs by moving them to a separate queue for inspection and retry.
Provides configurable retry policies and monitoring for failed jobs.

Features:
- Automatic retry with exponential backoff
- Maximum retry limits
- Dead letter queue for permanently failed jobs
- Monitoring and alerting for failed jobs
- Manual retry interface
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import traceback

from rq import Queue, Worker
from rq.job import Job
from redis import Redis

from app.config import settings

logger = logging.getLogger(__name__)


class FailureReason(Enum):
    """Reasons for job failure"""
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    MAX_RETRIES = "max_retries"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass
class RetryPolicy:
    """Retry policy for failed jobs"""
    max_retries: int = 3
    backoff_factor: float = 2.0  # Exponential backoff factor
    initial_delay: float = 60.0  # Initial delay in seconds
    max_delay: float = 3600.0  # Maximum delay between retries
    retry_on: List[Exception] = field(default_factory=list)  # Empty = retry on all exceptions
    
    def get_retry_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff
        
        Args:
            attempt: Retry attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if job should be retried
        
        Args:
            exception: Exception that caused failure
            attempt: Current retry attempt
            
        Returns:
            True if should retry, False otherwise
        """
        # Check max retries
        if attempt >= self.max_retries:
            return False
        
        # Check specific exceptions
        if self.retry_on:
            return any(isinstance(exception, exc_type) for exc_type in self.retry_on)
        
        # Retry on all exceptions by default
        return True


@dataclass
class DeadLetterJob:
    """Dead letter job data"""
    job_id: str
    original_job_id: str
    job_func: str
    job_args: List[Any]
    job_kwargs: Dict[str, Any]
    exception: str
    exception_type: str
    traceback: str
    failure_reason: FailureReason
    failed_at: datetime
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeadLetterQueue:
    """
    Dead Letter Queue for handling failed RQ jobs
    
    Moves failed jobs to a separate queue for inspection and retry.
    Implements configurable retry policies.
    """
    
    # Default retry policies for different job types
    DEFAULT_POLICIES = {
        "etl_job": RetryPolicy(max_retries=3, backoff_factor=2.0, initial_delay=300),
        "batch_prediction": RetryPolicy(max_retries=2, backoff_factor=2.0, initial_delay=60),
        "report_generation": RetryPolicy(max_retries=3, backoff_factor=2.0, initial_delay=180),
        "cleanup_job": RetryPolicy(max_retries=2, backoff_factor=2.0, initial_delay=600),
        "notification_job": RetryPolicy(max_retries=5, backoff_factor=1.5, initial_delay=60),
    }
    
    def __init__(
        self,
        redis_conn: Optional[Redis] = None,
        dlq_queue_name: str = "dead_letter",
        retry_queue_name: str = "retry_queue"
    ):
        """
        Initialize Dead Letter Queue
        
        Args:
            redis_conn: Redis connection
            dlq_queue_name: Name of dead letter queue
            retry_queue_name: Name of retry queue
        """
        self.redis_conn = redis_conn
        self.dlq_queue_name = dlq_queue_name
        self.retry_queue_name = retry_queue_name
        
        # Create queues
        self.dlq_queue = Queue(dlq_queue_name, connection=redis_conn, is_async=False)
        self.retry_queue = Queue(retry_queue_name, connection=redis_conn, is_async=False)
        
        # Custom retry policies
        self.custom_policies: Dict[str, RetryPolicy] = {}
        
        logger.info(f"Dead Letter Queue initialized: dlq={dlq_queue_name}, retry={retry_queue_name}")
    
    def set_retry_policy(self, job_type: str, policy: RetryPolicy):
        """
        Set custom retry policy for job type
        
        Args:
            job_type: Type of job (function name)
            policy: Retry policy
        """
        self.custom_policies[job_type] = policy
        logger.info(f"Set custom retry policy for {job_type}: max_retries={policy.max_retries}")
    
    def get_retry_policy(self, job_func: str) -> RetryPolicy:
        """
        Get retry policy for job function
        
        Args:
            job_func: Job function name
            
        Returns:
            Retry policy
        """
        # Check custom policies first
        if job_func in self.custom_policies:
            return self.custom_policies[job_func]
        
        # Check default policies
        for job_type, policy in self.DEFAULT_POLICIES.items():
            if job_type in job_func:
                return policy
        
        # Default policy
        return RetryPolicy()
    
    def handle_failed_job(self, job: Job, exc: Exception) -> bool:
        """
        Handle failed job
        
        Args:
            job: Failed RQ job
            exc: Exception that caused failure
            
        Returns:
            True if job was moved to DLQ, False otherwise
        """
        try:
            # Get job details
            job_func = job.func_name
            job_args = job.args
            job_kwargs = job.kwargs
            
            # Determine failure reason
            failure_reason = self._classify_failure(exc)
            
            # Get retry policy
            policy = self.get_retry_policy(job_func)
            
            # Get current retry count
            retry_count = job.meta.get("retry_count", 0)
            
            # Check if should retry
            if policy.should_retry(exc, retry_count):
                # Schedule for retry
                return self._schedule_retry(job, exc, policy)
            else:
                # Move to dead letter queue
                return self._move_to_dlq(job, exc, failure_reason)
        
        except Exception as e:
            logger.error(f"Error handling failed job {job.id}: {e}")
            return False
    
    def _classify_failure(self, exc: Exception) -> FailureReason:
        """Classify failure reason"""
        if isinstance(exc, TimeoutError):
            return FailureReason.TIMEOUT
        elif "ValidationError" in type(exc).__name__:
            return FailureReason.VALIDATION_ERROR
        else:
            return FailureReason.EXCEPTION
    
    def _schedule_retry(self, job: Job, exc: Exception, policy: RetryPolicy) -> bool:
        """
        Schedule job for retry
        
        Args:
            job: Failed job
            exc: Exception that caused failure
            policy: Retry policy
            
        Returns:
            True if scheduled for retry
        """
        retry_count = job.meta.get("retry_count", 0) + 1
        delay = policy.get_retry_delay(retry_count)
        
        # Calculate retry time
        next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        
        # Create retry job
        retry_job = self.retry_queue.enqueue_at(
            job.func,
            next_retry_at,
            *job.args,
            **job.kwargs,
            meta={
                "original_job_id": job.id,
                "retry_count": retry_count,
                "last_exception": str(exc),
                "last_exception_type": type(exc).__name__,
                "scheduled_for": next_retry_at.isoformat()
            },
            job_timeout=job.timeout,
            result_ttl=job.result_ttl,
            ttl=job.ttl
        )
        
        logger.info(
            f"Scheduled job {job.id} for retry (attempt {retry_count}) "
            f"at {next_retry_at.isoformat()}"
        )
        
        # Record metrics
        self._record_retry_scheduled(job, exc, retry_count, delay)
        
        return True
    
    def _move_to_dlq(self, job: Job, exc: Exception, reason: FailureReason) -> bool:
        """
        Move job to dead letter queue
        
        Args:
            job: Failed job
            exc: Exception that caused failure
            reason: Failure reason
            
        Returns:
            True if moved to DLQ
        """
        # Create DLQ job
        dlq_job = self.dlq_queue.enqueue(
            self._dlq_handler,
            job.id,
            job.func_name,
            job.args,
            job.kwargs,
            str(exc),
            type(exc).__name__,
            traceback.format_exc(),
            reason.value,
            job.meta.get("retry_count", 0),
            meta={
                "original_job_id": job.id,
                "failed_at": datetime.utcnow().isoformat(),
                "failure_reason": reason.value
            }
        )
        
        logger.warning(
            f"Moved job {job.id} to dead letter queue. "
            f"Reason: {reason.value}, Exception: {type(exc).__name__}"
        )
        
        # Record metrics
        self._record_dlq_job(job, exc, reason)
        
        # Send alert if configured
        self._send_dlq_alert(job, exc, reason)
        
        return True
    
    def _dlq_handler(
        self,
        original_job_id: str,
        job_func: str,
        job_args: List[Any],
        job_kwargs: Dict[str, Any],
        exception: str,
        exception_type: str,
        traceback_str: str,
        failure_reason: str,
        retry_count: int
    ):
        """
        Handler for dead letter queue jobs
        
        This is called when a job is processed from the DLQ.
        """
        logger.info(f"Processing DLQ job for original job {original_job_id}")
        
        # Store DLQ job info in database for inspection
        self._store_dlq_job(
            original_job_id, job_func, job_args, job_kwargs,
            exception, exception_type, traceback_str, failure_reason, retry_count
        )
    
    def _store_dlq_job(
        self,
        original_job_id: str,
        job_func: str,
        job_args: List[Any],
        job_kwargs: Dict[str, Any],
        exception: str,
        exception_type: str,
        traceback_str: str,
        failure_reason: str,
        retry_count: int
    ):
        """Store DLQ job in database for inspection"""
        from app.utils.database import DatabaseManager
        
        query = """
        CREATE TABLE IF NOT EXISTS dead_letter_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_job_id TEXT NOT NULL,
            job_func TEXT NOT NULL,
            job_args TEXT,
            job_kwargs TEXT,
            exception TEXT NOT NULL,
            exception_type TEXT NOT NULL,
            traceback TEXT NOT NULL,
            failure_reason TEXT NOT NULL,
            retry_count INTEGER NOT NULL,
            failed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN NOT NULL DEFAULT 0,
            resolved_at TIMESTAMP,
            resolution_notes TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_dlq_original_job ON dead_letter_jobs(original_job_id);
        CREATE INDEX IF NOT EXISTS idx_dlq_resolved ON dead_letter_jobs(resolved);
        """
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                # Ensure table exists
                conn.execute(query)
                
                # Insert DLQ job
                insert_query = """
                INSERT INTO dead_letter_jobs (
                    original_job_id, job_func, job_args, job_kwargs,
                    exception, exception_type, traceback, failure_reason, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                
                conn.execute(insert_query, (
                    original_job_id,
                    job_func,
                    str(job_args),
                    str(job_kwargs),
                    exception,
                    exception_type,
                    traceback_str,
                    failure_reason,
                    retry_count
                ))
                conn.commit()
                
                logger.info(f"Stored DLQ job {original_job_id} in database")
        
        except Exception as e:
            logger.error(f"Failed to store DLQ job in database: {e}")
    
    def get_dlq_jobs(self, resolved: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get dead letter jobs from database
        
        Args:
            resolved: Include resolved jobs
            limit: Maximum number of jobs to return
            
        Returns:
            List of DLQ jobs
        """
        from app.utils.database import DatabaseManager
        
        query = """
        SELECT * FROM dead_letter_jobs
        WHERE resolved = ?
        ORDER BY failed_at DESC
        LIMIT ?;
        """
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (1 if resolved else 0, limit))
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
        
        except Exception as e:
            logger.error(f"Failed to get DLQ jobs: {e}")
            return []
    
    def retry_dlq_job(self, original_job_id: str) -> bool:
        """
        Retry a job from dead letter queue
        
        Args:
            original_job_id: Original job ID to retry
            
        Returns:
            True if job was scheduled for retry
        """
        from app.utils.database import DatabaseManager
        
        # Get job details from database
        query = """
        SELECT * FROM dead_letter_jobs
        WHERE original_job_id = ? AND resolved = 0
        LIMIT 1;
        """
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (original_job_id,))
                
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"DLQ job {original_job_id} not found")
                    return False
                
                columns = [desc[0] for desc in cursor.description]
                job_data = dict(zip(columns, row))
                
                # Parse job args and kwargs
                import ast
                job_args = ast.literal_eval(job_data["job_args"])
                job_kwargs = ast.literal_eval(job_data["job_kwargs"])
                
                # Re-enqueue job
                from app.queue import get_queue
                queue = get_queue()
                
                queue.enqueue(
                    job_data["job_func"],
                    *job_args,
                    **job_kwargs,
                    meta={
                        "dlq_retry": True,
                        "original_job_id": original_job_id,
                        "dlq_id": job_data["id"]
                    }
                )
                
                # Mark as resolved
                update_query = """
                UPDATE dead_letter_jobs
                SET resolved = 1, resolved_at = CURRENT_TIMESTAMP, resolution_notes = 'Retried manually'
                WHERE id = ?;
                """
                
                cursor.execute(update_query, (job_data["id"],))
                conn.commit()
                
                logger.info(f"Retried DLQ job {original_job_id}")
                return True
        
        except Exception as e:
            logger.error(f"Failed to retry DLQ job {original_job_id}: {e}")
            return False
    
    def _record_retry_scheduled(self, job: Job, exc: Exception, retry_count: int, delay: float):
        """Record retry scheduled metric"""
        try:
            from app.monitoring import MetricsManager
            MetricsManager.record_dlq_retry_scheduled(job.func_name, retry_count, delay)
        except Exception as e:
            logger.error(f"Failed to record retry metric: {e}")
    
    def _record_dlq_job(self, job: Job, exc: Exception, reason: FailureReason):
        """Record DLQ job metric"""
        try:
            from app.monitoring import MetricsManager
            MetricsManager.record_dlq_job_added(job.func_name, reason.value)
        except Exception as e:
            logger.error(f"Failed to record DLQ metric: {e}")
    
    def _send_dlq_alert(self, job: Job, exc: Exception, reason: FailureReason):
        """Send alert for DLQ job"""
        try:
            # Log warning
            logger.warning(
                f"DLQ Alert: Job {job.id} ({job.func_name}) failed. "
                f"Reason: {reason.value}, Exception: {type(exc).__name__}: {exc}"
            )
            
            # In production, integrate with alerting system
            # (PagerDuty, Slack, etc.)
            
        except Exception as e:
            logger.error(f"Failed to send DLQ alert: {e}")


# Global DLQ instance
_dlq_instance: Optional[DeadLetterQueue] = None


def get_dlq(redis_conn: Optional[Redis] = None) -> DeadLetterQueue:
    """
    Get or create Dead Letter Queue instance
    
    Args:
        redis_conn: Redis connection
        
    Returns:
        DeadLetterQueue instance
    """
    global _dlq_instance
    
    if _dlq_instance is None:
        if redis_conn is None:
            from app.queue import get_redis_connection
            redis_conn = get_redis_connection()
        
        _dlq_instance = DeadLetterQueue(redis_conn)
    
    return _dlq_instance
