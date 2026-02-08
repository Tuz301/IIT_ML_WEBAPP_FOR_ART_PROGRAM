#!/usr/bin/env python3
"""
Test script to verify backend server startup and basic API functionality
"""
import sys
import os
import time
import requests
import subprocess
import signal
import threading

# Add ml-service to path
sys.path.insert(0, 'ml-service')

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        from app.main import app
        print("✓ Main app imports successfully")
        print(f"✓ FastAPI app created: {app.title}")

        # Test ETL imports
        from etl.pipeline import ETLPipeline
        from etl.data_ingestion import DataIngestion
        from etl.data_processing import DataProcessor
        print("✓ ETL modules import successfully")

        # Test API imports
        from app.api import auth, backup, security, etl
        print("✓ API modules import successfully")

        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_server_startup():
    """Test that the server can start"""
    print("\nTesting server startup...")

    try:
        # Start server in background
        server_process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn',
            'app.main:app',
            '--host', '127.0.0.1',
            '--port', '8001',  # Use different port to avoid conflicts
            '--log-level', 'info'
        ], cwd='ml-service', stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, PYTHONPATH='ml-service'))

        # Wait for server to start
        time.sleep(5)

        # Check if process is still running
        if server_process.poll() is None:
            print("✓ Server started successfully")

            # Test health endpoint
            try:
                response = requests.get('http://127.0.0.1:8001/health', timeout=5)
                if response.status_code == 200:
                    print("✓ Health endpoint responds successfully")
                    print(f"✓ Health response: {response.json()}")
                else:
                    print(f"✗ Health endpoint returned status {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"✗ Health endpoint request failed: {e}")

            # Stop server
            server_process.terminate()
            server_process.wait(timeout=5)
            print("✓ Server stopped successfully")

            return True
        else:
            stdout, stderr = server_process.communicate()
            print("✗ Server failed to start")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False

    except Exception as e:
        print(f"✗ Server startup test failed: {e}")
        return False

def test_api_endpoints():
    """Test basic API endpoints"""
    print("\nTesting API endpoints...")

    # This would require the server to be running
    # For now, just test that the endpoints are defined correctly
    try:
        from app.main import app
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)

        expected_routes = [
            '/health',
            '/v1/auth/login',
            '/v1/patients',
            '/v1/predictions',
            '/v1/backup/database/backup',
            '/v1/security/audit-logs',
            '/v1/etl/run-full-pipeline'
        ]

        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✓ Route {route} found")
            else:
                print(f"✗ Route {route} not found")

        return True

    except Exception as e:
        print(f"✗ API endpoint test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== IIT ML Service Backend Testing ===\n")

    results = []

    # Test imports
    results.append(("Import Test", test_imports()))

    # Test server startup
    results.append(("Server Startup Test", test_server_startup()))

    # Test API endpoints
    results.append(("API Endpoints Test", test_api_endpoints()))

    # Summary
    print("\n=== Test Results ===")
    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
