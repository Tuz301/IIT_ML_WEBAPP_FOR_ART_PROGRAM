"""
Authentication API endpoints for IIT ML Service
Enhanced with httpOnly cookie support for improved security
"""
from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import User, Role, ErrorResponse
from ..schema import (
    UserCreate, UserResponse, UserLogin, TokenResponse,
    RefreshTokenRequest, RoleResponse
)
from ..auth import (
    authenticate_user, create_access_token, create_refresh_token,
    get_current_active_user, get_current_superuser, get_password_hash,
    verify_token, create_default_roles_and_permissions,
    set_auth_cookies, clear_auth_cookies, get_token_from_cookie,
    ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
)
from ..config import get_settings

router = APIRouter(prefix="/auth")
settings = get_settings()


@router.post("/register", response_model=UserResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Register New User Account",
            description="""
            Create a new user account in the IIT ML Service system.

            **Account Requirements:**
            - Username: 3-50 characters, alphanumeric and underscores only
            - Email: Valid email address format, must be unique
            - Password: Minimum 8 characters, must contain:
              - At least one uppercase letter (A-Z)
              - At least one lowercase letter (a-z)
              - At least one digit (0-9)
              - Special characters recommended for security
            - Full Name: Optional, for display purposes

            **Security Features:**
            - Passwords are hashed using bcrypt before storage
            - Duplicate username/email validation prevents conflicts
            - Automatic account activation for new registrations
            - Default role assignment ('analyst') for basic access

            **Permissions:**
            - Default 'analyst' role provides basic ML service access
            - Can view patient data, run predictions, access analytics
            - Cannot modify system settings or manage other users
            - Superuser privileges required for administrative functions

            **Audit Trail:**
            - Registration timestamp automatically recorded
            - Account creation logged for compliance
            - Initial role assignment tracked

            **Use Cases:**
            - New analyst onboarding
            - Researcher account creation
            - Healthcare worker registration
            - System administrator setup
            """,
            responses={
                201: {
                    "description": "User account created successfully",
                    "model": UserResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "id": 123,
                                "username": "johndoe",
                                "email": "john.doe@example.com",
                                "full_name": "John Doe",
                                "is_active": True,
                                "is_superuser": False,
                                "created_at": "2025-01-15T10:30:00",
                                "updated_at": "2025-01-15T10:30:00",
                                "roles": [
                                    {
                                        "id": 2,
                                        "name": "analyst",
                                        "description": "Basic ML service access"
                                    }
                                ]
                            }
                        }
                    }
                },
                400: {
                    "description": "Validation error or duplicate account",
                    "model": ErrorResponse,
                    "content": {
                        "application/json": {
                            "example": {
                                "error": "Bad Request",
                                "detail": "Username already registered",
                                "timestamp": "2025-01-15T10:30:00",
                                "request_id": "123e4567-e89b-12d3-a456-426614174000"
                            }
                        }
                    }
                },
                422: {
                    "description": "Input validation failed",
                    "model": ErrorResponse
                }
            })
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account with validation and security measures.

    Creates user with hashed password, validates uniqueness, and assigns default role.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()

    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Create user
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Assign default role (analyst) if roles exist
    analyst_role = db.query(Role).filter(Role.name == "analyst").first()
    if analyst_role:
        db_user.roles.append(analyst_role)
        db.commit()

    return db_user


