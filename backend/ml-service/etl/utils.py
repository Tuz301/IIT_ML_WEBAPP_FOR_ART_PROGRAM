"""
ETL Utilities Module for IIT ML Service
Provides utility functions for ETL operations
"""

import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class ETLUtils:
    """Utility functions for ETL operations"""

    @staticmethod
    def generate_hash(data: Any) -> str:
        """Generate a hash for data deduplication"""
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        elif isinstance(data, str):
            data_str = data
        else:
            data_str = str(data)
        return hashlib.md5(data_str.encode()).hexdigest()

    @staticmethod
    def validate_json_structure(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """Validate JSON structure against required fields"""
        errors = []
        missing_fields = []

        for field in required_fields:
            if field not in data:
                missing_fields.append(field)

        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "missing_fields": missing_fields
        }

    @staticmethod
    def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data by removing null/empty values"""
        return {k: v for k, v in data.items() if v is not None and v != ""}

    @staticmethod
    def parse_date(date_str: Optional[str], default: Optional[datetime] = None) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return default

        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d/%m/%Y"
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return default

    @staticmethod
    def calculate_age(birthdate: datetime, reference_date: Optional[datetime] = None) -> int:
        """Calculate age from birthdate"""
        if not birthdate:
            return None

        ref_date = reference_date or datetime.utcnow()
        age = ref_date.year - birthdate.year

        # Adjust if birthday hasn't occurred yet this year
        if (ref_date.month, ref_date.day) < (birthdate.month, birthdate.day):
            age -= 1

        return age

    @staticmethod
    def normalize_gender(gender: Optional[str]) -> Optional[str]:
        """Normalize gender values to standard format"""
        if not gender:
            return None

        gender_map = {
            "M": "male",
            "F": "female",
            "MALE": "male",
            "FEMALE": "female",
            "1": "male",
            "2": "female"
        }

        return gender_map.get(str(gender).upper(), str(gender).lower())

    @staticmethod
    def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split a list into chunks"""
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

    @staticmethod
    def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely get a value from a nested dictionary"""
        keys = key.split(".")
        value = data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @staticmethod
    def format_phone_number(phone: Optional[str]) -> Optional[str]:
        """Format phone number to standard format"""
        if not phone:
            return None

        # Remove all non-digit characters
        digits = ''.join(c for c in str(phone) if c.isdigit())

        # Basic validation - check if it looks like a phone number
        if len(digits) >= 10:
            return digits
        return None

    @staticmethod
    def deduplicate_records(records: List[Dict[str, Any]], key_field: str) -> List[Dict[str, Any]]:
        """Remove duplicate records based on a key field"""
        seen = set()
        unique_records = []

        for record in records:
            key_value = record.get(key_field)
            if key_value and key_value not in seen:
                seen.add(key_value)
                unique_records.append(record)

        return unique_records

    @staticmethod
    def merge_records(base: Dict[str, Any], update: Dict[str, Any], overwrite_nulls: bool = True) -> Dict[str, Any]:
        """Merge two records, with options for handling null values"""
        merged = base.copy()

        for key, value in update.items():
            if key not in merged:
                merged[key] = value
            elif overwrite_nulls and value is not None:
                merged[key] = value
            elif merged[key] is None and value is not None:
                merged[key] = value

        return merged

    @staticmethod
    def create_backup_path(base_dir: str, backup_name: Optional[str] = None) -> Path:
        """Create a backup file path"""
        backup_dir = Path(base_dir) / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        if backup_name:
            return backup_dir / backup_name

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return backup_dir / f"backup_{timestamp}.json"

    @staticmethod
    def log_etl_metrics(operation: str, metrics: Dict[str, Any]):
        """Log ETL operation metrics"""
        logger.info(f"ETL Metrics [{operation}]: {json.dumps(metrics, indent=2)}")

    @staticmethod
    def calculate_processing_time(start_time: datetime, end_time: Optional[datetime] = None) -> Dict[str, float]:
        """Calculate processing time metrics"""
        end = end_time or datetime.utcnow()
        duration = (end - start_time).total_seconds()

        return {
            "duration_seconds": duration,
            "duration_minutes": duration / 60,
            "duration_hours": duration / 3600
        }
