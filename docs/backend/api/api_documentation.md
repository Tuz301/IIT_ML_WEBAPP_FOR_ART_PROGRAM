# IIT ML Service API Documentation

## Overview

The IIT ML Service provides RESTful APIs for IIT (Interruption in Treatment) risk prediction, patient management, and analytics. This document describes all available endpoints, request/response formats, and usage examples.

## Table of Contents

1. [Authentication](#authentication)
2. [Patient Management](#patient-management)
3. [Prediction APIs](#prediction-apis)
4. [Analytics and Reporting](#analytics-and-reporting)
5. [Model Management](#model-management)
6. [System Health](#system-health)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)
9. [API Versions](#api-versions)

## Authentication

All API requests require authentication using API keys or JWT tokens.

### API Key Authentication

```bash
curl -X GET "https://api.iit-ml-service.com/patients" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json"
```

### JWT Token Authentication

```bash
curl -X GET "https://api.iit-ml-service.com/patients" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json"
```

### Obtaining API Keys

Contact the system administrator to obtain API keys for your application.

## Patient Management

### Create Patient

Create a new patient record.

```http
POST /api/v1/patients
```

**Request Body:**
```json
{
  "datim_id": "string",
  "pepfar_id": "string",
  "given_name": "John",
  "family_name": "Doe",
  "birthdate": "1990-01-01",
  "gender": "M",
  "state_province": "Lagos",
  "city_village": "Ikeja",
  "phone_number": "+2348012345678"
}
```

**Response (201 Created):**
```json
{
  "patient_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "datim_id": "string",
  "pepfar_id": "string",
  "given_name": "John",
  "family_name": "Doe",
  "birthdate": "1990-01-01",
  "gender": "M",
  "state_province": "Lagos",
  "city_village": "Ikeja",
  "phone_number": "+2348012345678",
  "phone_present": true,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### Get Patient

Retrieve patient information by UUID.

```http
GET /api/v1/patients/{patient_uuid}
```

**Response (200 OK):**
```json
{
  "patient_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "datim_id": "string",
  "pepfar_id": "string",
  "given_name": "John",
  "family_name": "Doe",
  "birthdate": "1990-01-01",
  "gender": "M",
  "state_province": "Lagos",
  "city_village": "Ikeja",
  "phone_number": "+2348012345678",
  "phone_present": true,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z",
  "iit_features": {
    "days_since_last_visit": 30,
    "visit_frequency": 0.8,
    "medication_adherence": 0.9,
    "last_cd4_count": 450,
    "viral_load_status": "suppressed"
  },
  "latest_prediction": {
    "prediction_id": "pred_123",
    "iit_risk_score": 0.25,
    "iit_risk_level": "LOW",
    "created_at": "2024-01-01T10:00:00Z"
  }
}
```

### Update Patient

Update patient information.

```http
PUT /api/v1/patients/{patient_uuid}
```

**Request Body:**
```json
{
  "phone_number": "+2348012345679",
  "state_province": "Abuja"
}
```

### List Patients

Retrieve a paginated list of patients.

```http
GET /api/v1/patients?page=1&per_page=50&state=Lagos&risk_level=HIGH
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 50, max: 100)
- `state`: Filter by state/province
- `risk_level`: Filter by IIT risk level (LOW, MEDIUM, HIGH)
- `created_after`: Filter patients created after date (ISO 8601)
- `phone_present`: Filter by phone presence (true/false)

**Response (200 OK):**
```json
{
  "patients": [
    {
      "patient_uuid": "123e4567-e89b-12d3-a456-426614174000",
      "given_name": "John",
      "family_name": "Doe",
      "state_province": "Lagos",
      "latest_risk_score": 0.25,
      "latest_risk_level": "LOW",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 1250,
    "total_pages": 25,
    "has_next": true,
    "has_prev": false
  }
}
```

## Prediction APIs

### Single Prediction

Generate IIT risk prediction for a single patient.

```http
POST /api/v1/predictions
```

**Request Body:**
```json
{
  "patient_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "features": {
    "age": 34,
    "bmi": 22.5,
    "days_since_last_visit": 45,
    "visit_frequency": 0.7,
    "medication_adherence": 0.8,
    "last_cd4_count": 380,
    "viral_load_status": "unsuppressed",
    "regimen_type": "TLD",
    "time_on_art": 24,
    "previous_iit_episodes": 1,
    "social_support_score": 7,
    "distance_to_clinic": 15.5,
    "stigma_score": 3,
    "mental_health_score": 8,
    "substance_use": false,
    "unstable_housing": false,
    "food_insecurity": true,
    "transportation_issues": false
  },
  "model_version": "v2.1",
  "include_explanation": true
}
```

**Response (200 OK):**
```json
{
  "prediction_id": "pred_123456789",
  "patient_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "model_version": "v2.1",
  "iit_risk_score": 0.75,
  "iit_risk_level": "HIGH",
  "confidence_score": 0.85,
  "features_used": {
    "age": 34,
    "bmi": 22.5,
    "days_since_last_visit": 45
  },
  "explanation": {
    "top_positive_factors": [
      {"feature": "days_since_last_visit", "contribution": 0.35, "description": "Long time since last visit increases risk"},
      {"feature": "medication_adherence", "contribution": 0.25, "description": "Low medication adherence is concerning"}
    ],
    "top_negative_factors": [
      {"feature": "social_support_score", "contribution": -0.15, "description": "Good social support reduces risk"},
      {"feature": "mental_health_score", "contribution": -0.10, "description": "Good mental health reduces risk"}
    ],
    "summary": "High risk due to missed visits and poor medication adherence, despite good social support"
  },
  "created_at": "2024-01-01T10:00:00Z"
}
```

### Batch Predictions

Generate predictions for multiple patients.

```http
POST /api/v1/predictions/batch
```

**Request Body:**
```json
{
  "predictions": [
    {
      "patient_uuid": "123e4567-e89b-12d3-a456-426614174000",
      "features": { /* feature object */ }
    },
    {
      "patient_uuid": "456e7890-e89b-12d3-a456-426614174001",
      "features": { /* feature object */ }
    }
  ],
  "model_version": "v2.1"
}
```

**Response (200 OK):**
```json
{
  "batch_id": "batch_123456789",
  "predictions": [
    {
      "prediction_id": "pred_123",
      "patient_uuid": "123e4567-e89b-12d3-a456-426614174000",
      "iit_risk_score": 0.75,
      "iit_risk_level": "HIGH",
      "confidence_score": 0.85
    },
    {
      "prediction_id": "pred_124",
      "patient_uuid": "456e7890-e89b-12d3-a456-426614174001",
      "iit_risk_score": 0.25,
      "iit_risk_level": "LOW",
      "confidence_score": 0.90
    }
  ],
  "processing_time": 2.34,
  "created_at": "2024-01-01T10:00:00Z"
}
```

### Get Prediction History

Retrieve prediction history for a patient.

```http
GET /api/v1/patients/{patient_uuid}/predictions?page=1&per_page=20
```

**Response (200 OK):**
```json
{
  "predictions": [
    {
      "prediction_id": "pred_123",
      "model_version": "v2.1",
      "iit_risk_score": 0.75,
      "iit_risk_level": "HIGH",
      "confidence_score": 0.85,
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

## Analytics and Reporting

### Risk Distribution Report

Get IIT risk distribution across patients.

```http
GET /api/v1/analytics/risk-distribution?state=Lagos&date_from=2024-01-01&date_to=2024-01-31
```

**Response (200 OK):**
```json
{
  "total_patients": 1250,
  "risk_distribution": {
    "LOW": {"count": 625, "percentage": 50.0},
    "MEDIUM": {"count": 375, "percentage": 30.0},
    "HIGH": {"count": 250, "percentage": 20.0}
  },
  "trends": {
    "high_risk_increase": 5.2,
    "period": "2024-01-01 to 2024-01-31"
  },
  "generated_at": "2024-01-31T23:59:59Z"
}
```

### Model Performance Metrics

Get model performance metrics and drift detection.

```http
GET /api/v1/analytics/model-performance?model_version=v2.1&period=30d
```

**Response (200 OK):**
```json
{
  "model_version": "v2.1",
  "metrics": {
    "accuracy": 0.87,
    "precision": 0.82,
    "recall": 0.79,
    "f1_score": 0.80,
    "auc_roc": 0.91
  },
  "drift_detection": {
    "feature_drift_detected": false,
    "prediction_drift_detected": true,
    "drift_score": 0.15,
    "last_calculated": "2024-01-31T12:00:00Z"
  },
  "performance_trend": [
    {"date": "2024-01-01", "accuracy": 0.88},
    {"date": "2024-01-15", "accuracy": 0.86},
    {"date": "2024-01-31", "accuracy": 0.87}
  ]
}
```

### Generate PDF Report

Generate and download a PDF report.

```http
POST /api/v1/reports/generate
```

**Request Body:**
```json
{
  "report_type": "monthly_risk_summary",
  "parameters": {
    "state": "Lagos",
    "month": "2024-01",
    "include_charts": true,
    "include_trends": true
  },
  "format": "pdf"
}
```

**Response (200 OK):**
```json
{
  "report_id": "report_123456789",
  "status": "processing",
  "download_url": "https://api.iit-ml-service.com/reports/download/report_123456789",
  "estimated_completion": "2024-01-01T10:05:00Z"
}
```

### Scheduled Reports

Configure automated report delivery.

```http
POST /api/v1/reports/scheduled
```

**Request Body:**
```json
{
  "name": "Weekly Risk Summary",
  "report_type": "weekly_risk_summary",
  "schedule": "0 9 * * 1",  // Every Monday at 9 AM
  "recipients": ["admin@ihvnigeria.org", "manager@ihvnigeria.org"],
  "parameters": {
    "include_states": ["Lagos", "Abuja", "Kano"],
    "format": "pdf"
  }
}
```

## Model Management

### List Available Models

Get list of available model versions.

```http
GET /api/v1/models
```

**Response (200 OK):**
```json
{
  "models": [
    {
      "model_id": "iit_lightgbm_v2.1",
      "version": "v2.1",
      "algorithm": "LightGBM",
      "is_active": true,
      "performance_metrics": {
        "accuracy": 0.87,
        "auc_roc": 0.91
      },
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Model Comparison

Compare performance of different models.

```http
POST /api/v1/models/compare
```

**Request Body:**
```json
{
  "model_ids": ["iit_lightgbm_v2.0", "iit_lightgbm_v2.1"],
  "test_dataset": "validation_2024",
  "metrics": ["accuracy", "precision", "recall", "auc_roc"]
}
```

**Response (200 OK):**
```json
{
  "comparison_id": "comp_123456789",
  "models_compared": ["iit_lightgbm_v2.0", "iit_lightgbm_v2.1"],
  "results": {
    "iit_lightgbm_v2.0": {
      "accuracy": 0.85,
      "precision": 0.80,
      "recall": 0.75,
      "auc_roc": 0.89
    },
    "iit_lightgbm_v2.1": {
      "accuracy": 0.87,
      "precision": 0.82,
      "recall": 0.79,
      "auc_roc": 0.91
    }
  },
  "recommendation": "v2.1 shows better performance across all metrics",
  "created_at": "2024-01-01T10:00:00Z"
}
```

## System Health

### Health Check

Basic health check endpoint.

```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2024-01-01T10:00:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "model": "healthy"
  }
}
```

### Detailed Health Check

Comprehensive system health information.

```http
GET /health/detailed
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "uptime": "30d 4h 15m",
  "timestamp": "2024-01-01T10:00:00Z",
  "services": {
    "database": {
      "status": "healthy",
      "response_time": 15,
      "connection_pool": {
        "active": 5,
        "available": 20,
        "size": 25
      }
    },
    "redis": {
      "status": "healthy",
      "response_time": 2,
      "memory_usage": "45MB",
      "hit_rate": 0.92
    },
    "model": {
      "status": "healthy",
      "model_version": "v2.1",
      "last_loaded": "2024-01-01T08:00:00Z"
    }
  },
  "system": {
    "cpu_usage": 35.2,
    "memory_usage": 2.1,
    "disk_usage": 45.8
  }
}
```

### Metrics Endpoint

Prometheus-compatible metrics.

```http
GET /metrics
```

**Response (200 OK):**
```
# HELP iit_api_requests_total Total number of API requests
# TYPE iit_api_requests_total counter
iit_api_requests_total{method="GET",endpoint="/patients",status="200"} 12543

# HELP iit_prediction_duration_seconds Time spent processing predictions
# TYPE iit_prediction_duration_seconds histogram
iit_prediction_duration_seconds_bucket{le="0.1"} 1234
iit_prediction_duration_seconds_bucket{le="0.5"} 5678
iit_prediction_duration_seconds_bucket{le="1.0"} 7890
```

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "birthdate",
      "issue": "Date must be in the past"
    }
  },
  "request_id": "req_123456789",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `AUTHENTICATION_ERROR` | 401 | Invalid or missing credentials |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### Validation Errors

Detailed validation error example:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Multiple validation errors",
    "details": [
      {
        "field": "birthdate",
        "issue": "Date must be in the past",
        "value": "2030-01-01"
      },
      {
        "field": "gender",
        "issue": "Must be one of: M, F, MALE, FEMALE",
        "value": "OTHER"
      }
    ]
  }
}
```

## Rate Limiting

API requests are rate limited to ensure fair usage.

### Rate Limits

- **Authenticated requests:** 1000 requests per hour per API key
- **Prediction endpoints:** 100 predictions per minute per API key
- **Batch predictions:** 10 batch requests per minute per API key
- **Analytics endpoints:** 100 requests per hour per API key

### Rate Limit Headers

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 3600
```

### Rate Limit Exceeded Response

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 1000,
      "remaining": 0,
      "reset_time": "2024-01-01T11:00:00Z",
      "retry_after": 3600
    }
  }
}
```

## API Versions

### Versioning Strategy

API versions follow semantic versioning (MAJOR.MINOR.PATCH).

- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes (backward compatible)

### Current Versions

- **v1.0.0:** Initial release (deprecated)
- **v1.1.0:** Added batch predictions
- **v1.2.0:** Added explainability features
- **v2.0.0:** Major rewrite with improved architecture
- **v2.1.0:** Current version with ensemble methods

### Version Headers

Specify API version in request headers:

```bash
curl -X GET "https://api.iit-ml-service.com/patients" \
  -H "Accept-Version: v2.1" \
  -H "X-API-Key: your-api-key"
```

### Deprecation Policy

- Versions are supported for 12 months after a new major version release
- Deprecated versions return a deprecation warning header
- Breaking changes are communicated 3 months in advance

## SDKs and Libraries

### Python SDK

```python
from iit_ml_client import IITMLClient

client = IITMLClient(api_key="your-api-key")

# Create patient
patient = client.patients.create({
    "given_name": "John",
    "family_name": "Doe",
    "birthdate": "1990-01-01"
})

# Generate prediction
prediction = client.predictions.create({
    "patient_uuid": patient["patient_uuid"],
    "features": {
        "age": 34,
        "days_since_last_visit": 45,
        # ... other features
    }
})

print(f"Risk score: {prediction['iit_risk_score']}")
```

### JavaScript SDK

```javascript
import { IITMLClient } from 'iit-ml-sdk';

const client = new IITMLClient({
  apiKey: 'your-api-key',
  baseURL: 'https://api.iit-ml-service.com'
});

// Get patient list
const patients = await client.patients.list({
  page: 1,
  perPage: 50,
  riskLevel: 'HIGH'
});

console.log(`Found ${patients.total} high-risk patients`);
```

## Support

### Getting Help

- **Documentation:** https://docs.iit-ml-service.com
- **API Reference:** https://api.iit-ml-service.com/docs
- **Support Email:** api-support@ihvnigeria.org
- **Issue Tracker:** https://github.com/ihvnigeria/iit-ml-service/issues

### Service Level Agreement

- **Uptime:** 99.9% availability
- **Response Time:** P95 < 500ms for predictions
- **Support Response:** Within 4 hours for critical issues
- **API Compatibility:** 12 months for major versions

## Changelog

### v2.1.0 (Current)
- Added ensemble prediction methods
- Improved explainability features
- Enhanced analytics dashboard
- Added scheduled reporting

### v2.0.0
- Complete API redesign
- Added JWT authentication
- Improved error handling
- Added comprehensive health checks

### v1.2.0
- Added prediction explanations
- Enhanced batch processing
- Added model performance monitoring

### v1.1.0
- Added batch prediction endpoint
- Improved pagination
- Added filtering capabilities

### v1.0.0
- Initial API release
- Basic patient management
- Single prediction endpoint
- Simple analytics