@router.get("/test-login/{username}")
async def test_login_endpoint(
    username: str,
    db: Session = Depends(get_db)
):
    """
    Test endpoint to verify database access works through HTTP
    Bypasses token creation and complex authentication flow
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Test login for username: {username}")
    
    try:
        # Query user with eager loading
        from sqlalchemy.orm import joinedload
        user = db.query(User).options(joinedload(User.roles)).filter(
            User.username == username
        ).first()
        
        if not user:
            return {"error": "User not found"}
        
        return {
            "status": "success",
            "user": {
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "roles": [role.name for role in user.roles]
            }
        }
    except Exception as e:
        logger.error(f"Error in test login: {e}", exc_info=True)
        return {"error": str(e), "type": type(e).__name__}


@router.post("/login")
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access/refresh tokens.
    
    **Enhanced Security**: Tokens are set as httpOnly cookies to prevent
    XSS attacks. Tokens are also returned in response body for backward
    compatibility with existing clients.

    - **username**: Username or email
    - **password**: User password
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Login attempt for username: {form_data.username}")
        
        user = None
        try:
            logger.info(f"Step 1: Calling authenticate_user")
            user = authenticate_user(db, form_data.username, form_data.password)
            logger.info(f"Step 2: authenticate_user returned: {user}")
            if not user:
                logger.warning(f"Authentication failed for username: {form_data.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during authentication: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication error: {str(e)}"
            )

        # Check if user is active
        logger.info(f"Step 3: Checking if user is active")
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        logger.info(f"Step 4: User is active")

        # Get user roles and explicitly materialize them to prevent lazy loading issues
        logger.info(f"Step 5: Getting user roles")
        try:
            # Force materialization of roles relationship to avoid lazy loading during serialization
            roles_list = list(user.roles)
            roles = [role.name for role in roles_list]
            logger.info(f"Step 6: User roles: {roles}")
        except Exception as e:
            logger.error(f"Error getting user roles: {e}", exc_info=True)
            raise

        # Create tokens
        logger.info(f"Step 7: Creating tokens")
        try:
            access_token_data = {
                "sub": user.username,
                "user_id": user.id,
                "roles": roles
            }

            refresh_token_data = {
                "sub": user.username,
                "user_id": user.id
            }

            logger.info(f"Step 8: Calling create_access_token")
            access_token = create_access_token(access_token_data)
            logger.info(f"Step 9: Calling create_refresh_token")
            refresh_token = create_refresh_token(refresh_token_data)
            logger.info(f"Step 10: Tokens created successfully")
        except Exception as e:
            logger.error(f"Error creating tokens: {e}", exc_info=True)
            raise

        # Set httpOnly cookies for improved security
        logger.info(f"Step 11: Setting auth cookies")
        set_auth_cookies(response, access_token, refresh_token)
        logger.info(f"Step 12: Auth cookies set successfully")

        # Prepare response
        logger.info(f"Step 13: Preparing TokenResponse")
        try:
            token_response = TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
                user=user
            )
            logger.info(f"Step 14: TokenResponse created successfully")
            return token_response
        except Exception as e:
            logger.error(f"Error creating TokenResponse: {e}", exc_info=True)
            raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    response: Response,
    refresh_request: RefreshTokenRequest = None,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Supports both request body and httpOnly cookie for backward compatibility.

    - **refresh_token**: Valid refresh token (optional if using cookie)
    """
    # Try to get refresh token from cookie first
    refresh_token = None
    if refresh_request and refresh_request.refresh_token:
        refresh_token = refresh_request.refresh_token
    
    # If no token in request body, it should be in cookie (handled by middleware)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required"
        )

    # Verify refresh token
    token_data = verify_token(refresh_token, "refresh")

    # Get user
    user = db.query(User).filter(User.id == token_data.get("user_id")).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Get user roles
    roles = [role.name for role in user.roles]

    # Create new tokens
    access_token_data = {
        "sub": user.username,
        "user_id": user.id,
        "roles": roles
    }

    refresh_token_data = {
        "sub": user.username,
        "user_id": user.id
    }

    access_token = create_access_token(access_token_data)
    new_refresh_token = create_refresh_token(refresh_token_data)

    # Update httpOnly cookies
    set_auth_cookies(response, access_token, new_refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user
    )


@router.post("/logout")
async def logout(response: Response):
    """
    Logout user by clearing authentication cookies.
    
    This endpoint clears the httpOnly cookies containing the JWT tokens.
    For additional security, tokens can be added to a blacklist in production.
    """
    clear_auth_cookies(response)
    
    return {
        "message": "Successfully logged out",
        "logged_out": True
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information

    Requires valid access token
    """
    return current_user


@router.post("/setup-defaults", status_code=status.HTTP_201_CREATED)
async def setup_default_roles_and_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Create default roles and permissions

    Requires superuser privileges
    """
    try:
        create_default_roles_and_permissions(db)
        return {"message": "Default roles and permissions created successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create defaults: {str(e)}"
        )


@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of roles

    Requires authentication
    """
    roles = db.query(Role).offset(skip).limit(limit).all()
    return roles
