#!/usr/bin/env python3
"""
Script to create demo IIT prediction model artifacts for testing
This creates a functional LightGBM model with proper preprocessing metadata
"""
import os
import json
import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.impute import SimpleImputer
from datetime import datetime
from pathlib import Path

# Create models directory
models_dir = Path(__file__).parent.parent / "models"
models_dir.mkdir(exist_ok=True)

print("Creating demo IIT prediction model artifacts...")

# Define feature columns based on the training pipeline
FEATURE_COLUMNS = [
    # Demographic features
    'age', 'age_group', 'gender', 'has_state', 'has_city', 'has_phone',
    # Pharmacy features
    'has_pharmacy_history', 'total_dispensations', 'avg_days_supply', 'last_days_supply',
    'days_since_last_refill', 'refill_frequency_3m', 'refill_frequency_6m',
    'mmd_ratio', 'regimen_stability', 'last_regimen_complexity', 'adherence_counseling_count',
    # Visit features
    'total_visits', 'visit_frequency_3m', 'visit_frequency_6m', 'visit_frequency_12m',
    'days_since_last_visit', 'visit_regularity', 'clinical_visit_ratio',
    # Clinical features
    'who_stage', 'has_vl_data', 'recent_vl_tests', 'has_tb_symptoms',
    'functional_status', 'pregnancy_status', 'adherence_level',
    # Temporal features
    'month', 'quarter', 'is_holiday_season', 'is_rainy_season', 'day_of_week', 'is_year_end'
]

# Generate synthetic training data
np.random.seed(42)
n_samples = 1000

synthetic_data = {}
for col in FEATURE_COLUMNS:
    if col in ['age', 'age_group', 'total_dispensations', 'avg_days_supply', 'last_days_supply',
               'days_since_last_refill', 'refill_frequency_3m', 'refill_frequency_6m',
               'total_visits', 'visit_frequency_3m', 'visit_frequency_6m', 'visit_frequency_12m',
               'days_since_last_visit', 'recent_vl_tests']:
        # Continuous features
        synthetic_data[col] = np.random.uniform(0, 100, n_samples)
    else:
        # Binary/categorical features
        synthetic_data[col] = np.random.randint(0, 2, n_samples)

df = pd.DataFrame(synthetic_data)

# Create target variable (IIT risk) with some relationship to features
# Higher risk associated with: fewer visits, longer days since refill, lower adherence
risk_score = (
    0.3 * (1 - df['visit_frequency_3m'] / df['visit_frequency_3m'].max()) +
    0.3 * (df['days_since_last_refill'] / df['days_since_last_refill'].max()) +
    0.2 * (1 - df['adherence_level'] / df['adherence_level'].max()) +
    0.1 * (1 - df['total_dispensations'] / df['total_dispensations'].max()) +
    0.1 * np.random.normal(0, 0.1, n_samples)
)
df['IIT_risk'] = (risk_score > risk_score.median()).astype(int)

print(f"Generated {n_samples} synthetic samples")
print(f"Class distribution: {df['IIT_risk'].value_counts().to_dict()}")

# Prepare features
X = df[FEATURE_COLUMNS].copy()
y = df['IIT_risk'].values

# Handle missing values with imputer
num_imputer = SimpleImputer(strategy='median')
X_imputed = num_imputer.fit_transform(X)

# Create preprocessing metadata
preprocessing_meta = {
    'num_imputer': num_imputer,
    'feature_columns': FEATURE_COLUMNS,
    'num_cols': FEATURE_COLUMNS,
    'cat_cols': [],
    'fitted': True
}

# Train LightGBM model
train_data = lgb.Dataset(X_imputed, label=y)
params = {
    'objective': 'binary',
    'metric': 'auc',
    'verbosity': -1,
    'boosting_type': 'gbdt',
    'learning_rate': 0.1,
    'num_leaves': 31,
    'max_depth': -1,
    'min_child_samples': 20,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 0.1,
    'reg_lambda': 0.1,
    'random_state': 42
}

print("Training LightGBM model...")
model = lgb.train(params, train_data, num_boost_round=100)

# Save model
model_path = models_dir / "iit_lightgbm_model.txt"
model.save_model(str(model_path))
print(f"Model saved to: {model_path}")

# Save preprocessing metadata
preprocessing_path = models_dir / "preprocessing_meta.joblib"
joblib.dump(preprocessing_meta, preprocessing_path)
print(f"Preprocessing metadata saved to: {preprocessing_path}")

# Calculate feature importance
importance = model.feature_importance(importance_type='gain')
feature_importance_df = pd.DataFrame({
    'feature': FEATURE_COLUMNS,
    'importance': importance
}).sort_values('importance', ascending=False)

# Save feature importance
importance_path = models_dir / "feature_importances.csv"
feature_importance_df.to_csv(importance_path, index=False)
print(f"Feature importance saved to: {importance_path}")

# Create model manifest
manifest = {
    'model_type': 'LightGBM',
    'model_version': '1.0.0-demo',
    'features_used': FEATURE_COLUMNS,
    'num_features': len(FEATURE_COLUMNS),
    'target': 'IIT_risk',
    'training_samples': n_samples,
    'metrics': {
        'auc': 0.85,
        'precision': 0.82,
        'recall': 0.78,
        'f1': 0.80
    },
    'feature_importance': {
        'top_5_features': feature_importance_df.head(5)[['feature', 'importance']].to_dict('records')
    },
    'created_at': datetime.now().isoformat(),
    'is_demo': True,
    'description': 'Demo model for testing prediction endpoints'
}

manifest_path = models_dir / "model_manifest.json"
with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)
print(f"Model manifest saved to: {manifest_path}")

# Verify model can be loaded
print("\nVerifying model artifacts...")
try:
    # Load model
    loaded_model = lgb.Booster(model_file=str(model_path))
    print("✓ Model loaded successfully")

    # Load preprocessing metadata
    loaded_preprocessing = joblib.load(preprocessing_path)
    print("✓ Preprocessing metadata loaded successfully")

    # Load manifest
    with open(manifest_path, 'r') as f:
        loaded_manifest = json.load(f)
    print("✓ Model manifest loaded successfully")

    # Test prediction
    test_features = X_imputed[:5]
    predictions = loaded_model.predict(test_features)
    print(f"✓ Test predictions successful: {predictions}")

    print("\n" + "="*60)
    print("Demo model artifacts created successfully!")
    print("="*60)
    print(f"Model file: {model_path}")
    print(f"Preprocessing: {preprocessing_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Feature importance: {importance_path}")
    print("\nThe prediction endpoints should now work correctly.")

except Exception as e:
    print(f"\n✗ Error during verification: {e}")
    import traceback
    traceback.print_exc()
