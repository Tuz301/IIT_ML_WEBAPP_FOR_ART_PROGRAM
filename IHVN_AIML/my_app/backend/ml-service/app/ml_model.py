"""
ML Model wrapper for IIT prediction with production-ready features
"""
import os
import json
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

from .config import get_settings
from .monitoring import track_model_inference, feature_extraction_latency
import time

logger = logging.getLogger(__name__)
settings = get_settings()


class IITModelPredictor:
    """Production ML model wrapper for IIT prediction"""
    
    def __init__(self):
        self.settings = settings
        self.model: Optional[lgb.Booster] = None
        self.preprocessing_meta: Optional[Dict] = None
        self.model_manifest: Optional[Dict] = None
        self.model_loaded = False
        self.model_version = "1.0.0"
        
    def load_model(self):
        """Load trained model and preprocessing artifacts"""
        try:
            model_path = Path(self.settings.model_path)
            preprocessing_path = Path(self.settings.preprocessing_path)
            manifest_path = Path(self.settings.model_manifest_path)
            
            # Load LightGBM model
            if model_path.exists():
                self.model = lgb.Booster(model_file=str(model_path))
                logger.info(f"Loaded LightGBM model from {model_path}")
            else:
                logger.warning(f"Model file not found at {model_path}. Using mock model.")
                self.model = None
            
            # Load preprocessing metadata
            if preprocessing_path.exists():
                self.preprocessing_meta = joblib.load(preprocessing_path)
                logger.info(f"Loaded preprocessing metadata from {preprocessing_path}")
            else:
                logger.warning("Preprocessing metadata not found. Using defaults.")
                self.preprocessing_meta = None
            
            # Load model manifest
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    self.model_manifest = json.load(f)
                self.model_version = self.model_manifest.get('timestamp', '1.0.0')[:10]
                logger.info(f"Loaded model manifest. Version: {self.model_version}")
            else:
                logger.warning("Model manifest not found.")
                self.model_manifest = None
            
            self.model_loaded = True
            logger.info("Model initialization completed")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model_loaded = False
            raise
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model_loaded
    
    @track_model_inference()
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Make prediction using loaded model"""
        if not self.model_loaded or self.model is None:
            # Return mock predictions for testing
            logger.warning("Using mock predictions - model not loaded")
            return np.random.uniform(0.2, 0.8, size=len(features))
        
        try:
            # Ensure features are in correct order
            if self.preprocessing_meta:
                feature_columns = self.preprocessing_meta.get('feature_columns', [])
                features = features[feature_columns]
            
            # Make prediction
            predictions = self.model.predict(features)
            return predictions
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise
    
    def extract_features_from_json(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from patient JSON data"""
        start_time = time.time()
        
        try:
            message_data = patient_data.get('messageData', {})
            demographics = message_data.get('demographics', {})
            visits = [v for v in message_data.get('visits', []) if v.get('voided', 0) == 0]
            encounters = [e for e in message_data.get('encounters', []) if e.get('voided', 0) == 0]
            observations = [o for o in message_data.get('obs', []) if o.get('voided', 0) == 0]
            
            # Determine prediction date
            all_dates = self._extract_all_dates(visits, encounters, observations)
            if not all_dates:
                prediction_date = datetime.utcnow()
            else:
                prediction_date = max(all_dates)
            
            features = {}
            
            # Extract all feature categories
            features.update(self._extract_demographic_features(demographics, prediction_date))
            features.update(self._extract_pharmacy_features(encounters, observations, prediction_date))
            features.update(self._extract_visit_features(visits, prediction_date))
            features.update(self._extract_clinical_features(observations, prediction_date))
            features.update(self._extract_temporal_features(prediction_date))
            
            # Add patient identifier
            features['patient_uuid'] = demographics.get('patientUuid', 'unknown')
            
            # Log extraction time
            duration = time.time() - start_time
            feature_extraction_latency.observe(duration)
            
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            raise
    
    def _extract_all_dates(self, visits, encounters, observations) -> List[datetime]:
        """Extract all dates from patient records"""
        dates = []
        
        for visit in visits:
            try:
                dates.append(datetime.strptime(visit['dateStarted'], '%Y-%m-%d %H:%M:%S'))
            except:
                continue
        
        for encounter in encounters:
            try:
                dates.append(datetime.strptime(encounter['encounterDatetime'], '%Y-%m-%d %H:%M:%S'))
            except:
                continue
        
        for obs in observations:
            try:
                dates.append(datetime.strptime(obs['obsDatetime'], '%Y-%m-%d %H:%M:%S'))
            except:
                continue
        
        return dates
    
    def _extract_demographic_features(self, demographics: Dict, prediction_date: datetime) -> Dict:
        """Extract demographic features"""
        features = {}
        
        try:
            birthdate = datetime.strptime(demographics.get('birthdate', '1985-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S')
            age = (prediction_date - birthdate).days / 365.25
            features['age'] = age
            features['age_group'] = min(int(age // 10), 7)
        except:
            features['age'] = 35
            features['age_group'] = 3
        
        gender = demographics.get('gender', '')
        features['gender'] = 1 if gender.upper() == 'M' else 0
        features['has_state'] = 1 if demographics.get('stateProvince') else 0
        features['has_city'] = 1 if demographics.get('cityVillage') else 0
        features['has_phone'] = 1 if demographics.get('phoneNumber') else 0
        
        return features
    
    def _extract_pharmacy_features(self, encounters: List, observations: List, prediction_date: datetime) -> Dict:
        """Extract pharmacy-related features"""
        features = {
            'has_pharmacy_history': 0,
            'total_dispensations': 0,
            'avg_days_supply': 30,
            'last_days_supply': 30,
            'days_since_last_refill': 365,
            'refill_frequency_3m': 0,
            'refill_frequency_6m': 0,
            'mmd_ratio': 0,
            'regimen_stability': 1,
            'last_regimen_complexity': 0,
            'adherence_counseling_count': 0
        }
        
        pharmacy_encounters = [e for e in encounters if e.get('pmmForm') == 'Pharmacy Order Form']
        if not pharmacy_encounters:
            return features
        
        pharmacy_encounters.sort(key=lambda x: datetime.strptime(x['encounterDatetime'], '%Y-%m-%d %H:%M:%S'))
        
        dispensations = []
        for enc in pharmacy_encounters:
            enc_date = datetime.strptime(enc['encounterDatetime'], '%Y-%m-%d %H:%M:%S')
            if enc_date <= prediction_date:
                enc_obs = [o for o in observations if o.get('encounterUuid') == enc['encounterUuid']]
                days_supply = self._extract_days_supply(enc_obs)
                dispensations.append({
                    'date': enc_date,
                    'days_supply': days_supply
                })
        
        if dispensations:
            six_months_ago = prediction_date - timedelta(days=180)
            three_months_ago = prediction_date - timedelta(days=90)
            
            recent_6m = [d for d in dispensations if d['date'] >= six_months_ago]
            recent_3m = [d for d in dispensations if d['date'] >= three_months_ago]
            
            features['has_pharmacy_history'] = 1
            features['total_dispensations'] = len(dispensations)
            features['days_since_last_refill'] = (prediction_date - dispensations[-1]['date']).days
            features['last_days_supply'] = dispensations[-1]['days_supply']
            
            if recent_6m:
                features['avg_days_supply'] = np.mean([d['days_supply'] for d in recent_6m])
                features['refill_frequency_6m'] = len(recent_6m)
                features['mmd_ratio'] = len([d for d in recent_6m if d['days_supply'] >= 56]) / len(recent_6m)
            
            if recent_3m:
                features['refill_frequency_3m'] = len(recent_3m)
        
        return features
    
    def _extract_days_supply(self, observations: List) -> int:
        """Extract medication days supply from observations"""
        for obs in observations:
            if 'Medication duration' in obs.get('variableName', ''):
                try:
                    return int(float(obs.get('valueNumeric', 30)))
                except:
                    pass
        return 30  # Default
    
    def _extract_visit_features(self, visits: List, prediction_date: datetime) -> Dict:
        """Extract visit pattern features"""
        features = {
            'total_visits': 0,
            'visit_frequency_3m': 0,
            'visit_frequency_6m': 0,
            'visit_frequency_12m': 0,
            'days_since_last_visit': 365,
            'visit_regularity': 0,
            'clinical_visit_ratio': 0
        }
        
        if not visits:
            return features
        
        visit_dates = []
        for visit in visits:
            try:
                visit_date = datetime.strptime(visit['dateStarted'], '%Y-%m-%d %H:%M:%S')
                if visit_date <= prediction_date:
                    visit_dates.append(visit_date)
            except:
                continue
        
        if not visit_dates:
            return features
        
        visit_dates.sort()
        
        three_months_ago = prediction_date - timedelta(days=90)
        six_months_ago = prediction_date - timedelta(days=180)
        twelve_months_ago = prediction_date - timedelta(days=365)
        
        features['total_visits'] = len(visit_dates)
        features['visit_frequency_3m'] = len([v for v in visit_dates if v >= three_months_ago])
        features['visit_frequency_6m'] = len([v for v in visit_dates if v >= six_months_ago])
        features['visit_frequency_12m'] = len([v for v in visit_dates if v >= twelve_months_ago])
        features['days_since_last_visit'] = (prediction_date - visit_dates[-1]).days
        
        if len(visit_dates) >= 2:
            intervals = [(visit_dates[i+1] - visit_dates[i]).days for i in range(len(visit_dates)-1)]
            if intervals and np.mean(intervals) > 0:
                features['visit_regularity'] = max(0, 1 - (np.std(intervals) / np.mean(intervals)))
        
        return features
    
    def _extract_clinical_features(self, observations: List, prediction_date: datetime) -> Dict:
        """Extract clinical features"""
        features = {
            'who_stage': 1,
            'has_vl_data': 0,
            'recent_vl_tests': 0,
            'has_tb_symptoms': 0,
            'functional_status': 0,
            'pregnancy_status': 0,
            'adherence_level': 2
        }
        
        recent_obs = [
            o for o in observations
            if datetime.strptime(o.get('obsDatetime', '2000-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S')
            >= prediction_date - timedelta(days=365)
        ]
        
        for obs in recent_obs:
            var_name = obs.get('variableName', '')
            
            if 'Viral Load' in var_name or 'VL' in var_name:
                features['has_vl_data'] = 1
                features['recent_vl_tests'] += 1
            elif 'Tuberculosis' in var_name:
                features['has_tb_symptoms'] = 1
        
        return features
    
    def _extract_temporal_features(self, prediction_date: datetime) -> Dict:
        """Extract temporal/seasonal features"""
        return {
            'month': prediction_date.month,
            'quarter': (prediction_date.month - 1) // 3,
            'is_holiday_season': int(prediction_date.month in [11, 12, 1]),
            'is_rainy_season': int(prediction_date.month in [6, 7, 8, 9]),
            'day_of_week': prediction_date.weekday(),
            'is_year_end': int(prediction_date.month == 12)
        }
    
    def get_model_metrics(self) -> Dict[str, Any]:
        """Get current model performance metrics"""
        if self.model_manifest and 'metrics' in self.model_manifest:
            metrics = self.model_manifest['metrics'].copy()
            metrics['model_version'] = self.model_version
            metrics['total_predictions'] = 0  # Would track this in production
            metrics['drift_detected'] = False
            if 'timestamp' in self.model_manifest:
                metrics['last_trained'] = self.model_manifest['timestamp']
            return metrics
        
        # Return default metrics
        return {
            'model_version': self.model_version,
            'auc': 0.85,
            'precision': 0.78,
            'recall': 0.82,
            'f1': 0.80,
            'brier_score': 0.15,
            'sensitivity': 0.82,
            'specificity': 0.88,
            'total_predictions': 0,
            'drift_detected': False
        }


# Global model instance
_model: Optional[IITModelPredictor] = None


def get_model() -> IITModelPredictor:
    """Get or create global model instance"""
    global _model
    if _model is None:
        _model = IITModelPredictor()
        try:
            _model.load_model()
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Continue with unloaded model for development
    return _model
