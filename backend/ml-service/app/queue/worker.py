"""
RQ Worker Configuration for IHVN ML Service

Provides Redis queue connection and worker setup for background job processing.
"""
import logging
from typing import Optional
from redis import Redis
from rq import Queue, Worker
from rq.job import Job

from ..config import settings

logger = logging.getLogger(__name__)

# Global connection and queue instances
_redis_connection: Optional[Redis] = None
_queue: Optional[Queue] = None


def get_redis_connection() -> Redis:
    """
    Get or create Redis connection for RQ
    
    Returns:
        Redis connection instance
    
    Example:
        redis_conn = get_redis_connection()
    """
    global _redis_connection
    
    if _redis_connection is None:
        _redis_connection = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password if settings.redis_password else None,
            decode_responses=False,  # RQ needs binary responses
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        logger.info(
            f"Redis connection created: {settings.redis_host}:{settings.redis_port}"
        )
    
    return _redis_connection


def get_queue(name: Optional[str] = None) -> Queue:
    """
    Get or create RQ queue
    
    Args:
        name: Queue name (default: from settings)
    
    Returns:
        RQ Queue instance
    
    Example:
        queue = get_queue()
        job = queue.enqueue(process_etl_job, 'data.csv')
    """
    global _queue
    
    queue_name = name or settings.queue_name
    
    if _queue is None or _queue.name != queue_name:
        redis_conn = get_redis_connection()
        _queue = Queue(queue_name, connection=redis_conn, is_async=settings.redis_queue_enabled)
        logger.info(f"Queue '{queue_name}' created (async={settings.redis_queue_enabled})")
    
    return _queue


def get_worker(
    queue_names: Optional[list[str]] = None,
    name: Optional[str] = None
) -> Worker:
    """
    Get RQ worker instance
    
    Args:
        queue_names: List of queue names to listen to (default: [settings.queue_name])
        name: Worker name (default: auto-generated)
    
    Returns:
        RQ Worker instance
    
    Example:
        worker = get_worker()
        worker.work(with_scheduler=True)
    """
    if queue_names is None:
        queue_names = [settings.queue_name]
    
    redis_conn = get_redis_connection()
    
    worker = Worker(
        queue_names,
        connection=redis_conn,
        name=name,
    )
    
    logger.info(f"Worker '{worker.name}' created for queues: {queue_names}")
    return worker


def enqueue_job(
    func,
    *args,
    queue_name: Optional[str] = None,
    timeout: Optional[int] = None,
    result_ttl: int = 86400,  # 24 hours
    failure_ttl: int = 3600,  # 1 hour
    **kwargs
) -> Optional[Job]:
    """
    Enqueue a job to the queue
    
    Args:
        func: Function to execute
        *args: Function arguments
        queue_name: Queue name (default: from settings)
        timeout: Job timeout in seconds (default: from settings)
        result_ttl: Result TTL in seconds
        failure_ttl: Failure TTL in seconds
        **kwargs: Function keyword arguments
    
    Returns:
        Job instance or None if queuing is disabled
    
    Example:
        job = enqueue_job(
            process_etl_job,
            'data.csv',
            batch_size=50,
            timeout=300
        )
    """
    if not settings.redis_queue_enabled:
        logger.warning("Queue is disabled, executing job synchronously")
        try:
            func(*args, **kwargs)
            return None
        except Exception as e:
            logger.error(f"Synchronous job execution failed: {e}")
            raise
    
    queue = get_queue(queue_name)
    job_timeout = timeout or settings.default_job_timeout
    
    job = queue.enqueue(
        func,
        *args,
        job_timeout=job_timeout,
        result_ttl=result_ttl,
        failure_ttl=failure_ttl,
        **kwargs
    )
    
    logger.info(
        f"Job {job.id} enqueued to queue '{queue.name}' "
        f"(timeout={job_timeout}s)"
    )
    
    return job


def get_job_status(job_id: str, queue_name: Optional[str] = None) -> Optional[dict]:
    """
    Get job status by ID
    
    Args:
        job_id: Job ID
        queue_name: Queue name (default: from settings)
    
    Returns:
        Dict with job status or None if not found
    
    Example:
        status = get_job_status('abc123')
        print(status['status'])  # 'queued', 'started', 'finished', 'failed'
    """
    try:
        redis_conn = get_redis_connection()
        job = Job.fetch(job_id, connection=redis_conn)
        
        return {
            "id": job.id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "exc_info": job.exc_info,
            "result": job.result,
        }
    except Exception as e:
        logger.error(f"Failed to fetch job {job_id}: {e}")
        return None


def cancel_job(job_id: str, queue_name: Optional[str] = None) -> bool:
    """
    Cancel a job by ID
    
    Args:
        job_id: Job ID
        queue_name: Queue name (default: from settings)
    
    Returns:
        True if job was cancelled, False otherwise
    
    Example:
        success = cancel_job('abc123')
    """
    try:
        redis_conn = get_redis_connection()
        job = Job.fetch(job_id, connection=redis_conn)
        
        # Can only cancel queued jobs
        if job.get_status() == "queued":
            job.cancel()
            logger.info(f"Job {job_id} cancelled")
            return True
        else:
            logger.warning(f"Cannot cancel job {job_id} with status {job.get_status()}")
            return False
    
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        return False


def get_queue_stats(queue_name: Optional[str] = None) -> dict:
    """
    Get queue statistics
    
    Args:
        queue_name: Queue name (default: from settings)
    
    Returns:
        Dict with queue statistics
    
    Example:
        stats = get_queue_stats()
        print(f"Queued: {stats['queued']}, Failed: {stats['failed']}")
    """
    queue = get_queue(queue_name)
    
    return {
        "name": queue.name,
        "queued": len(queue),
        "failed": queue.failed_job_count,
        "started": queue.started_job_count,
        "finished": queue.finished_job_count,
        "workers": queue.worker_count,
    }


def get_all_workers(queue_name: Optional[str] = None) -> list[dict]:
    """
    Get all workers for a queue
    
    Args:
        queue_name: Queue name (default: from settings)
    
    Returns:
        List of worker information dicts
    
    Example:
        workers = get_all_workers()
        for worker in workers:
            print(f"Worker: {worker['name']}, State: {worker['state']}")
    """
    redis_conn = get_redis_connection()
    queue = get_queue(queue_name)
    
    workers = Worker.all(queue=queue, connection=redis_conn)
    
    return [
        {
            "name": w.name,
            "state": w.get_state(),
            "current_job": w.get_current_job_id(),
            "queues": [q.name for q in w.queues],
        }
        for w in workers
    ]


def close_redis_connection() -> None:
    """Close Redis connection (cleanup)"""
    global _redis_connection, _queue
    
    if _redis_connection:
        _redis_connection.close()
        _redis_connection = None
        logger.info("Redis connection closed")
    
    _queue = None
