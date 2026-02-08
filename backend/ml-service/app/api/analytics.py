"""
Analytics API for IIT ML Service
Provides reporting and analytics endpoints
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import io
import csv

from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User, IITPrediction, Patient, Observation
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/risk-distribution", response_model=dict)
async def get_risk_distribution(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get distribution of risk levels across predictions
    """
    try:
        query = db.query(IITPrediction)
        
        if start_date:
            query = query.filter(IITPrediction.prediction_timestamp >= start_date)
        if end_date:
            query = query.filter(IITPrediction.prediction_timestamp <= end_date)
        
        predictions = query.all()
        
        # Count by risk level
        distribution = {
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for pred in predictions:
            risk_level = pred.risk_level or "unknown"
            if risk_level in distribution:
                distribution[risk_level] += 1
        
        total = len(predictions)
        
        return {
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "distribution": distribution,
            "total": total,
            "percentages": {
                k: round((v / total * 100), 2) if total > 0 else 0
                for k, v in distribution.items()
            }
        }
    except Exception as e:
        logger.error(f"Failed to get risk distribution: {str(e)}")
        raise

@router.get("/trends", response_model=dict)
async def get_trends(
    metric: str = Query(..., description="Metric to analyze (iit_risk, prediction_count, patient_count)"),
    period: str = Query("30d", description="Time period (1d, 7d, 30d, 90d)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trends for specified metric over time period
    """
    try:
        # Calculate start date based on period
        period_days = {
            "1d": 1,
            "7d": 7,
            "30d": 30,
            "90d": 90
        }
        days = period_days.get(period, 30)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get data based on metric
        if metric == "iit_risk":
            query = db.query(IITPrediction).filter(
                IITPrediction.prediction_timestamp >= start_date
            )
            predictions = query.all()
            
            # Group by day
            daily_data = {}
            for pred in predictions:
                day = pred.prediction_timestamp.date().isoformat()
                if day not in daily_data:
                    daily_data[day] = {"count": 0, "high_risk": 0, "avg_score": 0, "scores": []}
                daily_data[day]["count"] += 1
                daily_data[day]["scores"].append(pred.prediction_score or 0)
                if pred.risk_level == "high":
                    daily_data[day]["high_risk"] += 1
            
            # Calculate averages
            result = []
            for date_str, data in sorted(daily_data.items()):
                avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
                result.append({
                    "date": date_str,
                    "count": data["count"],
                    "high_risk_count": data["high_risk"],
                    "avg_score": round(avg_score, 3)
                })
            
            return {
                "metric": metric,
                "period": period,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "data": result
            }
        
        elif metric == "prediction_count":
            query = db.query(IITPrediction).filter(
                IITPrediction.prediction_timestamp >= start_date
            )
            count = query.count()
            
            return {
                "metric": metric,
                "period": period,
                "value": count,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat()
            }
        
        elif metric == "patient_count":
            query = db.query(Patient).filter(
                Patient.created_at >= start_date
            )
            count = query.count()
            
            return {
                "metric": metric,
                "period": period,
                "value": count,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat()
            }
        
        else:
            return {"error": f"Unknown metric: {metric}"}
    
    except Exception as e:
        logger.error(f"Failed to get trends: {str(e)}")
        raise

@router.get("/cohort-analysis", response_model=dict)
async def get_cohort_analysis(
    age_group: str = Query(..., description="Age group (18-25, 26-35, 36-50, 50+)"),
    gender: Optional[str] = Query(None, description="Filter by gender (M, F)"),
    state_province: Optional[str] = Query(None, description="Filter by state"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cohort analysis - analyze patient groups by demographics
    """
    try:
        query = db.query(Patient)
        
        if start_date:
            query = query.filter(Patient.created_at >= start_date)
        if end_date:
            query = query.filter(Patient.created_at <= end_date)
        if gender:
            query = query.filter(Patient.gender == gender)
        if state_province:
            query = query.filter(Patient.state_province == state_province)
        
        patients = query.all()
        
        # Group by age
        cohorts = {
            "18-25": {"count": 0, "high_risk": 0, "avg_score": 0},
            "26-35": {"count": 0, "high_risk": 0, "avg_score": 0},
            "36-50": {"count": 0, "high_risk": 0, "avg_score": 0},
            "50+": {"count": 0, "high_risk": 0, "avg_score": 0}
        }
        
        # Get predictions for each patient
        patient_uuids = [p.patient_uuid for p in patients]
        predictions = db.query(IITPrediction).filter(
            IITPrediction.patient_uuid.in_(patient_uuids)
        ).all()
        
        # Map predictions to patients
        pred_map = {p.patient_uuid: p for p in predictions}
        
        # Calculate cohort statistics
        for patient in patients:
            age = patient.get_age() if hasattr(patient, 'get_age') else 0
            if 18 <= age <= 25:
                cohort = "18-25"
            elif 26 <= age <= 35:
                cohort = "26-35"
            elif 36 <= age <= 50:
                cohort = "36-50"
            else:
                cohort = "50+"
            
            cohorts[cohort]["count"] += 1
            
            pred = pred_map.get(patient.patient_uuid)
            if pred:
                cohorts[cohort]["high_risk"] += 1 if pred.risk_level == "high" else 0
                cohorts[cohort]["avg_score"] = (cohorts[cohort]["avg_score"] * (cohorts[cohort]["count"] - 1) + (pred.prediction_score or 0)) / cohorts[cohort]["count"]
        
        # Calculate percentages
        total = len(patients)
        for cohort in cohorts.values():
            cohort["percentage"] = round((cohort["count"] / total * 100), 2) if total > 0 else 0
            cohort["high_risk_percentage"] = round((cohort["high_risk"] / cohort["count"] * 100), 2) if cohort["count"] > 0 else 0
        
        return {
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "filters": {
                "age_group": age_group,
                "gender": gender,
                "state_province": state_province
            },
            "cohorts": cohorts,
            "total_patients": total
        }
    except Exception as e:
        logger.error(f"Failed to get cohort analysis: {str(e)}")
        raise

@router.get("/risk-factors", response_model=dict)
async def get_risk_factors(
    patient_uuid: str = Query(..., description="Patient UUID to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze risk factors for a specific patient
    """
    try:
        # Get patient
        patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Get observations for this patient
        observations = db.query(Observation).filter(
            Observation.patient_uuid == patient_uuid
        ).all()
        
        # Get latest prediction
        prediction = db.query(IITPrediction).filter(
            IITPrediction.patient_uuid == patient_uuid
        ).order_by(IITPrediction.prediction_timestamp.desc()).first()
        
        # Analyze risk factors
        factors = []
        
        # Missed appointments
        missed_appts = [o for o in observations if o.variable_name == "Missed_Appointment"]
        if missed_appts:
            factors.append({
                "name": "Missed Appointments",
                "value": len(missed_appts),
                "impact": 0.3,
                "severity": "high" if len(missed_appts) > 3 else "medium"
            })
        
        # Low CD4 count
        cd4_obs = [o for o in observations if o.variable_name == "CD4_Count"]
        if cd4_obs:
            latest_cd4 = max([o.value_numeric for o in cd4_obs if o.value_numeric is not None], default=0)
            if latest_cd4 < 200:
                factors.append({
                    "name": "Low CD4 Count",
                    "value": latest_cd4,
                    "impact": 0.25,
                    "severity": "high"
                })
        
        # Viral load
        viral_obs = [o for o in observations if o.variable_name == "Viral_Load"]
        if viral_obs:
            latest_viral = max([o.value_numeric for o in viral_obs if o.value_numeric is not None], default=0)
            if latest_viral > 1000:
                factors.append({
                    "name": "High Viral Load",
                    "value": latest_viral,
                    "impact": 0.2,
                    "severity": "medium"
                })
        
        return {
            "patient_uuid": patient_uuid,
            "patient_name": f"{patient.first_name} {patient.surname}",
            "prediction": {
                "risk_level": prediction.risk_level if prediction else "unknown",
                "score": prediction.prediction_score,
                "timestamp": prediction.prediction_timestamp.isoformat() if prediction else None
            },
            "risk_factors": factors,
            "total_impact": sum(f["impact"] for f in factors),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get risk factors: {str(e)}")
        raise

@router.get("/export/csv", response_model=dict)
async def export_data_csv(
    data_type: str = Query(..., description="Data type (patients, predictions, observations)"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export data as CSV file
    """
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        if data_type == "patients":
            writer.writerow(["patient_uuid", "datim_id", "pepfar_id", "first_name", "surname",
                           "gender", "date_of_birth", "state_province", "created_at"])
            
            query = db.query(Patient)
            if start_date:
                query = query.filter(Patient.created_at >= start_date)
            if end_date:
                query = query.filter(Patient.created_at <= end_date)
            
            patients = query.all()
            for p in patients:
                writer.writerow([
                    p.patient_uuid, p.datim_id, p.pepfar_id, p.first_name, p.surname,
                    p.gender, str(p.date_of_birth), p.state_province, str(p.created_at)
                ])
            
            filename = f"patients_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            
        elif data_type == "predictions":
            writer.writerow(["patient_uuid", "risk_level", "prediction_score", "prediction_timestamp", "model_version"])
            
            query = db.query(IITPrediction)
            if start_date:
                query = query.filter(IITPrediction.prediction_timestamp >= start_date)
            if end_date:
                query = query.filter(IITPrediction.prediction_timestamp <= end_date)
            
            predictions = query.all()
            for pred in predictions:
                writer.writerow([
                    pred.patient_uuid, pred.risk_level, pred.prediction_score,
                    str(pred.prediction_timestamp), pred.model_version
                ])
            
            filename = f"predictions_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        else:
            raise HTTPException(status_code=400, detail=f"Invalid data type: {data_type}")
        
        # Return CSV content
        csv_content = output.getvalue()
        
        return {
            "filename": filename,
            "content": csv_content,
            "content_type": "text/csv",
            "record_count": len(patients) if data_type == "patients" else len(predictions),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to export CSV: {str(e)}")
        raise

@router.get("/summary", response_model=dict)
async def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall system summary statistics
    """
    try:
        # Patient statistics
        total_patients = db.query(Patient).count()
        
        # Prediction statistics
        total_predictions = db.query(IITPrediction).count()
        
        # Recent predictions (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_predictions = db.query(IITPrediction).filter(
            IITPrediction.prediction_timestamp >= week_ago
        ).count()
        
        # Risk breakdown
        predictions = db.query(IITPrediction).all()
        risk_breakdown = {
            "high": 0,
            "medium": 0,
            "low": 0
        }
        for pred in predictions:
            risk_level = pred.risk_level or "unknown"
            if risk_level in risk_breakdown:
                risk_breakdown[risk_level] += 1
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "patients": {
                "total": total_patients
            },
            "predictions": {
                "total": total_predictions,
                "recent_7_days": recent_predictions
            },
            "risk_distribution": risk_breakdown,
            "risk_percentages": {
                k: round((v / total_predictions * 100), 2) if total_predictions > 0 else 0
                for k, v in risk_breakdown.items()
            }
        }
    except Exception as e:
        logger.error(f"Failed to get summary: {str(e)}")
        raise

@router.get("/model-performance", response_model=dict)
async def get_model_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get ML model performance metrics
    """
    try:
        predictions = db.query(IITPrediction).all()
        
        if not predictions:
            return {
                "model_version": "unknown",
                "total_predictions": 0,
                "avg_score": 0,
                "message": "No predictions available"
            }
        
        # Calculate statistics
        scores = [p.prediction_score for p in predictions if p.prediction_score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Count by risk level
        risk_counts = {"high": 0, "medium": 0, "low": 0}
        for pred in predictions:
            risk_level = pred.risk_level or "unknown"
            if risk_level in risk_counts:
                risk_counts[risk_level] += 1
        
        # Get model version from first prediction
        model_version = predictions[0].model_version if predictions else "unknown"
        
        return {
            "model_version": model_version,
            "total_predictions": len(predictions),
            "avg_prediction_score": round(avg_score, 4),
            "risk_distribution": risk_counts,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get model performance: {str(e)}")
        raise
