"""
Data Ingestion Module for IIT ML Service
Handles data ingestion from various sources
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from .etl_ingest import ingest_json_record

logger = logging.getLogger(__name__)

class DataIngestion:
    """Handles data ingestion from various sources"""

    def __init__(self):
        self.ingestion_stats = {
            "total_files_processed": 0,
            "total_records_ingested": 0,
            "failed_files": 0,
            "last_ingestion_time": None
        }

    def run_ingestion(self) -> Dict[str, Any]:
        """Run data ingestion process"""
        try:
            logger.info("Starting data ingestion")

            # Find data files to process
            data_files = self._find_data_files()

            total_processed = 0
            total_records = 0

            for file_path in data_files:
                try:
                    records_processed = self._process_file(file_path)
                    total_processed += 1
                    total_records += records_processed
                    logger.info(f"Processed file: {file_path.name} ({records_processed} records)")
                except Exception as e:
                    logger.error(f"Failed to process file {file_path}: {str(e)}")
                    self.ingestion_stats["failed_files"] += 1

            self.ingestion_stats["total_files_processed"] += total_processed
            self.ingestion_stats["total_records_ingested"] += total_records
            self.ingestion_stats["last_ingestion_time"] = datetime.utcnow().isoformat()

            return {
                "status": "success",
                "files_processed": total_processed,
                "records_ingested": total_records,
                "failed_files": self.ingestion_stats["failed_files"]
            }

        except Exception as e:
            logger.error(f"Data ingestion failed: {str(e)}")
            raise

    def ingest_from_source(self, source_path: str, source_type: str = "json", batch_size: int = 1000):
        """Ingest data from a specific source"""
        try:
            logger.info(f"Starting ingestion from source: {source_path}")

            file_path = Path(source_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")

            records_processed = self._process_file(file_path, batch_size=batch_size)

            logger.info(f"Successfully ingested {records_processed} records from {source_path}")

            return {
                "status": "success",
                "source_path": source_path,
                "records_processed": records_processed
            }

        except Exception as e:
            logger.error(f"Failed to ingest from source {source_path}: {str(e)}")
            raise

    def validate_data_source(self, source_path: str, source_type: str = "json") -> Dict[str, Any]:
        """Validate a data source before ingestion"""
        try:
            file_path = Path(source_path)
            if not file_path.exists():
                return {"is_valid": False, "errors": ["File not found"]}

            if source_type == "json":
                return self._validate_json_file(file_path)
            else:
                return {"is_valid": False, "errors": [f"Unsupported source type: {source_type}"]}

        except Exception as e:
            return {"is_valid": False, "errors": [str(e)]}

    def cleanup_failed_batches(self) -> Dict[str, Any]:
        """Clean up failed batch data"""
        # Placeholder implementation
        logger.info("Cleaning up failed batch data")
        return {"batches_cleaned": 0}

    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        return self.ingestion_stats.copy()

    def _find_data_files(self) -> List[Path]:
        """Find data files to process"""
        # Look for JSON files in data directories
        data_dirs = ["./data", "./etl/data", "../data"]

        data_files = []
        for data_dir in data_dirs:
            dir_path = Path(data_dir)
            if dir_path.exists():
                data_files.extend(dir_path.glob("*.json"))

        return data_files

    def _process_file(self, file_path: Path, batch_size: int = 1000) -> int:
        """Process a single data file"""
        records_processed = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() == '.json':
                # Try to load as JSON array or single object
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        # Process each record in the array
                        for record in data:
                            ingest_json_record(record)
                            records_processed += 1
                    else:
                        # Single JSON object
                        ingest_json_record(data)
                        records_processed += 1
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in file {file_path}: {str(e)}")
                    raise

        return records_processed

    def _validate_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate a JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            record_count = 1
            if isinstance(data, list):
                record_count = len(data)

            # Basic validation - check for required fields
            errors = []
            if isinstance(data, list):
                for i, record in enumerate(data):
                    if not isinstance(record, dict):
                        errors.append(f"Record {i} is not a valid object")
                    elif "messageData" not in record:
                        errors.append(f"Record {i} missing required 'messageData' field")
            else:
                if not isinstance(data, dict):
                    errors.append("File does not contain a valid JSON object")
                elif "messageData" not in data:
                    errors.append("Missing required 'messageData' field")

            return {
                "is_valid": len(errors) == 0,
                "errors": errors,
                "record_count": record_count
            }

        except json.JSONDecodeError as e:
            return {"is_valid": False, "errors": [f"Invalid JSON: {str(e)}"], "record_count": 0}
        except Exception as e:
            return {"is_valid": False, "errors": [str(e)], "record_count": 0}
