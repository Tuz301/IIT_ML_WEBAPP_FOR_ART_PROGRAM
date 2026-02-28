"""
Feature Flag Decorators and Helper Functions

Provides decorator-based feature flag usage and helper functions
for checking feature flags in code.
"""
import functools
import logging
from typing import Optional, Callable, Any, TypeVar
from dataclasses import dataclass

from .service import get_feature_flag_service

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class FeatureFlag:
    """
    Feature flag configuration for decorator-based usage
    
    Attributes:
        name: Unique name for the feature flag
        rollout_percentage: Percentage of users to enable (0-100)
        whitelist: List of user IDs to always enable
        environment: Environment to force enable
        default_enabled: Default value if flag doesn't exist
    """
    name: str
    rollout_percentage: Optional[int] = None
    whitelist: Optional[list[str]] = None
    environment: Optional[str] = None
    default_enabled: bool = False


def feature_flag(
    flag_name: str,
    user_id_param: Optional[str] = None,
    default: bool = False,
    on_disabled: Optional[str] = "skip"
) -> Callable:
    """
    Decorator to conditionally execute functions based on feature flags
    
    Args:
        flag_name: Name of the feature flag to check
        user_id_param: Name of the parameter containing user ID (for percentage rollout)
        default: Default value if flag doesn't exist
        on_disabled: Action when flag is disabled ('skip', 'return_none', 'raise')
    
    Example:
        @feature_flag("new_prediction_model", user_id_param="user_id")
        def predict_with_new_model(data: dict, user_id: str):
            return model.predict(data)
    
        @feature_flag("experimental_analytics")
        def run_experimental_analytics():
            return analytics.run()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            service = get_feature_flag_service()
            
            # Extract user_id from function parameters if specified
            user_id: Optional[str] = None
            if user_id_param:
                # Try to get user_id from kwargs first
                user_id = kwargs.get(user_id_param)
                
                # If not in kwargs, try to get from function signature
                if user_id is None:
                    import inspect
                    sig = inspect.signature(func)
                    if user_id_param in sig.parameters:
                        param_index = list(sig.parameters.keys()).index(user_id_param)
                        if param_index < len(args):
                            user_id = args[param_index]
            
            # Check if flag is enabled
            is_enabled = service.is_enabled(
                flag_name=flag_name,
                user_id=user_id,
                default=default
            )
            
            if not is_enabled:
                logger.debug(f"Feature flag '{flag_name}' is disabled, skipping function '{func.__name__}'")
                
                if on_disabled == "skip":
                    # Skip execution, return None
                    return None  # type: ignore
                elif on_disabled == "return_none":
                    return None  # type: ignore
                elif on_disabled == "raise":
                    raise RuntimeError(f"Feature flag '{flag_name}' is disabled")
                else:
                    return None  # type: ignore
            
            # Execute the function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def is_enabled(
    flag_name: str,
    user_id: Optional[str] = None,
    environment: str = "production",
    default: bool = False
) -> bool:
    """
    Check if a feature flag is enabled
    
    Args:
        flag_name: Name of the feature flag
        user_id: Optional user identifier for percentage-based rollout
        environment: Current environment (development, staging, production)
        default: Default value if flag doesn't exist
    
    Returns:
        bool: True if feature is enabled
    
    Example:
        if is_enabled("new_prediction_model", user_id=current_user.id):
            return predict_with_new_model(data)
        else:
            return predict_with_old_model(data)
    """
    service = get_feature_flag_service()
    return service.is_enabled(
        flag_name=flag_name,
        user_id=user_id,
        environment=environment,
        default=default
    )


def get_flag(flag_name: str) -> Optional[dict]:
    """
    Get feature flag configuration
    
    Args:
        flag_name: Name of the feature flag
    
    Returns:
        Dict with flag configuration or None if not found
    
    Example:
        flag_config = get_flag("new_prediction_model")
        if flag_config:
            percentage = flag_config.get("user_percentage", 0)
    """
    service = get_feature_flag_service()
    return service.get_flag(flag_name)


def with_feature_flag(
    flag_name: str,
    enabled_value: Any,
    disabled_value: Any = None,
    user_id: Optional[str] = None
) -> Any:
    """
    Return different values based on feature flag status
    
    Args:
        flag_name: Name of the feature flag
        enabled_value: Value to return if flag is enabled
        disabled_value: Value to return if flag is disabled
        user_id: Optional user identifier for percentage-based rollout
    
    Returns:
        enabled_value if flag is enabled, disabled_value otherwise
    
    Example:
        model_version = with_feature_flag(
            "new_prediction_model",
            enabled_value="v2.0",
            disabled_value="v1.0",
            user_id=current_user.id
        )
    """
    if is_enabled(flag_name, user_id=user_id):
        return enabled_value
    return disabled_value


class FeatureFlaggedValue:
    """
    Context manager for feature-flagged values
    
    Example:
        with FeatureFlaggedValue("new_api", new_api_client, old_api_client) as client:
            result = client.get_data()
    """
    
    def __init__(
        self,
        flag_name: str,
        enabled_value: Any,
        disabled_value: Any,
        user_id: Optional[str] = None
    ):
        self.flag_name = flag_name
        self.enabled_value = enabled_value
        self.disabled_value = disabled_value
        self.user_id = user_id
        self._current_value: Any = None
    
    def __enter__(self) -> Any:
        if is_enabled(self.flag_name, user_id=self.user_id):
            self._current_value = self.enabled_value
        else:
            self._current_value = self.disabled_value
        return self._current_value
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._current_value = None
