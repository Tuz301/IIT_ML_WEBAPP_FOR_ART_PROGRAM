#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create default admin user for IIT ML Service"""

import sys
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app.core.db import SessionLocal
from app.models import User, Role
from app.auth import get_password_hash, create_default_roles_and_permissions

def main():
    print("=" * 60)
    print("Creating Default Admin User")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Create roles first
        print("\n[1/3] Creating roles...")
        try:
            create_default_roles_and_permissions(db)
            print("[OK] Roles created successfully")
        except Exception as e:
            print(f"[WARN] Roles might exist: {e}")
        
        # Check if admin user exists
        print("\n[2/3] Checking for existing admin user...")
        admin = db.query(User).filter(User.username == 'admin').first()
        
        if admin:
            print(f"[OK] Admin user already exists")
            print(f"     Username: {admin.username}")
            print(f"     Email: {admin.email}")
            print(f"     Active: {admin.is_active}")
            print(f"     Superuser: {admin.is_superuser}")
            roles = [role.name for role in admin.roles]
            print(f"     Roles: {roles}")
        else:
            print("[INFO] Creating admin user...")
            hashed_password = get_password_hash('admin123')
            admin = User(
                username='admin',
                email='admin@example.com',
                full_name='System Administrator',
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True
            )
            
            # Assign admin role
            admin_role = db.query(Role).filter(Role.name == 'admin').first()
            if admin_role:
                admin.roles.append(admin_role)
                print(f"[OK] Assigned admin role")
            else:
                print("[WARN] Admin role not found")
            
            db.add(admin)
            db.commit()
            db.refresh(admin)
            
            print("[OK] Admin user created successfully")
            print(f"     Username: admin")
            print(f"     Password: admin123")
            print(f"     Email: admin@example.com")
        
        # Verify all users
        print("\n[3/3] Verifying all users...")
        all_users = db.query(User).all()
        print(f"[INFO] Total users in database: {len(all_users)}")
        
        for user in all_users:
            roles = [role.name for role in user.roles]
            print(f"     - {user.username} ({user.email})")
            print(f"       Roles: {roles}")
        
        print("\n" + "=" * 60)
        print("SUCCESS: Admin user setup complete!")
        print("=" * 60)
        print("\nYou can now login with:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\nFrontend URL: http://localhost:5173/login")
        print("Backend API: http://localhost:8000/docs")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Failed to create admin user: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
