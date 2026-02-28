"""
Queue System for IHVN ML Service

Provides RQ-based background job processing for:
- ETL data processing
- Batch predictions
- Report generation
- Scheduled tasks
"""

from .jobs import (
    process_etl_job,
    batch_prediction_job,
    generate_report_job,
    cleanup_old_data_job,
    send_notifications_job,
)
from .worker import get_queue, get_redis_connection, get_worker

# Optional scheduler import (may not be available due to compatibility issues)
try:
    from .scheduler import get_scheduler
    _scheduler_available = True
except ImportError:
    _scheduler_available = False
    get_scheduler = None

__all__ = [
    "process_etl_job",
    "batch_prediction_job",
    "generate_report_job",
    "cleanup_old_data_job",
    "send_notifications_job",
    "get_queue",
    "get_redis_connection",
    "get_worker",
]

if _scheduler_available:
    __all__.append("get_scheduler")
