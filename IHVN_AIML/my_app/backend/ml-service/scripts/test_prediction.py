#!/usr/bin/env python3
"""
Script to test prediction API with sample data
"""
import requests
import json
from datetime import datetime


SAMPLE_PATIENT = {
    "messageData": {
        "demographics": {
            "patientUuid": "sample-patient-001",
            "birthdate": "1985-06-15 00:00:00",
            "gender": "F",
            "stateProvince": "Lagos",
            "cityVillage": "Ikeja",
            "phoneNumber": "+234801234567"
        },
        "visits": [
            {
                "dateStarted": "2024-10-01 10:30:00",
                "voided": 0,
                "visitType": "CLINICAL"
            },
            {
                "dateStarted": "2024-09-01 09:15:00",
                "voided": 0,
                "visitType": "PHARMACY"
            }
        ],
        "encounters": [
            {
                "encounterUuid": "enc-001",
                "encounterDatetime": "2024-10-01 10:30:00",
                "pmmForm": "Pharmacy Order Form",
                "encounterType": "PHARMACY",
                "voided": 0
            }
        ],
        "obs": [
            {
                "obsDatetime": "2024-10-01 10:30:00",
                "variableName": "Medication duration",
                "valueNumeric": 90.0,
                "encounterUuid": "enc-001",
                "voided": 0
            },
            {
                "obsDatetime": "2024-10-01 10:30:00",
                "variableName": "Viral Load",
                "valueNumeric": 50.0,
                "voided": 0
            }
        ]
    }
}


def test_health(base_url: str):
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{base_url}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_predict(base_url: str):
    """Test single prediction endpoint"""
    print("\n=== Testing Single Prediction ===")
    response = requests.post(
        f"{base_url}/predict",
        json=SAMPLE_PATIENT
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nPrediction Results:")
        print(f"  Patient UUID: {result['patient_uuid']}")
        print(f"  IIT Risk Score: {result['iit_risk_score']:.4f}")
        print(f"  Risk Level: {result['risk_level']}")
        print(f"  Confidence: {result['confidence']:.4f}")
        print(f"  Model Version: {result['model_version']}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200


def test_batch_predict(base_url: str):
    """Test batch prediction endpoint"""
    print("\n=== Testing Batch Prediction ===")
    batch_request = {
        "patients": [SAMPLE_PATIENT, SAMPLE_PATIENT]
    }
    
    response = requests.post(
        f"{base_url}/batch_predict",
        json=batch_request
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nBatch Results:")
        print(f"  Batch ID: {result['batch_id']}")
        print(f"  Total Processed: {result['total_processed']}")
        print(f"  Failed Count: {result['failed_count']}")
        print(f"  Processing Time: {result['processing_time_seconds']:.2f}s")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200


def test_model_metrics(base_url: str):
    """Test model metrics endpoint"""
    print("\n=== Testing Model Metrics ===")
    response = requests.get(f"{base_url}/model_metrics")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        metrics = response.json()
        print(f"\nModel Metrics:")
        print(f"  AUC: {metrics['auc']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall: {metrics['recall']:.4f}")
        print(f"  F1 Score: {metrics['f1']:.4f}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200


def main():
    base_url = "http://localhost:8000"
    
    print("="*60)
    print("IIT Prediction API Test Suite")
    print("="*60)
    print(f"API Base URL: {base_url}")
    
    tests = [
        ("Health Check", lambda: test_health(base_url)),
        ("Single Prediction", lambda: test_predict(base_url)),
        ("Batch Prediction", lambda: test_batch_predict(base_url)),
        ("Model Metrics", lambda: test_model_metrics(base_url))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\nTest '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")


if __name__ == "__main__":
    main()
