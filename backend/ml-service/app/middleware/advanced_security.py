"""
Advanced security middleware for comprehensive threat detection and response
"""
import asyncio
import hashlib
import json
import logging
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from ..config import get_settings
from ..monitoring import MetricsManager
from ..core.db import get_db
from ..crud import log_audit

logger = logging.getLogger(__name__)
settings = get_settings()

class ThreatIntelligence:
    """Threat intelligence and pattern recognition"""

    def __init__(self):
        self.suspicious_ips: Set[str] = set()
        self.blocked_ips: Set[str] = set()
        self.suspicious_patterns = {
            'sql_injection': [
                r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
                r"(\bor\b\s+\d+\s*=\s*\d+)",
                r"(\band\b\s+\d+\s*=\s*\d+)",
                r"(\bscript\b)",
                r"(\bon\w+\s*=)",
                r"(\beval\()",
                r"(\bexec\()",
                r"(\bsystem\()",
                r"(\bpassthru\()",
                r"(\bshell_exec\()",
            ],
            'xss': [
                r"(<script[^>]*>.*?</script>)",
                r"(javascript:)",
                r"(vbscript:)",
                r"(onload\s*=)",
                r"(onerror\s*=)",
                r"(onclick\s*=)",
                r"(<iframe[^>]*>)",
                r"(<object[^>]*>)",
                r"(<embed[^>]*>)",
            ],
            'path_traversal': [
                r"(\.\./)",
                r"(\.\.\\)",
                r"(%2e%2e/)",
                r"(%2e%2e\\)",
                r"(\.\.%2f)",
                r"(\.\.%5c)",
            ],
            'command_injection': [
                r"(\|\|)",
                r"(;)",
                r"(&&)",
                r"(\|)",
                r"(\$\()",
                r"(\`.*?\`)",
                r"(\$\{.*?\})",
            ]
        }

        # Suspicious user agents
        self.suspicious_uas = {
            'scanners': [
                "sqlmap", "nmap", "nikto", "dirbuster", "gobuster",
                "masscan", "zmap", "nessus", "openvas", "acunetix",
                "qualys", "rapid7", "metasploit", "burpsuite"
            ],
            'bots': [
                "bot", "crawler", "spider", "scraper", "harvest",
                "extract", "dataminer", "python-requests", "go-http-client"
            ]
        }

    def is_ip_suspicious(self, ip: str) -> bool:
        """Check if IP is marked as suspicious"""
        return ip in self.suspicious_ips

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        return ip in self.blocked_ips

    def block_ip(self, ip: str, reason: str):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        logger.warning(f"IP {ip} blocked: {reason}")

    def detect_attack_patterns(self, request: Request) -> List[Dict[str, str]]:
        """Detect various attack patterns in the request"""
        threats = []
        url = str(request.url)
        query_params = str(request.query_params)
        headers = dict(request.headers)
        user_agent = headers.get('user-agent', '').lower()

        # Check URL and query parameters
        check_text = f"{url} {query_params}"

        for attack_type, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                if re.search(pattern, check_text, re.IGNORECASE):
                    threats.append({
                        'type': attack_type,
                        'pattern': pattern,
                        'location': 'url_query',
                        'severity': 'high' if attack_type in ['sql_injection', 'command_injection'] else 'medium'
                    })

        # Check headers for suspicious content
        for header_name, header_value in headers.items():
            for attack_type, patterns in self.suspicious_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, header_value, re.IGNORECASE):
                        threats.append({
                            'type': attack_type,
                            'pattern': pattern,
                            'location': f'header_{header_name}',
                            'severity': 'high' if attack_type in ['sql_injection', 'command_injection'] else 'medium'
                        })

        # Check user agent
        for category, uas in self.suspicious_uas.items():
            for ua in uas:
                if ua.lower() in user_agent:
                    threats.append({
                        'type': f'suspicious_ua_{category}',
                        'pattern': ua,
                        'location': 'user_agent',
                        'severity': 'low' if category == 'bots' else 'medium'
                    })

        # Check for unusual request patterns
        if len(query_params) > 2000:
            threats.append({
                'type': 'unusual_request_size',
                'pattern': f'query_params_length_{len(query_params)}',
                'location': 'query_params',
                'severity': 'low'
            })

        if len(url) > 2000:
            threats.append({
                'type': 'unusual_url_length',
                'pattern': f'url_length_{len(url)}',
                'location': 'url',
                'severity': 'low'
            })

        return threats

