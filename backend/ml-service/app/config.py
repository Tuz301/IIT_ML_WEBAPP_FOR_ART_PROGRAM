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
    
    security_enabled: bool = False  # Disabled due to ASGI middleware signature issues
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
    
    # Session Configuration
    session_timeout_minutes: int = 30
    
    # IIT Prediction Specific
    iit_grace_period: int = 28
    prediction_window: int = 90
    default_threshold: float = 0.5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
