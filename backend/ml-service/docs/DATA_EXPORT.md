# Data Export Functionality Documentation

## Overview
The IIT ML Service provides data export functionality for patients, predictions, and reports.

## Export Endpoints

### 1. Export Patients
```http
GET /analytics/export/csv?data_type=patients&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <token>
```

**Response:**
```json
{
  "filename": "patients_export_20240131_123456.csv",
  "content_type": "text/csv",
  "record_count": 150,
  "generated_at": "2024-01-24T12:00:00Z"
}
```

### 2. Export Predictions
```http
GET /analytics/export/csv?data_type=predictions&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <token>
```

**Response:**
```json
{
  "filename": "predictions_export_20240131_123456.csv",
  "content_type": "text/csv",
  "record_count": 500,
  "generated_at": "2024-01-24T12:00:00Z"
}
```

### 3. Export Observations
```http
GET /analytics/export/csv?data_type=observations&patient_uuid=<uuid>
Authorization: Bearer <token>
```

### 4. Export Risk Distribution Report
```http
GET /analytics/export/csv?data_type=risk_distribution&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <token>
```

### 5. Export Model Performance
```http
GET /analytics/export/csv?data_type=model_performance
Authorization: Bearer <token>
```

## CSV Format

### Patients Export
| Column | Description |
|---------|-------------|---------|
| patient_uuid | Unique patient identifier |
| datim_id | DATIM identifier |
| pepfar_id | PEPFAR identifier |
| first_name | Patient's first name |
| surname | Patient's surname |
| gender | M/F |
| date_of_birth | YYYY-MM-DD format |
| state_province | State/Province |
| lga | Local Government Area |
| phone_number | Phone number |
| created_at | Record creation timestamp |

### Predictions Export
| Column | Description |
|---------|-------------|---------|
| patient_uuid | Patient UUID |
| risk_level | Risk level (high/medium/low) |
| prediction_score | Risk score (0.0-1.0) |
| confidence | Confidence score (0.0-1.0) |
| prediction_timestamp | When prediction was made |
| model_version | Model version used |

### Observations Export
| Column | Description |
|---------|-------------|---------|
| obs_uuid | Observation UUID |
| patient_uuid | Patient UUID |
| encounter_id | Encounter UUID |
| concept_id | Observation concept code |
| variable_name | Observation variable name |
| value_numeric | Numeric value (if applicable) |
| value_text | Text value (if applicable) |
| obs_datetime | When observation was recorded |

## Implementation Details

### Backend Implementation
File: [`app/api/analytics.py`](app/api/analytics.py)

The `/export/csv` endpoint:
- Accepts `data_type` parameter (patients, predictions, observations, risk_distribution, model_performance)
- Returns CSV content as string
- Sets appropriate filename with timestamp
- Uses Python `csv` module for CSV generation
- Filters by date range if provided
- Includes all relevant fields for each data type

### Frontend Integration

To use the export functionality from frontend:

```javascript
// Export patients
async function exportPatients(startDate, endDate) {
  const response = await fetch('/analytics/export/csv?data_type=patients&start_date=${startDate}&end_date=${endDate}', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'patients_export.csv';
  document.body = blob;
  link.click();
}

// Export predictions
async function exportPredictions(startDate, endDate) {
  const response = await fetch('/analytics/export/csv?data_type=predictions&start_date=${startDate}&end_date=${endDate}', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'predictions_export.csv';
  document.body = blob;
  link.click();
}
```

## Best Practices

### 1. Large Exports
- Use streaming for very large datasets (>10,000 records)
- Implement background job for long-running exports
- Send email notification when export is complete

### 2. Date Range Limit
- Maximum date range is 1 year (365 days)
- For larger datasets, consider implementing pagination

### 3. Security
- All exports require authentication
- Export logs track who exported what
- Consider implementing download logging

### 4. Error Handling
- Handle database connection errors gracefully
- Return appropriate HTTP status codes
- Log export failures for troubleshooting

## Troubleshooting

### Export Returns Empty File
**Problem:** Export returns empty CSV

**Solutions:**
1. Check date range includes data
2. Verify database has records in range
3. Check user has export permissions

### Export Fails to Start
**Problem:** Download doesn't start

**Solutions:**
1. Check browser allows downloads
2. Check network connectivity
3. Try smaller date range first
4. Contact support if issue persists

### Export Fails Partway Through
**Problem:** CSV is incomplete

**Solutions:**
1. This is expected for large datasets
2. Check if export completed in background
3. Monitor network connection
4. Try again if interrupted

## Usage Examples

### Command Line (curl)
```bash
# Export patients for January 2024
curl -G "patients_export_2024_01_31_123456.csv" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  "http://localhost:8000/analytics/export/csv?data_type=patients&start_date=2024-01-01&end_date=2024-01-31"
```

### Python Script
```python
import requests

# Export patients
token = "your_access_token"
url = "http://localhost:8000/analytics/export/csv?data_type=patients&start_date=2024-01-01&end_date=2024-01-31"
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(url, headers=headers)
with open("patients_export.csv", "wb") as f:
    f.write(response.content)
```

## Monitoring

### Export Metrics
Track the following metrics:
- Number of exports per day
- Total records exported
- Average export time
- Failed exports count
- Export success rate

### Logs
All export attempts are logged with:
- User who requested
- Data type requested
- Date range
- Record count
- Success/failure status
- Timestamp
