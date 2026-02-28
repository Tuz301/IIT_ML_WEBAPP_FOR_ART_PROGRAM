"""
Full login flow test to identify where the error occurs
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models import User
from app.auth import authenticate_user, create_access_token, create_refresh_token
from app.schema import TokenResponse, UserResponse
from app.config import get_settings

def test_full_login_flow():
    """Test the full login flow"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("Testing FULL login flow")
        print("=" * 60)
        
        settings = get_settings()
        
        # Step 1: Authenticate
        print("\n1. Authenticating user...")
        user = authenticate_user(db, "admin", "admin123")
        if not user:
            print("   ERROR: Authentication failed!")
            return
        print(f"   SUCCESS: Authenticated {user.username}")
        
        # Step 2: Get roles
        print("\n2. Getting user roles...")
        try:
            roles_list = list(user.roles)
            roles = [role.name for role in roles_list]
            print(f"   SUCCESS: Roles = {roles}")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 3: Create access token
        print("\n3. Creating access token...")
        try:
            access_token_data = {
                "sub": user.username,
                "user_id": user.id,
                "roles": roles
            }
            access_token = create_access_token(access_token_data)
            print(f"   SUCCESS: Access token created")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 4: Create refresh token
        print("\n4. Creating refresh token...")
        try:
            refresh_token_data = {
                "sub": user.username,
                "user_id": user.id
            }
            refresh_token = create_refresh_token(refresh_token_data)
            print(f"   SUCCESS: Refresh token created")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 5: Create UserResponse
        print("\n5. Creating UserResponse...")
        try:
            user_response = UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                created_at=user.created_at,
                updated_at=user.updated_at,
                roles=roles
            )
            print(f"   SUCCESS: UserResponse created")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 6: Create TokenResponse
        print("\n6. Creating TokenResponse...")
        try:
            token_response = TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
                user=user_response
            )
            print(f"   SUCCESS: TokenResponse created")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 7: Try to serialize to dict
        print("\n7. Serializing TokenResponse to dict...")
        try:
            token_dict = token_response.dict()
            print(f"   SUCCESS: Serialized")
            print(f"   Keys: {list(token_dict.keys())}")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 8: Try to serialize to JSON
        print("\n8. Serializing TokenResponse to JSON...")
        try:
            import json
            token_json = token_response.json()
            print(f"   SUCCESS: JSON serialized")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return
        
        print("\n" + "=" * 60)
        print("ALL STEPS PASSED!")
        print("=" * 60)
        
    finally:
        db.close()

if __name__ == "__main__":
    test_full_login_flow()
