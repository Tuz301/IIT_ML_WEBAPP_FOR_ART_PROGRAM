"""
Test script to simulate FastAPI response serialization
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.db import SessionLocal
from app.models import User
from app.schema import TokenResponse, UserResponse
from app.auth import authenticate_user, create_access_token, create_refresh_token
from app.config import get_settings
from sqlalchemy.orm import joinedload
import json

def test_json_serialization():
    """Test JSON serialization of TokenResponse"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("TEST: JSON serialization of TokenResponse")
        print("=" * 60)

        # Authenticate user
        user = authenticate_user(db, "admin", "admin123")
        if not user:
            print("[ERROR] Authentication failed")
            return

        print(f"[OK] User authenticated: {user.username}")

        # Create tokens
        settings = get_settings()
        access_token = create_access_token({"sub": user.username, "user_id": user.id, "roles": ["admin"]})
        refresh_token = create_refresh_token({"sub": user.username, "user_id": user.id})
        print(f"[OK] Tokens created")

        # Create TokenResponse
        try:
            token_response = TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
                user=user
            )
            print(f"[OK] TokenResponse created")
        except Exception as e:
            print(f"[ERROR] Error creating TokenResponse: {e}")
            import traceback
            traceback.print_exc()
            return

        # Try to serialize to dict (like FastAPI does)
        try:
            response_dict = token_response.model_dump()
            print(f"[OK] TokenResponse serialized to dict")
            print(f"  Keys: {list(response_dict.keys())}")
        except Exception as e:
            print(f"[ERROR] Error serializing to dict: {e}")
            import traceback
            traceback.print_exc()
            return

        # Try to serialize to JSON (like FastAPI does)
        try:
            response_json = json.dumps(response_dict, default=str)
            print(f"[OK] TokenResponse serialized to JSON")
            print(f"  JSON length: {len(response_json)}")
        except Exception as e:
            print(f"[ERROR] Error serializing to JSON: {e}")
            import traceback
            traceback.print_exc()
            return

        print("[SUCCESS] All serialization tests passed")

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_json_serialization()
