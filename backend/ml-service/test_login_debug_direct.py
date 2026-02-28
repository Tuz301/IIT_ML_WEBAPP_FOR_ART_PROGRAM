"""
Direct test to see the actual error during login
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models import User
from app.auth import authenticate_user

def test_login():
    """Test login with debug output"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("Testing login for user: admin")
        print("=" * 60)
        
        # First, check if user exists
        print("\n1. Checking if user exists...")
        user = db.query(User).filter(User.username == "admin").first()
        if user:
            print(f"   User found: {user.username}")
            print(f"   User ID: {user.id}")
            print(f"   User email: {user.email}")
            print(f"   User active: {user.is_active}")
        else:
            print("   User NOT found!")
            return
        
        # Now try to authenticate
        print("\n2. Attempting authentication...")
        try:
            authenticated_user = authenticate_user(db, "admin", "admin123")
            if authenticated_user:
                print(f"   Authentication SUCCESS!")
                print(f"   Authenticated user: {authenticated_user.username}")
                
                # Try to access roles
                print("\n3. Trying to access roles...")
                try:
                    roles_list = list(authenticated_user.roles)
                    print(f"   Roles: {[r.name for r in roles_list]}")
                except Exception as e:
                    print(f"   ERROR accessing roles: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("   Authentication FAILED!")
        except Exception as e:
            print(f"   ERROR during authentication: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    test_login()
