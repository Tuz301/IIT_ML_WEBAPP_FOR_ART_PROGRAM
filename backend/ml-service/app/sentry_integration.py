"""
Sentry Error Tracking Integration for IIT ML Service

Provides automatic error tracking and reporting to Sentry for production monitoring.
"""
import logging
from typing import Optional
from sentry_sdk import init as sentry_init, capture_exception, capture_message, set_tag
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration


logger = logging.getLogger(__name__)


class SentryConfig:
    """Sentry configuration"""
    def __init__(
        self,
        dsn: str,
        environment: str = "production",
        release: Optional[str] = None,
        traces_sample_rate: float = 0.1,  # 10% of transactions
        profiles_sample_rate: float = 0.1,  # 10% of transactions
        session_sample_rate: float = 0.1,  # 10% of sessions
        before_send: Optional[callable] = None,
        before_send_transaction: Optional[callable] = None,
        ignore_errors: Optional[list] = None
    ):
        self.dsn = dsn
        self.environment = environment
        self.release = release
        self.traces_sample_rate = traces_sample_rate
        self.profiles_sample_rate = profiles_sample_rate
        self.session_sample_rate = session_sample_rate
        self.before_send = before_send
        self.before_send_transaction = before_send_transaction
        self.ignore_errors = ignore_errors or []


def init_sentry(config: SentryConfig) -> None:
    """
    Initialize Sentry SDK for error tracking
    
    Args:
        config: Sentry configuration
    """
    if not config.dsn:
        logger.warning("Sentry DSN not configured, skipping initialization")
        return
    
    try:
        sentry_init(
            dsn=config.dsn,
            environment=config.environment,
            release=config.release,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
                HttpxIntegration(),
            ],
            traces_sample_rate=config.traces_sample_rate,
            profiles_sample_rate=config.profiles_sample_rate,
            session_sample_rate=config.session_sample_rate,
            before_send=config.before_send,
            before_send_transaction=config.before_send_transaction,
            ignore_errors=config.ignore_errors,
        )
        
        logger.info(f"Sentry initialized for environment: {config.environment}")
        capture_message(f"Sentry error tracking initialized in {config.environment} environment")
        
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def capture_exception_with_context(
    exception: Exception,
    tags: Optional[dict] = None,
    extra: Optional[dict] = None,
    level: str = "error"
) -> None:
    """
    Capture an exception with additional context
    
    Args:
        exception: The exception to capture
        tags: Tags to add to the event (e.g., {"user_id": "123"})
        extra: Additional context data
        level: Log level (error, warning, info)
    """
    try:
        with sentry_sdk.configure_scope() as scope:
            if tags:
                for key, value in tags.items():
                    set_tag(key, value)
            
            if extra:
                scope.set_context("extra", extra)
            
            capture_exception(exception)
            logger.error(f"Exception captured and sent to Sentry: {exception.__class__.__name__}")
            
    except Exception as e:
        logger.error(f"Failed to capture exception for Sentry: {e}")


def capture_message_with_context(
    message: str,
    level: str = "info",
    tags: Optional[dict] = None,
    extra: Optional[dict] = None
) -> None:
    """
    Capture a message with additional context
    
    Args:
        message: The message to send
        level: Log level (error, warning, info)
        tags: Tags to add to the event
        extra: Additional context data
    """
    try:
        with sentry_sdk.configure_scope() as scope:
            if tags:
                for key, value in tags.items():
                    set_tag(key, value)
            
            if extra:
                scope.set_context("extra", extra)
            
            capture_message(message, level=level)
            logger.info(f"Message captured and sent to Sentry: {message}")
            
    except Exception as e:
        logger.error(f"Failed to capture message for Sentry: {e}")


def create_sentry_middleware(app, config: SentryConfig):
    """
    Create Sentry middleware for FastAPI
    
    Args:
        app: FastAPI application
        config: Sentry configuration
    """
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """
        Global exception handler that sends errors to Sentry
        """
        # Capture exception with context
        capture_exception_with_context(
            exception=exc,
            tags={
                "request_method": request.method,
                "request_url": str(request.url),
                "user_agent": request.headers.get("user-agent", "unknown")
            },
            extra={
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else "unknown"
            }
        )
        
        # Re-raise the exception for FastAPI to handle
        raise exc


def create_sentry_filter():
    """
    Create a filter to exclude certain errors from Sentry
    
    Returns:
        Function to use as before_send callback
    """
    def before_send(event, hint):
        # Don't send 404 errors to Sentry (not actionable)
        if "exc_info" in event:
            exc_type = event.get("exc_info", {}).get("type")
            if exc_type == "NotFound":
                return None
            
            # Don't send validation errors
            if exc_type == "ValidationError":
                return None
            
            # Don't send authentication errors
            if exc_type == "HTTPException" and event.get("context", {}).get("response", {}).get("status") == 401:
                return None
        
        return event
    
    return before_send


# Import sentry_sdk at module level for use in functions
import sentry_sdk
