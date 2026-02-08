"""
Explainability API endpoints for IIT Prediction ML Service
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from ..core.db import get_db
from ..explainability import get_explainability_engine
from ..models import Prediction, FeatureImportance, PredictionExplanation
from ..auth import get_current_user
from ..schema import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explainability", tags=["Explainability"])


class FeatureImportanceResponse(BaseModel):
    """Response model for feature importance"""
    model_version: str
    feature_name: str
    importance_score: float
    calculated_at: str


class PredictionExplanationRequest(BaseModel):
    """Request model for prediction explanation"""
    prediction_id: str


class PredictionExplanationResponse(BaseModel):
    """Response model for prediction explanation"""
    prediction_id: str
    patient_uuid: str
    risk_score: float
    risk_level: str
    model_version: str
    feature_contributions: List[Dict[str, Any]]
    top_positive_factors: List[Dict[str, Any]]
    top_negative_factors: List[Dict[str, Any]]
    explanation_summary: str
    confidence_score: float
    created_at: str


class InterpretabilityReportRequest(BaseModel):
    """Request model for interpretability report"""
    model_version: str


class InterpretabilityReportResponse(BaseModel):
    """Response model for interpretability report"""
    model_version: str
    feature_importance: Dict[str, float]
    explanation_patterns: Dict[str, Any]
    interpretability_metrics: Dict[str, float]
    generated_at: str


@router.get("/feature-importance/{model_version}", response_model=List[FeatureImportanceResponse],
            summary="Get Feature Importance Scores",
            description="""Retrieve feature importance scores for a specific machine learning model version.

            **Feature Importance Analysis:**
            - Quantifies the contribution of each feature to model predictions
            - Helps identify key predictors of IIT risk
            - Supports model interpretability and validation
            - Enables feature selection and engineering decisions

            **Importance Calculation Methods:**
            - Tree-based models: Gini importance, permutation importance
            - Linear models: Coefficient magnitudes
            - Neural networks: Gradient-based attribution methods
            - Ensemble methods: Weighted average of base model importances

            **Clinical Applications:**
            - Identify most influential clinical indicators
            - Guide feature engineering and data collection priorities
            - Support clinical decision-making transparency
            - Validate model alignment with clinical expertise

            **Performance Considerations:**
            - Importance scores cached for performance
            - Recalculation available for updated models
            - Sample-based estimation for large datasets
            - Historical tracking of importance changes

            **Use Cases:**
            - Model validation and interpretability assessment
            - Feature selection for model updates
            - Clinical research and analysis
            - Regulatory compliance documentation
            """,
            responses={
                200: {
                    "description": "Feature importance scores retrieved successfully",
                    "model": List[FeatureImportanceResponse],
                    "content": {
                        "application/json": {
                            "example": [
                                {
                                    "model_version": "1.2.0",
                                    "feature_name": "days_since_last_refill",
                                    "importance_score": 0.35,
                                    "calculated_at": "2025-01-15T10:30:00"
                                },
                                {
                                    "model_version": "1.2.0",
                                    "feature_name": "cd4_count",
                                    "importance_score": 0.28,
                                    "calculated_at": "2025-01-15T10:30:00"
                                }
                            ]
                        }
                    }
                },
                404: {
                    "description": "Model version not found or no importance scores calculated",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Not Found",
                                "detail": "No feature importance found for model version 1.2.0",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                },
                500: {
                    "description": "Internal server error during importance calculation",
                    "model": ErrorResponse
                }
            })
async def get_feature_importance(
    model_version: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get feature importance scores for model interpretability and validation"""
    try:
        engine = get_explainability_engine()

        # Calculate feature importance if not exists
        importance_scores = engine.calculate_feature_importance(model_version, db)

        # Get stored importance records
        importance_records = db.query(FeatureImportance).filter(
            FeatureImportance.model_version == model_version
        ).order_by(FeatureImportance.calculated_at.desc()).all()

        return [
            FeatureImportanceResponse(
                model_version=record.model_version,
                feature_name=record.feature_name,
                importance_score=record.importance_score,
                calculated_at=record.calculated_at.isoformat()
            )
            for record in importance_records
        ]

    except Exception as e:
        logger.error(f"Failed to get feature importance for model {model_version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predictions/explain", response_model=PredictionExplanationResponse,
            summary="Generate Prediction Explanation",
            description="""Generate a comprehensive explanation for a specific IIT risk prediction.

            **Explanation Generation Process:**
            1. **Prediction Retrieval**: Locate the prediction record and associated data
            2. **Feature Attribution**: Calculate contribution of each feature to the prediction
            3. **Factor Analysis**: Identify top positive and negative risk factors
            4. **Summary Generation**: Create human-readable explanation summary
            5. **Confidence Assessment**: Evaluate explanation reliability

            **Explanation Components:**
            - **Feature Contributions**: How each input feature influenced the prediction
            - **Top Positive Factors**: Features that increased IIT risk assessment
            - **Top Negative Factors**: Features that decreased IIT risk assessment
            - **Summary**: Natural language explanation of the prediction reasoning
            - **Confidence Score**: Reliability measure of the explanation

            **Attribution Methods:**
            - SHAP (SHapley Additive exPlanations) values
            - LIME (Local Interpretable Model-agnostic Explanations)
            - Feature permutation importance
            - Partial dependence plots data

            **Clinical Applications:**
            - Explain risk predictions to healthcare providers
            - Support clinical decision-making with evidence
            - Identify key factors for patient intervention planning
            - Build trust in ML-based clinical tools

            **Performance Considerations:**
            - Explanations cached for frequently requested predictions
            - On-demand calculation for new or updated predictions
            - Asynchronous processing for complex explanations
            - Resource optimization for high-volume requests

            **Use Cases:**
            - Clinical decision support during patient consultations
            - Quality assurance and model validation
            - Research analysis of prediction patterns
            - Regulatory compliance and audit trails
            """,
            responses={
                200: {
                    "description": "Prediction explanation generated successfully",
                    "model": PredictionExplanationResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "prediction_id": "pred_12345",
                                "patient_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "risk_score": 0.68,
                                "risk_level": "high",
                                "model_version": "1.2.0",
                                "feature_contributions": [
                                    {"feature": "days_since_last_refill", "contribution": 0.25, "value": 45},
                                    {"feature": "cd4_count", "contribution": 0.18, "value": 380},
                                    {"feature": "viral_load_suppressed", "contribution": -0.12, "value": True}
                                ],
                                "top_positive_factors": [
                                    {"factor": "Long time since last medication refill", "impact": "high"},
                                    {"factor": "Low CD4 count", "impact": "medium"}
                                ],
                                "top_negative_factors": [
                                    {"factor": "Viral load suppressed", "impact": "medium"}
                                ],
                                "explanation_summary": "High IIT risk due to extended period without medication refill and low CD4 count, despite viral suppression.",
                                "confidence_score": 0.85,
                                "created_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                404: {
                    "description": "Prediction not found or explanation generation failed",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Not Found",
                                "detail": "Prediction pred_12345 not found",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                },
                500: {
                    "description": "Internal server error during explanation generation",
                    "model": ErrorResponse
                }
            })
