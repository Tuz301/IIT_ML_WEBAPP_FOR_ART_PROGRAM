#!/usr/bin/env python
"""Test script to verify server connectivity and HTTP responses."""

import urllib.request
import json
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_backend():
    """Test backend health endpoint."""
    print("=" * 60)
    print("Testing Backend (http://127.0.0.1:8000)")
    print("=" * 60)
    
    try:
        # Test health endpoint
        print("\n[1] Testing /health endpoint...")
        resp = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=10)
        data = json.loads(resp.read().decode())
        print(f"    Status: {resp.status} {resp.reason}")
        print(f"    Response: {json.dumps(data, indent=4)}")
        
        # Test API docs
        print("\n[2] Testing /docs endpoint...")
        resp = urllib.request.urlopen('http://127.0.0.1:8000/docs', timeout=10)
        print(f"    Status: {resp.status} {resp.reason}")
        print(f"    Content-Type: {resp.headers.get('Content-Type')}")
        
        print("\n✅ Backend is responding correctly!")
        return True
        
    except urllib.error.HTTPError as e:
        print(f"\n❌ HTTP Error: {e.code} {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"\n❌ Connection Error: {e.reason}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        return False

def test_frontend():
    """Test frontend server."""
    print("\n" + "=" * 60)
    print("Testing Frontend (http://127.0.0.1:5173)")
    print("=" * 60)
    
    try:
        print("\n[1] Testing root endpoint...")
        resp = urllib.request.urlopen('http://127.0.0.1:5173/', timeout=10)
        content = resp.read().decode()[:500]  # First 500 chars
        print(f"    Status: {resp.status} {resp.reason}")
        print(f"    Content-Type: {resp.headers.get('Content-Type')}")
        print(f"    Preview: {content[:100]}...")
        
        print("\n✅ Frontend is responding correctly!")
        return True
        
    except urllib.error.HTTPError as e:
        print(f"\n❌ HTTP Error: {e.code} {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"\n❌ Connection Error: {e.reason}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        return False

def test_localhost():
    """Test specifically with localhost hostname."""
    print("\n" + "=" * 60)
    print("Testing with localhost (DNS resolution)")
    print("=" * 60)
    
    try:
        print("\n[1] Testing http://localhost:8000/health...")
        resp = urllib.request.urlopen('http://localhost:8000/health', timeout=10)
        data = json.loads(resp.read().decode())
        print(f"    Status: {resp.status} {resp.reason}")
        print(f"    Response: {json.dumps(data, indent=4)}")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("SERVER CONNECTION TEST")
    print("=" * 60)
    
    backend_ok = test_backend()
    frontend_ok = test_frontend()
    localhost_ok = test_localhost()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Backend (127.0.0.1):  {'OK' if backend_ok else 'FAILED'}")
    print(f"Frontend (127.0.0.1): {'OK' if frontend_ok else 'FAILED'}")
    print(f"Backend (localhost):  {'OK' if localhost_ok else 'FAILED'}")
    print("=" * 60)
    
    if backend_ok and frontend_ok and localhost_ok:
        print("\n[SUCCESS] All servers are accessible!")
        print("\nTROUBLESHOOTING BROWSER ISSUES:")
        print("1. Try clearing browser cache and cookies")
        print("2. Disable browser extensions temporarily")
        print("3. Check browser proxy settings")
        print("4. Try incognito/private mode")
        print("5. Check Windows Firewall for browser-specific rules")
        return 0
    else:
        print("\n[WARNING] Some servers are not responding correctly!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
