# User Training Materials

## Overview
This document provides training materials for users of the IIT ML Service.

## Quick Start Guide

### 1. Access the Application
- Open browser and navigate to: `http://localhost:3000` (Grafana)
- Login with your credentials
- Navigate to the application

### 2. View the Dashboard
- Click on "Dashboard" in the main menu
- Review patient data and predictions
- Check system health and performance metrics

### 3. Make a Prediction
- Click on "New Prediction" in the main menu
- Select a patient from the list
- Fill in the prediction form with required fields
- Click "Submit" to get risk assessment

### 4. View Reports
- Click on "Reports" in the main menu
- Select report type (Risk Distribution, Patient Summary, Model Performance)
- Configure filters (date range, risk level, location)
- Click "Generate Report"

## Patient Management

### Adding a New Patient

1. Navigate to **Patients** section
2. Click **"Add Patient"** button
3. Fill in the form:
   - **Demographics:**
     - First Name (required)
     - Surname (required)
     - Date of Birth (required)
     - Gender (required)
     - State/Province (required)
     - LGA (required)
     - Phone Number (optional)
     - DATIM ID (optional)
     - PEPFAR ID (optional)
     - Hospital Number (optional)

   - **Contact Information:**
     - Email (optional)
     - Emergency Contact (optional)

   - **Medical Information:**
     - HIV Status (required)
     - Enrollment Date (optional)
     - ART Start Date (optional)
     - Current Regimen (optional)
     - Last Viral Load (optional)

4. Click **"Save Patient"** button

### Updating Patient Information

1. Click on a patient from the list
2. Click **"Edit Patient"** button
3. Make necessary changes
4. Click **"Save"** to persist changes

### Viewing Patient Details

1. Click on a patient's name or ID
2. View their complete profile including:
   - Demographics
   - Medical history
   - Treatment history
   - Predictions history
   - Observations
   - Visits
   - Risk factors

### Deleting a Patient

1. Click on the patient
2. Click **"Delete"** button
3. Confirm the deletion

## Prediction Interpretation

### Risk Levels

| Risk Level | Score Range | Description | Action |
|-----------|-----------|-------------|--------|
| **High Risk** | 0.75 - 1.00 | Immediate intervention required, high priority follow-up |
| **Medium Risk** | 0.50 - 0.74 | Schedule follow-up, consider adherence counseling |
| **Low Risk** | 0.25 - 0.49 | Routine monitoring, regular check-ups recommended |

### Risk Factors

The ML model considers these factors when calculating risk:

| Factor | Impact | Weight | Description |
|---------|--------|---------|--------|
| Missed Appointments | High | 0.30 | Patient missed 3+ appointments increases IIT risk significantly |
| Low CD4 Count | High | 0.25 | CD4 count < 200 indicates poor adherence |
| High Viral Load | Medium | 0.20 | Viral load > 1000 copies/mL increases transmission risk |
| No Recent Visits | Medium | 0.15 | No visits in 90+ days suggests patient disengaged |
| Young Age | Low | 0.10 | Age 18-35 has higher IIT risk than older patients |
| Male Gender | Low | 0.05 | Slight male bias in risk model |
| Urban Location | Medium | 0.10 | Urban areas may have different risk profiles |

### Model Performance Metrics

| Metric | Good | Warning | Action |
|-----------|-----------|--------|
| AUC Score | > 0.85 | Excellent | Monitor for model drift |
| Precision | > 0.80 | Good | Review false positive/negative balance |
| Recall | > 0.75 | Good | Review class distribution |
| F1 Score | > 0.75 | Good | Review false positive rate |
| Brier Score | < 0.20 | Good | Review calibration |

## Data Entry Best Practices

### 1. Use Standard Formats
- Enter dates in YYYY-MM-DD format
- Use proper case for gender (M/F instead of m/f)
- Use standard state codes for locations

### 2. Validate Before Saving
- Check all required fields are filled
- Verify phone numbers are valid format
- Ensure dates are not in the future

### 3. Data Quality
- Check for duplicate records before creating
- Verify relationships (observations linked to encounters)
- Ensure patient UUIDs are consistent

### 4. Security
- Follow HIPAA guidelines for patient data
- Use role-based access control
- Log all data access and modifications

## Troubleshooting

### Common Issues

#### Patient Not Found
- Check patient list filters
- Verify correct UUID format
- Check if patient exists in database

#### Prediction Not Working
- Verify model is loaded: Check `/health` endpoint
- Check feature store has patient data
- Review model version in use

#### Reports Not Generating
- Check date range filters
- Verify database connectivity
- Review server logs for errors

## Support Resources

### Documentation Links
- API Usage Guide: [`docs/API_USAGE_GUIDE.md`](docs/API_USAGE_GUIDE.md)
- Cloud Deployment Guide: [`docs/CLOUD_DEPLOYMENT.md`](docs/CLOUD_DEPLOYMENT.md)
- Grafana Setup Guide: [`monitoring/GRAFANA_SETUP.md`](monitoring/GRAFANA_SETUP.md)
- Post-Launch Monitoring: [`docs/POST_LAUNCH_MONITORING.md`](docs/POST_LAUNCH_MONITORING.md)

### Getting Help
- Contact system administrator
- Review this documentation
- Check application logs for specific errors
