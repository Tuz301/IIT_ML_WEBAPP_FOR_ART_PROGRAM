"""
Data validation middleware for IIT ML Service
Provides comprehensive input validation and sanitization
"""
import logging
import re
from typing import Dict, Any, List, Optional, Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ValidationMiddleware:
    """
    Comprehensive validation middleware for request/response validation
    """

    def __init__(self, app, exclude_paths: List[str] = None):
        self.app = app
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json", "/v1/auth", "/v1/patients", "/v1/predictions", "/v1/observations", "/v1/visits", "/v1/features", "/v1/analytics", "/v1/etl", "/v1/cache", "/v1/backup", "/v1/security", "/v1/explainability", "/v1/ensemble"]

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

        request = Request(scope, receive_wrapper)

        # Skip validation for excluded paths
        if any(path in request.url.path for path in self.exclude_paths):
            await self.app(scope, receive_wrapper, send)
            return

        # Validate request
        validation_errors = await self._validate_request(request)
        if validation_errors:
            response = JSONResponse(
                status_code=422,
                content={
                    "error": "Request validation failed",
                    "details": validation_errors,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            await response(scope, receive_wrapper, send)
            return

        # Process request and validate response
        await self.app(scope, receive_wrapper, send)


    async def _validate_request(self, request: Request) -> List[Dict[str, Any]]:
        """
        Validate incoming request data

        Args:
            request: FastAPI request object

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Get request body for validation
            body = await request.body()

            if body:
                # Parse JSON if content type is application/json
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        json_data = json.loads(body.decode())
                        errors.extend(self._validate_json_data(json_data, request.url.path))
                    except json.JSONDecodeError as e:
                        errors.append({
                            "field": "body",
                            "error": "Invalid JSON format",
                            "details": str(e)
                        })

                # Validate query parameters
                errors.extend(self._validate_query_params(dict(request.query_params)))

                # Validate headers
                errors.extend(self._validate_headers(dict(request.headers)))

            # Validate path parameters
            errors.extend(self._validate_path_params(request.path_params))

        except Exception as e:
            logger.error(f"Request validation error: {str(e)}")
            errors.append({
                "field": "request",
                "error": "Validation processing failed",
                "details": str(e)
            })

        return errors

    def _validate_json_data(self, data: Dict[str, Any], path: str) -> List[Dict[str, Any]]:
        """
        Validate JSON data based on endpoint requirements

        Args:
            data: Parsed JSON data
            path: Request path

        Returns:
            List of validation errors
        """
        errors = []

        # Common validations for all endpoints
        errors.extend(self._validate_common_fields(data))

        # Endpoint-specific validations
        if "/patients" in path:
            errors.extend(self._validate_patient_data(data))
        elif "/predictions" in path:
            errors.extend(self._validate_prediction_data(data))
        elif "/observations" in path:
            errors.extend(self._validate_observation_data(data))
        elif "/analytics" in path:
            errors.extend(self._validate_analytics_data(data))

        return errors

    def _validate_common_fields(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate common fields across all endpoints"""
        errors = []

        # Check for malicious content
        for key, value in data.items():
            if isinstance(value, str):
                # Check for script injection
                if re.search(r'<script[^>]*>.*?</script>', value, re.IGNORECASE | re.DOTALL):
                    errors.append({
                        "field": key,
                        "error": "Potential script injection detected",
                        "value": value[:100] + "..." if len(value) > 100 else value
                    })

                # Check for SQL injection patterns
                sql_patterns = [
                    r"(\b(union|select|insert|update|delete|drop|create|alter)\b)",
                    r"(\bor\b\s+\d+\s*=\s*\d+)",
                    r"(\band\b\s+\d+\s*=\s*\d+)",
                    r"(\bscript\b)",
                    r"(\bon\w+\s*=)",
                ]

                for pattern in sql_patterns:
                    if re.search(pattern, value.lower(), re.IGNORECASE):
                        errors.append({
                            "field": key,
                            "error": f"Potential SQL injection pattern detected: {pattern}",
                            "value": value[:100] + "..." if len(value) > 100 else value
                        })

                # Check string length limits
                if len(value) > 10000:  # 10KB limit
                    errors.append({
                        "field": key,
                        "error": "Field value exceeds maximum length (10KB)",
                        "length": len(value)
                    })

        return errors

    def _validate_patient_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate patient-specific data"""
        errors = []

        # Required fields for patient creation/update (matching PatientCreate schema)
        required_fields = ["given_name", "family_name", "birthdate"]
        for field in required_fields:
            if field not in data:
                errors.append({
                    "field": field,
                    "error": "Required field is missing"
                })

        # Validate date of birth
        if "birthdate" in data:
            try:
                # Handle both string and datetime inputs
                birthdate = data["birthdate"]
                if isinstance(birthdate, str):
                    # Try multiple date formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"]:
                        try:
                            dob = datetime.strptime(birthdate, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError("Invalid date format")
                elif isinstance(birthdate, datetime):
                    dob = birthdate
                else:
                    raise ValueError("Invalid date type")
                    
                if dob > datetime.utcnow():
                    errors.append({
                        "field": "birthdate",
                        "error": "Date of birth cannot be in the future"
                    })
            except ValueError:
                errors.append({
                    "field": "birthdate",
                    "error": "Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)"
                })

        # Validate phone number format
        if "phone" in data:
            phone = data["phone"]
            if not re.match(r'^\+?[\d\s\-\(\)]+$', phone):
                errors.append({
                    "field": "phone",
                    "error": "Invalid phone number format"
                })

        # Validate email format
        if "email" in data:
            email = data["email"]
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                errors.append({
                    "field": "email",
                    "error": "Invalid email format"
                })

        return errors

    def _validate_prediction_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate prediction-specific data"""
        errors = []

        # Validate patient_id
        if "patient_id" in data:
            if not isinstance(data["patient_id"], (int, str)):
                errors.append({
                    "field": "patient_id",
                    "error": "Patient ID must be integer or string"
                })

        # Validate observation data
        if "observations" in data:
            if not isinstance(data["observations"], list):
                errors.append({
                    "field": "observations",
                    "error": "Observations must be a list"
                })
            else:
                for i, obs in enumerate(data["observations"]):
                    if not isinstance(obs, dict):
                        errors.append({
                            "field": f"observations[{i}]",
                            "error": "Each observation must be an object"
                        })
                    elif "type" not in obs or "value" not in obs:
                        errors.append({
                            "field": f"observations[{i}]",
                            "error": "Observation must have 'type' and 'value' fields"
                        })

        return errors

    def _validate_observation_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate observation-specific data"""
        errors = []

        # Required fields
        required_fields = ["patient_id", "observation_type", "value"]
        for field in required_fields:
            if field not in data:
                errors.append({
                    "field": field,
                    "error": f"Required field '{field}' is missing"
                })

        # Validate observation types
        valid_types = [
            "blood_pressure", "heart_rate", "temperature", "weight", "height",
            "bmi", "hemoglobin", "malaria_test", "pregnancy_test", "gestational_age"
        ]

        if "observation_type" in data and data["observation_type"] not in valid_types:
            errors.append({
                "field": "observation_type",
                "error": f"Invalid observation type. Must be one of: {', '.join(valid_types)}"
            })

        # Validate numeric values
        if "value" in data:
            try:
                float(data["value"])
            except (ValueError, TypeError):
                errors.append({
                    "field": "value",
                    "error": "Observation value must be numeric"
                })

        return errors

    def _validate_analytics_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate analytics-specific data"""
        errors = []

        # Validate date ranges
        if "date_from" in data and "date_to" in data:
            try:
                date_from = datetime.fromisoformat(data["date_from"].replace('Z', '+00:00'))
                date_to = datetime.fromisoformat(data["date_to"].replace('Z', '+00:00'))

                if date_from > date_to:
                    errors.append({
                        "field": "date_range",
                        "error": "Start date cannot be after end date"
                    })

                if (date_to - date_from).days > 365:  # Max 1 year range
                    errors.append({
                        "field": "date_range",
                        "error": "Date range cannot exceed 1 year"
                    })

            except ValueError as e:
                errors.append({
                    "field": "date_range",
                    "error": f"Invalid date format: {str(e)}"
                })

        # Validate aggregation levels
        if "aggregation" in data:
            valid_aggs = ["hour", "day", "week", "month", "year"]
            if data["aggregation"] not in valid_aggs:
                errors.append({
                    "field": "aggregation",
                    "error": f"Invalid aggregation level. Must be one of: {', '.join(valid_aggs)}"
                })

        return errors

    def _validate_query_params(self, params: Dict[str, str]) -> List[Dict[str, Any]]:
        """Validate query parameters"""
        errors = []

        # Check for malicious query parameters
        for key, value in params.items():
            # Check for directory traversal
            if ".." in value or "%2e%2e" in value.lower():
                errors.append({
                    "field": f"query.{key}",
                    "error": "Potential directory traversal detected"
                })

            # Check parameter length
            if len(value) > 1000:
                errors.append({
                    "field": f"query.{key}",
                    "error": "Query parameter too long (max 1000 characters)"
                })

        # Validate pagination parameters
        if "page" in params:
            try:
                page = int(params["page"])
                if page < 1:
                    errors.append({
                        "field": "query.page",
                        "error": "Page number must be positive"
                    })
            except ValueError:
                errors.append({
                    "field": "query.page",
                    "error": "Page number must be an integer"
                })

        if "limit" in params:
            try:
                limit = int(params["limit"])
                if limit < 1 or limit > 1000:
                    errors.append({
                        "field": "query.limit",
                        "error": "Limit must be between 1 and 1000"
                    })
            except ValueError:
                errors.append({
                    "field": "query.limit",
                    "error": "Limit must be an integer"
                })

        return errors

    def _validate_headers(self, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Validate request headers"""
        errors = []

        # Check for suspicious headers
        suspicious_headers = [
            "x-forwarded-for", "x-real-ip", "x-client-ip",
            "x-remote-addr", "x-host", "x-forwarded-host"
        ]

        for header in suspicious_headers:
            if header in [h.lower() for h in headers.keys()]:
                # This might be legitimate, so just log it
                logger.warning(f"Suspicious header detected: {header}")

        # Validate content-type for API endpoints
        if "content-type" in headers:
            content_type = headers["content-type"].lower()
            if not any(ct in content_type for ct in ["application/json", "multipart/form-data", "application/x-www-form-urlencoded"]):
                errors.append({
                    "field": "header.content-type",
                    "error": "Unsupported content type"
                })

        return errors

    def _validate_path_params(self, path_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate path parameters"""
        errors = []

        for key, value in path_params.items():
            # Validate ID parameters
            if key.endswith("_id") or key == "id":
                if isinstance(value, str):
                    # Check if it's a valid UUID or integer string
                    if not (value.isdigit() or self._is_valid_uuid(value)):
                        errors.append({
                            "field": f"path.{key}",
                            "error": "Invalid ID format"
                        })

        return errors

    def _is_valid_uuid(self, value: str) -> bool:
        """Check if string is a valid UUID"""
        import uuid
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False


def create_validation_middleware(exclude_paths: List[str] = None) -> Callable:
    """
    Create validation middleware function

    Args:
        exclude_paths: List of paths to exclude from validation

    Returns:
        Middleware function
    """
    async def validation_middleware(request: Request, call_next):
        middleware = ValidationMiddleware(None, exclude_paths)

        # Validate request
        errors = await middleware._validate_request(request)
        if errors:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Request validation failed",
                    "details": errors,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        response = await call_next(request)
        return response

    return validation_middleware
