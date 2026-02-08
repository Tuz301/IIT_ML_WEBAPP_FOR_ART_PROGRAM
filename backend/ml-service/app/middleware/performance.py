"""
Performance monitoring middleware for FastAPI
"""
import time
import psutil
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any
import logging
from ..monitoring import MetricsManager

logger = logging.getLogger(__name__)

# Track in-progress requests
in_progress_requests: Dict[str, Dict[str, Any]] = {}


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive performance monitoring"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', str(time.time()))

        # Track request start
        endpoint = request.url.path
        method = request.method
        MetricsManager.update_api_requests_in_progress(method, endpoint, 1)

        # Record request start in progress tracking
        in_progress_requests[request_id] = {
            'method': method,
            'endpoint': endpoint,
            'start_time': start_time
        }

        try:
            # Process the request
            response = await call_next(request)

            # Calculate metrics
            process_time = time.time() - start_time
            response_size = len(response.body) if hasattr(response, 'body') and response.body else 0

            # Record API request metrics
            MetricsManager.record_api_request(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=process_time,
                response_size=response_size
            )

            # Log performance metrics
            logger.info("API request completed", extra={
                "request_id": request_id,
                "method": method,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "duration_ms": round(process_time * 1000, 2),
                "response_size_bytes": response_size
            })

            return response

        except Exception as exc:
            # Record failed request
            process_time = time.time() - start_time
            MetricsManager.record_api_request(
                method=method,
                endpoint=endpoint,
                status_code=500,  # Internal server error
                duration=process_time
            )

            # Log error
            logger.error("API request failed", extra={
                "request_id": request_id,
                "method": method,
                "endpoint": endpoint,
                "error": str(exc),
                "duration_ms": round(process_time * 1000, 2)
            }, exc_info=True)

            raise

        finally:
            # Always decrement in-progress counter
            MetricsManager.update_api_requests_in_progress(method, endpoint, -1)

            # Clean up progress tracking
            if request_id in in_progress_requests:
                del in_progress_requests[request_id]


class SystemResourceMonitor:
    """Monitor system resources and update metrics"""

    def __init__(self, update_interval: int = 30):
        self.update_interval = update_interval
        self.last_update = 0

    async def update_metrics(self):
        """Update system resource metrics"""
        current_time = time.time()

        # Only update if enough time has passed
        if current_time - self.last_update < self.update_interval:
            return

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_used = memory.used
            memory_total = memory.total

            # Disk usage
            disk_usage = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        'used': usage.used,
                        'total': usage.total
                    }
                except (PermissionError, OSError):
                    # Skip partitions we can't access
                    continue

            # Update metrics
            MetricsManager.update_system_resources(
                cpu_percent=cpu_percent,
                memory_used=memory_used,
                memory_total=memory_total,
                disk_usage=disk_usage
            )

            self.last_update = current_time

            logger.debug("System resource metrics updated", extra={
                "cpu_percent": cpu_percent,
                "memory_used_mb": round(memory_used / 1024 / 1024, 2),
                "memory_total_mb": round(memory_total / 1024 / 1024, 2),
                "disk_partitions": len(disk_usage)
            })

        except Exception as e:
            logger.error(f"Failed to update system resource metrics: {e}")


class DatabaseQueryMonitor:
    """Monitor database query performance"""

    @staticmethod
    def track_query(query_type: str, table: str = "unknown"):
        """Decorator to track database query performance"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                error = False

                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    error = True
                    raise
                finally:
                    duration = time.time() - start_time
                    MetricsManager.record_db_query(
                        query_type=query_type,
                        table=table,
                        duration=duration,
                        error=error
                    )
            return wrapper
        return decorator


# Global instances
system_monitor = SystemResourceMonitor()
db_monitor = DatabaseQueryMonitor()


async def update_system_metrics():
    """Background task to update system metrics"""
    await system_monitor.update_metrics()


def get_in_progress_requests() -> Dict[str, Dict[str, Any]]:
    """Get current in-progress requests"""
    return in_progress_requests.copy()
