#IIT PREEDICTION ML ALGORITHM
import os
import json
import pandas as pd
import numpy as np
import joblib
import lightgbm as lgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix, brier_score_loss
from sklearn.impute import SimpleImputer
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class EnhancedIITPredictor:
    def __init__(self, iit_grace_period=28, prediction_window=90):
        self.iit_grace_period = iit_grace_period
        self.prediction_window = prediction_window
        
    def process_json_directory(self, json_directory):
        """Process all JSON files in directory and create feature matrix"""
        all_patient_features = []
        
        for filename in os.listdir(json_directory):
            if filename.endswith('.json'):
                filepath = os.path.join(json_directory, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    features = self.extract_features_from_json(data)
                    if features:
                        all_patient_features.append(features)
                        
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")
                    continue
        
        return pd.DataFrame(all_patient_features)

    def extract_features_from_json(self, json_data):
        """Extract comprehensive features from JSON data"""
        try:
            demographics = json_data['messageData']['demographics']
            visits = [v for v in json_data['messageData']['visits'] if v.get('voided', 0) == 0]
            encounters = [e for e in json_data['messageData']['encounters'] if e.get('voided', 0) == 0]
            observations = [o for o in json_data['messageData']['obs'] if o.get('voided', 0) == 0]
            
            # Determine prediction date (last date in data minus buffer)
            all_dates = self._extract_all_dates(visits, encounters, observations)
            if not all_dates:
                return None
                
            prediction_date = max(all_dates) - timedelta(days=30)
            
            features = {}
            
            # Core demographic features
            features.update(self._extract_demographic_features(demographics, prediction_date))
            
            # Advanced pharmacy features
            pharmacy_features = self._extract_pharmacy_features(encounters, observations, prediction_date)
            features.update(pharmacy_features)
            
            # Visit pattern features
            visit_features = self._extract_visit_features(visits, prediction_date)
            features.update(visit_features)
            
            # Clinical features
            clinical_features = self._extract_clinical_features(observations, prediction_date)
            features.update(clinical_features)
            
            # Temporal features
            temporal_features = self._extract_temporal_features(prediction_date)
            features.update(temporal_features)
            
            # IIT label calculation
            features['IIT_next_90d'] = self._calculate_iit_label(visits, encounters, observations, prediction_date)
            
            # Patient identifier
            features['patient_uuid'] = demographics.get('patientUuid', 'unknown')
            
            return features
            
        except Exception as e:
            print(f"Error extracting features: {str(e)}")
            return None

    def _extract_all_dates(self, visits, encounters, observations):
        """Extract all dates from patient records"""
        dates = []
        
        # Visit dates
        for visit in visits:
            try:
                dates.append(datetime.strptime(visit['dateStarted'], '%Y-%m-%d %H:%M:%S'))
            except:
                continue
                
        # Encounter dates
        for encounter in encounters:
            try:
                dates.append(datetime.strptime(encounter['encounterDatetime'], '%Y-%m-%d %H:%M:%S'))
            except:
                continue
                
        # Observation dates
        for obs in observations:
            try:
                dates.append(datetime.strptime(obs['obsDatetime'], '%Y-%m-%d %H:%M:%S'))
            except:
                continue
                
        return dates

    def _extract_demographic_features(self, demographics, prediction_date):
        """Extract demographic features"""
        features = {}
        
        # Age calculation
        try:
            birthdate = datetime.strptime(demographics['birthdate'], '%Y-%m-%d %H:%M:%S')
            age = (prediction_date - birthdate).days / 365.25
            features['age'] = age
            features['age_group'] = min(int(age // 10), 7)  # 0-7 age groups
        except:
            features['age'] = 35  # Default age
            features['age_group'] = 3
            
        # Gender (encoded as binary)
        gender = demographics.get('gender', '')
        features['gender'] = 1 if gender.upper() == 'M' else 0
        
        # Location features
        features['has_state'] = 1 if demographics.get('stateProvince') else 0
        features['has_city'] = 1 if demographics.get('cityVillage') else 0
        
        # Contact information
        features['has_phone'] = 1 if demographics.get('phoneNumber') else 0
        
        return features

    def _extract_pharmacy_features(self, encounters, observations, prediction_date):
        """Extract advanced pharmacy behavior features"""
        features = {
            'has_pharmacy_history': 0,
            'total_dispensations': 0,
            'avg_days_supply': 0,
            'last_days_supply': 0,
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
            
        # Sort encounters by date
        pharmacy_encounters.sort(key=lambda x: datetime.strptime(x['encounterDatetime'], '%Y-%m-%d %H:%M:%S'))
        
        # Extract dispensation details
        dispensations = []
        for enc in pharmacy_encounters:
            enc_obs = [o for o in observations if o.get('encounterUuid') == enc['encounterUuid']]
            dispense_data = self._parse_dispensation_data(enc_obs, enc)
            if dispense_data:
                dispensations.append(dispense_data)
        
        if not dispensations:
            return features
            
        # Filter to pre-prediction date
        recent_dispensations = [d for d in dispensations if d['date'] <= prediction_date]
        if not recent_dispensations:
            return features
            
        last_dispense = recent_dispensations[-1]
        six_months_ago = prediction_date - timedelta(days=180)
        three_months_ago = prediction_date - timedelta(days=90)
        
        recent_6m_dispensations = [d for d in recent_dispensations if d['date'] >= six_months_ago]
        recent_3m_dispensations = [d for d in recent_dispensations if d['date'] >= three_months_ago]
        
        # Calculate features
        features.update({
            'has_pharmacy_history': 1,
            'total_dispensations': len(recent_dispensations),
            'avg_days_supply': np.mean([d.get('days_supply', 30) for d in recent_6m_dispensations]),
            'last_days_supply': last_dispense.get('days_supply', 30),
            'days_since_last_refill': (prediction_date - last_dispense['date']).days,
            'refill_frequency_3m': len(recent_3m_dispensations),
            'refill_frequency_6m': len(recent_6m_dispensations),
            'mmd_ratio': len([d for d in recent_6m_dispensations if d.get('days_supply', 0) >= 56]) / max(len(recent_6m_dispensations), 1),
            'adherence_counseling_count': len([d for d in recent_6m_dispensations if d.get('had_counseling', False)])
        })
        
        # Regimen complexity (simplified - 1 if complex regimen, 0 if simple)
        last_regimen = last_dispense.get('regimen', '')
        features['last_regimen_complexity'] = 1 if 'DTG' in str(last_regimen) or 'EFV' in str(last_regimen) else 0
        
        return features

    def _parse_dispensation_data(self, observations, encounter):
        """Parse medication dispensation data from observations"""
        try:
            dispense_date = datetime.strptime(encounter['encounterDatetime'], '%Y-%m-%d %H:%M:%S')
            
            days_supply = None
            quantity = None
            regimen = None
            had_counseling = False
            
            for obs in observations:
                var_name = obs.get('variableName', '')
                value = obs.get('valueNumeric') or obs.get('valueText') or obs.get('valueCoded')
                
                if 'Medication duration' in var_name and value:
                    days_supply = float(value)
                elif 'Medication dispensed' in var_name and value:
                    quantity = float(value)
                elif 'regimen' in var_name.lower():
                    regimen = value
                elif 'Adherence counseling' in var_name and 'Yes' in str(value):
                    had_counseling = True
            
            # Default days supply if not found
            if days_supply is None:
                days_supply = 30 if quantity and quantity <= 60 else 90
                
            return {
                'date': dispense_date,
                'days_supply': days_supply,
                'quantity': quantity,
                'regimen': regimen,
                'had_counseling': had_counseling
            }
        except:
            return None

    def _extract_visit_features(self, visits, prediction_date):
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
            
        # Parse visit dates
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
        
        # Time windows
        three_months_ago = prediction_date - timedelta(days=90)
        six_months_ago = prediction_date - timedelta(days=180)
        twelve_months_ago = prediction_date - timedelta(days=365)
        
        # Calculate features
        recent_3m_visits = [v for v in visit_dates if v >= three_months_ago]
        recent_6m_visits = [v for v in visit_dates if v >= six_months_ago]
        recent_12m_visits = [v for v in visit_dates if v >= twelve_months_ago]
        
        features.update({
            'total_visits': len(visit_dates),
            'visit_frequency_3m': len(recent_3m_visits),
            'visit_frequency_6m': len(recent_6m_visits),
            'visit_frequency_12m': len(recent_12m_visits),
            'days_since_last_visit': (prediction_date - visit_dates[-1]).days
        })
        
        # Visit regularity (coefficient of variation of inter-visit intervals)
        if len(visit_dates) >= 2:
            intervals = [(visit_dates[i+1] - visit_dates[i]).days for i in range(len(visit_dates)-1)]
            if intervals and np.mean(intervals) > 0:
                features['visit_regularity'] = 1 - (np.std(intervals) / np.mean(intervals))
        
        return features

    def _extract_clinical_features(self, observations, prediction_date):
        """Extract clinical features from observations"""
        features = {
            'who_stage': 1,
            'has_vl_data': 0,
            'recent_vl_tests': 0,
            'has_tb_symptoms': 0,
            'functional_status': 0,  # 0=able to work, 1=limited
            'pregnancy_status': 0,   # 0=not pregnant, 1=pregnant
            'adherence_level': 2     # 2=good, 1=fair, 0=poor
        }
        
        recent_obs = [
            o for o in observations 
            if datetime.strptime(o.get('obsDatetime', '2000-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S') 
            >= prediction_date - timedelta(days=365)
        ]
        
        for obs in recent_obs:
            var_name = obs.get('variableName', '')
            value = obs.get('valueNumeric') or obs.get('valueText') or obs.get('valueCoded')
            
            if 'WHO' in var_name and 'STAGE' in var_name:
                try:
                    features['who_stage'] = int(value) if value else 1
                except:
                    pass
            elif 'Viral Load' in var_name or 'VL' in var_name:
                features['has_vl_data'] = 1
                features['recent_vl_tests'] = features.get('recent_vl_tests', 0) + 1
            elif 'Tuberculosis' in var_name and 'symptom' in var_name.lower():
                if 'Yes' in str(value) or 'true' in str(value).lower():
                    features['has_tb_symptoms'] = 1
            elif 'Functional Status' in var_name:
                if 'limited' in str(value).lower() or 'disabled' in str(value).lower():
                    features['functional_status'] = 1
            elif 'Pregnancy' in var_name:
                if 'pregnant' in str(value).lower() or 'yes' in str(value).lower():
                    features['pregnancy_status'] = 1
            elif 'Adherence' in var_name:
                if 'poor' in str(value).lower() or 'fair' in str(value).lower():
                    features['adherence_level'] = 1 if 'fair' in str(value).lower() else 0
        
        return features

    def _extract_temporal_features(self, prediction_date):
        """Extract temporal/seasonal features"""
        return {
            'month': prediction_date.month,
            'quarter': (prediction_date.month - 1) // 3,
            'is_holiday_season': int(prediction_date.month in [11, 12, 1]),
            'is_rainy_season': int(prediction_date.month in [6, 7, 8, 9]),
            'day_of_week': prediction_date.weekday(),
            'is_year_end': int(prediction_date.month == 12)
        }

    def _calculate_iit_label(self, visits, encounters, observations, prediction_date):
        """Calculate IIT label based on pharmacy and visit patterns"""
        # Simplified IIT calculation for demonstration
        # In practice, this would use the full pharmacy refill logic
        
        # Get last pharmacy encounter before prediction date
        pharmacy_encounters = [e for e in encounters if e.get('pmmForm') == 'Pharmacy Order Form']
        if not pharmacy_encounters:
            return 1  # No pharmacy history = high risk
            
        # Sort and get last dispensation
        pharmacy_encounters.sort(key=lambda x: datetime.strptime(x['encounterDatetime'], '%Y-%m-%d %H:%M:%S'))
        last_pharmacy = pharmacy_encounters[-1]
        last_dispense_date = datetime.strptime(last_pharmacy['encounterDatetime'], '%Y-%m-%d %H:%M:%S')
        
        # Check if patient had activity after prediction date
        follow_up_end = prediction_date + timedelta(days=self.prediction_window)
        
        # Check for any visits after prediction date
        recent_visits = [
            v for v in visits 
            if datetime.strptime(v['dateStarted'], '%Y-%m-%d %H:%M:%S') > prediction_date
            and datetime.strptime(v['dateStarted'], '%Y-%m-%d %H:%M:%S') <= follow_up_end
        ]
        
        # Check for any pharmacy encounters after prediction date
        recent_pharmacy = [
            e for e in encounters 
            if e.get('pmmForm') == 'Pharmacy Order Form'
            and datetime.strptime(e['encounterDatetime'], '%Y-%m-%d %H:%M:%S') > prediction_date
            and datetime.strptime(e['encounterDatetime'], '%Y-%m-%d %H:%M:%S') <= follow_up_end
        ]
        
        # IIT = no visits AND no pharmacy in follow-up period
        return 1 if not recent_visits and not recent_pharmacy else 0

# Enhanced Training Pipeline
class IITModelTrainer:
    def __init__(self, output_dir="./iit_model_artifacts"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.RANDOM_SEED = 42
        
    def train_from_json_directory(self, json_directory):
        """Complete training pipeline from JSON directory"""
        print("Processing JSON files...")
        predictor = EnhancedIITPredictor()
        df = predictor.process_json_directory(json_directory)
        
        if df is None or df.empty:
            raise ValueError("No valid data processed from JSON files")
            
        print(f"Processed {len(df)} patients")
        return self.train_from_dataframe(df)
    
    def train_from_dataframe(self, df):
        """Train model from prepared DataFrame"""
        # Define features (excluding target and ID columns)
        feature_columns = [col for col in df.columns if col not in ['IIT_next_90d', 'patient_uuid']]
        
        X = df[feature_columns].copy()
        y = df['IIT_next_90d'].astype(int).values
        
        print(f"Training on {len(feature_columns)} features")
        print(f"Class distribution: {np.bincount(y)}")
        
        # Handle missing values
        num_cols = X.select_dtypes(include=[np.number]).columns
        cat_cols = X.select_dtypes(include=['object', 'category']).columns
        
        # Impute numerical features
        num_imputer = SimpleImputer(strategy='median')
        X[num_cols] = num_imputer.fit_transform(X[num_cols])
        
        # Convert categorical features for LightGBM
        for col in cat_cols:
            X[col] = X[col].astype('category')
        
        # Save preprocessing artifacts
        preprocessing_meta = {
            'num_imputer': num_imputer,
            'feature_columns': feature_columns,
            'cat_cols': list(cat_cols),
            'num_cols': list(num_cols)
        }
        joblib.dump(preprocessing_meta, os.path.join(self.output_dir, 'preprocessing_meta.joblib'))
        
        # Train/validation split with stratification
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=self.RANDOM_SEED, stratify=y
        )
        
        # Handle class imbalance
        pos_rate = y_train.mean()
        scale_pos_weight = (1 - pos_rate) / max(pos_rate, 1e-6)
        
        # LightGBM parameters (optimized for IIT prediction)
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': -1,
            'min_child_samples': 20,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
            'random_state': self.RANDOM_SEED,
            'scale_pos_weight': scale_pos_weight
        }
        
        # Create LightGBM datasets
        lgb_train = lgb.Dataset(
            X_train, label=y_train, 
            categorical_feature=cat_cols, 
            free_raw_data=False
        )
        lgb_val = lgb.Dataset(
            X_val, label=y_val, 
            reference=lgb_train,
            categorical_feature=cat_cols, 
            free_raw_data=False
        )
        
        # Train with early stopping
        print("Training LightGBM model...")
        model = lgb.train(
            params,
            lgb_train,
            num_boost_round=1000,
            valid_sets=[lgb_train, lgb_val],
            valid_names=['train', 'val'],
            early_stopping_rounds=50,
            verbose_eval=50
        )
        
        # Evaluate model
        y_pred_proba = model.predict(X_val)
        y_pred = (y_pred_proba >= 0.5).astype(int)
        
        metrics = self._calculate_metrics(y_val, y_pred, y_pred_proba)
        print("Validation Metrics:", metrics)
        
        # Save model and artifacts
        self._save_artifacts(model, metrics, X_train, feature_columns)
        
        return model, metrics, df
    
    def _calculate_metrics(self, y_true, y_pred, y_pred_proba):
        """Calculate comprehensive evaluation metrics"""
        auc = roc_auc_score(y_true, y_pred_proba)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        brier = brier_score_loss(y_true, y_pred_proba)
        
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        return {
            'auc': float(auc),
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'brier_score': float(brier),
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_positives': int(tp),
            'sensitivity': float(tp / (tp + fn)) if (tp + fn) > 0 else 0,
            'specificity': float(tn / (tn + fp)) if (tn + fp) > 0 else 0
        }
    
    def _save_artifacts(self, model, metrics, X_train, feature_columns):
        """Save model artifacts"""
        # Save model
        model.save_model(os.path.join(self.output_dir, 'iit_lightgbm_model.txt'))
        
        # Save metrics
        joblib.dump(metrics, os.path.join(self.output_dir, 'model_metrics.joblib'))
        
        # Feature importance
        importance = model.feature_importance(importance_type='gain')
        feature_importance_df = pd.DataFrame({
            'feature': feature_columns,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        feature_importance_df.to_csv(
            os.path.join(self.output_dir, 'feature_importances.csv'), 
            index=False
        )
        
        # Manifest file
        manifest = {
            'model_type': 'LightGBM',
            'features_used': feature_columns,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(os.path.join(self.output_dir, 'model_manifest.json'), 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Model artifacts saved to: {self.output_dir}")

# Usage Example
if __name__ == "__main__":
    # Option 1: Train from JSON directory
    trainer = IITModelTrainer(output_dir="./optimized_iit_model")
    
    # Train model
    model, metrics, processed_data = trainer.train_from_json_directory(
        "/path/to/your/json/files"
    )
    
    # Save processed data for analysis
    processed_data.to_csv("./processed_patient_data.csv", index=False)
    
    print("Training completed successfully!")
    print(f"Final AUC: {metrics['auc']:.4f}")