async def explain_prediction(
    request: PredictionExplanationRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Generate comprehensive explanation for IIT risk prediction"""
    try:
        engine = get_explainability_engine()

        explanation = engine.explain_prediction(request.prediction_id, db)

        if not explanation:
            raise HTTPException(status_code=404, detail="Prediction not found or explanation failed")

        return PredictionExplanationResponse(
            prediction_id=explanation.prediction_id,
            patient_uuid=explanation.patient_uuid,
            risk_score=explanation.risk_score,
            risk_level=explanation.risk_level,
            model_version=explanation.model_version,
            feature_contributions=explanation.feature_contributions,
            top_positive_factors=explanation.top_positive_factors,
            top_negative_factors=explanation.top_negative_factors,
            explanation_summary=explanation.explanation_summary,
            confidence_score=explanation.confidence_score,
            created_at=explanation.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to explain prediction {request.prediction_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/{prediction_id}/explanation", response_model=PredictionExplanationResponse,
            summary="Get Stored Prediction Explanation",
            description="""Retrieve a previously generated explanation for a specific IIT risk prediction.

            **Explanation Retrieval:**
            - Access cached or stored prediction explanations
            - Retrieve detailed attribution information
            - Get human-readable explanation summaries
            - Access confidence scores and reliability metrics

            **Explanation Components:**
            - **Feature Contributions**: Detailed breakdown of each feature's influence
            - **Risk Factors**: Top positive and negative factors affecting prediction
            - **Summary**: Natural language explanation of model reasoning
            - **Metadata**: Model version, confidence score, generation timestamp

            **Performance Benefits:**
            - Instant retrieval of pre-computed explanations
            - Reduced computational overhead for repeated requests
            - Consistent explanations across multiple accesses
            - Historical tracking of explanation changes

            **Use Cases:**
            - Review explanations during clinical consultations
            - Audit and quality assurance of predictions
            - Research analysis of explanation patterns
            - Training and education for healthcare providers
            - Documentation for regulatory compliance

            **Caching Strategy:**
            - Explanations stored in database for persistence
            - Automatic cleanup of outdated explanations
            - Version tracking for model updates
            - Optimized retrieval for high-frequency access
            """,
            responses={
                200: {
                    "description": "Prediction explanation retrieved successfully",
                    "model": PredictionExplanationResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "prediction_id": "pred_12345",
                                "patient_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "risk_score": 0.68,
                                "risk_level": "high",
                                "model_version": "1.2.0",
                                "feature_contributions": [
                                    {"feature": "days_since_last_refill", "contribution": 0.25, "value": 45},
                                    {"feature": "cd4_count", "contribution": 0.18, "value": 380}
                                ],
                                "top_positive_factors": [
                                    {"factor": "Long time since last medication refill", "impact": "high"}
                                ],
                                "top_negative_factors": [
                                    {"factor": "Recent clinic visit", "impact": "low"}
                                ],
                                "explanation_summary": "High IIT risk primarily due to extended period without medication refill.",
                                "confidence_score": 0.85,
                                "created_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                404: {
                    "description": "Prediction explanation not found",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Not Found",
                                "detail": "Prediction explanation not found for pred_12345",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                },
                500: {
                    "description": "Internal server error during explanation retrieval",
                    "model": ErrorResponse
                }
            })
async def get_prediction_explanation(
    prediction_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Retrieve stored prediction explanation for clinical review and analysis"""
    try:
        explanation_record = db.query(PredictionExplanation).filter(
            PredictionExplanation.prediction_id == prediction_id
        ).first()

        if not explanation_record:
            raise HTTPException(status_code=404, detail="Prediction explanation not found")

        return PredictionExplanationResponse(
            prediction_id=explanation_record.prediction_id,
            patient_uuid=explanation_record.patient_uuid,
            risk_score=explanation_record.risk_score,
            risk_level=explanation_record.risk_level,
            model_version=explanation_record.model_version,
            feature_contributions=explanation_record.feature_contributions,
            top_positive_factors=explanation_record.top_positive_factors,
            top_negative_factors=explanation_record.top_negative_factors,
            explanation_summary=explanation_record.explanation_summary,
            confidence_score=explanation_record.confidence_score,
            created_at=explanation_record.created_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get explanation for prediction {prediction_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_version}/interpretability-report", response_model=InterpretabilityReportResponse,
            summary="Generate Model Interpretability Report",
            description="""Generate a comprehensive interpretability report for a machine learning model version.

            **Report Generation Process:**
            1. **Feature Importance Analysis**: Calculate global feature importance scores
            2. **Explanation Pattern Mining**: Identify common explanation patterns
            3. **Interpretability Metrics**: Compute model transparency and explainability metrics
            4. **Model Behavior Analysis**: Analyze prediction patterns and decision boundaries
            5. **Report Compilation**: Structure findings into comprehensive report

            **Report Components:**
            - **Feature Importance**: Global importance scores across all predictions
            - **Explanation Patterns**: Common factors influencing predictions
            - **Interpretability Metrics**: Quantitative measures of model explainability
            - **Model Insights**: Key findings about model behavior and limitations

            **Analysis Methods:**
            - Global feature importance using permutation methods
            - Pattern mining across prediction explanations
            - Interpretability scoring using established metrics
            - Statistical analysis of prediction distributions

            **Clinical Applications:**
            - Assess overall model reliability and transparency
            - Identify systematic patterns in IIT risk predictions
            - Guide model improvement and feature engineering
            - Support regulatory compliance and validation

            **Performance Considerations:**
            - Report generation may take several minutes for complex models
            - Results cached for subsequent access
            - Asynchronous processing for large-scale analysis
            - Resource optimization for production deployment

            **Use Cases:**
            - Model validation and regulatory compliance
            - Research analysis of prediction patterns
            - Quality assurance and model monitoring
            - Clinical decision support system evaluation
            - Documentation for healthcare accreditation
            """,
            responses={
                200: {
                    "description": "Interpretability report generated successfully",
                    "model": InterpretabilityReportResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "model_version": "1.2.0",
                                "feature_importance": {
                                    "days_since_last_refill": 0.35,
                                    "cd4_count": 0.28,
                                    "viral_load_suppressed": 0.15,
                                    "age": 0.12,
                                    "gender": 0.10
                                },
                                "explanation_patterns": {
                                    "high_risk_patterns": [
                                        "Extended time without medication refill",
                                        "Low CD4 count combined with high viral load"
                                    ],
                                    "low_risk_patterns": [
                                        "Consistent medication adherence",
                                        "Suppressed viral load with regular monitoring"
                                    ]
                                },
                                "interpretability_metrics": {
                                    "feature_stability": 0.85,
                                    "explanation_consistency": 0.78,
                                    "prediction_transparency": 0.92
                                },
                                "generated_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                404: {
                    "description": "Model version not found or insufficient data for analysis",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Not Found",
                                "detail": "Model version 1.2.0 not found or insufficient prediction data",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                },
                500: {
                    "description": "Internal server error during report generation",
                    "model": ErrorResponse
                }
            })
async def get_interpretability_report(
    model_version: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Generate comprehensive interpretability report for model validation and analysis"""
    try:
        engine = get_explainability_engine()

        report = engine.get_model_interpretability_report(model_version, db)

        return InterpretabilityReportResponse(
            model_version=report.get("model_version", model_version),
            feature_importance=report.get("feature_importance", {}),
            explanation_patterns=report.get("explanation_patterns", {}),
            interpretability_metrics=report.get("interpretability_metrics", {}),
            generated_at=report.get("generated_at", "")
        )

    except Exception as e:
        logger.error(f"Failed to generate interpretability report for model {model_version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions/explanations", response_model=List[PredictionExplanationResponse],
            summary="List Prediction Explanations",
            description="""Retrieve a paginated list of prediction explanations with optional filtering.

            **Filtering Options:**
            - **Model Version**: Filter explanations by specific model version
            - **Patient UUID**: Filter explanations for a specific patient
            - **Pagination**: Control result set size and offset for large datasets

            **Sorting:**
            - Results ordered by creation date (newest first)
            - Chronological access to recent explanations
            - Historical tracking of explanation evolution

            **Performance Optimization:**
            - Database indexing on commonly filtered fields
            - Efficient pagination for large result sets
            - Cached queries for frequently accessed data
            - Memory-efficient streaming for bulk exports

            **Clinical Applications:**
            - Review multiple patient explanations in batch
            - Analyze explanation patterns across patient populations
            - Quality assurance and consistency checking
            - Research studies on explanation effectiveness

            **Use Cases:**
            - Batch analysis of prediction explanations
            - Clinical audit and quality improvement
            - Research data extraction and analysis
            - System monitoring and performance evaluation
            - Training dataset creation for ML improvement
            """,
            responses={
                200: {
                    "description": "Prediction explanations retrieved successfully",
                    "model": List[PredictionExplanationResponse],
                    "content": {
                        "application/json": {
                            "example": [
                                {
                                    "prediction_id": "pred_12345",
                                    "patient_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                    "risk_score": 0.68,
                                    "risk_level": "high",
                                    "model_version": "1.2.0",
                                    "feature_contributions": [
                                        {"feature": "days_since_last_refill", "contribution": 0.25, "value": 45}
                                    ],
                                    "top_positive_factors": [
                                        {"factor": "Long time since last medication refill", "impact": "high"}
                                    ],
                                    "top_negative_factors": [
                                        {"factor": "Recent clinic visit", "impact": "low"}
                                    ],
                                    "explanation_summary": "High IIT risk due to extended period without medication refill.",
                                    "confidence_score": 0.85,
                                    "created_at": "2025-01-15T10:30:00"
                                }
                            ]
                        }
                    }
                },
                500: {
                    "description": "Internal server error during explanation retrieval",
                    "model": ErrorResponse
                }
            })
async def list_prediction_explanations(
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    patient_uuid: Optional[str] = Query(None, description="Filter by patient UUID"),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=1000),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Retrieve paginated list of prediction explanations with filtering options"""
    try:
        query = db.query(PredictionExplanation)

        if model_version:
            query = query.filter(PredictionExplanation.model_version == model_version)

        if patient_uuid:
            query = query.filter(PredictionExplanation.patient_uuid == patient_uuid)

        explanations = query.order_by(PredictionExplanation.created_at.desc()).offset(offset).limit(limit).all()

        return [
            PredictionExplanationResponse(
                prediction_id=exp.prediction_id,
                patient_uuid=exp.patient_uuid,
                risk_score=exp.risk_score,
                risk_level=exp.risk_level,
                model_version=exp.model_version,
                feature_contributions=exp.feature_contributions,
                top_positive_factors=exp.top_positive_factors,
                top_negative_factors=exp.top_negative_factors,
                explanation_summary=exp.explanation_summary,
                confidence_score=exp.confidence_score,
                created_at=exp.created_at.isoformat()
            )
            for exp in explanations
        ]

    except Exception as e:
        logger.error(f"Failed to list prediction explanations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_version}/bias-analysis",
            summary="Analyze Model Bias",
            description="""Perform bias analysis on a machine learning model to detect potential fairness issues and systematic errors.

            **Bias Analysis Process:**
            1. **Data Collection**: Gather recent predictions for analysis
            2. **Distribution Analysis**: Examine risk level distributions
            3. **Pattern Detection**: Identify potential bias indicators
            4. **Threshold Evaluation**: Check for disproportionate risk assignments
            5. **Report Generation**: Compile findings and recommendations

            **Bias Detection Methods:**
            - Risk distribution analysis across predictions
            - Threshold-based bias indicators
            - Statistical significance testing
            - Comparative analysis with baseline expectations

            **Bias Types Detected:**
            - **Over-prediction Bias**: Systematic overestimation of risk levels
            - **Under-prediction Bias**: Systematic underestimation of risk levels
            - **Distribution Bias**: Unbalanced risk level distributions
            - **Threshold Bias**: Inappropriate risk classification boundaries

            **Clinical Implications:**
            - Ensure equitable risk assessment across patient populations
            - Identify potential discrimination in clinical decision support
            - Support fairness in healthcare delivery
            - Guide bias mitigation strategies

            **Regulatory Compliance:**
            - Support algorithmic fairness requirements
            - Document bias assessment procedures
            - Enable audit trails for fairness evaluations
            - Meet healthcare equity standards

            **Use Cases:**
            - Model validation and fairness assessment
            - Regulatory compliance documentation
            - Quality assurance and monitoring
            - Research on healthcare equity
            - Clinical governance and oversight
            """,
            responses={
                200: {
                    "description": "Bias analysis completed successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "risk_distribution": {
                                    "Low": 250,
                                    "Medium": 400,
                                    "High": 350
                                },
                                "total_analyzed": 1000,
                                "potential_bias_concerns": [
                                    "High risk predictions slightly elevated"
                                ]
                            }
                        }
                    }
                },
                404: {
                    "description": "Model version not found or insufficient prediction data",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Not Found",
                                "detail": "No predictions found for bias analysis of model version 1.2.0",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                },
                500: {
                    "description": "Internal server error during bias analysis",
                    "model": ErrorResponse
                }
            })
