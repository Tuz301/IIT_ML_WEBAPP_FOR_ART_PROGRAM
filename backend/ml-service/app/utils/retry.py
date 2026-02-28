"""
Retry Mechanism using Tenacity

Provides decorators for retrying operations with exponential backoff:
- database_retry: For database operations
- api_retry: For external API calls
- redis_retry: For Redis operations
"""
import logging
from typing import Type, Tuple, Optional, Callable, Any
from functools import wraps
import time

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

from ..config import settings

logger = logging.getLogger(__name__)


# Configuration from settings
MAX_ATTEMPTS = getattr(settings, 'retry_max_attempts', 3)
WAIT_MIN = getattr(settings, 'retry_wait_min', 1.0)
WAIT_MAX = getattr(settings, 'retry_wait_max', 10.0)


def _get_retry_config(
    max_attempts: Optional[int] = None,
    wait_min: Optional[float] = None,
    wait_max: Optional[float] = None
) -> Tuple[int, float, float]:
    """Get retry configuration with defaults from settings"""
    return (
        max_attempts or MAX_ATTEMPTS,
        wait_min or WAIT_MIN,
        wait_max or WAIT_MAX
    )


def database_retry(
    max_attempts: Optional[int] = None,
    wait_min: Optional[float] = None,
    wait_max: Optional[float] = None,
    reraise: bool = True
) -> Callable:
    """
    Retry decorator for database operations
    
    Retries on common database errors with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: from settings)
        wait_min: Minimum wait time in seconds (default: from settings)
        wait_max: Maximum wait time in seconds (default: from settings)
        reraise: Whether to reraise the exception after all retries
    
    Example:
        @database_retry()
        def get_user(db: Session, user_id: int):
            return db.query(User).filter(User.id == user_id).first()
    
        @database_retry(max_attempts=5)
        def bulk_insert(db: Session, items: list):
            db.bulk_insert_mappings(Item, items)
            db.commit()
    """
    attempts, min_wait, max_wait = _get_retry_config(max_attempts, wait_min, wait_max)
    
    # Common database exceptions to retry on
    # Import here to avoid circular imports
    try:
        from sqlalchemy.exc import (
            OperationalError,
            IntegrityError,
            DatabaseError,
            InterfaceError,
            DisconnectionError,
        )
        from psycopg2 import OperationalError as PostgresOperationalError
        DB_EXCEPTIONS = (
            OperationalError,
            DisconnectionError,
            InterfaceError,
        )
    except ImportError:
        # Fallback if psycopg2 not available
        DB_EXCEPTIONS = ()
    
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(DB_EXCEPTIONS) if DB_EXCEPTIONS else retry_if_exception_type(Exception),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
            reraise=reraise
        )
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Database operation failed after {attempts} attempts: {e}")
                if reraise:
                    raise
                return None
        
        return wrapper
    
    return decorator


def api_retry(
    max_attempts: Optional[int] = None,
    wait_min: Optional[float] = None,
    wait_max: Optional[float] = None,
    reraise: bool = True,
    status_codes: Optional[Tuple[int, ...]] = None
) -> Callable:
    """
    Retry decorator for external API calls
    
    Retries on network errors and specific HTTP status codes.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: from settings)
        wait_min: Minimum wait time in seconds (default: from settings)
        wait_max: Maximum wait time in seconds (default: from settings)
        reraise: Whether to reraise the exception after all retries
        status_codes: HTTP status codes to retry on (default: 502, 503, 504)
    
    Example:
        @api_retry()
        def fetch_external_data(url: str):
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
    
        @api_retry(max_attempts=5, status_codes=(429, 500, 502, 503, 504))
        def call_ml_api(data: dict):
            return requests.post(API_URL, json=data).json()
    """
    attempts, min_wait, max_wait = _get_retry_config(max_attempts, wait_min, wait_max)
    
    if status_codes is None:
        status_codes = (502, 503, 504)  # Bad Gateway, Service Unavailable, Gateway Timeout
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(attempts):
                try:
                    result = func(*args, **kwargs)
                    
                    # Check for HTTP status codes if result is a response object
                    if hasattr(result, 'status_code'):
                        if result.status_code in status_codes:
                            last_exception = Exception(f"HTTP {result.status_code}")
                            if attempt < attempts - 1:
                                wait_time = min(min_wait * (2 ** attempt), max_wait)
                                logger.warning(
                                    f"API call returned {result.status_code}, "
                                    f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{attempts})"
                                )
                                time.sleep(wait_time)
                                continue
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    # Retry on network errors
                    if attempt < attempts - 1:
                        wait_time = min(min_wait * (2 ** attempt), max_wait)
                        logger.warning(
                            f"API call failed: {e}, "
                            f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{attempts})"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"API call failed after {attempts} attempts: {e}")
            
            if reraise and last_exception:
                raise last_exception
            return None
        
        return wrapper
    
    return decorator


