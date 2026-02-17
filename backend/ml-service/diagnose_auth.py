#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic script to identify and fix backend authentication issues.

This script checks:
1. Database connectivity
2. Database table existence
3. User existence
4. JWT configuration
5. Required dependencies

Run this script to diagnose and fix authentication issues.
"""

import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add app directory to path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_success(message: str):
    """Print a success message"""
    print(f"[OK] {message}")

def print_error(message: str):
    """Print an error message"""
    print(f"[ERROR] {message}")

def print_warning(message: str):
    """Print a warning message"""
    print(f"[WARN] {message}")

def print_info(message: str):
    """Print an info message"""
    print(f"[INFO] {message}")

def check_dependencies():
    """Check if required dependencies are installed"""
    print_header("Checking Dependencies")
    
    required_packages = [
        ('fastapi', 'FastAPI'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('bcrypt', 'bcrypt'),
        ('jose', 'python-jose'),  # Note: import is 'jose' but package is 'python-jose'
        ('pydantic', 'Pydantic'),
    ]
    
    missing = []
    for package, display_name in required_packages:
        try:
            __import__(package)
            print_success(f"{display_name} is installed")
        except ImportError:
            print_error(f"{display_name} is NOT installed")
            missing.append(package)
    
    if missing:
        print_warning(f"\nMissing packages: {', '.join(missing)}")
        print_info("Install them with: pip install " + " ".join(missing))
        return False
    
    print_success("\nAll dependencies are installed")
    return True

def check_database():
    """Check database connectivity and tables"""
    print_header("Checking Database")
    
    try:
        from app.core.db import engine, Base, verify_database_connectivity
        from app.models import User, Role, Permission
        
        # Check connectivity
        if verify_database_connectivity():
            print_success("Database is accessible")
        else:
            print_error("Database is NOT accessible")
            return False
        
        # Check tables
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        required_tables = ['users', 'roles', 'permissions', 'user_roles', 'role_permissions']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print_warning(f"Missing tables: {', '.join(missing_tables)}")
            print_info("Creating missing tables...")
            
            try:
                Base.metadata.create_all(bind=engine)
                print_success("Database tables created")
            except Exception as e:
                print_error(f"Failed to create tables: {e}")
                return False
        else:
            print_success("All required tables exist")
        
        return True
        
    except Exception as e:
        print_error(f"Database check failed: {e}")
        return False

def check_users():
    """Check if users exist in database"""
    print_header("Checking Users")
    
    try:
        from app.core.db import SessionLocal
        from app.models import User, Role
        
        db = SessionLocal()
        
        # Check user count
        user_count = db.query(User).count()
        print_info(f"Users in database: {user_count}")
        
        if user_count == 0:
            print_warning("No users found in database")
            return False
        
        # List users
        users = db.query(User).all()
        print_info("Existing users:")
        for user in users:
            roles = [role.name for role in user.roles]
            print(f"  - {user.username} ({user.email}) - Roles: {', '.join(roles) or 'None'}")
        
        db.close()
        return True
        
    except Exception as e:
        print_error(f"Failed to check users: {e}")
        return False

def check_roles():
    """Check if roles exist"""
    print_header("Checking Roles")
    
    try:
        from app.core.db import SessionLocal
        from app.models import Role
        
        db = SessionLocal()
        
        # Check role count
        role_count = db.query(Role).count()
        print_info(f"Roles in database: {role_count}")
        
        if role_count == 0:
            print_warning("No roles found in database")
            return False
        
        # List roles
        roles = db.query(Role).all()
        print_info("Existing roles:")
        for role in roles:
            permissions = [perm.name for perm in role.permissions]
            print(f"  - {role.name}: {', '.join(permissions) or 'No permissions'}")
        
        db.close()
        return True
        
    except Exception as e:
        print_error(f"Failed to check roles: {e}")
        return False

def check_config():
    """Check JWT configuration"""
    print_header("Checking Configuration")
    
    try:
        from app.config import get_settings
        
        settings = get_settings()
        
        # Check JWT secret
        if not settings.jwt_secret_key or settings.jwt_secret_key == "your-secret-key":
            print_error("JWT_SECRET_KEY is not configured")
            print_info("Generate a secure key with:")
            print_info("  python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
            return False
        else:
            print_success("JWT_SECRET_KEY is configured")
        
        # Check other settings
        print_info(f"JWT Algorithm: {settings.jwt_algorithm}")
        print_info(f"Access Token Expires: {settings.access_token_expire_minutes} minutes")
        print_info(f"Refresh Token Expires: {settings.refresh_token_expire_days} days")
        
        return True
        
    except Exception as e:
        print_error(f"Configuration check failed: {e}")
        return False

def create_default_user():
    """Create default admin user"""
    print_header("Creating Default User")
    
    try:
        from app.core.db import SessionLocal
        from app.models import User, Role
        from app.auth import get_password_hash, create_default_roles_and_permissions
        
        db = SessionLocal()
        
        # Create roles first
        try:
            create_default_roles_and_permissions(db)
            print_success("Default roles created")
        except Exception as e:
            print_warning(f"Roles might exist: {e}")
        
        # Check if admin user exists
        admin = db.query(User).filter(User.username == 'admin').first()
        
        if admin:
            print_warning("Admin user already exists")
            print_info("Username: admin")
            print_info("Email: admin@example.com")
        else:
            # Create admin user
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
            
            db.add(admin)
            db.commit()
            db.refresh(admin)
            
            print_success("Admin user created")
            print_info("Username: admin")
            print_info("Password: admin123")
            print_info("Email: admin@example.com")
        
        db.close()
        return True
        
    except Exception as e:
        print_error(f"Failed to create default user: {e}")
        return False

def test_login():
    """Test login endpoint"""
    print_header("Testing Login")
    
    try:
        import requests
        
        # Check if backend is running
        try:
            response = requests.get('http://localhost:8000/health/', timeout=2)
            if response.status_code == 200:
                print_success("Backend is running")
            else:
                print_warning(f"Backend returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print_error("Backend is NOT running on http://localhost:8000")
            print_info("Start the backend with:")
            print_info("  cd backend/ml-service")
            print_info("  uvicorn app.main:app --reload")
            return False
        
        # Test login
        print_info("Testing login endpoint...")
        
        response = requests.post(
            'http://localhost:8000/v1/auth/login',
            data={
                'username': 'admin',
                'password': 'admin123'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print_success("Login successful!")
            data = response.json()
            print_info(f"Access Token: {data.get('access_token', 'N/A')[:20]}...")
            print_info(f"User: {data.get('user', {}).get('username', 'N/A')}")
            return True
        else:
            print_error(f"Login failed with status {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except ImportError:
        print_warning("requests library not installed")
        print_info("Install it with: pip install requests")
        return None
    except Exception as e:
        print_error(f"Login test failed: {e}")
        return False

def main():
    """Main diagnostic function"""
    print_header("IIT ML Service - Authentication Diagnostic")
    
    all_passed = True
    
    # Run checks
    if not check_dependencies():
        all_passed = False
        print_error("\n❌ Dependency check failed")
        print_info("Please install missing dependencies and run again")
        return 1
    
    if not check_database():
        all_passed = False
        print_error("\n❌ Database check failed")
        return 1
    
    if not check_roles():
        all_passed = False
        print_warning("\n⚠️  Roles check failed")
    
    if not check_users():
        print_warning("\n⚠️  No users found")
        print_info("Creating default user...")
        if not create_default_user():
            print_error("\n❌ Failed to create default user")
            return 1
    
    if not check_config():
        all_passed = False
        print_error("\n❌ Configuration check failed")
        return 1
    
    # Test login if all checks passed
    if all_passed:
        test_login()
    
    # Summary
    print_header("Diagnostic Summary")
    
    if all_passed:
        print_success("\n✅ All checks passed!")
        print_info("\nYou can now login with:")
        print_info("  Username: admin")
        print_info("  Password: admin123")
        print_info("\nFrontend URL: http://localhost:5173/login")
        print_info("Backend URL: http://localhost:8000/docs")
        return 0
    else:
        print_error("\n❌ Some checks failed")
        print_info("Please fix the issues above and run again")
        return 1

if __name__ == "__main__":
    sys.exit(main())
