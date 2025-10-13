"""
Prometheus metrics collection for the Calendar API.
Provides comprehensive monitoring of parsing performance, component latencies,
and system health metrics.
"""

import time
import logging
from typing import Dict, Optional, Any
from functools import wraps
from contextlib import contextmanager

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info, CollectorRegistry, 
        generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Fallback for when prometheus_client is not available
    PROMETHEUS_AVAILABLE = False
    
    # Mock classes for when prometheus is not available
    class MockMetric:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
    
    Counter = Histogram = Gauge = Info = MockMetric
    CollectorRegistry = lambda: None
    generate_latest = lambda registry: ""
    CONTENT_TYPE_LATEST = "text/plain"

logger = logging.getLogger(__name__)

# Create custom registry for our metrics
registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None

# HTTP request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

# Parsing performance metrics
parsing_requests_total = Counter(
    'parsing_requests_total',
    'Total parsing requests',
    ['mode', 'use_llm'],
    registry=registry
)

parsing_duration_seconds = Histogram(
    'parsing_duration_seconds',
    'Parsing duration in seconds',
    ['component'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
    registry=registry
)

parsing_accuracy_score = Gauge(
    'parsing_accuracy_score',
    'Current parsing accuracy score',
    registry=registry
)

parsing_confidence_score = Histogram(
    'parsing_confidence_score',
    'Distribution of parsing confidence scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry
)

# Component latency metrics
component_latency_seconds = Histogram(
    'component_latency_seconds',
    'Component processing latency in seconds',
    ['component'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry
)

component_requests_total = Counter(
    'component_requests_total',
    'Total component processing requests',
    ['component', 'status'],
    registry=registry
)

# Cache metrics
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result'],
    registry=registry
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Current cache hit rate',
    registry=registry
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Current cache size in bytes',
    registry=registry
)

cache_entries_total = Gauge(
    'cache_entries_total',
    'Total number of cache entries',
    registry=registry
)

# LLM service metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM service requests',
    ['status'],
    registry=registry
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration in seconds',
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0],
    registry=registry
)

llm_service_available = Gauge(
    'llm_service_available',
    'LLM service availability (1=available, 0=unavailable)',
    registry=registry
)

# System health metrics
system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=registry
)

system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=registry
)

api_uptime_seconds = Gauge(
    'api_uptime_seconds',
    'API uptime in seconds',
    registry=registry
)

# Field extraction metrics
field_extraction_success_total = Counter(
    'field_extraction_success_total',
    'Successful field extractions',
    ['field', 'method'],
    registry=registry
)

field_extraction_confidence = Histogram(
    'field_extraction_confidence',
    'Field extraction confidence scores',
    ['field'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry
)

# Error metrics
parsing_errors_total = Counter(
    'parsing_errors_total',
    'Total parsing errors',
    ['error_type'],
    registry=registry
)

api_errors_total = Counter(
    'api_errors_total',
    'Total API errors',
    ['error_code'],
    registry=registry
)

# Application info
app_info = Info(
    'calendar_api_info',
    'Calendar API application information',
    registry=registry
)

# Set application info
app_info.info({
    'version': '2.0.0',
    'python_version': '3.11',
    'environment': 'production'
})


class MetricsCollector:
    """Centralized metrics collection and reporting."""
    
    def __init__(self):
        self.start_time = time.time()
        self._update_uptime()
    
    def _update_uptime(self):
        """Update the uptime metric."""
        uptime = time.time() - self.start_time
        api_uptime_seconds.set(uptime)
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_parsing_request(self, mode: str, use_llm: bool, duration: float, 
                             confidence: float, accuracy: Optional[float] = None):
        """Record parsing request metrics."""
        parsing_requests_total.labels(
            mode=mode,
            use_llm=str(use_llm).lower()
        ).inc()
        
        parsing_duration_seconds.labels(component='overall').observe(duration)
        parsing_confidence_score.observe(confidence)
        
        if accuracy is not None:
            parsing_accuracy_score.set(accuracy)
    
    def record_component_latency(self, component: str, duration: float, success: bool = True):
        """Record component processing latency."""
        component_latency_seconds.labels(component=component).observe(duration)
        component_requests_total.labels(
            component=component,
            status='success' if success else 'error'
        ).inc()
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation metrics."""
        cache_operations_total.labels(
            operation=operation,
            result=result
        ).inc()
    
    def update_cache_metrics(self, hit_rate: float, size_bytes: int, entries_count: int):
        """Update cache performance metrics."""
        cache_hit_rate.set(hit_rate)
        cache_size_bytes.set(size_bytes)
        cache_entries_total.set(entries_count)
    
    def record_llm_request(self, duration: float, success: bool = True):
        """Record LLM service request metrics."""
        status = 'success' if success else 'error'
        llm_requests_total.labels(status=status).inc()
        llm_request_duration_seconds.observe(duration)
    
    def update_llm_availability(self, available: bool):
        """Update LLM service availability."""
        llm_service_available.set(1 if available else 0)
    
    def record_field_extraction(self, field: str, method: str, confidence: float):
        """Record field extraction metrics."""
        field_extraction_success_total.labels(
            field=field,
            method=method
        ).inc()
        
        field_extraction_confidence.labels(field=field).observe(confidence)
    
    def record_parsing_error(self, error_type: str):
        """Record parsing error."""
        parsing_errors_total.labels(error_type=error_type).inc()
    
    def record_api_error(self, error_code: str):
        """Record API error."""
        api_errors_total.labels(error_code=error_code).inc()
    
    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            system_memory_usage_bytes.set(memory.used)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_usage_percent.set(cpu_percent)
            
        except ImportError:
            logger.warning("psutil not available for system metrics")
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
        
        # Update uptime
        self._update_uptime()
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus metrics not available\n"
        
        # Update system metrics before returning
        self.update_system_metrics()
        return generate_latest(registry)
    
    def get_content_type(self) -> str:
        """Get the content type for metrics response."""
        return CONTENT_TYPE_LATEST


# Global metrics collector instance
metrics_collector = MetricsCollector()


def track_request_metrics(endpoint: str):
    """Decorator to track HTTP request metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            start_time = time.time()
            method = request.method
            status_code = 200
            
            try:
                response = await func(request, *args, **kwargs)
                if hasattr(response, 'status_code'):
                    status_code = response.status_code
                return response
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.record_http_request(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    duration=duration
                )
        
        return wrapper
    return decorator


@contextmanager
def track_component_timing(component: str):
    """Context manager to track component processing time."""
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration = time.time() - start_time
        metrics_collector.record_component_latency(component, duration, success)


def track_parsing_metrics(mode: str = "normal", use_llm: bool = True):
    """Decorator to track parsing request metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Extract metrics from result
                duration = time.time() - start_time
                confidence = getattr(result, 'confidence_score', 0.0)
                
                metrics_collector.record_parsing_request(
                    mode=mode,
                    use_llm=use_llm,
                    duration=duration,
                    confidence=confidence
                )
                
                return result
                
            except Exception as e:
                # Record error
                error_type = type(e).__name__
                metrics_collector.record_parsing_error(error_type)
                raise
        
        return wrapper
    return decorator