"""
Prometheus metrics and monitoring utilities
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable


# Prediction Metrics
prediction_requests_total = Counter(
    'iit_prediction_requests_total',
    'Total number of prediction requests',
    ['endpoint', 'status']
)

prediction_duration_seconds = Histogram(
    'iit_prediction_duration_seconds',
    'Time spent processing predictions',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

prediction_risk_distribution = Counter(
    'iit_prediction_risk_distribution',
    'Distribution of predicted risk levels',
    ['risk_level']
)

batch_size_distribution = Histogram(
    'iit_batch_size_distribution',
    'Distribution of batch prediction sizes',
    buckets=[1, 5, 10, 25, 50, 100]
)

# Model Metrics
model_inference_latency = Histogram(
    'iit_model_inference_latency_seconds',
    'Model inference latency',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

feature_extraction_latency = Histogram(
    'iit_feature_extraction_latency_seconds',
    'Feature extraction latency',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)

model_predictions_total = Counter(
    'iit_model_predictions_total',
    'Total predictions made by the model',
    ['model_version']
)

# System Metrics
redis_operations_total = Counter(
    'iit_redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)

redis_latency_seconds = Histogram(
    'iit_redis_latency_seconds',
    'Redis operation latency',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
)

api_errors_total = Counter(
    'iit_api_errors_total',
    'Total API errors',
    ['endpoint', 'error_type']
)

# Model Performance Metrics
model_auc_score = Gauge(
    'iit_model_auc_score',
    'Current model AUC score'
)

model_drift_detected = Gauge(
    'iit_model_drift_detected',
    'Model drift detection flag (0=no drift, 1=drift detected)'
)

# Advanced Model Metrics
model_performance_drift = Gauge(
    'iit_model_performance_drift',
    'Model performance drift score (0-1, higher = more drift)'
)

model_data_drift_score = Gauge(
    'iit_model_data_drift_score',
    'Data drift score (0-1, higher = more drift)',
    ['feature']
)

model_retraining_needed = Gauge(
    'iit_model_retraining_needed',
    'Retraining needed flag (0=no, 1=yes)'
)

model_versions_total = Gauge(
    'iit_model_versions_total',
    'Total number of model versions in registry'
)

ab_test_active = Gauge(
    'iit_ab_test_active',
    'Active A/B test flag (0=no active test, 1=active test)'
)

ab_test_variants_total = Gauge(
    'iit_ab_test_variants_total',
    'Total number of variants in active A/B test'
)

ab_test_sample_size = Gauge(
    'iit_ab_test_sample_size',
    'Current sample size for A/B test',
    ['variant']
)

model_explainability_requests = Counter(
    'iit_model_explainability_requests_total',
    'Total explainability requests',
    ['request_type']
)

model_bias_score = Gauge(
    'iit_model_bias_score',
    'Model bias detection score (0-1, higher = more bias)',
    ['bias_type']
)

ensemble_model_predictions = Counter(
    'iit_ensemble_model_predictions_total',
    'Total predictions from ensemble models',
    ['ensemble_type', 'model_version']
)

hyperparameter_tuning_jobs = Counter(
    'iit_hyperparameter_tuning_jobs_total',
    'Total hyperparameter tuning jobs',
    ['status']
)

# Application Info
app_info = Info(
    'iit_service_info',
    'IIT ML Service information'
)

# System Health
system_uptime_seconds = Gauge(
    'iit_system_uptime_seconds',
    'System uptime in seconds'
)

feature_store_cache_hits = Counter(
    'iit_feature_store_cache_hits_total',
    'Feature store cache hits'
)

feature_store_cache_misses = Counter(
    'iit_feature_store_cache_misses_total',
    'Feature store cache misses'
)

# Database Performance Metrics
db_query_duration_seconds = Histogram(
    'iit_db_query_duration_seconds',
    'Database query execution time',
    ['query_type', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
)

db_connection_pool_size = Gauge(
    'iit_db_connection_pool_size',
    'Database connection pool size',
    ['pool_type']
)

db_connection_pool_checked_out = Gauge(
    'iit_db_connection_pool_checked_out',
    'Number of checked out database connections'
)

db_connection_pool_overflow = Gauge(
    'iit_db_connection_pool_overflow',
    'Number of overflow database connections'
)

db_query_errors_total = Counter(
    'iit_db_query_errors_total',
    'Total database query errors',
    ['error_type', 'query_type']
)

# API Performance Metrics
api_request_duration_seconds = Histogram(
    'iit_api_request_duration_seconds',
    'API request duration by endpoint and method',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

api_requests_in_progress = Gauge(
    'iit_api_requests_in_progress',
    'Number of API requests currently in progress',
    ['method', 'endpoint']
)

api_request_rate_per_second = Counter(
    'iit_api_request_rate_total',
    'Total API requests per second',
    ['method', 'endpoint']
)

api_response_size_bytes = Histogram(
    'iit_api_response_size_bytes',
    'API response size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000]
)

# Caching Metrics
api_cache_hits_total = Counter(
    'iit_api_cache_hits_total',
    'Total API cache hits',
    ['endpoint', 'method']
)

api_cache_misses_total = Counter(
    'iit_api_cache_misses_total',
    'Total API cache misses',
    ['endpoint', 'method']
)

db_cache_hits_total = Counter(
    'iit_db_cache_hits_total',
    'Total database query cache hits',
    ['query_type']
)

db_cache_misses_total = Counter(
    'iit_db_cache_misses_total',
    'Total database query cache misses',
    ['query_type']
)

# System Resource Metrics
system_cpu_usage_percent = Gauge(
    'iit_system_cpu_usage_percent',
    'System CPU usage percentage'
)

system_memory_usage_bytes = Gauge(
    'iit_system_memory_usage_bytes',
    'System memory usage in bytes'
)

system_memory_total_bytes = Gauge(
    'iit_system_memory_total_bytes',
    'Total system memory in bytes'
)

system_disk_usage_bytes = Gauge(
    'iit_system_disk_usage_bytes',
    'System disk usage in bytes',
    ['mount_point']
)

system_disk_total_bytes = Gauge(
    'iit_system_disk_total_bytes',
    'Total system disk space in bytes',
    ['mount_point']
)

# Service Health Metrics
service_health_status = Gauge(
    'iit_service_health_status',
    'Service health status (1=healthy, 0=unhealthy)',
    ['service']
)

service_response_time_seconds = Gauge(
    'iit_service_response_time_seconds',
    'Service response time in seconds',
    ['service']
)

# Load Testing Metrics
load_test_active = Gauge(
    'iit_load_test_active',
    'Load test active flag (1=active, 0=inactive)'
)

load_test_concurrent_users = Gauge(
    'iit_load_test_concurrent_users',
    'Number of concurrent users in load test'
)

load_test_requests_per_second = Gauge(
    'iit_load_test_requests_per_second',
    'Requests per second during load test'
)

# Profiling Metrics
profiling_active = Gauge(
    'iit_profiling_active',
    'Profiling active flag (1=active, 0=inactive)'
)

profiling_memory_peak_bytes = Gauge(
    'iit_profiling_memory_peak_bytes',
    'Peak memory usage during profiling'
)

profiling_cpu_time_seconds = Gauge(
    'iit_profiling_cpu_time_seconds',
    'CPU time spent during profiling'
)


def track_prediction_time(endpoint: str):
    """Decorator to track prediction processing time"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                prediction_duration_seconds.labels(endpoint=endpoint).observe(duration)
                prediction_requests_total.labels(endpoint=endpoint, status=status).inc()
        
        return wrapper
    return decorator