def redis_retry(
    max_attempts: Optional[int] = None,
    wait_min: Optional[float] = None,
    wait_max: Optional[float] = None,
    reraise: bool = True
) -> Callable:
    """
    Retry decorator for Redis operations
    
    Retries on Redis connection errors with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: from settings)
        wait_min: Minimum wait time in seconds (default: from settings)
        wait_max: Maximum wait time in seconds (default: from settings)
        reraise: Whether to reraise the exception after all retries
    
    Example:
        @redis_retry()
        def get_from_cache(key: str):
            return redis_client.get(key)
    
        @redis_retry(max_attempts=5)
        def set_cache(key: str, value: str, ttl: int = 3600):
            return redis_client.setex(key, ttl, value)
    """
    attempts, min_wait, max_wait = _get_retry_config(max_attempts, wait_min, wait_max)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Retry on connection-related errors
                    if any(keyword in error_msg for keyword in [
                        'connection', 'timeout', 'broken pipe', 
                        'redis connection', 'cannot connect'
                    ]):
                        if attempt < attempts - 1:
                            wait_time = min(min_wait * (2 ** attempt), max_wait)
                            logger.warning(
                                f"Redis operation failed: {e}, "
                                f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{attempts})"
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Redis operation failed after {attempts} attempts: {e}")
                    else:
                        # Don't retry on non-connection errors
                        raise
            
            if reraise and last_exception:
                raise last_exception
            return None
        
        return wrapper
    
    return decorator


class RetryableError(Exception):
    """Base exception for errors that should be retried"""
    pass


class TransientError(RetryableError):
    """Exception for transient/temporary errors that should be retried"""
    pass


def retry_on_transient(
    max_attempts: Optional[int] = None,
    wait_min: Optional[float] = None,
    wait_max: Optional[float] = None
) -> Callable:
    """
    Retry decorator for transient errors
    
    Use this decorator for custom transient errors.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: from settings)
        wait_min: Minimum wait time in seconds (default: from settings)
        wait_max: Maximum wait time in seconds (default: from settings)
    
    Example:
        @retry_on_transient()
        def process_data(data: dict):
            if data.get('retry_later'):
                raise TransientError("Data not ready yet")
            return process(data)
    """
    attempts, min_wait, max_wait = _get_retry_config(max_attempts, wait_min, wait_max)
    
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(RetryableError),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def async_retry(
    max_attempts: Optional[int] = None,
    wait_min: Optional[float] = None,
    wait_max: Optional[float] = None
) -> Callable:
    """
    Async retry decorator for async operations
    
    Args:
        max_attempts: Maximum number of retry attempts (default: from settings)
        wait_min: Minimum wait time in seconds (default: from settings)
        wait_max: Maximum wait time in seconds (default: from settings)
    
    Example:
        @async_retry()
        async def fetch_async_data(url: str):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
    """
    attempts, min_wait, max_wait = _get_retry_config(max_attempts, wait_min, wait_max)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < attempts - 1:
                        wait_time = min(min_wait * (2 ** attempt), max_wait)
                        logger.warning(
                            f"Async operation failed: {e}, "
                            f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{attempts})"
                        )
                        import asyncio
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Async operation failed after {attempts} attempts: {e}")
            
            raise last_exception
        
        return wrapper
    
    return decorator
