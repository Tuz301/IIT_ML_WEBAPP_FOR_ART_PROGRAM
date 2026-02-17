"""
Custom error handling middleware for IIT ML Service
"""
import logging
import traceback
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import redis.exceptions as redis_exceptions

logger = logging.getLogger(__name__)


class IITException(Exception):
    """Base exception for IIT ML Service"""

    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(IITException):
    """Validation-related exceptions"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=422, details=details)


class NotFoundException(IITException):
    """Resource not found exceptions"""
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, status_code=404)


class ConflictException(IITException):
    """Resource conflict exceptions"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=409, details=details)


class ServiceUnavailableException(IITException):
    """Service unavailable exceptions"""
    def __init__(self, service: str, details: dict = None):
        message = f"Service temporarily unavailable: {service}"
        super().__init__(message, status_code=503, details=details)


async def custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for IIT ML Service
    """
    # Generate request ID for tracking
    import uuid
    request_id = str(uuid.uuid4())[:8]

    # Log the exception with context
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        },
        exc_info=True
    )

    # Handle different exception types
    if isinstance(exc, IITException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
                "request_id": request_id,
                "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow() in real implementation
            }
        )

    elif isinstance(exc, ValidationError):
        # Pydantic validation errors
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "details": exc.errors(),
                "request_id": request_id,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )

    elif isinstance(exc, HTTPException):
        # FastAPI HTTP exceptions
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "request_id": request_id,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )

    elif isinstance(exc, IntegrityError):
        # Database integrity errors (duplicates, constraints)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Data integrity violation",
                "details": "The operation would violate data constraints",
                "request_id": request_id,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )

    elif isinstance(exc, SQLAlchemyError):
        # General database errors
        # Log the actual error for debugging
        import logging
        logger = logging.getLogger(__name__)
        print(f"[DEBUG] Database error: {str(exc)}")  # Add print for visibility
        logger.error(f"Database error: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Database operation failed",
                "details": "Please try again later",
                "request_id": request_id,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )

    elif isinstance(exc, redis_exceptions.ConnectionError):
        # Redis connection errors
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Cache service temporarily unavailable",
                "details": "Some features may be limited",
                "request_id": request_id,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )

    elif isinstance(exc, redis_exceptions.TimeoutError):
        # Redis timeout errors
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "error": "Request timeout",
                "details": "The operation took too long to complete",
                "request_id": request_id,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )

    else:
        # Generic unhandled exceptions
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "details": "An unexpected error occurred",
                "request_id": request_id,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )


def setup_error_handlers(app):
    """
    Setup global error handlers for the FastAPI application
    """
    # Add custom exception handler
    app.add_exception_handler(Exception, custom_exception_handler)

    # Add specific exception handlers
    app.add_exception_handler(IITException, custom_exception_handler)
    app.add_exception_handler(ValidationError, custom_exception_handler)
    app.add_exception_handler(HTTPException, custom_exception_handler)
    app.add_exception_handler(IntegrityError, custom_exception_handler)
    app.add_exception_handler(SQLAlchemyError, custom_exception_handler)
    app.add_exception_handler(redis_exceptions.ConnectionError, custom_exception_handler)
    app.add_exception_handler(redis_exceptions.TimeoutError, custom_exception_handler)


# Utility functions for raising custom exceptions
def raise_not_found(resource: str, resource_id: str = None):
    """Raise a not found exception"""
    raise NotFoundException(resource, resource_id)


def raise_validation_error(message: str, details: dict = None):
    """Raise a validation exception"""
    raise ValidationException(message, details)


def raise_conflict(message: str, details: dict = None):
    """Raise a conflict exception"""
    raise ConflictException(message, details)


def raise_service_unavailable(service: str, details: dict = None):
    """Raise a service unavailable exception"""
    raise ServiceUnavailableException(service, details)
