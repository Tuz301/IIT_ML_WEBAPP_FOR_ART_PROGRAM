#!/usr/bin/env python3
"""Debug script to test login functionality"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.db import get_db, engine
from app.models import User, Role
from app.auth import authenticate_user
from sqlalchemy.orm import joinedload
import traceback

print("=== Testing Database Connection ===")
try:
    db = next(get_db())
    print("[OK] Database connection successful")
except Exception as e:
    print(f"[FAIL] Database connection failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n=== Testing User Query ===")
try:
    admin = db.query(User).filter_by(username='admin').first()
    if admin:
        print(f"[OK] Found user: {admin.username}")
        print(f"  - Email: {admin.email}")
        print(f"  - Active: {admin.is_active}")
    else:
        print("[FAIL] Admin user not found")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] User query failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n=== Testing Roles Relationship ===")
try:
    # Test with eager loading
    admin_with_roles = db.query(User).options(joinedload(User.roles)).filter_by(username='admin').first()
    if admin_with_roles:
        print(f"[OK] User with roles loaded: {admin_with_roles.username}")
        print(f"  - Roles count: {len(admin_with_roles.roles)}")
        for role in admin_with_roles.roles:
            print(f"    - {role.name}: {role.description}")
    else:
        print("[FAIL] Failed to load user with roles")
except Exception as e:
    print(f"[FAIL] Roles relationship failed: {e}")
    traceback.print_exc()

print("\n=== Testing Authentication ===")
try:
    # Test with wrong password
    user = authenticate_user(db, 'admin', 'wrongpassword')
    if user is None:
        print("[OK] Authentication correctly failed for wrong password")
    else:
        print("[FAIL] Authentication should have failed")
except Exception as e:
    print(f"[FAIL] Authentication failed: {e}")
    traceback.print_exc()

print("\n=== Testing Login Endpoint Flow ===")
try:
    # Simulate the login endpoint flow
    admin = db.query(User).filter_by(username='admin').first()
    
    # Step 1: Check if user exists
    if not admin:
        print("[FAIL] User not found")
    else:
        print(f"[OK] User found: {admin.username}")
    
    # Step 2: Check if user is active
    if not admin.is_active:
        print("[FAIL] User is not active")
    else:
        print("[OK] User is active")
    
    # Step 3: Get user roles (this is where the error might occur)
    roles = [role.name for role in admin.roles]
    print(f"[OK] User roles: {roles}")
    
    print("\n[OK] All login flow steps passed!")
    
except Exception as e:
    print(f"[FAIL] Login flow failed: {e}")
    print(f"Error type: {type(e).__name__}")
    traceback.print_exc()

db.close()
print("\n=== Debug Complete ===")