def track_model_inference():
    """Decorator to track model inference latency"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                model_inference_latency.observe(duration)
        
        return wrapper
    return decorator


def track_redis_operation(operation: str):
    """Decorator to track Redis operations"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                redis_latency_seconds.labels(operation=operation).observe(duration)
                redis_operations_total.labels(operation=operation, status=status).inc()
        
        return wrapper
    return decorator


class MetricsManager:
    """Manager for updating model performance metrics"""
    
    @staticmethod
    def update_model_metrics(metrics: dict):
        """Update model performance metrics"""
        if 'auc' in metrics:
            model_auc_score.set(metrics['auc'])
    
    @staticmethod
    def record_prediction(risk_level: str, model_version: str):
        """Record a prediction"""
        prediction_risk_distribution.labels(risk_level=risk_level).inc()
        model_predictions_total.labels(model_version=model_version).inc()
    
    @staticmethod
    def set_drift_status(drift_detected: bool):
        """Set model drift detection status"""
        model_drift_detected.set(1 if drift_detected else 0)
    
    @staticmethod
    def record_batch_size(size: int):
        """Record batch prediction size"""
        batch_size_distribution.observe(size)
    
    @staticmethod
    def record_error(endpoint: str, error_type: str):
        """Record an API error"""
        api_errors_total.labels(endpoint=endpoint, error_type=error_type).inc()
    
    @staticmethod
    def update_uptime(uptime_seconds: float):
        """Update system uptime"""
        system_uptime_seconds.set(uptime_seconds)
    
    @staticmethod
    def set_app_info(version: str, model_version: str):
        """Set application info"""
        app_info.info({
            'version': version,
            'model_version': model_version,
            'service': 'iit-prediction'
        })

    @staticmethod
    def record_db_query(query_type: str, table: str, duration: float, error: bool = False):
        """Record database query metrics"""
        if error:
            db_query_errors_total.labels(error_type="query_error", query_type=query_type).inc()
        else:
            db_query_duration_seconds.labels(query_type=query_type, table=table).observe(duration)

    @staticmethod
    def update_db_pool_stats(pool_stats: dict):
        """Update database connection pool statistics"""
        db_connection_pool_size.labels(pool_type="main").set(pool_stats.get('pool_size', 0))
        db_connection_pool_checked_out.set(pool_stats.get('checkedout', 0))
        db_connection_pool_overflow.set(pool_stats.get('overflow', 0))

    @staticmethod
    def record_api_request(method: str, endpoint: str, status_code: int, duration: float, response_size: int = 0):
        """Record API request metrics"""
        api_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).observe(duration)
        api_request_rate_per_second.labels(method=method, endpoint=endpoint).inc()
        if response_size > 0:
            api_response_size_bytes.labels(method=method, endpoint=endpoint).observe(response_size)

    @staticmethod
    def update_api_requests_in_progress(method: str, endpoint: str, count: int):
        """Update number of in-progress API requests"""
        api_requests_in_progress.labels(method=method, endpoint=endpoint).set(count)

    @staticmethod
    def record_cache_hit(cache_type: str, endpoint: str = "", method: str = "", query_type: str = ""):
        """Record cache hit"""
        if cache_type == "api":
            api_cache_hits_total.labels(endpoint=endpoint, method=method).inc()
        elif cache_type == "db":
            db_cache_hits_total.labels(query_type=query_type).inc()
        elif cache_type == "feature_store":
            feature_store_cache_hits.inc()

    @staticmethod
    def record_cache_miss(cache_type: str, endpoint: str = "", method: str = "", query_type: str = ""):
        """Record cache miss"""
        if cache_type == "api":
            api_cache_misses_total.labels(endpoint=endpoint, method=method).inc()
        elif cache_type == "db":
            db_cache_misses_total.labels(query_type=query_type).inc()
        elif cache_type == "feature_store":
            feature_store_cache_misses.inc()

    @staticmethod
    def update_system_resources(cpu_percent: float, memory_used: int, memory_total: int,
                               disk_usage: dict = None):
        """Update system resource metrics"""
        system_cpu_usage_percent.set(cpu_percent)
        system_memory_usage_bytes.set(memory_used)
        system_memory_total_bytes.set(memory_total)

        if disk_usage:
            for mount_point, stats in disk_usage.items():
                system_disk_usage_bytes.labels(mount_point=mount_point).set(stats.get('used', 0))
                system_disk_total_bytes.labels(mount_point=mount_point).set(stats.get('total', 0))

    @staticmethod
    def update_service_health(service: str, healthy: bool, response_time: float = 0):
        """Update service health status"""
        service_health_status.labels(service=service).set(1 if healthy else 0)
        if response_time > 0:
            service_response_time_seconds.labels(service=service).set(response_time)

    @staticmethod
    def update_load_test_status(active: bool, concurrent_users: int = 0, rps: float = 0):
        """Update load testing metrics"""
        load_test_active.set(1 if active else 0)
        load_test_concurrent_users.set(concurrent_users)
        load_test_requests_per_second.set(rps)

    @staticmethod
    def update_profiling_status(active: bool, memory_peak: int = 0, cpu_time: float = 0):
        """Update profiling metrics"""
        profiling_active.set(1 if active else 0)
        if memory_peak > 0:
            profiling_memory_peak_bytes.set(memory_peak)
        if cpu_time > 0:
            profiling_cpu_time_seconds.set(cpu_time)

    @staticmethod
    def update_model_performance_drift(drift_score: float):
        """Update model performance drift score"""
        model_performance_drift.set(drift_score)

    @staticmethod
    def update_data_drift_score(feature: str, drift_score: float):
        """Update data drift score for a specific feature"""
        model_data_drift_score.labels(feature=feature).set(drift_score)

    @staticmethod
    def set_retraining_needed(needed: bool):
        """Set retraining needed flag"""
        model_retraining_needed.set(1 if needed else 0)

    @staticmethod
    def update_model_versions_count(count: int):
        """Update total number of model versions"""
        model_versions_total.set(count)

    @staticmethod
    def update_ab_test_status(active: bool, variants_count: int = 0):
        """Update A/B test status"""
        ab_test_active.set(1 if active else 0)
        ab_test_variants_total.set(variants_count)

    @staticmethod
    def update_ab_test_sample_size(variant: str, sample_size: int):
        """Update sample size for A/B test variant"""
        ab_test_sample_size.labels(variant=variant).set(sample_size)

    @staticmethod
    def record_explainability_request(request_type: str):
        """Record explainability request"""
        model_explainability_requests.labels(request_type=request_type).inc()

    @staticmethod
    def update_bias_score(bias_type: str, score: float):
        """Update bias detection score"""
        model_bias_score.labels(bias_type=bias_type).set(score)

    @staticmethod
    def record_ensemble_prediction(ensemble_type: str, model_version: str):
        """Record ensemble model prediction"""
        ensemble_model_predictions.labels(ensemble_type=ensemble_type, model_version=model_version).inc()

    @staticmethod
    def record_hyperparameter_tuning_job(status: str):
        """Record hyperparameter tuning job"""
        hyperparameter_tuning_jobs.labels(status=status).inc()
