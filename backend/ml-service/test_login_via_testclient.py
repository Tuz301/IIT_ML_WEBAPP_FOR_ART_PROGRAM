"""
Test login using FastAPI TestClient to simulate actual HTTP request
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from app.main import app

def test_login_via_testclient():
    """Test login using TestClient"""
    print("=" * 60)
    print("Testing login via FastAPI TestClient")
    print("=" * 60)
    
    client = TestClient(app)
    
    # Test login
    print("\n1. Testing POST /v1/auth/login...")
    response = client.post(
        "/v1/auth/login",
        data={
            "username": "admin",
            "password": "admin123"
        }
    )
    
    print(f"   Status code: {response.status_code}")
    print(f"   Response: {response.text[:500]}")
    
    if response.status_code == 200:
        print("\n   SUCCESS: Login worked!")
        print(f"   Response keys: {response.json().keys()}")
    else:
        print(f"\n   FAILED: Status {response.status_code}")
        print(f"   Error: {response.json()}")

if __name__ == "__main__":
    test_login_via_testclient()