class BehavioralAnalyzer:
    """Analyze user behavior patterns for anomaly detection"""

    def __init__(self):
        self.ip_request_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.ip_request_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.endpoint_access_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record_request(self, ip: str, endpoint: str, timestamp: float):
        """Record a request for behavioral analysis"""
        self.ip_request_counts[ip].append(timestamp)
        self.ip_request_times[ip].append(timestamp)
        self.endpoint_access_patterns[ip][endpoint] += 1

    def detect_anomalies(self, ip: str) -> List[Dict[str, str]]:
        """Detect behavioral anomalies"""
        anomalies = []

        # Check request frequency
        if len(self.ip_request_times[ip]) >= 10:
            recent_requests = [t for t in self.ip_request_times[ip] if time.time() - t < 60]  # Last minute
            if len(recent_requests) > 50:  # More than 50 requests per minute
                anomalies.append({
                    'type': 'high_frequency_requests',
                    'description': f'{len(recent_requests)} requests in last minute',
                    'severity': 'medium'
                })

        # Check endpoint access patterns
        total_requests = sum(self.endpoint_access_patterns[ip].values())
        if total_requests > 20:
            # Check if accessing too many different endpoints
            unique_endpoints = len(self.endpoint_access_patterns[ip])
            if unique_endpoints > 10:  # Accessing more than 10 different endpoints
                anomalies.append({
                    'type': 'endpoint_scanning',
                    'description': f'Accessing {unique_endpoints} different endpoints',
                    'severity': 'medium'
                })

            # Check for sequential endpoint access (potential scanning)
            endpoints = list(self.endpoint_access_patterns[ip].keys())
            if len(endpoints) >= 5:
                # Simple heuristic: if endpoints look like they're being scanned sequentially
                sorted_endpoints = sorted(endpoints)
                if any('api' in ep for ep in sorted_endpoints[:3]):  # First few are API endpoints
                    anomalies.append({
                        'type': 'sequential_access',
                        'description': 'Sequential API endpoint access detected',
                        'severity': 'low'
                    })

        return anomalies

