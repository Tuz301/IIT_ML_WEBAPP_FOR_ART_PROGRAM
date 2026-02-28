"""
Idempotency Keys Middleware

Ensures that requests with the same idempotency key return the same result,
allowing safe retries without duplicate operations.

Usage:
    - Client sends Idempotency-Key header with request
    - First request processes normally and caches result
    - Subsequent requests with same key return cached result
    - Keys expire after a configurable TTL (default: 48 hours)
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from functools import wraps
import logging

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.utils.database import DatabaseManager

logger = logging.getLogger(__name__)


# Default TTL for idempotency keys (48 hours)
DEFAULT_IDEMPOTENCY_TTL = 48 * 3600


class IdempotencyStore:
    """
    Storage for idempotency key results
    
    Uses database for persistence across restarts.
    In production, consider using Redis for better performance.
    """
    
    @staticmethod
    def _get_table_name() -> str:
        """Get the idempotency table name"""
        return "idempotency_keys"
    
    @staticmethod
    def _ensure_table_exists():
        """Ensure idempotency table exists"""
        query = """
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT NOT NULL UNIQUE,
            key_value TEXT NOT NULL,
            response_data TEXT NOT NULL,
            response_status INTEGER NOT NULL,
            response_headers TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            request_path TEXT NOT NULL,
            request_method TEXT NOT NULL,
            user_id TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_idempotency_key_hash ON idempotency_keys(key_hash);
        CREATE INDEX IF NOT EXISTS idx_idempotency_expires_at ON idempotency_keys(expires_at);
        """
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                conn.execute(query)
        except Exception as e:
            logger.error(f"Failed to create idempotency table: {e}")
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash idempotency key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def get(key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response for idempotency key
        
        Args:
            key: Idempotency key
            
        Returns:
            Cached response data or None if not found/expired
        """
        IdempotencyStore._ensure_table_exists()
        
        key_hash = IdempotencyStore._hash_key(key)
        
        query = """
        SELECT response_data, response_status, response_headers, created_at, expires_at
        FROM idempotency_keys
        WHERE key_hash = ? AND expires_at > datetime('now')
        LIMIT 1;
        """
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (key_hash,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        "response_data": result[0],
                        "response_status": result[1],
                        "response_headers": json.loads(result[2]),
                        "created_at": result[3],
                        "expires_at": result[4]
                    }
        except Exception as e:
            logger.error(f"Error retrieving idempotency key: {e}")
        
        return None
    
    @staticmethod
    def store(
        key: str,
        response_data: str,
        response_status: int,
        response_headers: Dict[str, str],
        request_path: str,
        request_method: str,
        user_id: Optional[str] = None,
        ttl: int = DEFAULT_IDEMPOTENCY_TTL
    ) -> bool:
        """
        Store response for idempotency key
        
        Args:
            key: Idempotency key
            response_data: Response body
            response_status: HTTP status code
            response_headers: Response headers
            request_path: Request path
            request_method: HTTP method
            user_id: User ID (optional)
            ttl: Time to live in seconds
            
        Returns:
            True if stored successfully, False otherwise
        """
        IdempotencyStore._ensure_table_exists()
        
        key_hash = IdempotencyStore._hash_key(key)
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        query = """
        INSERT INTO idempotency_keys (
            key_hash, key_value, response_data, response_status,
            response_headers, request_path, request_method, user_id, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    key_hash,
                    key,
                    response_data,
                    response_status,
                    json.dumps(response_headers),
                    request_path,
                    request_method,
                    user_id,
                    expires_at.isoformat()
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error storing idempotency key: {e}")
            return False
    
    @staticmethod
    def cleanup_expired():
        """Remove expired idempotency keys"""
        IdempotencyStore._ensure_table_exists()
        
        query = """
        DELETE FROM idempotency_keys
        WHERE expires_at <= datetime('now');
        """
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"Cleaned up {deleted_count} expired idempotency keys")
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up idempotency keys: {e}")
            return 0


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle idempotency keys
    
    Checks for Idempotency-Key header and returns cached response if exists.
    Stores response for future requests with same key.
    """
    
    # Paths that require idempotency (POST, PUT, PATCH, DELETE)
    IDEMPOTENT_PATHS = {
        "/v1/patients/",
        "/v1/predictions",
        "/v1/predictions/batch",
        "/v1/interventions",
        "/v1/communications",
        "/v1/ensemble/predict",
    }
    
    # Methods that should be idempotent
    IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    
    def __init__(
        self,
        app,
        enabled: bool = True,
        ttl: int = DEFAULT_IDEMPOTENCY_TTL,
        header_name: str = "Idempotency-Key"
    ):
        super().__init__(app)
        self.enabled = enabled
        self.ttl = ttl
        self.header_name = header_name
        logger.info(f"Idempotency middleware initialized: enabled={enabled}, ttl={ttl}s")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with idempotency check
        
        Args:
            request: Incoming request
            call_next: Next middleware/route handler
            
        Returns:
            Response (either cached or new)
        """
        # Skip if idempotency is disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip if not an idempotent method
        if request.method not in self.IDEMPOTENT_METHODS:
            return await call_next(request)
        
        # Skip if path doesn't require idempotency
        if not any(request.url.path.startswith(path) for path in self.IDEMPOTENT_PATHS):
            return await call_next(request)
        
        # Get idempotency key from header
        idempotency_key = request.headers.get(self.header_name)
        
        if not idempotency_key:
            # No idempotency key, proceed normally
            return await call_next(request)
        
        # Validate idempotency key format
        if not self._is_valid_key(idempotency_key):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Invalid idempotency key format. "
                             "Must be a UUID, base64-encoded string, or hash with 3-255 characters."
                }
            )
        
        # Check for cached response
        cached = IdempotencyStore.get(idempotency_key)
        
        if cached:
            # Return cached response
            logger.info(f"Returning cached response for idempotency key: {idempotency_key[:8]}...")
            
            response = JSONResponse(
                status_code=cached["response_status"],
                content=json.loads(cached["response_data"])
            )
            
            # Add cached response headers
            for header, value in cached["response_headers"].items():
                if header.lower() != "content-length":  # Don't set content-length manually
                    response.headers[header] = value
            
            # Add idempotency headers
            response.headers["Idempotency-Replayed"] = "true"
            response.headers["Original-Date"] = cached["created_at"]
            
            return response
        
        # Process request normally
        response = await call_next(request)
        
        # Store response for future requests
        # Only cache successful responses (2xx status codes)
        if 200 <= response.status_code < 300:
            # Get response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Parse response body
            try:
                response_data = response_body.decode()
            except UnicodeDecodeError:
                response_data = response_body.decode("utf-8", errors="ignore")
            
            # Get response headers
            response_headers = dict(response.headers)
            
            # Get user ID if available
            user_id = getattr(request.state, "user_id", None)
            
            # Store in idempotency store
            IdempotencyStore.store(
                key=idempotency_key,
                response_data=response_data,
                response_status=response.status_code,
                response_headers=response_headers,
                request_path=request.url.path,
                request_method=request.method,
                user_id=user_id,
                ttl=self.ttl
            )
            
            # Rebuild response with body
            response = JSONResponse(
                status_code=response.status_code,
                content=json.loads(response_data),
                headers=response_headers
            )
            response.headers["Idempotency-Key"] = idempotency_key[:8] + "..."
        
        return response
    
    def _is_valid_key(self, key: str) -> bool:
        """
        Validate idempotency key format
        
        Args:
            key: Idempotency key to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check length (3-255 characters)
        if not (3 <= len(key) <= 255):
            return False
        
        # Check for valid characters (alphanumeric, hyphen, underscore, dot)
        import re
        if not re.match(r'^[a-zA-Z0-9\-._]+$', key):
            return False
        
        return True


