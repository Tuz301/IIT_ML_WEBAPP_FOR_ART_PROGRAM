"""
Authentication utilities for IIT ML Service
Enhanced with httpOnly cookie support for improved security
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from .core.db import get_db
from .models import User, Role, Permission, UserRole, RolePermission
from .config import get_settings

# OAuth2 scheme (still supported for backward compatibility)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

settings = get_settings()


# Cookie names for JWT tokens
ACCESS_COOKIE_NAME = "iit_access_token"
REFRESH_COOKIE_NAME = "iit_refresh_token"


class TokenData(BaseModel):
    """Token data model"""
    username: Optional[str] = None
    token_type: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Ensure the hashed password is properly formatted
        if not hashed_password.startswith('$2b$') and not hashed_password.startswith('$2a$'):
            return False
        
        # Convert to bytes for bcrypt
        plain_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Verify using bcrypt
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as e:
        print(f"Password verification error: {e}")
        print(f"Plain password: {plain_password}")
        print(f"Hashed password: {hashed_password}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username/email and password"""
    # Try username first, then email
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str
) -> None:
    """
    Set JWT tokens as httpOnly cookies for improved security
    
    This prevents XSS attacks from stealing tokens since JavaScript
    cannot access httpOnly cookies.
    """
    # Calculate access token expiry
    access_max_age = settings.access_token_expire_minutes * 60
    refresh_max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    
    # Set access token cookie
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=access_max_age,
        expires=datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes),
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,  # Critical: prevents JavaScript access
        samesite=settings.cookie_samesite,
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=refresh_max_age,
        expires=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,  # Critical: prevents JavaScript access
        samesite=settings.cookie_samesite,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies"""
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path="/",
        domain=settings.cookie_domain,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        domain=settings.cookie_domain,
    )


def get_token_from_cookie(request: Request, cookie_name: str) -> Optional[str]:
    """Extract token from httpOnly cookie"""
    return request.cookies.get(cookie_name)


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        token_type_in_payload = payload.get("type")
        if token_type_in_payload != token_type:
            raise JWTError(f"Invalid token type: expected {token_type}, got {token_type_in_payload}")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Supports both Authorization header (Bearer token) and httpOnly cookie
    for backward compatibility and improved security.
    """
    # Try to get token from cookie first (more secure)
    cookie_token = get_token_from_cookie(request, ACCESS_COOKIE_NAME)
    
    # Fall back to Authorization header if cookie not present
    final_token = cookie_token or token
    
    if not final_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_token(final_token, "access")
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def check_user_permission(user: User, resource: str, action: str) -> bool:
    """Check if user has permission for a specific resource and action"""
    for role in user.roles:
        for permission in role.permissions:
            if permission.resource == resource and permission.action == action:
                return True
    return False


def require_permission(resource: str, action: str):
    """Decorator to require specific permission for endpoint"""
    def permission_dependency(current_user: User = Depends(get_current_active_user)):
        if not check_user_permission(current_user, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {action} on {resource}"
            )
        return current_user
    return permission_dependency


def create_default_roles_and_permissions(db: Session) -> None:
    """Create default roles and permissions"""

    # Define default permissions
    default_permissions = [
        # Patients
        {"name": "patients:read", "resource": "patients", "action": "read"},
        {"name": "patients:write", "resource": "patients", "action": "write"},
        {"name": "patients:delete", "resource": "patients", "action": "delete"},

        # Predictions
        {"name": "predictions:read", "resource": "predictions", "action": "read"},
        {"name": "predictions:write", "resource": "predictions", "action": "write"},

        # Features
        {"name": "features:read", "resource": "features", "action": "read"},
        {"name": "features:write", "resource": "features", "action": "write"},

        # Users and Roles
        {"name": "users:read", "resource": "users", "action": "read"},
        {"name": "users:write", "resource": "users", "action": "write"},
        {"name": "roles:read", "resource": "roles", "action": "read"},
        {"name": "roles:write", "resource": "roles", "action": "write"},
    ]

    # Create permissions
    for perm_data in default_permissions:
        perm = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not perm:
            perm = Permission(**perm_data)
            db.add(perm)
            db.commit()
            db.refresh(perm)

    # Define default roles and their permissions
    default_roles = {
        "admin": ["patients:read", "patients:write", "patients:delete",
                 "predictions:read", "predictions:write",
                 "features:read", "features:write",
                 "users:read", "users:write", "roles:read", "roles:write"],

        "clinician": ["patients:read", "patients:write",
                     "predictions:read", "predictions:write",
                     "features:read"],

        "analyst": ["patients:read", "predictions:read",
                   "features:read", "features:write"],

        "field_worker": ["patients:read", "patients:write",
                        "predictions:read", "features:read"]
    }

    # Create roles and assign permissions
    for role_name, perm_names in default_roles.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name, description=f"{role_name.title()} role")
            db.add(role)
            db.commit()
            db.refresh(role)

        # Assign permissions to role
        for perm_name in perm_names:
            perm = db.query(Permission).filter(Permission.name == perm_name).first()
            if perm and perm not in role.permissions:
                role.permissions.append(perm)

        db.commit()


def create_default_admin_user(db: Session) -> None:
    """Create default admin user"""
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            hashed_password = get_password_hash("admin123")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                full_name="System Administrator",
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True
            )
            admin_user.roles.append(admin_role)
            db.add(admin_user)
            db.commit()
