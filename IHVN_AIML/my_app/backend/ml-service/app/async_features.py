"""
Async Feature Extraction Module for IIT ML Service
Provides asynchronous feature extraction for improved performance
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from .ml_model import IITModelPredictor, get_model
from .feature_store import get_feature_store
from .core.db import get_db
from .models import Patient, IITFeatures
from .config import get_settings
from .monitoring import MetricsManager, feature_extraction_latency

logger = logging.getLogger(__name__)
settings = get_settings()


class AsyncFeatureExtractor:
    """
    Asynchronous feature extraction for improved performance.
    
    Uses asyncio and thread pools to parallelize feature extraction
    across multiple patients or feature categories.
    """
    
    def __init__(self, max_workers: int = 4):
        self.model = get_model()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_workers = max_workers
        
    async def extract_features_for_patient(
        self,
        patient_uuid: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Extract features for a single patient asynchronously.
        
        Args:
            patient_uuid: Patient UUID
            force_refresh: Force re-computation even if cached
            
        Returns:
            Dictionary of extracted features or None if failed
        """
        start_time = datetime.utcnow()
        
        try:
            # Check cache first
            if not force_refresh:
                feature_store = await get_feature_store()
                cached_features = await feature_store.get_features(patient_uuid)
                if cached_features:
                    logger.debug(f"Using cached features for patient {patient_uuid}")
                    return cached_features
            
            # Run feature extraction in thread pool
            loop = asyncio.get_event_loop()
            features = await loop.run_in_executor(
                self.executor,
                self._extract_features_sync,
                patient_uuid
            )
            
            # Cache the features
            if features:
                feature_store = await get_feature_store()
                await feature_store.set_features(patient_uuid, features)
            
            # Record metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            feature_extraction_latency.observe(duration)
            
            return features
            
        except Exception as e:
            logger.error(f"Async feature extraction failed for patient {patient_uuid}: {e}")
            return None
    
    async def extract_features_for_patients(
        self,
        patient_uuids: List[str],
        force_refresh: bool = False
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Extract features for multiple patients in parallel.
        
        Args:
            patient_uuids: List of patient UUIDs
            force_refresh: Force re-computation even if cached
            
        Returns:
            Dictionary mapping patient_uuid to features
        """
        # Create tasks for all patients
        tasks = [
            self.extract_features_for_patient(uuid, force_refresh)
            for uuid in patient_uuids
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build results dictionary
        feature_dict = {}
        for uuid, result in zip(patient_uuids, results):
            if isinstance(result, Exception):
                logger.error(f"Feature extraction failed for {uuid}: {result}")
                feature_dict[uuid] = None
            else:
                feature_dict[uuid] = result
        
        return feature_dict
    
    def _extract_features_sync(self, patient_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous feature extraction (runs in thread pool).
        
        Args:
            patient_uuid: Patient UUID
            
        Returns:
            Dictionary of extracted features
        """
        try:
            db = next(get_db())
            
            # Get patient with related data
            patient = db.query(Patient).filter(
                Patient.patient_uuid == patient_uuid
            ).first()
            
            if not patient:
                logger.warning(f"Patient {patient_uuid} not found")
                return None
            
            # Build patient data dict for feature extraction
            patient_data = self._build_patient_data_dict(patient, db)
            
            # Extract features using model
            features = self.model.extract_features_from_json(patient_data)
            
            return features
            
        except Exception as e:
            logger.error(f"Sync feature extraction failed for {patient_uuid}: {e}")
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    def _build_patient_data_dict(self, patient: Patient, db) -> Dict[str, Any]:
        """Build patient data dictionary for feature extraction"""
        # This would build the full patient data structure
        # including visits, encounters, observations, etc.
        
        patient_data = {
            "messageData": {
                "demographics": {
                    "patientUuid": str(patient.patient_uuid),
                    "givenName": patient.given_name,
                    "familyName": patient.family_name,
                    "birthdate": patient.birthdate.isoformat() if patient.birthdate else "1985-01-01",
                    "gender": patient.gender,
                    "stateProvince": patient.state_province,
                    "cityVillage": patient.city_village,
                    "phoneNumber": patient.phone_number
                },
                "visits": [],
                "encounters": [],
                "obs": []
            }
        }
        
        # Add visits
        for visit in patient.visits:
            patient_data["messageData"]["visits"].append({
                "visitUuid": str(visit.visit_uuid),
                "dateStarted": visit.date_started.isoformat() if visit.date_started else "",
                "dateStopped": visit.date_stopped.isoformat() if visit.date_stopped else "",
                "visitType": visit.visit_type,
                "voided": 0
            })
        
        # Add encounters and observations
        for encounter in patient.encounters:
            patient_data["messageData"]["encounters"].append({
                "encounterUuid": str(encounter.encounter_uuid),
                "encounterDatetime": encounter.encounter_datetime.isoformat() if encounter.encounter_datetime else "",
                "encounterType": encounter.encounter_type,
                "voided": 0
            })
            
            for obs in encounter.observations:
                patient_data["messageData"]["obs"].append({
                    "obsUuid": str(obs.obs_uuid),
                    "obsDatetime": obs.obs_datetime.isoformat() if obs.obs_datetime else "",
                    "variableName": obs.variable_name,
                    "valueNumeric": obs.value_numeric,
                    "valueText": obs.value_text,
                    "valueCoded": obs.value_coded,
                    "voided": 0
                })
        
        return patient_data
    
    async def get_feature_extraction_status(
        self,
        patient_uuids: List[str]
    ) -> Dict[str, str]:
        """
        Get feature extraction status for multiple patients.
        
        Args:
            patient_uuids: List of patient UUIDs
            
        Returns:
            Dictionary mapping patient_uuid to status
        """
        feature_store = await get_feature_store()
        status_dict = {}
        
        for uuid in patient_uuids:
            cached = await feature_store.get_features(uuid)
            status_dict[uuid] = "cached" if cached else "pending"
        
        return status_dict
    
    async def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)


# Global instance
_async_extractor: Optional[AsyncFeatureExtractor] = None


async def get_async_extractor() -> AsyncFeatureExtractor:
    """Get or create global async feature extractor instance"""
    global _async_extractor
    if _async_extractor is None:
        _async_extractor = AsyncFeatureExtractor(
            max_workers=getattr(settings, 'async_feature_workers', 4)
        )
    return _async_extractor


async def extract_patient_features_async(
    patient_uuid: str,
    force_refresh: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to extract features for a single patient.
    
    Args:
        patient_uuid: Patient UUID
        force_refresh: Force re-computation
        
    Returns:
        Extracted features or None
    """
    extractor = await get_async_extractor()
    return await extractor.extract_features_for_patient(patient_uuid, force_refresh)


async def extract_batch_features_async(
    patient_uuids: List[str],
    force_refresh: bool = False
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Convenience function to extract features for multiple patients.
    
    Args:
        patient_uuids: List of patient UUIDs
        force_refresh: Force re-computation
        
    Returns:
        Dictionary mapping patient_uuid to features
    """
    extractor = await get_async_extractor()
    return await extractor.extract_features_for_patients(patient_uuids, force_refresh)
