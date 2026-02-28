"""
Configuration management for IIT Prediction ML Service
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    api_title: str = "IIT Prediction ML Service"
    api_version: str = "1.0.0"
    api_description: str = "Production-ready ML service for predicting IIT (Interruption in Treatment) risk"
    debug: bool = False
    
    # Model Configuration
    model_path: str = "./models/iit_lightgbm_model.txt"
    preprocessing_path: str = "./models/preprocessing_meta.joblib"
    model_manifest_path: str = "./models/model_manifest.json"
    
    # Feature Store Configuration
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    feature_store_ttl: int = 86400  # 24 hours
    
    # Database Configuration (SQLite for development, PostgreSQL for production)
    database_path: str = "./iit_ml_service.db"
    use_postgres: bool = False  # Use SQLite for local development
    
    # PostgreSQL settings (for production only)
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "iit_ml_service"
    postgres_user: str = "ml_service"
    postgres_password: str = "changeme"  # CHANGED: Should be overridden by env var
    iit_db_name: str = "iit_db"
    iit_db_user: str = "iit_user"
    iit_db_password: str = "strong_password_here"  # CHANGED: Should be overridden by env var
    medical_db_name: str = "medical_records"

    @property
    def database_url(self) -> str:
        """Construct database URL - SQLite for development, PostgreSQL for production"""
        if self.use_postgres:
            return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        else:
            return f"sqlite:///{self.database_path}"
    
    # Performance Configuration
    max_batch_size: int = 100
    prediction_timeout: float = 30.0

    # Backup Configuration
    backup_dir: str = "./backups"

    # Caching Configuration
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5 minutes default TTL
    cache_max_size: int = 1000  # Maximum cache entries
    cache_exclude_patterns: list[str] = ["/health", "/metrics", "/docs", "/openapi.json"]
    
    # Monitoring Configuration
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Security Configuration
    api_key_enabled: bool = False
    api_key_header: str = "X-API-Key"
    # CHANGED: Restrict CORS to specific origins instead of wildcard
    # Read from environment variable for flexibility
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://localhost:8080",  # Alternative dev port
            "http://127.0.0.1:8080",
        ]
    )
    # Add production frontend URL via environment variable
    frontend_url: str = Field(default="http://localhost:3000")
    
    security_enabled: bool = True  # Fixed - ASGI middleware signature issue resolved
    security_exclude_paths: list[str] = ["/health", "/docs", "/openapi.json", "/metrics"]
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100  # requests per window
    rate_limit_window: int = 60  # seconds
    rate_limit_per_user: bool = True  # CHANGED: Enable per-user rate limiting
    
    # JWT Configuration
    # CHANGED: Generate strong secret if not provided (for development only)
    jwt_secret_key: str = secrets.token_urlsafe(32)  # Override in production via env var
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Cookie Configuration for JWT
    cookie_domain: str | None = None  # Set for production
    cookie_secure: bool = False  # Use secure cookies only in production (HTTPS)
    cookie_samesite: str = "lax"  # Use lax for CSRF protection
    
    # HTTPS Configuration
    force_https: bool = False  # Enable HTTPS redirect (set to True in production)
    https_port: int = 443  # HTTPS port
    https_strict: bool = False  # If True, reject HTTP with 400 instead of redirect
    ssl_cert_path: str | None = None  # Path to SSL certificate
    ssl_key_path: str | None = None  # Path to SSL private key
    https_exclude_paths: list[str] = ["/health", "/metrics"]  # Paths excluded from HTTPS check
    
    # Idempotency Configuration
    idempotency_enabled: bool = True  # Enable idempotency key middleware
    idempotency_ttl: int = 172800  # 48 hours in seconds
    idempotency_header: str = "Idempotency-Key"  # Header name for idempotency key
    
    # OpenTelemetry Configuration
    telemetry_enabled: bool = True  # Enable distributed tracing
    jaeger_endpoint: str | None = None  # Jaeger collector endpoint (e.g., http://localhost:4318)
    jaeger_agent_host: str | None = None  # Jaeger agent host (e.g., localhost)
    jaeger_agent_port: int | None = None  # Jaeger agent port (e.g., 6831)
    telemetry_console_export: bool = False  # Enable console export for debugging
    telemetry_sample_rate: float = 1.0  # Sampling rate (0.0 to 1.0)
    
    # Session Configuration
    session_timeout_minutes: int = 30
    
    # IIT Prediction Specific
    iit_grace_period: int = 28
    prediction_window: int = 90
    default_threshold: float = 0.5
    
    # Retry Configuration
    retry_max_attempts: int = 3
    retry_wait_min: float = 1.0  # seconds
    retry_wait_max: float = 10.0  # seconds
    
    # Queue Configuration (for RQ)
    redis_queue_enabled: bool = True
    queue_name: str = "ihvn_ml_tasks"
    default_job_timeout: int = 600  # 10 minutes
    
    # Alerting Configuration
    pagerduty_routing_key: str | None = None
    pagerduty_api_url: str = "https://events.pagerduty.com/v2/enqueue"
    slack_webhook_url: str | None = None
    slack_default_channel: str = "#alerts"
    alerting_enabled: bool = True
    alert_rate_limit_critical: int = 0  # No rate limiting
    alert_rate_limit_error: int = 300  # 5 minutes
    alert_rate_limit_warning: int = 900  # 15 minutes
    alert_rate_limit_info: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Create a singleton instance for direct import
settings = get_settings()
