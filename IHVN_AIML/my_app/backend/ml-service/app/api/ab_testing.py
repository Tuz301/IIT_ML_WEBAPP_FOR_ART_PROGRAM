"""
A/B Testing API endpoints for IIT Prediction ML Service
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from ..core.db import get_db
from ..ab_testing import get_ab_testing_engine, ABTestConfiguration, VariantConfiguration
from ..models import ABTest, ABTestVariant, ABTestResult
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ab-testing", tags=["A/B Testing"])


class ABTestCreateRequest(BaseModel):
    """Request model for creating A/B test"""
    name: str
    description: str
    traffic_percentage: float
    variants: List[Dict[str, Any]]
    test_duration_days: int
    primary_metric: str
    secondary_metrics: Optional[List[str]] = None


class ABTestResponse(BaseModel):
    """Response model for A/B test"""
    test_id: str
    name: str
    description: str
    status: str
    traffic_percentage: float
    variants: List[Dict[str, Any]]
    start_date: Optional[str]
    end_date: Optional[str]
    primary_metric: str
    secondary_metrics: Optional[List[str]]


class VariantAssignmentResponse(BaseModel):
    """Response model for variant assignment"""
    test_id: str
    variant_id: str
    variant_name: str
    assigned_at: str


class ABTestResultsResponse(BaseModel):
    """Response model for A/B test results"""
    test_id: str
    status: str
    total_participants: int
    variants_results: List[Dict[str, Any]]
    winner_variant: Optional[str]
    confidence_level: float
    statistical_significance: bool
    recommendations: List[str]


@router.post("/tests", response_model=ABTestResponse)
async def create_ab_test(
    request: ABTestCreateRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Create a new A/B test"""
    try:
        engine = get_ab_testing_engine()

        # Convert request to configuration
        variants = []
        for variant_data in request.variants:
            variants.append(VariantConfiguration(
                variant_id=variant_data["variant_id"],
                name=variant_data["name"],
                description=variant_data.get("description", ""),
                traffic_weight=variant_data["traffic_weight"],
                model_version=variant_data.get("model_version"),
                parameters=variant_data.get("parameters", {})
            ))

        config = ABTestConfiguration(
            name=request.name,
            description=request.description,
            traffic_percentage=request.traffic_percentage,
            variants=variants,
            test_duration_days=request.test_duration_days,
            primary_metric=request.primary_metric,
            secondary_metrics=request.secondary_metrics or []
        )

        # Create the test
        test_id = engine.create_ab_test(config, db)

        # Get the created test
        test = db.query(ABTest).filter(ABTest.test_id == test_id).first()
        if not test:
            raise HTTPException(status_code=500, detail="Failed to create A/B test")

        return ABTestResponse(
            test_id=test.test_id,
            name=test.name,
            description=test.description,
            status=test.status,
            traffic_percentage=test.traffic_percentage,
            variants=[{
                "variant_id": v.variant_id,
                "name": v.name,
                "description": v.description,
                "traffic_weight": v.traffic_weight,
                "model_version": v.model_version,
                "parameters": v.parameters
            } for v in test.variants],
            start_date=test.start_date.isoformat() if test.start_date else None,
            end_date=test.end_date.isoformat() if test.end_date else None,
            primary_metric=test.primary_metric,
            secondary_metrics=test.secondary_metrics
        )

    except Exception as e:
        logger.error(f"Failed to create A/B test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests", response_model=List[ABTestResponse])
