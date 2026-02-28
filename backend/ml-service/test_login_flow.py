"""
Test script to simulate the full login flow and identify the error
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.db import SessionLocal
from app.models import User
from app.auth import authenticate_user, verify_password
from app.schema import TokenResponse, UserResponse
from sqlalchemy.orm import joinedload
import traceback

def test_authenticate_user():
    """Test authenticate_user function"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("TEST 1: authenticate_user function")
        print("=" * 60)
        user = authenticate_user(db, "admin", "admin123")
        if user:
            print(f"[OK] User authenticated: {user.username}")
            print(f"  User ID: {user.id}")
            print(f"  User email: {user.email}")
            print(f"  User is_active: {user.is_active}")
            try:
                roles = [role.name for role in user.roles]
                print(f"  User roles: {roles}")
            except Exception as e:
                print(f"[ERROR] Error accessing user.roles: {e}")
                traceback.print_exc()
        else:
            print("[ERROR] Authentication failed")
    except Exception as e:
        print(f"[ERROR] Error in authenticate_user: {e}")
        traceback.print_exc()
    finally:
        db.close()

def test_user_response_serialization():
    """Test UserResponse serialization"""
    db = SessionLocal()
    try:
        print("\n" + "=" * 60)
        print("TEST 2: UserResponse serialization")
        print("=" * 60)
        user = db.query(User).options(joinedload(User.roles)).filter(
            User.username == "admin"
        ).first()
        
        if user:
            print(f"[OK] User found: {user.username}")
            try:
                user_response = UserResponse.model_validate(user)
                print(f"[OK] UserResponse created successfully")
                print(f"  Username: {user_response.username}")
                print(f"  Roles: {user_response.roles}")
            except Exception as e:
                print(f"[ERROR] Error creating UserResponse: {e}")
                traceback.print_exc()
        else:
            print("[ERROR] User not found")
    except Exception as e:
        print(f"[ERROR] Error in test: {e}")
        traceback.print_exc()
    finally:
        db.close()

def test_token_response():
    """Test TokenResponse creation"""
    db = SessionLocal()
    try:
        print("\n" + "=" * 60)
        print("TEST 3: TokenResponse creation")
        print("=" * 60)
        user = db.query(User).options(joinedload(User.roles)).filter(
            User.username == "admin"
        ).first()
        
        if user:
            print(f"[OK] User found: {user.username}")
            try:
                token_response = TokenResponse(
                    access_token="test_token",
                    refresh_token="test_refresh",
                    token_type="bearer",
                    expires_in=3600,
                    user=user
                )
                print(f"[OK] TokenResponse created successfully")
                print(f"  Username: {token_response.user.username}")
                print(f"  Roles: {token_response.user.roles}")
            except Exception as e:
                print(f"[ERROR] Error creating TokenResponse: {e}")
                traceback.print_exc()
        else:
            print("[ERROR] User not found")
    except Exception as e:
        print(f"[ERROR] Error in test: {e}")
        traceback.print_exc()
    finally:
        db.close()

def test_roles_permissions():
    """Test accessing roles and permissions"""
    db = SessionLocal()
    try:
        print("\n" + "=" * 60)
        print("TEST 4: Roles and Permissions access")
        print("=" * 60)
        user = db.query(User).options(joinedload(User.roles)).filter(
            User.username == "admin"
        ).first()
        
        if user:
            print(f"[OK] User found: {user.username}")
            try:
                for role in user.roles:
                    print(f"  Role: {role.name}")
                    # Try to access permissions
                    try:
                        perms = [p.name for p in role.permissions]
                        print(f"    Permissions: {perms}")
                    except Exception as e:
                        print(f"    [ERROR] Error accessing permissions: {e}")
            except Exception as e:
                print(f"[ERROR] Error accessing roles: {e}")
                traceback.print_exc()
        else:
            print("[ERROR] User not found")
    except Exception as e:
        print(f"[ERROR] Error in test: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_authenticate_user()
    test_user_response_serialization()
    test_token_response()
    test_roles_permissions()
    print("\n" + "=" * 60)
    print("All tests completed")
    print("=" * 60)
