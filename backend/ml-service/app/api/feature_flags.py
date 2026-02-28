"""
Feature Flags API endpoints for IHVN ML Service

Provides REST API for managing feature flags including:
- List all feature flags
- Get specific flag configuration
- Create new feature flags
- Update existing flags
- Delete flags
- Check flag status for a user
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..features.service import get_feature_flag_service
from ..features.models import FeatureFlag as FeatureFlagModel
from ..auth import get_current_active_user, get_current_superuser
from ..models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feature-flags", tags=["Feature Flags"])


# Pydantic models for request/response
class FeatureFlagCreate(BaseModel):
    """Request model for creating a feature flag"""
    name: str = Field(..., min_length=1, max_length=255, description="Unique name for the feature flag")
    description: Optional[str] = Field(None, description="Description of what the flag controls")
    enabled: bool = Field(False, description="Whether the flag is enabled")
    user_percentage: int = Field(0, ge=0, le=100, description="Percentage of users to enable (0-100)")
    user_whitelist: Optional[List[str]] = Field(None, description="List of user IDs to always enable")
    environment_override: Optional[str] = Field(None, description="Environment to force enable")


class FeatureFlagUpdate(BaseModel):
    """Request model for updating a feature flag"""
    description: Optional[str] = None
    enabled: Optional[bool] = None
    user_percentage: Optional[int] = Field(None, ge=0, le=100)
    user_whitelist: Optional[List[str]] = None
    environment_override: Optional[str] = None


class FeatureFlagResponse(BaseModel):
    """Response model for feature flag data"""
    id: int
    name: str
    description: Optional[str]
    enabled: bool
    user_percentage: int
    user_whitelist: Optional[List[str]]
    environment_override: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class FeatureFlagCheckRequest(BaseModel):
    """Request model for checking a feature flag for a user"""
    user_id: Optional[str] = Field(None, description="User ID for percentage-based rollout")
    environment: str = Field("production", description="Current environment")


class FeatureFlagCheckResponse(BaseModel):
    """Response model for feature flag check"""
    flag_name: str
    enabled: bool
    user_id: Optional[str]
    environment: str


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None


@router.get(
    "",
    response_model=List[FeatureFlagResponse],
    summary="List All Feature Flags",
    description="""
    Retrieve all feature flags in the system.
    
    **Returns:**
    - List of all feature flags with their configurations
    - Includes enabled status, rollout percentage, and whitelist
    
    **Permissions:**
    - Requires active user authentication
    - All users can view flags (read-only access)
    """
)
async def list_feature_flags(
    current_user: User = Depends(get_current_active_user)
) -> List[FeatureFlagResponse]:
    """List all feature flags"""
    service = get_feature_flag_service()
    flags = service.list_all_flags()
    return flags


@router.get(
    "/{flag_name}",
    response_model=FeatureFlagResponse,
    summary="Get Feature Flag Configuration",
    description="""
    Retrieve configuration for a specific feature flag.
    
    **Parameters:**
    - flag_name: Name of the feature flag to retrieve
    
    **Returns:**
    - Feature flag configuration including rollout settings
    
    **Error:**
    - 404: Feature flag not found
    """
)
async def get_feature_flag(
    flag_name: str,
    current_user: User = Depends(get_current_active_user)
) -> FeatureFlagResponse:
    """Get a specific feature flag configuration"""
    service = get_feature_flag_service()
    flags = service.list_all_flags()
    
    for flag in flags:
        if flag["name"] == flag_name:
            return flag
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Feature flag '{flag_name}' not found"
    )


@router.post(
    "",
    response_model=FeatureFlagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Feature Flag",
    description="""
    Create a new feature flag.
    
    **Permissions:**
    - Requires superuser/admin privileges
    
    **Parameters:**
    - name: Unique name for the flag (required)
    - description: Optional description
    - enabled: Whether the flag is enabled (default: false)
    - user_percentage: Percentage rollout 0-100 (default: 0)
    - user_whitelist: List of user IDs to always enable
    - environment_override: Environment to force enable
    
    **Error:**
    - 400: Flag with this name already exists
    """
)
async def create_feature_flag(
    flag_data: FeatureFlagCreate,
    current_user: User = Depends(get_current_superuser)
) -> FeatureFlagResponse:
    """Create a new feature flag"""
    service = get_feature_flag_service()
    
    result = service.create_flag(
        name=flag_data.name,
        description=flag_data.description,
        enabled=flag_data.enabled,
        user_percentage=flag_data.user_percentage,
        user_whitelist=flag_data.user_whitelist,
        environment_override=flag_data.environment_override
    )
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feature flag '{flag_data.name}' already exists or creation failed"
        )
    
    logger.info(f"Feature flag '{flag_data.name}' created by user {current_user.username}")
    return result


@router.put(
    "/{flag_name}",
    response_model=FeatureFlagResponse,
    summary="Update Feature Flag",
    description="""
    Update an existing feature flag.
    
    **Permissions:**
    - Requires superuser/admin privileges
    
    **Parameters:**
    - All parameters are optional
    - Only provided fields will be updated
    
    **Error:**
    - 404: Feature flag not found
    """
)
async def update_feature_flag(
    flag_name: str,
    flag_data: FeatureFlagUpdate,
    current_user: User = Depends(get_current_superuser)
) -> FeatureFlagResponse:
    """Update an existing feature flag"""
    service = get_feature_flag_service()
    
    result = service.update_flag(
        name=flag_name,
        enabled=flag_data.enabled,
        user_percentage=flag_data.user_percentage,
        user_whitelist=flag_data.user_whitelist,
        environment_override=flag_data.environment_override,
        description=flag_data.description
    )
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{flag_name}' not found"
        )
    
    logger.info(f"Feature flag '{flag_name}' updated by user {current_user.username}")
    return result


@router.delete(
    "/{flag_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Feature Flag",
    description="""
    Delete a feature flag from the system.
    
    **Permissions:**
    - Requires superuser/admin privileges
    
    **Warning:**
    - This action cannot be undone
    - Code referencing this flag will use default values
    
    **Error:**
    - 404: Feature flag not found
    """
)
async def delete_feature_flag(
    flag_name: str,
    current_user: User = Depends(get_current_superuser)
) -> None:
    """Delete a feature flag"""
    service = get_feature_flag_service()
    
    success = service.delete_flag(flag_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{flag_name}' not found"
        )
    
    logger.info(f"Feature flag '{flag_name}' deleted by user {current_user.username}")


@router.post(
    "/{flag_name}/check",
    response_model=FeatureFlagCheckResponse,
    summary="Check Feature Flag for User",
    description="""
    Check if a feature flag is enabled for a specific user.
    
    **Use Case:**
    - Frontend can query this endpoint to determine feature availability
    - Useful for A/B testing and gradual rollouts
    
    **Parameters:**
    - flag_name: Name of the feature flag to check
    - user_id: Optional user ID for percentage-based rollout
    - environment: Current environment (default: production)
    
    **Returns:**
    - enabled: true if feature is enabled for the user
    """
)
async def check_feature_flag(
    flag_name: str,
    request: FeatureFlagCheckRequest,
    current_user: User = Depends(get_current_active_user)
) -> FeatureFlagCheckResponse:
    """Check if a feature flag is enabled for a user"""
    service = get_feature_flag_service()
    
    enabled = service.is_enabled(
        flag_name=flag_name,
        user_id=request.user_id,
        environment=request.environment,
        default=False
    )
    
    return FeatureFlagCheckResponse(
        flag_name=flag_name,
        enabled=enabled,
        user_id=request.user_id,
        environment=request.environment
    )


@router.get(
    "/{flag_name}/check",
    response_model=FeatureFlagCheckResponse,
    summary="Check Feature Flag (GET)",
    description="""
    Check if a feature flag is enabled (GET method for simpler queries).
    
    **Query Parameters:**
    - user_id: Optional user ID for percentage-based rollout
    - environment: Current environment (default: production)
    """
)
async def check_feature_flag_get(
    flag_name: str,
    user_id: Optional[str] = Query(None, description="User ID for percentage-based rollout"),
    environment: str = Query("production", description="Current environment"),
    current_user: User = Depends(get_current_active_user)
) -> FeatureFlagCheckResponse:
    """Check if a feature flag is enabled (GET method)"""
    service = get_feature_flag_service()
    
    enabled = service.is_enabled(
        flag_name=flag_name,
        user_id=user_id,
        environment=environment,
        default=False
    )
    
    return FeatureFlagCheckResponse(
        flag_name=flag_name,
        enabled=enabled,
        user_id=user_id,
        environment=environment
    )
