"""
HTTPS Redirect Middleware

Enforces HTTPS by redirecting HTTP requests to HTTPS.
Can be enabled/disabled via configuration.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS
    
    This middleware checks if the incoming request is HTTP and redirects
    to HTTPS. It respects the X-Forwarded-Proto header for proxied requests.
    
    Configuration:
    - settings.force_https: Enable/disable HTTPS redirect
    - settings.https_port: HTTPS port (default: 443)
    - settings.https_strict: If True, reject non-HTTPS with 400 instead of redirect
    """
    
    def __init__(
        self,
        app,
        force_https: bool = True,
        https_port: int = 443,
        strict_mode: bool = False,
        excluded_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.force_https = force_https
        self.https_port = https_port
        self.strict_mode = strict_mode
        self.excluded_paths = excluded_paths or [
            "/health",  # Health checks
            "/metrics",  # Metrics endpoints
        ]
        logger.info(
            f"HTTPS redirect middleware initialized: "
            f"force_https={force_https}, port={https_port}, strict={strict_mode}"
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and redirect to HTTPS if needed
        
        Args:
            request: Incoming request
            call_next: Next middleware/route handler
            
        Returns:
            Response (either redirect or normal response)
        """
        # Skip HTTPS check if disabled
        if not self.force_https:
            return await call_next(request)
        
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Determine if request is HTTPS
        is_https = self._is_https_request(request)
        
        if not is_https:
            if self.strict_mode:
                # Strict mode: reject with 400 Bad Request
                logger.warning(
                    f"Non-HTTPS request rejected (strict mode): {request.url}"
                )
                return Response(
                    content="HTTPS Required. Please use HTTPS protocol.",
                    status_code=400,
                    headers={"Strict-Transport-Security": "max-age=31536000; includeSubDomains"}
                )
            else:
                # Redirect mode: redirect to HTTPS
                https_url = self._build_https_url(request)
                logger.info(f"Redirecting HTTP to HTTPS: {request.url} -> {https_url}")
                
                response = RedirectResponse(
                    url=https_url,
                    status_code=301  # Permanent redirect
                )
                # Add HSTS header
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                return response
        
        # Request is HTTPS, add HSTS header and continue
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    
    def _is_https_request(self, request: Request) -> bool:
        """
        Determine if request is HTTPS
        
        Checks:
        1. Request URL scheme
        2. X-Forwarded-Proto header (for proxied requests)
        3. X-Forwarded-SSL header (for proxied requests)
        
        Args:
            request: Incoming request
            
        Returns:
            True if request is HTTPS, False otherwise
        """
        # Check URL scheme
        if request.url.scheme == "https":
            return True
        
        # Check X-Forwarded-Proto header (set by reverse proxy)
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        if forwarded_proto == "https":
            return True
        
        # Check X-Forwarded-SSL header (set by some proxies)
        forwarded_ssl = request.headers.get("x-forwarded-ssl", "").lower()
        if forwarded_ssl in ("on", "1", "true"):
            return True
        
        # Check CloudFront specific headers
        cloudfront_proto = request.headers.get("cloudfront-forwarded-proto", "").lower()
        if cloudfront_proto == "https":
            return True
        
        return False
    
    def _build_https_url(self, request: Request) -> str:
        """
        Build HTTPS URL from HTTP request
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            HTTPS URL
        """
        # Get host from headers or URL
        host = request.headers.get("x-forwarded-host", request.url.hostname)
        if not host:
            host = request.url.hostname or "localhost"
        
        # Build HTTPS URL
        if self.https_port == 443:
            # Default HTTPS port, don't include port in URL
            https_url = f"https://{host}{request.url.path}"
        else:
            # Custom HTTPS port
            https_url = f"https://{host}:{self.https_port}{request.url.path}"
        
        # Preserve query string
        if request.url.query:
            https_url += f"?{request.url.query}"
        
        # Preserve fragment
        if request.url.fragment:
            https_url += f"#{request.url.fragment}"
        
        return https_url


def create_https_redirect_middleware(
    force_https: Optional[bool] = None,
    https_port: Optional[int] = None,
    strict_mode: Optional[bool] = None,
    excluded_paths: Optional[list] = None
) -> HTTPSRedirectMiddleware:
    """
    Factory function to create HTTPS redirect middleware
    
    Args:
        force_https: Override default from settings
        https_port: Override default from settings
        strict_mode: Override default from settings
        excluded_paths: Paths to exclude from HTTPS check
        
    Returns:
        Configured HTTPSRedirectMiddleware instance
    """
    # Use provided values or fall back to settings
    if force_https is None:
        force_https = getattr(settings, 'force_https', False)
    if https_port is None:
        https_port = getattr(settings, 'https_port', 443)
    if strict_mode is None:
        strict_mode = getattr(settings, 'https_strict', False)
    
    return HTTPSRedirectMiddleware(
        app=None,  # Will be set when middleware is added to app
        force_https=force_https,
        https_port=https_port,
        strict_mode=strict_mode,
        excluded_paths=excluded_paths
    )


# Security headers for HTTPS
HTTPS_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}


def add_https_security_headers(response: Response) -> Response:
    """
    Add security headers for HTTPS to response
    
    Args:
        response: HTTP response
        
    Returns:
        Response with security headers added
    """
    for header, value in HTTPS_SECURITY_HEADERS.items():
        if header not in response.headers:
            response.headers[header] = value
    return response
