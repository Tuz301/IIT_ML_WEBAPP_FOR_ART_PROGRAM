"""
Database configuration and connection management for IIT ML Service
"""
import os
import logging
import hashlib
import json
from typing import Optional, Any, Dict, Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Database configuration
from ..config import get_settings
settings = get_settings()
DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)

# Connection pool settings
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Create engine with connection pooling
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Enable connection health checks
        echo=False,  # Set to True for SQL query logging in development
        connect_args=connect_args,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=POOL_RECYCLE,
        pool_pre_ping=True,  # Enable connection health checks
        echo=False,  # Set to True for SQL query logging in development
        connect_args=connect_args,
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()
metadata = Base.metadata


class QueryCache:
    """
    Redis-based cache for database query results
    """

    def __init__(self):
        try:
            import redis
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True
            )
            self.enabled = settings.cache_enabled
        except ImportError:
            logger.warning("Redis not available, query caching disabled")
            self.redis_client = None
            self.enabled = False

    def _generate_query_key(self, query_hash: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate a unique cache key for a query"""
        key_parts = ["db_query", query_hash]
        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            params_str = json.dumps(sorted_params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            key_parts.append(params_hash)
        return "|".join(key_parts)

    def get_cached_result(self, query_hash: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Get cached query result"""
        if not self.enabled or not self.redis_client:
            return None

        try:
            cache_key = self._generate_query_key(query_hash, params)
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"Query cache hit for key: {cache_key}")
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warning(f"Failed to get cached query result: {str(e)}")
            return None

    def set_cached_result(self, query_hash: str, result: Any, params: Optional[Dict[str, Any]] = None, ttl: Optional[int] = None) -> bool:
        """Cache query result"""
        if not self.enabled or not self.redis_client:
            return False

        try:
            cache_key = self._generate_query_key(query_hash, params)
            ttl_value = ttl or settings.cache_ttl

            # Serialize result
            serialized_result = json.dumps(result, default=str)

            success = self.redis_client.setex(cache_key, ttl_value, serialized_result)
            if success:
                logger.debug(f"Query result cached with key: {cache_key}, TTL: {ttl_value}")
            return bool(success)
        except Exception as e:
            logger.warning(f"Failed to cache query result: {str(e)}")
            return False

    def invalidate_query_cache(self, query_hash: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Invalidate cached query result"""
        if not self.enabled or not self.redis_client:
            return False

        try:
            cache_key = self._generate_query_key(query_hash, params)
            result = self.redis_client.delete(cache_key)
            if result:
                logger.debug(f"Query cache invalidated for key: {cache_key}")
            return bool(result)
        except Exception as e:
            logger.warning(f"Failed to invalidate query cache: {str(e)}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disabled", "reason": "Redis not available"}

        try:
            info = self.redis_client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": self.redis_client.dbsize(),
                "cache_enabled": self.enabled
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global query cache instance
query_cache = QueryCache()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_database_connectivity() -> bool:
    """
    Verify database connectivity and return connection status

    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        # Test connection
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connectivity verified successfully")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connectivity check failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during database connectivity check: {str(e)}")
        return False

def get_database_stats() -> dict:
    """
    Get database connection pool statistics

    Returns:
        dict: Dictionary containing pool statistics
    """
    try:
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checkedin": pool.checkedin(),
            "checkedout": pool.checkedout(),
            "invalid": pool.invalid(),
            "overflow": pool.overflow(),
            "timeout": pool.timeout(),
        }
    except Exception as e:
        logger.error(f"Failed to get database stats: {str(e)}")
        return {}

def create_database_backup(backup_path: str) -> bool:
    """
    Create a database backup using pg_dump

    Args:
        backup_path: Path where backup file should be saved

    Returns:
        bool: True if backup successful, False otherwise
    """
    import subprocess
    import shlex

    try:
        # Parse DATABASE_URL to extract connection details
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)

        # Build pg_dump command
        cmd = [
            "pg_dump",
            "--host", parsed.hostname or "localhost",
            "--port", str(parsed.port or 5432),
            "--username", parsed.username or "",
            "--dbname", parsed.path.lstrip("/"),
            "--format", "custom",
            "--compress", "9",
            "--file", backup_path
        ]

        # Set password environment variable
        env = os.environ.copy()
        if parsed.password:
            env["PGPASSWORD"] = parsed.password

        # Execute backup
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            logger.info(f"Database backup created successfully: {backup_path}")
            return True
        else:
            logger.error(f"Database backup failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Database backup timed out")
        return False
    except Exception as e:
        logger.error(f"Database backup failed with error: {str(e)}")
        return False