async def list_ab_tests(
    status: Optional[str] = Query(None, description="Filter by test status"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """List all A/B tests"""
    try:
        query = db.query(ABTest)

        if status:
            query = query.filter(ABTest.status == status)

        tests = query.order_by(ABTest.created_at.desc()).all()

        return [
            ABTestResponse(
                test_id=test.test_id,
                name=test.name,
                description=test.description,
                status=test.status,
                traffic_percentage=test.traffic_percentage,
                variants=[{
                    "variant_id": v.variant_id,
                    "name": v.name,
                    "description": v.description,
                    "traffic_weight": v.traffic_weight,
                    "model_version": v.model_version,
                    "parameters": v.parameters
                } for v in test.variants],
                start_date=test.start_date.isoformat() if test.start_date else None,
                end_date=test.end_date.isoformat() if test.end_date else None,
                primary_metric=test.primary_metric,
                secondary_metrics=test.secondary_metrics
            )
            for test in tests
        ]

    except Exception as e:
        logger.error(f"Failed to list A/B tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests/{test_id}", response_model=ABTestResponse)
async def get_ab_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get A/B test details"""
    try:
        test = db.query(ABTest).filter(ABTest.test_id == test_id).first()
        if not test:
            raise HTTPException(status_code=404, detail="A/B test not found")

        return ABTestResponse(
            test_id=test.test_id,
            name=test.name,
            description=test.description,
            status=test.status,
            traffic_percentage=test.traffic_percentage,
            variants=[{
                "variant_id": v.variant_id,
                "name": v.name,
                "description": v.description,
                "traffic_weight": v.traffic_weight,
                "model_version": v.model_version,
                "parameters": v.parameters
            } for v in test.variants],
            start_date=test.start_date.isoformat() if test.start_date else None,
            end_date=test.end_date.isoformat() if test.end_date else None,
            primary_metric=test.primary_metric,
            secondary_metrics=test.secondary_metrics
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get A/B test {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/{test_id}/assign", response_model=VariantAssignmentResponse)
async def assign_variant(
    test_id: str,
    patient_uuid: str = Query(..., description="Patient UUID for assignment"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Assign a variant for a patient in an A/B test"""
    try:
        engine = get_ab_testing_engine()

        assignment = engine.assign_variant(test_id, patient_uuid, db)

        return VariantAssignmentResponse(
            test_id=assignment.test_id,
            variant_id=assignment.variant_id,
            variant_name=assignment.variant_name,
            assigned_at=assignment.assigned_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to assign variant for test {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/{test_id}/record")
async def record_ab_test_result(
    test_id: str,
    patient_uuid: str,
    variant_id: str,
    metric_name: str,
    metric_value: float,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Record a metric result for an A/B test"""
    try:
        engine = get_ab_testing_engine()

        engine.record_metric_result(
            test_id=test_id,
            patient_uuid=patient_uuid,
            variant_id=variant_id,
            metric_name=metric_name,
            metric_value=metric_value,
            db=db
        )

        return {"message": "Metric result recorded successfully"}

    except Exception as e:
        logger.error(f"Failed to record metric result for test {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests/{test_id}/results", response_model=ABTestResultsResponse)
async def get_ab_test_results(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get A/B test results and analysis"""
    try:
        engine = get_ab_testing_engine()

        results = engine.analyze_test_results(test_id, db)

        return ABTestResultsResponse(
            test_id=results["test_id"],
            status=results["status"],
            total_participants=results["total_participants"],
            variants_results=results["variants_results"],
            winner_variant=results.get("winner_variant"),
            confidence_level=results["confidence_level"],
            statistical_significance=results["statistical_significance"],
            recommendations=results["recommendations"]
        )

    except Exception as e:
        logger.error(f"Failed to get results for test {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/{test_id}/stop")
async def stop_ab_test(
    test_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Stop an A/B test"""
    try:
        engine = get_ab_testing_engine()

        engine.stop_test(test_id, db)

        return {"message": f"A/B test {test_id} stopped successfully"}

    except Exception as e:
        logger.error(f"Failed to stop A/B test {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/{test_id}/conclude")
async def conclude_ab_test(
    test_id: str,
    winner_variant_id: Optional[str] = Query(None, description="Winner variant ID"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Conclude an A/B test with a winner"""
    try:
        engine = get_ab_testing_engine()

        engine.conclude_test(test_id, winner_variant_id, db)

        return {"message": f"A/B test {test_id} concluded successfully"}

    except Exception as e:
        logger.error(f"Failed to conclude A/B test {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
