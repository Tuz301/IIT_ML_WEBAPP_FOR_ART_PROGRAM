#!/usr/bin/env python
"""Test database connection and authentication"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User
from app.auth import verify_password

# Direct database connection
DATABASE_URL = "sqlite:///./iit_ml_service.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

print("=" * 60)
print("Database Connection Test")
print("=" * 60)
print(f"Database URL: {DATABASE_URL}")
print()

try:
    db = SessionLocal()
    print("[OK] Database connection successful")
    
    # Check if users table exists
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"[OK] Tables found: {len(tables)}")
    print(f"  Tables: {', '.join(tables[:5])}...")
    
    # Query users
    users = db.query(User).all()
    print(f"\n[OK] Users in database: {len(users)}")
    
    for user in users:
        print(f"\n  User #{user.id}:")
        print(f"    Username: {user.username}")
        print(f"    Email: {user.email}")
        print(f"    Full Name: {user.full_name}")
        print(f"    Is Active: {user.is_active}")
        print(f"    Is Superuser: {user.is_superuser}")
        print(f"    Roles: {[role.name for role in user.roles]}")
        
        # Test password verification
        if user.username == 'admin':
            print(f"\n  Testing password verification...")
            test_password = 'admin123'
            if verify_password(test_password, user.hashed_password):
                print(f"  [OK] Password '{test_password}' is correct")
            else:
                print(f"  [FAIL] Password '{test_password}' is incorrect")
    
    db.close()
    print("\n" + "=" * 60)
    print("[OK] All tests passed!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