def restore_database_backup(backup_path: str) -> bool:
    """
    Restore database from backup using pg_restore

    Args:
        backup_path: Path to the backup file

    Returns:
        bool: True if restore successful, False otherwise
    """
    import subprocess

    try:
        # Parse DATABASE_URL to extract connection details
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)

        # Build pg_restore command
        cmd = [
            "pg_restore",
            "--host", parsed.hostname or "localhost",
            "--port", str(parsed.port or 5432),
            "--username", parsed.username or "",
            "--dbname", parsed.path.lstrip("/"),
            "--clean",  # Drop existing objects before recreating
            "--if-exists",
            "--create",  # Create database if it doesn't exist
            backup_path
        ]

        # Set password environment variable
        env = os.environ.copy()
        if parsed.password:
            env["PGPASSWORD"] = parsed.password

        # Execute restore
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            logger.info(f"Database restore completed successfully from: {backup_path}")
            return True
        else:
            logger.error(f"Database restore failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Database restore timed out")
        return False
    except Exception as e:
        logger.error(f"Database restore failed with error: {str(e)}")
        return False

def init_database():
    """
    Initialize database by creating all tables
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise

def reset_database():
    """
    Reset database by dropping and recreating all tables
    WARNING: This will delete all data!
    """
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.warning("Database reset completed - all data deleted")
    except Exception as e:
        logger.error(f"Failed to reset database: {str(e)}")
        raise


def invalidate_cache_for_model(model_name: str, record_ids: Optional[list] = None) -> bool:
    """
    Invalidate cache entries related to a specific model

    Args:
        model_name: Name of the model (e.g., 'Patient', 'Prediction')
        record_ids: Optional list of specific record IDs to invalidate

    Returns:
        bool: True if invalidation successful
    """
    if not query_cache.enabled:
        return True

    try:
        # Invalidate general model queries
        patterns = [f"db_query|*{model_name.lower()}*"]

        if record_ids:
            # Invalidate specific record queries
            for record_id in record_ids:
                patterns.append(f"db_query|*{model_name.lower()}*{record_id}*")

        invalidated_count = 0
        for pattern in patterns:
            # Use Redis SCAN to find matching keys
            cursor = 0
            while True:
                cursor, keys = query_cache.redis_client.scan(cursor, match=pattern)
                if keys:
                    query_cache.redis_client.delete(*keys)
                    invalidated_count += len(keys)
                if cursor == 0:
                    break

        logger.info(f"Invalidated {invalidated_count} cache entries for model: {model_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to invalidate cache for model {model_name}: {str(e)}")
        return False


def get_query_cache_stats() -> Dict[str, Any]:
    """
    Get comprehensive cache statistics

    Returns:
        dict: Cache statistics including hit rates and performance metrics
    """
    cache_stats = query_cache.get_cache_stats()

    # Add database-specific stats
    db_stats = get_database_stats()

    return {
        "cache": cache_stats,
        "database": db_stats,
        "combined": {
            "cache_enabled": cache_stats.get("cache_enabled", False),
            "db_connections": db_stats.get("pool_size", 0),
            "db_checked_out": db_stats.get("checkedout", 0)
        }
    }


def optimize_query_performance():
    """
    Apply database performance optimizations

    This function can be called during application startup to ensure
    optimal database performance settings.
    """
    try:
        # Enable query execution time logging in development
        if settings.debug:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

        # Additional optimizations can be added here:
        # - Index creation
        # - Query plan analysis
        # - Connection pool tuning

        logger.info("Database performance optimizations applied")
    except Exception as e:
        logger.warning(f"Failed to apply database optimizations: {str(e)}")
