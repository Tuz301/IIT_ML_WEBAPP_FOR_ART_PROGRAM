#!/usr/bin/env python3
"""
Test script to verify application imports work correctly
"""
try:
    from app.main import app
    print("✓ Application imports successfully")
    print(f"✓ FastAPI app created: {app.title}")
    print(f"✓ App version: {app.version}")
    print("✓ All routers imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)