class SecurityEventLogger:
    """Enhanced security event logging and alerting"""

    def __init__(self):
        self.event_buffer: List[Dict] = []
        self.buffer_size = 100
        self.alert_thresholds = {
            'high': 5,  # Alert if 5+ high severity events in buffer
            'critical': 1  # Alert immediately on critical events
        }

    async def log_security_event(self, event_type: str, severity: str, details: Dict,
                                client_ip: str, request: Request = None):
        """Log a security event with enhanced context"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'client_ip': client_ip,
            'details': details,
            'request_context': self._extract_request_context(request) if request else {}
        }

        # Add to buffer
        self.event_buffer.append(event)
        if len(self.event_buffer) > self.buffer_size:
            self.event_buffer.pop(0)

        # Log to database
        await self._persist_event(event)

        # Check for alerts
        await self._check_alerts(event)

        # Log to application logger
        log_message = f"Security event: {event_type} ({severity}) from {client_ip}"
        if severity == 'critical':
            logger.critical(log_message)
        elif severity == 'high':
            logger.error(log_message)
        elif severity == 'medium':
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def _extract_request_context(self, request: Request) -> Dict:
        """Extract relevant context from the request"""
        return {
            'method': request.method,
            'url': str(request.url),
            'user_agent': request.headers.get('user-agent', 'unknown'),
            'referer': request.headers.get('referer', 'unknown'),
            'accept': request.headers.get('accept', 'unknown'),
            'content_type': request.headers.get('content-type', 'unknown')
        }

    async def _persist_event(self, event: Dict):
        """Persist security event to database"""
        try:
            db_generator = get_db()
            db = next(db_generator)

            try:
                log_audit(
                    db,
                    user_id=None,  # Would be extracted from auth context
                    action=f"SECURITY_{event['event_type'].upper()}",
                    details=json.dumps(event)
                )
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to persist security event: {str(e)}")

    async def _check_alerts(self, event: Dict):
        """Check if alerts should be triggered"""
        severity = event['severity']

        if severity == 'critical':
            await self._trigger_alert(f"Critical security event: {event['event_type']}", event)
            return

        # Count events in buffer by severity
        severity_counts = defaultdict(int)
        for buffered_event in self.event_buffer[-20:]:  # Check last 20 events
            severity_counts[buffered_event['severity']] += 1

        if severity_counts['high'] >= self.alert_thresholds['high']:
            await self._trigger_alert(f"Multiple high-severity security events detected", {
                'event_counts': dict(severity_counts),
                'recent_events': self.event_buffer[-5:]
            })

    async def _trigger_alert(self, message: str, details: Dict):
        """Trigger a security alert"""
        # In a real implementation, this would:
        # - Send email alerts
        # - Send SMS alerts
        # - Trigger incident response systems
        # - Update monitoring dashboards

        alert_data = {
            'message': message,
            'details': details,
            'timestamp': datetime.utcnow().isoformat(),
            'alert_type': 'security_incident'
        }

        logger.critical(f"SECURITY ALERT: {message}")
        logger.critical(f"Alert details: {json.dumps(alert_data, indent=2)}")

        # Update metrics
        MetricsManager.record_security_incident()

class AdvancedSecurityMiddleware:
    """Advanced security middleware with comprehensive threat detection"""

    def __init__(self, app, exclude_paths: List[str] = None):
        self.app = app
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.threat_intel = ThreatIntelligence()
        self.behavior_analyzer = BehavioralAnalyzer()
        self.event_logger = SecurityEventLogger()

        # Rate limiting configuration
        self.rate_limits = {
            'default': "100/minute",
            'auth': "5/minute",
            'api': "50/minute",
            'admin': "20/minute"
        }

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        client_ip = request.client.host if request.client else "unknown"

        # Skip security checks for excluded paths
        if any(path in request.url.path for path in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # Check if IP is blocked
        if self.threat_intel.is_ip_blocked(client_ip):
            await self._send_blocked_response(scope, receive, send, client_ip)
            return

        # Record request for behavioral analysis
        self.behavior_analyzer.record_request(client_ip, request.url.path, time.time())

        # Threat detection
        threats = self.threat_intel.detect_attack_patterns(request)
        if threats:
            for threat in threats:
                await self.event_logger.log_security_event(
                    f"THREAT_DETECTED_{threat['type'].upper()}",
                    threat['severity'],
                    threat,
                    client_ip,
                    request
                )

            # Block request if high-severity threats detected
            if any(t['severity'] in ['high', 'critical'] for t in threats):
                self.threat_intel.block_ip(client_ip, f"High-severity threat detected: {threats}")
                await self._send_blocked_response(scope, receive, send, client_ip)
                return

        # Behavioral anomaly detection
        anomalies = self.behavior_analyzer.detect_anomalies(client_ip)
        if anomalies:
            for anomaly in anomalies:
                await self.event_logger.log_security_event(
                    f"BEHAVIOR_ANOMALY_{anomaly['type'].upper()}",
                    anomaly['severity'],
                    anomaly,
                    client_ip,
                    request
                )

        # Enhanced request processing
        await self._process_request(scope, receive, send, request, client_ip)

    async def _process_request(self, scope, receive, send, request: Request, client_ip: str):
        """Process the request with enhanced security"""
        start_time = time.time()

        try:
            # Add security headers to response
            original_send = send

            async def security_send(message):
                if message["type"] == "http.response.start":
                    headers = self._enhance_security_headers(message.get("headers", []))
                    message["headers"] = headers
                await original_send(message)

            await self.app(scope, receive, security_send)

        except Exception as e:
            # Log security-related errors
            await self.event_logger.log_security_event(
                "REQUEST_PROCESSING_ERROR",
                "medium",
                {"error": str(e), "processing_time": time.time() - start_time},
                client_ip,
                request
            )
            raise

    async def _send_blocked_response(self, scope, receive, send, client_ip: str):
        """Send blocked response for malicious requests"""
        response = JSONResponse(
            status_code=403,
            content={
                "detail": "Access denied due to security policy",
                "incident_id": hashlib.md5(f"{client_ip}:{time.time()}".encode()).hexdigest()[:8]
            }
        )

        # Add security headers
        response.headers.update(self._get_security_headers_dict())

        await response(scope, receive, send)

    def _enhance_security_headers(self, headers: List[Tuple[bytes, bytes]]) -> List[Tuple[bytes, bytes]]:
        """Add comprehensive security headers"""
        security_headers = self._get_security_headers_dict()

        # Convert to bytes and add to existing headers
        enhanced_headers = list(headers)
        for header_name, header_value in security_headers.items():
            enhanced_headers.append((header_name.encode(), header_value.encode()))

        return enhanced_headers

    def _get_security_headers_dict(self) -> Dict[str, str]:
        """Get comprehensive security headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "media-src 'self'; "
                "object-src 'none'; "
                "child-src 'none'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "magnetometer=(), gyroscope=(), speaker=(), "
                "fullscreen=(), payment=()"
            ),
            "X-Permitted-Cross-Domain-Policies": "none",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            "X-DNS-Prefetch-Control": "off",
            "X-Download-Options": "noopen"
        }

# Global instances
threat_intel = ThreatIntelligence()
security_middleware = AdvancedSecurityMiddleware(None)
event_logger = SecurityEventLogger()
