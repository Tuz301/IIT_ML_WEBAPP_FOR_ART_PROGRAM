"""
ETL Pipeline Module for IIT ML Service
Orchestrates the complete ETL process
"""

import logging
from datetime import datetime
from typing import Dict, Any
from .data_ingestion import DataIngestion
from .data_processing import DataProcessor

logger = logging.getLogger(__name__)

class ETLPipeline:
    """Orchestrates the complete ETL pipeline"""

    def __init__(self):
        self.data_ingestion = DataIngestion()
        self.data_processor = DataProcessor()
        self.is_running = False
        self.last_run_time = None
        self.pipeline_status = {
            "ingestion_complete": False,
            "processing_complete": False,
            "errors": []
        }

    def run_full_pipeline(self, force_refresh: bool = False):
        """Run the complete ETL pipeline"""
        try:
            self.is_running = True
            self.pipeline_status = {
                "ingestion_complete": False,
                "processing_complete": False,
                "errors": []
            }

            logger.info("Starting full ETL pipeline")

            # Step 1: Data Ingestion
            try:
                ingestion_result = self.data_ingestion.run_ingestion()
                self.pipeline_status["ingestion_complete"] = True
                logger.info(f"Data ingestion completed: {ingestion_result}")
            except Exception as e:
                error_msg = f"Data ingestion failed: {str(e)}"
                logger.error(error_msg)
                self.pipeline_status["errors"].append(error_msg)
                raise

            # Step 2: Feature Processing
            try:
                processing_result = self.data_processor.process_all_features(force_reprocess=force_refresh)
                self.pipeline_status["processing_complete"] = True
                logger.info(f"Feature processing completed: {processing_result}")
            except Exception as e:
                error_msg = f"Feature processing failed: {str(e)}"
                logger.error(error_msg)
                self.pipeline_status["errors"].append(error_msg)
                raise

            self.last_run_time = datetime.utcnow().isoformat()
            logger.info("ETL pipeline completed successfully")

            return {
                "status": "success",
                "ingestion_result": ingestion_result,
                "processing_result": processing_result,
                "completed_at": self.last_run_time
            }

        except Exception as e:
            logger.error(f"ETL pipeline failed: {str(e)}")
            raise
        finally:
            self.is_running = False

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        return {
            "is_running": self.is_running,
            "last_run_time": self.last_run_time,
            "pipeline_status": self.pipeline_status.copy(),
            "timestamp": datetime.utcnow().isoformat()
        }

    def cleanup_temp_files(self) -> Dict[str, Any]:
        """Clean up temporary ETL files"""
        # Placeholder implementation
        logger.info("Cleaning up temporary ETL files")
        return {"temp_files_cleaned": 0}
