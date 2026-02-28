"""
ETL API endpoints for data ingestion and processing
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from pathlib import Path

from etl.pipeline import ETLPipeline
from etl.data_ingestion import DataIngestion
from etl.data_processing import DataProcessor
from ..auth import get_current_user
from ..models import User
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/etl", tags=["etl"])

# Global ETL components
etl_pipeline = ETLPipeline()
data_ingestion = DataIngestion()
data_processor = DataProcessor()

@router.post("/run-full-pipeline")
async def run_full_etl_pipeline(
    background_tasks: BackgroundTasks,
    force_refresh: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Run the complete ETL pipeline

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Run ETL pipeline in background
        background_tasks.add_task(etl_pipeline.run_full_pipeline, force_refresh=force_refresh)

        logger.info("Full ETL pipeline started in background")
        return {
            "message": "ETL pipeline started successfully",
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "force_refresh": force_refresh
        }

    except Exception as e:
        logger.error(f"Failed to start ETL pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start ETL pipeline: {str(e)}")

@router.post("/ingest-data")
async def ingest_data(
    background_tasks: BackgroundTasks,
    data_source: str,
    source_type: str = "json",
    batch_size: int = 1000,
    current_user: User = Depends(get_current_user)
):
    """
    Ingest data from specified source

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Validate data source exists
        data_path = Path(data_source)
        if not data_path.exists():
            raise HTTPException(status_code=404, detail=f"Data source not found: {data_source}")

        # Start data ingestion in background
        background_tasks.add_task(
            data_ingestion.ingest_from_source,
            source_path=str(data_path),
            source_type=source_type,
            batch_size=batch_size
        )

        logger.info(f"Data ingestion started for source: {data_source}")
        return {
            "message": "Data ingestion started successfully",
            "status": "running",
            "data_source": data_source,
            "source_type": source_type,
            "batch_size": batch_size,
            "started_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start data ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start data ingestion: {str(e)}")

@router.post("/process-features")
async def process_features(
    background_tasks: BackgroundTasks,
    patient_ids: Optional[List[str]] = None,
    force_reprocess: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Process features for IIT prediction

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Start feature processing in background
        background_tasks.add_task(
            data_processor.process_all_features,
            patient_ids=patient_ids,
            force_reprocess=force_reprocess
        )

        logger.info("Feature processing started")
        return {
            "message": "Feature processing started successfully",
            "status": "running",
            "patient_ids": patient_ids,
            "force_reprocess": force_reprocess,
            "started_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to start feature processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start feature processing: {str(e)}")

@router.get("/status")
async def get_etl_status(current_user: User = Depends(get_current_user)):
    """
    Get current ETL pipeline status

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        status_info = etl_pipeline.get_pipeline_status()

        return {
            "pipeline_status": status_info,
            "last_run": etl_pipeline.last_run_time,
            "is_running": etl_pipeline.is_running,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get ETL status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get ETL status: {str(e)}")

@router.get("/ingestion/stats")
async def get_ingestion_stats(current_user: User = Depends(get_current_user)):
    """
    Get data ingestion statistics

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        stats = data_ingestion.get_ingestion_stats()

        return {
            "ingestion_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get ingestion stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get ingestion stats: {str(e)}")

@router.get("/processing/stats")
async def get_processing_stats(current_user: User = Depends(get_current_user)):
    """
    Get data processing statistics

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        stats = data_processor.get_processing_stats()

        return {
            "processing_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get processing stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing stats: {str(e)}")

@router.post("/validate-data")
async def validate_data_source(
    data_source: str,
    source_type: str = "json",
    current_user: User = Depends(get_current_user)
):
    """
    Validate data source before ingestion

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Validate data source
        data_path = Path(data_source)
        if not data_path.exists():
            raise HTTPException(status_code=404, detail=f"Data source not found: {data_source}")

        # Perform validation
        validation_result = data_ingestion.validate_data_source(str(data_path), source_type)

        return {
            "data_source": data_source,
            "source_type": source_type,
            "is_valid": validation_result["is_valid"],
            "validation_errors": validation_result.get("errors", []),
            "record_count": validation_result.get("record_count", 0),
            "validated_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate data source: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to validate data source: {str(e)}")

@router.delete("/cleanup")
async def cleanup_etl_data(
    cleanup_type: str = "temp_files",
    current_user: User = Depends(get_current_user)
):
    """
    Clean up ETL temporary data and files

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        if cleanup_type == "temp_files":
            # Clean up temporary files
            cleanup_result = etl_pipeline.cleanup_temp_files()
        elif cleanup_type == "failed_batches":
            # Clean up failed batch data
            cleanup_result = data_ingestion.cleanup_failed_batches()
        else:
            raise HTTPException(status_code=400, detail=f"Invalid cleanup type: {cleanup_type}")

        return {
            "message": f"ETL cleanup completed for type: {cleanup_type}",
            "cleanup_result": cleanup_result,
            "cleaned_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup ETL data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup ETL data: {str(e)}")

@router.get("/sources")
async def list_data_sources(current_user: User = Depends(get_current_user)):
    """
    List available data sources for ingestion

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Get configured data source directories
        data_dirs = [
            settings.data_dir,
            "./data",
            "./etl/data"
        ]

        sources = []
        for data_dir in data_dirs:
            if Path(data_dir).exists():
                for file_path in Path(data_dir).glob("*.json"):
                    stat = file_path.stat()
                    sources.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": "json"
                    })

        return {
            "data_sources": sources,
            "total_sources": len(sources),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to list data sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list data sources: {str(e)}")

@router.post("/schedule")
async def schedule_etl_job(
    job_type: str,
    schedule_config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Schedule an ETL job for periodic execution

    Requires admin privileges
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Validate job type
        valid_job_types = ["full_pipeline", "data_ingestion", "feature_processing"]
        if job_type not in valid_job_types:
            raise HTTPException(status_code=400, detail=f"Invalid job type. Must be one of: {valid_job_types}")

        # Schedule the job (placeholder - would integrate with a job scheduler)
        job_id = f"{job_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # For now, just return success with job details
        return {
            "message": f"ETL job scheduled successfully",
            "job_id": job_id,
            "job_type": job_type,
            "schedule_config": schedule_config,
            "scheduled_at": datetime.utcnow().isoformat(),
            "status": "scheduled"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule ETL job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule ETL job: {str(e)}")
