# API Usage Guide

## Overview
This guide provides comprehensive documentation for using the IIT ML Service API.

## Base URL
```
Development: http://localhost:8000
Production: https://api.yourdomain.com
```

## Authentication

### Login
```http
POST /v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token
Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### Refresh Token
```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "<refresh_token>"
}
```

## API Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-24T12:00:00Z"
}
```

### Patients

#### List Patients
```http
GET /v1/patients?page=1&limit=10&search=john
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)
- `search` - Search term for name or ID

**Response:**
```json
{
  "patients": [
    {
      "patient_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "datim_id": "DATIM-12345",
      "pepfar_id": "PEPFAR-67890",
      "first_name": "John",
      "surname": "Doe",
      "gender": "M",
      "date_of_birth": "1985-05-15",
      "state_province": "Lagos",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 10
}
```

#### Get Patient Details
```http
GET /v1/patients/{patient_uuid}
Authorization: Bearer <token>
```

#### Create Patient
```http
POST /v1/patients
Content-Type: application/json
Authorization: Bearer <token>

{
  "datim_id": "DATIM-12345",
  "pepfar_id": "PEPFAR-67890",
  "hospital_number": "HOSP-001",
  "first_name": "John",
  "surname": "Doe",
  "gender": "M",
  "date_of_birth": "1985-05-15",
  "phone_number": "+234801234567",
  "state_province": "Lagos",
  "lga": "Ikeja",
  "ward": "Ojodu"
}
```

### Observations

#### List Observations
```http
GET /v1/observations?patient_uuid={uuid}&variable_name=ARV_Dispensed
Authorization: Bearer <token>
```

**Query Parameters:**
- `patient_uuid` - Filter by patient
- `variable_name` - Filter by observation type
- `start_date` - Filter observations after date
- `end_date` - Filter observations before date
- `limit` - Max results (default: 100)

#### Create Observation
```http
POST /v1/observations
Content-Type: application/json
Authorization: Bearer <token>

{
  "patient_uuid": "550e8400-e29b-41d4-a716-4466554400000",
  "variable_name": "ARV_Dispensed",
  "value_numeric": 30,
  "value_text": null,
  "obs_datetime": "2024-01-15T10:00:00Z",
  "encounter_id": "enc-123"
}
```

### Predictions

#### Get Prediction for Patient
```http
GET /v1/predictions/patient/{patient_uuid}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "patient_uuid": "550e8400-e29b-41d4-a716-4466554400000",
  "risk_level": "high",
  "prediction_score": 0.85,
  "probability": 85,
  "confidence": "high",
  "prediction_timestamp": "2024-01-24T12:00:00Z",
  "model_version": "4.5.0",
  "factors": [
    {"name": "missed_appointments", "value": true, "impact": 0.3},
    {"name": "low_cd4_count", "value": 150, "impact": 0.25},
    {"name": "age_group", "value": "35-44", "impact": 0.2}
  ]
}
```

#### Batch Predictions
```http
POST /v1/predictions/batch
Content-Type: application/json
Authorization: Bearer <token>

{
  "patient_uuids": [
    "550e8400-e29b-41d4-a716-4466554400000",
    "550e8400-e29b-41d4-a716-4466554400001"
  ]
}
```

**Response:**
```json
{
  "predictions": [
    {
      "patient_uuid": "550e8400-e29b-41d4-a716-4466554400000",
      "risk_level": "high",
      "prediction_score": 0.85
    },
    {
      "patient_uuid": "550e8400-e29b-41d4-a716-4466554400001",
      "risk_level": "low",
      "prediction_score": 0.15
    }
  ],
  "total": 2,
  "processed_at": "2024-01-24T12:00:00Z"
}
```

### Visits

#### List Visits
```http
GET /v1/visits?patient_uuid={uuid}
Authorization: Bearer <token>
```

#### Create Visit
```http
POST /v1/visits
Content-Type: application/json
Authorization: Bearer <token>

{
  "patient_uuid": "550e8400-e29b-41d4-a716-4466554400000",
  "date_started": "2024-01-15T10:00:00Z",
  "date_ended": "2024-01-15T11:00:00Z",
  "visit_type": "routine",
  "facility_id": "FAC-001"
}
```

### Analytics

#### Risk Distribution
```http
GET /v1/analytics/risk-distribution?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <token>
```

**Response:**
```json
{
  "period": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z"
  },
  "distribution": {
    "high": 45,
    "medium": 78,
    "low": 127
  },
  "total": 250
}
```

#### Trend Analysis
```http
GET /v1/analytics/trends?metric=iit_risk&period=30d
Authorization: Bearer <token>
```

### Security

#### Get Security Config
```http
GET /v1/security/config
Authorization: Bearer <token>
```

#### Get Audit Logs
```http
GET /v1/security/audit-logs?limit=100&offset=0&severity=high
Authorization: Bearer <token>
```

## Error Handling

### Error Response Format
```json
{
  "detail": "Error message here",
  "status_code": 400,
  "timestamp": "2024-01-24T12:00:00Z"
}
```

### Common HTTP Status Codes
| Code | Meaning |
|-------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default Limit**: 100 requests per minute
- **Headers**: Check `X-RateLimit-Limit` and `X-RateLimit-Remaining`
- **Retry-After**: Returned in seconds when limit exceeded

## Pagination

List endpoints support pagination:

```http
GET /v1/patients?page=2&limit=20
```

**Response Headers:**
- `X-Total-Count`: Total items available
- `X-Page-Count`: Total pages
- `X-Current-Page`: Current page number

## Filtering and Sorting

### Filtering
```http
GET /v1/observations?patient_uuid={uuid}&variable_name=ARV_Dispensed&start_date=2024-01-01
```

### Sorting
```http
GET /v1/patients?sort_by=created_at&sort_order=desc
```

## Webhooks

### Configure Webhook
```http
POST /v1/webhooks
Content-Type: application/json
Authorization: Bearer <token>

{
  "url": "https://your-domain.com/webhook",
  "events": ["prediction.created", "patient.updated"],
  "secret": "your_webhook_secret"
}
```

## SDK Examples

### Python
```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/v1/auth/login",
    json={"username": "admin", "password": "secure_password"}
)
token = response.json()["access_token"]

# Get patients
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8000/v1/patients",
    headers=headers
)
patients = response.json()["patients"]
```

### JavaScript
```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/v1/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    username: 'admin',
    password: 'secure_password'
  })
});
const { access_token } = await loginResponse.json();

// Get patients
const patientsResponse = await fetch('http://localhost:8000/v1/patients', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
const { patients } = await patientsResponse.json();
```

## Testing

### Interactive API Documentation
Visit: `http://localhost:8000/docs`

### Example cURL Commands
```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure_password"}'

# Get patients
curl http://localhost:8000/v1/patients \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Create patient
curl -X POST http://localhost:8000/v1/patients \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"John","surname":"Doe","gender":"M"}'
```

## Best Practices

1. **Use HTTPS in production**
2. **Implement proper error handling**
3. **Cache responses when appropriate**
4. **Use pagination for large datasets**
5. **Implement retry logic for transient failures**
6. **Monitor rate limits**
7. **Validate input data before sending**
8. **Use appropriate HTTP methods** (GET for read, POST for create)
9. **Include timestamps for debugging**
10. **Log API calls for troubleshooting**

## Support

For API support and questions:
- Documentation: `http://localhost:8000/docs`
- Status Page: `http://localhost:8000/health`
- Email: support@yourdomain.com
