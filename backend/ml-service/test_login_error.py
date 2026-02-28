"""
Test script to reproduce the login error and see the actual error message
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.db import SessionLocal
from app.models import User
from sqlalchemy.orm import joinedload
import traceback

def test_user_query():
    """Test querying user with roles"""
    db = SessionLocal()
    try:
        print("Testing user query with joinedload(User.roles)...")
        user = db.query(User).options(joinedload(User.roles)).filter(
            User.username == "admin"
        ).first()
        
        if user:
            print(f"User found: {user.username}")
            print(f"User ID: {user.id}")
            print(f"User email: {user.email}")
            try:
                roles = [role.name for role in user.roles]
                print(f"User roles: {roles}")
            except Exception as e:
                print(f"Error accessing user.roles: {e}")
                traceback.print_exc()
        else:
            print("User not found")
    except Exception as e:
        print(f"Error during query: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_user_query()
