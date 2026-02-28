from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..crud import log_audit
from ..dependencies import get_db
from ..config import get_settings
from ..auth import get_token_from_cookie, ACCESS_COOKIE_NAME
import time
import logging
import hashlib
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional
import re
from jose import JWTError, jwt

logger = logging.getLogger(__name__)
settings = get_settings()

# Rate limiting storage (in production, use Redis)
rate_limit_store: Dict[str, List[float]] = defaultdict(list)
# Per-user rate limiting storage (user_id -> List[timestamps])
user_rate_limit_store: Dict[str, List[float]] = defaultdict(list)


def extract_user_id_from_request(request: Request) -> Optional[str]:
    """
    Extract user ID from JWT token in Authorization header or cookie.
    
    Returns None if no valid token found.
    """
    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    token = None
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # Try cookie
        token = get_token_from_cookie(request, ACCESS_COOKIE_NAME)
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload.get("user_id")
    except (JWTError, KeyError):
        return None

async def log_requests(request: Request, call_next):
    """Middleware to log all HTTP requests for security monitoring"""
    start_time = time.time()

    # Get client information
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    method = request.method
    url = str(request.url)

    # Log the request
    logger.info(f"Request: {method} {url} from {client_host}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log successful requests
        logger.info(f"Response: {response.status_code} in {process_time:.3f}s")

        # For sensitive operations, log to audit trail
        if method in ["POST", "PUT", "DELETE"] and "/api/" in url:
            # Get database session
            db_generator = get_db()
            db = next(db_generator)

            try:
                # Log to audit (user_id would come from auth in real implementation)
                log_audit(
                    db,
                    user_id=None,  # Would be extracted from JWT token in real auth
                    action=f"HTTP_{method}",
                    details=f"{method} {url} - Status: {response.status_code}"
                )
            finally:
                db.close()

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {method} {url} - Error: {str(e)} in {process_time:.3f}s")

        # Log security incidents
        db_generator = get_db()
        db = next(db_generator)
        try:
            log_audit(
                db,
                user_id=None,
                action="SECURITY_INCIDENT",
                details=f"Request failed: {method} {url} - Error: {str(e)}"
            )
        finally:
            db.close()

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

def check_rate_limit(
    client_ip: str,
    endpoint: str,
    max_requests: int = None,
    window_seconds: int = None,
    user_id: Optional[str] = None
) -> bool:
    """
    Check if client has exceeded rate limit.
    
    Enhanced with per-user rate limiting support.

    Args:
        client_ip: Client IP address
        endpoint: API endpoint being accessed
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        user_id: User ID for per-user rate limiting (optional)

    Returns:
        bool: True if request is allowed, False if rate limited
    """
    # Use settings defaults if not provided
    if max_requests is None:
        max_requests = settings.rate_limit_requests
    if window_seconds is None:
        window_seconds = settings.rate_limit_window
    
    current_time = time.time()
    
    # Determine which rate limit to apply
    # If per-user rate limiting is enabled and user is authenticated, use user-based
    # Otherwise, fall back to IP-based rate limiting
    if settings.rate_limit_per_user and user_id:
        # Per-user rate limiting
        client_key = f"user:{user_id}:{endpoint}"
        store = user_rate_limit_store
    else:
        # IP-based rate limiting
        client_key = f"{client_ip}:{endpoint}"
        store = rate_limit_store
    
    # Clean old requests outside the window
    store[client_key] = [
        req_time for req_time in store[client_key]
        if current_time - req_time < window_seconds
    ]

    # Check if under limit
    if len(store[client_key]) < max_requests:
        store[client_key].append(current_time)
        return True

    return False


def detect_suspicious_activity(request: Request) -> List[str]:
    """
    Detect potentially suspicious activity patterns

    Args:
        request: FastAPI request object

    Returns:
        List of detected security issues
    """
    issues = []
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    url = str(request.url)

    # Check for SQL injection patterns
    sql_patterns = [
        r"(\b(union|select|insert|update|delete|drop|create|alter)\b)",
        r"(\bor\b\s+\d+\s*=\s*\d+)",
        r"(\band\b\s+\d+\s*=\s*\d+)",
        r"(\bscript\b)",
        r"(\bon\w+\s*=)",
    ]

    query_params = str(request.query_params)
    for pattern in sql_patterns:
        if re.search(pattern, query_params.lower(), re.IGNORECASE):
            issues.append(f"Potential SQL injection detected in query params: {pattern}")

    # Check for suspicious user agents
    suspicious_uas = [
        "sqlmap",
        "nmap",
        "nikto",
        "dirbuster",
        "gobuster",
        "masscan",
        "zmap"
    ]

    for ua in suspicious_uas:
        if ua.lower() in user_agent.lower():
            issues.append(f"Suspicious user agent detected: {ua}")

    # Check for directory traversal
    if ".." in url or "%2e%2e" in url.lower():
        issues.append("Potential directory traversal detected")

    # Check for unusual request patterns
    if len(query_params) > 1000:
        issues.append("Unusually long query parameters")

    return issues


def log_security_event(db: Session, event_type: str, severity: str, details: Dict[str, any], client_ip: str = None):
    """
    Log security events to audit trail

    Args:
        db: Database session
        event_type: Type of security event
        severity: Severity level (low, medium, high, critical)
        details: Event details
        client_ip: Client IP address
    """
    try:
        log_audit(
            db,
            user_id=None,  # Would be extracted from auth context
            action=f"SECURITY_{event_type.upper()}",
            details=json.dumps({
                "severity": severity,
                "client_ip": client_ip,
                "timestamp": datetime.utcnow().isoformat(),
                **details
            })
        )

        # Log to security logger with appropriate level
        log_message = f"Security event: {event_type} (severity: {severity}) from {client_ip}"
        if severity in ["high", "critical"]:
            logger.error(log_message)
        elif severity == "medium":
            logger.warning(log_message)
        else:
            logger.info(log_message)

    except Exception as e:
        logger.error(f"Failed to log security event: {str(e)}")


class SecurityMonitoringMiddleware:
    """
    Enhanced security monitoring middleware with rate limiting and threat detection
    """

    def __init__(self, app, exclude_paths=None):
        self.app = app
        self.exclude_paths = exclude_paths or []

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Cache the request body to allow re-reading
        body_bytes = b""
        received = False

        async def receive_wrapper():
            nonlocal body_bytes, received
            if not received:
                received = True
                message = await receive()
                if message["type"] == "http.request":
                    body_bytes = message.get("body", b"")
                return message
            else:
                # Return cached body on subsequent reads
                return {"type": "http.request", "body": body_bytes, "more_body": False}

        # Build request object for analysis
        request = Request(scope, receive_wrapper)

        # Skip security checks for excluded paths
        if any(path in request.url.path for path in self.exclude_paths):
            await self.app(scope, receive_wrapper, send)
            return

        client_ip = request.client.host if request.client else "unknown"

        # Extract user ID for per-user rate limiting
        user_id = extract_user_id_from_request(request)
        
        # Rate limiting check (supports both IP-based and per-user)
        if not check_rate_limit(client_ip, request.url.path, user_id=user_id):
            # Determine what was rate limited
            rate_limit_type = "user" if user_id else "IP"
            identifier = str(user_id) if user_id else client_ip
            
            logger.warning(f"Rate limit exceeded for {rate_limit_type} {identifier} on {request.url.path}")

            # Log rate limit violation
            db_generator = get_db()
            db = next(db_generator)
            try:
                log_security_event(
                    db,
                    "RATE_LIMIT_EXCEEDED",
                    "medium",
                    {
                        "endpoint": request.url.path,
                        "method": request.method,
                        "rate_limit_type": rate_limit_type,
                        "identifier": identifier
                    },
                    client_ip
                )
            finally:
                db.close()

            # Return rate limit response with retry info
            retry_after = settings.rate_limit_window
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )
            await response(scope, receive_wrapper, send)
            return

        # Suspicious activity detection
        security_issues = detect_suspicious_activity(request)
        if security_issues:
            db_generator = get_db()
            db = next(db_generator)
            try:
                for issue in security_issues:
                    log_security_event(
                        db,
                        "SUSPICIOUS_ACTIVITY",
                        "high" if "sql" in issue.lower() else "medium",
                        {"issue": issue, "endpoint": request.url.path},
                        client_ip
                    )
            finally:
                db.close()

            # Block request if critical issues detected
            if any("sql injection" in issue.lower() for issue in security_issues):
                response = JSONResponse(
                    status_code=403,
                    content={"detail": "Request blocked due to security policy"}
                )
                await response(scope, receive, send)
                return

        # Enhanced request logging
        await log_requests(request, lambda req: self.app(scope, receive_wrapper, send))


def setup_security_headers(response: Response):
    """Add comprehensive security headers to responses"""
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "X-Permitted-Cross-Domain-Policies": "none",
    }

    for header, value in headers.items():
        response.headers[header] = value

    return response


def create_rate_limiting_middleware(max_requests: int = 100, window_seconds: int = 60):
    """
    Create rate limiting middleware

    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds

    Returns:
        Middleware function
    """
    async def rate_limit_middleware(request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        if not check_rate_limit(client_ip, request.url.path, max_requests, window_seconds):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )

        response = await call_next(request)
        return response

    return rate_limit_middleware