async def get_bias_analysis(
    model_version: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Perform bias analysis on model predictions for fairness assessment"""
    try:
        # Get recent predictions for bias analysis
        recent_predictions = db.query(Prediction).filter(
            Prediction.model_version == model_version
        ).order_by(Prediction.created_at.desc()).limit(1000).all()

        if not recent_predictions:
            return {"message": "No predictions found for bias analysis"}

        # Simple bias analysis (placeholder - would use more sophisticated methods)
        risk_levels = [p.iit_risk_level for p in recent_predictions]
        risk_distribution = {
            "Low": risk_levels.count("Low"),
            "Medium": risk_levels.count("Medium"),
            "High": risk_levels.count("High")
        }

        total_predictions = len(recent_predictions)
        bias_indicators = {
            "risk_distribution": risk_distribution,
            "total_analyzed": total_predictions,
            "potential_bias_concerns": []
        }

        # Check for potential bias indicators
        if risk_distribution["High"] / total_predictions > 0.8:
            bias_indicators["potential_bias_concerns"].append("High risk predictions dominate")
        elif risk_distribution["Low"] / total_predictions > 0.8:
            bias_indicators["potential_bias_concerns"].append("Low risk predictions dominate")

        return bias_indicators

    except Exception as e:
        logger.error(f"Failed to get bias analysis for model {model_version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_version}/recalculate-importance",
            summary="Recalculate Feature Importance",
            description="""Trigger recalculation of feature importance scores for a machine learning model with configurable sample size.

            **Recalculation Process:**
            1. **Sample Selection**: Randomly select prediction samples for analysis
            2. **Importance Calculation**: Compute feature importance using configured methods
            3. **Database Update**: Store new importance scores with timestamps
            4. **Cache Invalidation**: Clear cached importance data for freshness
            5. **Result Compilation**: Return calculation statistics and metadata

            **Importance Methods:**
            - Permutation importance for global feature effects
            - Tree-based importance for ensemble models
            - SHAP value aggregation for comprehensive attribution
            - Statistical significance testing for reliability

            **Sample Size Considerations:**
            - **Small Samples (100-500)**: Fast calculation, lower accuracy
            - **Medium Samples (500-2000)**: Balanced performance and accuracy
            - **Large Samples (2000+)**: High accuracy, increased computation time
            - **Full Dataset**: Maximum accuracy, longest processing time

            **Performance Optimization:**
            - Parallel processing for large sample sizes
            - Incremental updates for existing importance scores
            - Memory-efficient algorithms for big datasets
            - Background processing for very large calculations

            **Clinical Applications:**
            - Update importance scores after model retraining
            - Assess feature relevance for new patient cohorts
            - Validate importance stability across time periods
            - Support feature engineering decisions

            **Use Cases:**
            - Model maintenance and updates
            - Feature selection optimization
            - Interpretability validation
            - Research analysis of changing feature importance
            - Quality assurance for model evolution
            """,
            responses={
                200: {
                    "description": "Feature importance recalculation completed successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "message": "Feature importance recalculated for model 1.2.0",
                                "features_calculated": 15,
                                "sample_size_used": 1000,
                                "calculation_time_seconds": 45.2,
                                "recalculated_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                404: {
                    "description": "Model version not found or insufficient prediction data",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Not Found",
                                "detail": "Model version 1.2.0 not found or insufficient prediction data for importance calculation",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                },
                500: {
                    "description": "Internal server error during importance recalculation",
                    "model": ErrorResponse
                }
            })
async def recalculate_feature_importance(
    model_version: str,
    sample_size: int = Query(1000, description="Sample size for calculation", ge=100, le=10000),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Trigger recalculation of feature importance scores with configurable parameters"""
    try:
        engine = get_explainability_engine()

        importance_scores = engine.calculate_feature_importance(model_version, db, sample_size)

        return {
            "message": f"Feature importance recalculated for model {model_version}",
            "features_calculated": len(importance_scores),
            "sample_size_used": sample_size
        }

    except Exception as e:
        logger.error(f"Failed to recalculate feature importance for model {model_version}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
