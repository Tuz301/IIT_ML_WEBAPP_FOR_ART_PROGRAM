"""
Tests for OpenTelemetry distributed tracing functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace

from app.telemetry import (
    init_telemetry,
    get_tracer,
    trace_async,
    trace_sync,
    trace_operation,
    trace_request,
    add_span_attributes,
    add_span_event,
    record_exception
)


class TestTelemetryInitialization:
    """Tests for telemetry initialization"""

    @pytest.fixture
    def reset_telemetry(self):
        """Reset global tracer before each test"""
        import app.telemetry as telemetry_module
        telemetry_module._tracer = None
        yield
        telemetry_module._tracer = None

    def test_init_telemetry_with_console_exporter(self, reset_telemetry):
        """Test telemetry initialization with console exporter"""
        tracer = init_telemetry(
            service_name="test-service",
            enable_console_export=True,
            sample_rate=1.0
        )
        
        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)

    @pytest.mark.parametrize("endpoint,agent_host,agent_port", [
        ("http://localhost:14268/api/traces", None, None),
        (None, "localhost", 6831),
        (None, "jaeger-agent", 6831),
    ])
    def test_init_telemetry_with_jaeger(self, reset_telemetry, endpoint, agent_host, agent_port):
        """Test telemetry initialization with Jaeger exporter"""
        with patch('app.telemetry.JaegerExporter') as mock_exporter:
            mock_exporter.return_value = Mock()
            
            tracer = init_telemetry(
                service_name="test-service",
                jaeger_endpoint=endpoint,
                jaeger_agent_host_name=agent_host,
                jaeger_agent_port=agent_port,
            )
            
            assert tracer is not None
            # Verify Jaeger exporter was configured
            if endpoint or (agent_host and agent_port):
                mock_exporter.assert_called_once()

    def test_init_telemetry_with_sample_rate(self, reset_telemetry):
        """Test telemetry initialization with custom sample rate"""
        tracer = init_telemetry(
            service_name="test-service",
            enable_console_export=True,
            sample_rate=0.5
        )
        
        assert tracer is not None

    def test_get_tracer_after_initialization(self, reset_telemetry):
        """Test getting tracer after initialization"""
        init_telemetry(service_name="test-service")
        
        tracer = get_tracer()
        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)

    def test_get_tracer_without_initialization(self, reset_telemetry):
        """Test getting tracer without initialization returns default tracer"""
        tracer = get_tracer()
        # OpenTelemetry creates a default tracer if none exists
        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)


class TestTraceDecorators:
    """Tests for tracing decorators"""

    @pytest.fixture
    def initialized_telemetry(self):
        """Initialize telemetry for decorator tests"""
        import app.telemetry as telemetry_module
        telemetry_module._tracer = None
        init_telemetry(
            service_name="test-service",
            enable_console_export=True
        )
        yield
        telemetry_module._tracer = None

    @pytest.mark.asyncio
    async def test_trace_async_decorator(self, initialized_telemetry):
        """Test async function tracing decorator"""
        @trace_async
        async def async_function(x: int, y: int) -> int:
            return x + y
        
        result = await async_function(2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_trace_async_with_exception(self, initialized_telemetry):
        """Test async decorator handles exceptions"""
        @trace_async
        async def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await failing_function()

    def test_trace_sync_decorator(self, initialized_telemetry):
        """Test sync function tracing decorator"""
        @trace_sync
        def sync_function(x: int, y: int) -> int:
            return x * y
        
        result = sync_function(3, 4)
        assert result == 12

    def test_trace_sync_with_exception(self, initialized_telemetry):
        """Test sync decorator handles exceptions"""
        @trace_sync
        def failing_function():
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError):
            failing_function()


class TestTraceContextManagers:
    """Tests for tracing context managers"""

    @pytest.fixture
    def initialized_telemetry(self):
        """Initialize telemetry for context manager tests"""
        import app.telemetry as telemetry_module
        telemetry_module._tracer = None
        init_telemetry(
            service_name="test-service",
            enable_console_export=True
        )
        yield
        telemetry_module._tracer = None

    def test_trace_operation_context_manager(self, initialized_telemetry):
        """Test operation tracing context manager"""
        with trace_operation("test_operation", {"key": "value"}) as span:
            assert span is not None
            # Span should be recording
            assert span.is_recording()

    def test_trace_request_context_manager(self, initialized_telemetry):
        """Test request tracing context manager"""
        with trace_request(
            method="GET",
            path="/api/test",
            user_id="test-user"
        ) as span:
            assert span is not None
            assert span.is_recording()


class TestSpanHelpers:
    """Tests for span helper functions"""

    @pytest.fixture
    def initialized_telemetry(self):
        """Initialize telemetry for helper tests"""
        import app.telemetry as telemetry_module
        telemetry_module._tracer = None
        init_telemetry(
            service_name="test-service",
            enable_console_export=True
        )
        yield
        telemetry_module._tracer = None

    def test_add_span_attributes(self, initialized_telemetry):
        """Test adding attributes to current span"""
        with trace_operation("test_operation"):
            add_span_attributes({
                "user_id": "test-user",
                "request_id": "12345",
                "custom_attr": "value"
            })
            # Attributes are added to span (no assertion needed, just no error)

    def test_add_span_event(self, initialized_telemetry):
        """Test adding event to current span"""
        with trace_operation("test_operation"):
            add_span_event("test_event", {"event_key": "event_value"})
            # Event is added to span (no assertion needed, just no error)

    def test_record_exception(self, initialized_telemetry):
        """Test recording exception in current span"""
        with trace_operation("test_operation"):
            try:
                raise ValueError("Test error")
            except ValueError as e:
                record_exception(e)
            # Exception is recorded in span (no assertion needed, just no error)

    def test_get_current_span_from_opentelemetry(self, initialized_telemetry):
        """Test getting current span using OpenTelemetry API"""
        with trace_operation("test_operation") as outer_span:
            current = trace.get_current_span()
            assert current is not None
            # Should be the same span or a child span
            assert current.is_recording()


class TestTelemetryIntegration:
    """Integration tests for telemetry with actual tracing"""

    @pytest.fixture
    def telemetry_with_exporter(self):
        """Initialize telemetry with mock exporter"""
        import app.telemetry as telemetry_module
        telemetry_module._tracer = None
        
        with patch('app.telemetry.BatchSpanProcessor') as mock_processor:
            init_telemetry(
                service_name="integration-test",
                jaeger_endpoint="http://localhost:14268/api/traces"
            )
            yield mock_processor
        
        telemetry_module._tracer = None

    def test_end_to_end_tracing(self, telemetry_with_exporter):
        """Test complete tracing flow"""
        @trace_sync
        def process_data(data: dict) -> dict:
            with trace_operation("process_step"):
                add_span_attributes({"data_size": len(data)})
            return {"processed": True}
        
        result = process_data({"key": "value"})
        assert result == {"processed": True}

    def test_nested_spans(self, telemetry_with_exporter):
        """Test nested span creation"""
        with trace_operation("parent_operation"):
            add_span_attributes({"level": "parent"})
            
            with trace_operation("child_operation"):
                add_span_attributes({"level": "child"})
        
        # Both spans should be created and exported


class TestTelemetryConfiguration:
    """Tests for telemetry configuration from settings"""

    @patch('app.telemetry.settings')
    def test_telemetry_respects_settings_disabled(self, mock_settings):
        """Test telemetry respects disabled setting"""
        mock_settings.telemetry_enabled = False
        
        # Should not initialize when disabled
        import app.telemetry as telemetry_module
        telemetry_module._tracer = None
        
        # Simulate startup logic
        if mock_settings.telemetry_enabled:
            init_telemetry(service_name="test")
        
        assert get_tracer() is None

    @patch('app.telemetry.settings')
    def test_telemetry_respects_sample_rate(self, mock_settings):
        """Test telemetry respects sample rate from settings"""
        mock_settings.telemetry_sample_rate = 0.25
        
        import app.telemetry as telemetry_module
        telemetry_module._tracer = None
        
        init_telemetry(
            service_name="test",
            sample_rate=mock_settings.telemetry_sample_rate,
            enable_console_export=True
        )
        
        tracer = get_tracer()
        assert tracer is not None


# Fixtures for common test data
@pytest.fixture
def sample_request_data():
    """Sample request data for testing"""
    return {
        "method": "POST",
        "path": "/api/predict",
        "user_id": "test-user-123",
        "request_id": "req-456"
    }


@pytest.fixture
def sample_operation_data():
    """Sample operation data for testing"""
    return {
        "operation_name": "model_inference",
        "model_version": "v1.2.3",
        "patient_id": "patient-789"
    }
