"""
OpenTelemetry Distributed Tracing Configuration

Configures distributed tracing for the application using OpenTelemetry.
Supports tracing across FastAPI, database operations, and external API calls.

Usage:
    from app.telemetry import init_telemetry
    
    # Initialize on startup
    init_telemetry(
        service_name="iit-ml-service",
        jaeger_endpoint="http://localhost:4318"
    )
"""

import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from functools import wraps

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from app.config import settings

logger = logging.getLogger(__name__)

# Global tracer
_tracer: Optional[trace.Tracer] = None


def init_telemetry(
    service_name: str = "iit-ml-service",
    jaeger_endpoint: Optional[str] = None,
    jaeger_agent_host_name: Optional[str] = None,
    jaeger_agent_port: Optional[int] = None,
    enable_console_export: bool = False,
    sample_rate: float = 1.0
) -> trace.Tracer:
    """
    Initialize OpenTelemetry tracing
    
    Args:
        service_name: Name of the service
        jaeger_endpoint: Jaeger collector endpoint (e.g., http://localhost:4318)
        jaeger_agent_host_name: Jaeger agent host (e.g., localhost)
        jaeger_agent_port: Jaeger agent port (e.g., 6831)
        enable_console_export: Enable console exporter for debugging
        sample_rate: Sampling rate (0.0 to 1.0)
        
    Returns:
        Configured tracer
    """
    global _tracer
    
    # Create resource with service name
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": getattr(settings, 'api_version', '1.0.0'),
        "deployment.environment": getattr(settings, 'environment', 'development')
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add Jaeger exporter if configured
    if jaeger_agent_host_name and jaeger_agent_port:
        # Use Jaeger Agent
        exporter = JaegerExporter(
            agent_host_name=jaeger_agent_host_name,
            agent_port=jaeger_agent_port
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(f"Jaeger exporter configured: {jaeger_agent_host_name}:{jaeger_agent_port}")
    elif jaeger_endpoint:
        # Parse endpoint URL for HTTP collector
        # Expected format: http://localhost:14268/api/traces or localhost:14268
        from urllib.parse import urlparse
        try:
            parsed = urlparse(jaeger_endpoint) if "://" in jaeger_endpoint else urlparse(f"http://{jaeger_endpoint}")
            host = parsed.hostname or "localhost"
            port = parsed.port or 14268
            
            exporter = JaegerExporter(
                agent_host_name=host,
                agent_port=port
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"Jaeger exporter configured: {host}:{port}")
        except Exception as e:
            logger.warning(f"Failed to parse Jaeger endpoint '{jaeger_endpoint}': {e}")
    
    # Add console exporter for debugging
    if enable_console_export:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Console exporter enabled for tracing")
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(__name__)
    
    logger.info(f"OpenTelemetry initialized for service: {service_name}")
    
    return _tracer


def instrument_fastapi(app):
    """
    Instrument FastAPI application with OpenTelemetry
    
    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumented with OpenTelemetry")


def instrument_sqlalchemy(engine):
    """
    Instrument SQLAlchemy engine with OpenTelemetry
    
    Args:
        engine: SQLAlchemy engine
    """
    SQLAlchemyInstrumentor().instrument(engine=engine)
    logger.info("SQLAlchemy instrumented with OpenTelemetry")


def instrument_httpx():
    """Instrument HTTPX client with OpenTelemetry"""
    HTTPXClientInstrumentor().instrument()
    logger.info("HTTPX instrumented with OpenTelemetry")


def instrument_redis():
    """Instrument Redis client with OpenTelemetry"""
    RedisInstrumentor().instrument()
    logger.info("Redis instrumented with OpenTelemetry")


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance
    
    Returns:
        Tracer instance
    """
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Context manager for tracing custom operations
    
    Args:
        operation_name: Name of the operation
        attributes: Additional span attributes
        
    Usage:
        with trace_operation("custom_operation", {"key": "value"}):
            # Your code here
            pass
    """
    tracer = get_tracer()
    
    with tracer.start_as_current_span(
        operation_name,
        attributes=attributes or {}
    ) as span:
        try:
            yield span
            span.set_status(trace.Status(trace.StatusCode.OK))
        except Exception as e:
            span.set_status(trace.Status(
                trace.StatusCode.ERROR,
                str(e)
            ))
            span.record_exception(e)
            raise


def trace_async(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator for tracing async functions
    
    Args:
        operation_name: Name of the operation
        attributes: Additional span attributes
        
    Usage:
        @trace_async("async_operation")
        async def my_async_function():
            return await some_async_call()
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with tracer.start_as_current_span(
                operation_name,
                attributes=attributes or {}
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(
                        trace.StatusCode.ERROR,
                        str(e)
                    ))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def trace_sync(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator for tracing sync functions
    
    Args:
        operation_name: Name of the operation
        attributes: Additional span attributes
        
    Usage:
        @trace_sync("sync_operation")
        def my_sync_function():
            return some_sync_call()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with tracer.start_as_current_span(
                operation_name,
                attributes=attributes or {}
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(
                        trace.StatusCode.ERROR,
                        str(e)
                    ))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def add_span_attributes(**attributes):
    """
    Add attributes to the current span
    
    Args:
        **attributes: Key-value pairs to add as span attributes
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.set_attributes(attributes)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to the current span
    
    Args:
        name: Event name
        attributes: Event attributes
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.add_event(name, attributes or {})


def record_exception(exception: Exception):
    """
    Record an exception in the current span
    
    Args:
        exception: Exception to record
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.record_exception(exception)
        current_span.set_status(trace.Status(
            trace.StatusCode.ERROR,
            str(exception)
        ))


class TracedRequest:
    """
    Helper class for tracing HTTP requests
    
    Usage:
        with TracedRequest("GET", "https://api.example.com/data"):
            response = requests.get("https://api.example.com/data")
    """
    
    def __init__(self, method: str, url: str, attributes: Optional[Dict[str, Any]] = None):
        self.method = method
        self.url = url
        self.attributes = {
            "http.method": method,
            "http.url": url,
            **(attributes or {})
        }
        self.span = None
    
    def __enter__(self):
        tracer = get_tracer()
        self.span = tracer.start_as_current_span(
            f"http.{self.method.lower()}",
            attributes=self.attributes
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_status(trace.Status(
                trace.StatusCode.ERROR,
                str(exc_val)
            ))
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(trace.Status(trace.StatusCode.OK))
        self.span.end()


def trace_request(method: str, url: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager for tracing HTTP requests
    
    Args:
        method: HTTP method
        url: Request URL
        attributes: Additional span attributes
        
    Usage:
        with trace_request("GET", "https://api.example.com/data"):
            response = requests.get("https://api.example.com/data")
    """
    return TracedRequest(method, url, attributes)
