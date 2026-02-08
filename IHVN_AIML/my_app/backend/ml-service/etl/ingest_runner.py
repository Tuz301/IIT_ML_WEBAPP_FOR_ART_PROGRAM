"""
ETL Runner Module for IIT ML Service
Manages ETL job execution and scheduling
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from .data_ingestion import DataIngestion
from .data_processing import DataProcessor

logger = logging.getLogger(__name__)

class ETLRunner:
    """Manages ETL job execution and scheduling"""

    def __init__(self):
        self.data_ingestion = DataIngestion()
        self.data_processor = DataProcessor()
        self.job_history = []
        self.current_job = None

    def run_ingestion_job(self, source_path: str, source_type: str = "json", batch_size: int = 1000) -> Dict[str, Any]:
        """Run a data ingestion job"""
        try:
            job_id = f"ingestion_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.current_job = {
                "job_id": job_id,
                "job_type": "ingestion",
                "status": "running",
                "started_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Starting ingestion job: {job_id}")

            result = self.data_ingestion.ingest_from_source(
                source_path=source_path,
                source_type=source_type,
                batch_size=batch_size
            )

            self.current_job["status"] = "completed"
            self.current_job["completed_at"] = datetime.utcnow().isoformat()
            self.current_job["result"] = result

            self.job_history.append(self.current_job)
            self.current_job = None

            return {
                "job_id": job_id,
                "status": "completed",
                "result": result
            }

        except Exception as e:
            logger.error(f"Ingestion job failed: {str(e)}")
            if self.current_job:
                self.current_job["status"] = "failed"
                self.current_job["error"] = str(e)
                self.current_job["completed_at"] = datetime.utcnow().isoformat()
                self.job_history.append(self.current_job)
                self.current_job = None
            raise

    def run_processing_job(self, patient_ids: Optional[list] = None, force_reprocess: bool = False) -> Dict[str, Any]:
        """Run a feature processing job"""
        try:
            job_id = f"processing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.current_job = {
                "job_id": job_id,
                "job_type": "processing",
                "status": "running",
                "started_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Starting processing job: {job_id}")

            result = self.data_processor.process_all_features(
                patient_ids=patient_ids,
                force_reprocess=force_reprocess
            )

            self.current_job["status"] = "completed"
            self.current_job["completed_at"] = datetime.utcnow().isoformat()
            self.current_job["result"] = result

            self.job_history.append(self.current_job)
            self.current_job = None

            return {
                "job_id": job_id,
                "status": "completed",
                "result": result
            }

        except Exception as e:
            logger.error(f"Processing job failed: {str(e)}")
            if self.current_job:
                self.current_job["status"] = "failed"
                self.current_job["error"] = str(e)
                self.current_job["completed_at"] = datetime.utcnow().isoformat()
                self.job_history.append(self.current_job)
                self.current_job = None
            raise

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        for job in self.job_history:
            if job["job_id"] == job_id:
                return job.copy()
        return None

    def get_current_job(self) -> Optional[Dict[str, Any]]:
        """Get current running job"""
        return self.current_job.copy() if self.current_job else None

    def get_job_history(self, limit: int = 10) -> list:
        """Get recent job history"""
        return self.job_history[-limit:]

    def cancel_current_job(self) -> bool:
        """Cancel the current running job"""
        if self.current_job and self.current_job["status"] == "running":
            self.current_job["status"] = "cancelled"
            self.current_job["completed_at"] = datetime.utcnow().isoformat()
            self.job_history.append(self.current_job)
            self.current_job = None
            return True
        return False
