"""
Test TokenResponse with SQLAlchemy User object directly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models import User
from app.auth import authenticate_user, create_access_token, create_refresh_token
from app.schema import TokenResponse
from app.config import get_settings

def test_token_response_with_user():
    """Test TokenResponse with SQLAlchemy User object"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("Testing TokenResponse with SQLAlchemy User object")
        print("=" * 60)
        
        settings = get_settings()
        
        # Authenticate
        print("\n1. Authenticating user...")
        user = authenticate_user(db, "admin", "admin123")
        if not user:
            print("   ERROR: Authentication failed!")
            return
        print(f"   SUCCESS: Authenticated {user.username}")
        
        # Get roles
        print("\n2. Getting user roles...")
        roles_list = list(user.roles)
        roles = [role.name for role in roles_list]
        print(f"   SUCCESS: Roles = {roles}")
        
        # Create tokens
        print("\n3. Creating tokens...")
        access_token_data = {
            "sub": user.username,
            "user_id": user.id,
            "roles": roles
        }
        access_token = create_access_token(access_token_data)
        refresh_token_data = {
            "sub": user.username,
            "user_id": user.id
        }
        refresh_token = create_refresh_token(refresh_token_data)
        print(f"   SUCCESS: Tokens created")
        
        # Create TokenResponse with SQLAlchemy User object (like the endpoint does)
        print("\n4. Creating TokenResponse with SQLAlchemy User object...")
        try:
            token_response = TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
                user=user  # Passing SQLAlchemy User object directly
            )
            print(f"   SUCCESS: TokenResponse created")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Try to serialize
        print("\n5. Serializing to JSON...")
        try:
            token_json = token_response.model_dump_json()
            print(f"   SUCCESS: JSON serialized")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
        
        print("\n" + "=" * 60)
        print("TEST PASSED!")
        print("=" * 60)
        
    finally:
        db.close()

if __name__ == "__main__":
    test_token_response_with_user()