def idempotent(ttl: int = DEFAULT_IDEMPOTENCY_TTL):
    """
    Decorator to mark endpoint as idempotent
    
    Args:
        ttl: Time to live for cached responses (seconds)
    
    Usage:
        @app.post("/v1/payments")
        @idempotent(ttl=86400)  # 24 hours
        async def create_payment(payment_data: PaymentCreate):
            # Your payment logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request = kwargs.get("request")
            
            if not request:
                return await func(*args, **kwargs)
            
            # Get idempotency key
            idempotency_key = request.headers.get("Idempotency-Key")
            
            if not idempotency_key:
                return await func(*args, **kwargs)
            
            # Check for cached response
            cached = IdempotencyStore.get(idempotency_key)
            
            if cached:
                return JSONResponse(
                    status_code=cached["response_status"],
                    content=json.loads(cached["response_data"]),
                    headers=json.loads(cached["response_headers"])
                )
            
            # Process request
            response = await func(*args, **kwargs)
            
            # Cache successful responses
            if hasattr(response, "status_code") and 200 <= response.status_code < 300:
                # Store response
                pass  # Storage handled by middleware
            
            return response
        
        return wrapper
    return decorator


def create_idempotency_middleware(
    enabled: Optional[bool] = None,
    ttl: Optional[int] = None,
    header_name: Optional[str] = None
) -> IdempotencyMiddleware:
    """
    Factory function to create idempotency middleware
    
    Args:
        enabled: Override default from settings
        ttl: Override default TTL
        header_name: Override default header name
        
    Returns:
        Configured IdempotencyMiddleware instance
    """
    if enabled is None:
        enabled = getattr(settings, 'idempotency_enabled', True)
    if ttl is None:
        ttl = getattr(settings, 'idempotency_ttl', DEFAULT_IDEMPOTENCY_TTL)
    if header_name is None:
        header_name = getattr(settings, 'idempotency_header', 'Idempotency-Key')
    
    return IdempotencyMiddleware(
        app=None,  # Will be set when middleware is added to app
        enabled=enabled,
        ttl=ttl,
        header_name=header_name
    )
