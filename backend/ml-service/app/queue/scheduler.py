"""
RQ Scheduler Configuration for IHVN ML Service

Provides scheduled task functionality for recurring jobs like:
- Daily data cleanup
- Weekly report generation
- Monthly model retraining
"""
import logging
from typing import Optional, Callable
from datetime import datetime, timedelta, time

from rq_scheduler import Scheduler
from redis import Redis

from .worker import get_redis_connection
from ..config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """
    Get or create RQ scheduler instance
    
    Returns:
        RQ Scheduler instance
    
    Example:
        scheduler = get_scheduler()
        scheduler.schedule(
            scheduled_time=datetime.now() + timedelta(minutes=5),
            func=cleanup_old_data_job,
            interval=86400,  # Daily
            interval_unit='seconds'
        )
    """
    global _scheduler
    
    if _scheduler is None:
        redis_conn = get_redis_connection()
        _scheduler = Scheduler(
            connection=redis_conn,
            queue_name=settings.queue_name,
            interval=60,  # Check for scheduled jobs every 60 seconds
        )
        logger.info("RQ Scheduler created")
    
    return _scheduler


def schedule_daily_cleanup(
    hour: int = 2,
    minute: int = 0,
    days_to_keep: int = 90
) -> str:
    """
    Schedule daily data cleanup job
    
    Args:
        hour: Hour to run (0-23, default: 2 for 2 AM)
        minute: Minute to run (0-59, default: 0)
        days_to_keep: Number of days of data to keep
    
    Returns:
        Job ID
    
    Example:
        job_id = schedule_daily_cleanup(hour=3, minute=30, days_to_keep=60)
    """
    from .jobs import cleanup_old_data_job
    
    scheduler = get_scheduler()
    
    # Calculate next scheduled time
    now = datetime.now()
    scheduled_time = datetime.combine(now.date(), time(hour=hour, minute=minute))
    if scheduled_time <= now:
        scheduled_time += timedelta(days=1)
    
    job = scheduler.schedule(
        scheduled_time=scheduled_time,
        func=cleanup_old_data_job,
        args=[days_to_keep, False],  # dry_run=False
        interval=86400,  # Daily (24 hours)
        interval_unit='seconds',
        repeat=None,  # Repeat indefinitely
        timeout=3600,  # 1 hour timeout
        result_ttl=86400,  # Keep results for 24 hours
    )
    
    logger.info(
        f"Scheduled daily cleanup job {job.id} at {scheduled_time} "
        f"(keeping {days_to_keep} days of data)"
    )
    
    return job.id


def schedule_weekly_report(
    day_of_week: int = 0,  # Monday=0, Sunday=6
    hour: int = 8,
    minute: int = 0,
    report_type: str = "predictions"
) -> str:
    """
    Schedule weekly report generation
    
    Args:
        day_of_week: Day of week (0=Monday, 6=Sunday)
        hour: Hour to run (0-23)
        minute: Minute to run (0-59)
        report_type: Type of report to generate
    
    Returns:
        Job ID
    
    Example:
        job_id = schedule_weekly_report(
            day_of_week=0,  # Monday
            hour=9,
            report_type='predictions'
        )
    """
    from .jobs import generate_report_job
    
    scheduler = get_scheduler()
    
    # Calculate next scheduled time
    now = datetime.now()
    days_ahead = day_of_week - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    
    scheduled_time = datetime.combine(
        (now + timedelta(days=days_ahead)).date(),
        time(hour=hour, minute=minute)
    )
    
    # Calculate date range for report (last 7 days)
    end_date = (scheduled_time - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (scheduled_time - timedelta(days=7)).strftime("%Y-%m-%d")
    
    job = scheduler.schedule(
        scheduled_time=scheduled_time,
        func=generate_report_job,
        args=[report_type, start_date, end_date],
        interval=7 * 86400,  # Weekly (7 days)
        interval_unit='seconds',
        repeat=None,
        timeout=1800,  # 30 minutes timeout
        result_ttl=86400 * 7,  # Keep results for 7 days
    )
    
    logger.info(
        f"Scheduled weekly {report_type} report job {job.id} at {scheduled_time}"
    )
    
    return job.id


def schedule_monthly_model_retraining(
    day_of_month: int = 1,
    hour: int = 3,
    minute: int = 0,
    model_version: Optional[str] = None
) -> str:
    """
    Schedule monthly model retraining
    
    Args:
        day_of_month: Day of month (1-31)
        hour: Hour to run (0-23)
        minute: Minute to run (0-59)
        model_version: Optional model version identifier
    
    Returns:
        Job ID
    
    Example:
        job_id = schedule_monthly_model_retraining(
            day_of_month=1,
            hour=4,
            model_version='v2.0'
        )
    """
    from .jobs import retrain_model_job
    
    scheduler = get_scheduler()
    
    # Calculate next scheduled time
    now = datetime.now()
    scheduled_time = datetime(
        year=now.year,
        month=now.month,
        day=min(day_of_month, 28),  # Handle months with fewer days
        hour=hour,
        minute=minute
    )
    
    if scheduled_time <= now:
        # Move to next month
        if now.month == 12:
            scheduled_time = datetime(year=now.year + 1, month=1, day=day_of_month)
        else:
            scheduled_time = datetime(year=now.year, month=now.month + 1, day=day_of_month)
    
    job = scheduler.schedule(
        scheduled_time=scheduled_time,
        func=retrain_model_job,
        args=["./data/training_data.csv", model_version],
        interval=30 * 86400,  # Monthly (30 days)
        interval_unit='seconds',
        repeat=None,
        timeout=7200,  # 2 hours timeout
        result_ttl=86400 * 30,  # Keep results for 30 days
    )
    
    logger.info(
        f"Scheduled monthly model retraining job {job.id} at {scheduled_time}"
    )
    
    return job.id


def schedule_hourly_notifications(
    minute: int = 0,
    notification_type: str = "in_app",
    recipients: Optional[list] = None,
    message_template: str = "Hourly update"
) -> str:
    """
    Schedule hourly notifications
    
    Args:
        minute: Minute to run (0-59)
        notification_type: Type of notification
        recipients: List of recipients
        message_template: Message template
    
    Returns:
        Job ID
    
    Example:
        job_id = schedule_hourly_notifications(
            minute=15,
            notification_type='in_app',
            recipients=['user1', 'user2']
        )
    """
    from .jobs import send_notifications_job
    
    scheduler = get_scheduler()
    
    # Calculate next scheduled time
    now = datetime.now()
    scheduled_time = datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=now.hour + 1,
        minute=minute
    )
    
    if recipients is None:
        recipients = []
    
    job = scheduler.schedule(
        scheduled_time=scheduled_time,
        func=send_notifications_job,
        args=[notification_type, recipients, message_template],
        interval=3600,  # Hourly
        interval_unit='seconds',
        repeat=None,
        timeout=300,  # 5 minutes timeout
        result_ttl=86400,  # Keep results for 24 hours
    )
    
    logger.info(
        f"Scheduled hourly notifications job {job.id} at {scheduled_time}"
    )
    
    return job.id


def schedule_custom_job(
    func: Callable,
    scheduled_time: datetime,
    interval: int,
    interval_unit: str = 'seconds',
    args: Optional[list] = None,
    kwargs: Optional[dict] = None,
    timeout: int = 600,
    repeat: Optional[int] = None
) -> str:
    """
    Schedule a custom job
    
    Args:
        func: Function to execute
        scheduled_time: When to first run the job
        interval: Interval between runs
        interval_unit: Unit of interval (seconds, minutes, hours, days)
        args: Function arguments
        kwargs: Function keyword arguments
        timeout: Job timeout in seconds
        repeat: Number of times to repeat (None = infinite)
    
    Returns:
        Job ID
    
    Example:
        job_id = schedule_custom_job(
            func=my_custom_function,
            scheduled_time=datetime.now() + timedelta(minutes=5),
            interval=3600,
            interval_unit='seconds',
            args=['arg1', 'arg2']
        )
    """
    scheduler = get_scheduler()
    
    # Convert interval to seconds
    multipliers = {
        'seconds': 1,
        'minutes': 60,
        'hours': 3600,
        'days': 86400,
    }
    interval_seconds = interval * multipliers.get(interval_unit, 1)
    
    job = scheduler.schedule(
        scheduled_time=scheduled_time,
        func=func,
        args=args or [],
        kwargs=kwargs or {},
        interval=interval_seconds,
        interval_unit='seconds',
        repeat=repeat,
        timeout=timeout,
        result_ttl=86400,
    )
    
    logger.info(
        f"Scheduled custom job {job.id} at {scheduled_time} "
        f"(interval={interval}{interval_unit})"
    )
    
    return job.id


def cancel_scheduled_job(job_id: str) -> bool:
    """
    Cancel a scheduled job
    
    Args:
        job_id: Job ID to cancel
    
    Returns:
        True if cancelled, False otherwise
    
    Example:
        success = cancel_scheduled_job('abc123')
    """
    try:
        scheduler = get_scheduler()
        scheduler.cancel(job_id)
        logger.info(f"Scheduled job {job_id} cancelled")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel scheduled job {job_id}: {e}")
        return False


def list_scheduled_jobs() -> list[dict]:
    """
    List all scheduled jobs
    
    Returns:
        List of scheduled job information
    
    Example:
        jobs = list_scheduled_jobs()
        for job in jobs:
            print(f"Job {job['id']}: {job['func_name']} at {job['scheduled_time']}")
    """
    try:
        scheduler = get_scheduler()
        jobs = scheduler.get_jobs()
        
        return [
            {
                "id": job.id,
                "func_name": job.func_name,
                "scheduled_time": job.scheduled_time.isoformat() if job.scheduled_time else None,
                "interval": job.meta.get('interval'),
                "timeout": job.timeout,
            }
            for job in jobs
        ]
    
    except Exception as e:
        logger.error(f"Failed to list scheduled jobs: {e}")
        return []


def start_scheduler() -> None:
    """
    Start the scheduler in blocking mode
    
    Example:
        start_scheduler()  # Blocks until interrupted
    """
    scheduler = get_scheduler()
    logger.info("Starting RQ scheduler...")
    scheduler.run()


def get_scheduler_status() -> dict:
    """
    Get scheduler status
    
    Returns:
        Dict with scheduler status information
    
    Example:
        status = get_scheduler_status()
        print(f"Jobs: {status['total_jobs']}")
    """
    try:
        scheduler = get_scheduler()
        jobs = scheduler.get_jobs()
        
        return {
            "running": scheduler._is_running,
            "total_jobs": len(jobs),
            "queue_name": scheduler.queue_name,
            "interval": scheduler._interval,
        }
    
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        return {
            "running": False,
            "error": str(e),
        }
