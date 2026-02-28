"""
Feature Flags System for IHVN ML Service

Provides database-backed feature flags with:
- User percentage-based rollout
- User whitelist support
- Decorator-based usage
- Environment-based overrides
- Audit logging for flag changes
"""

from .flags import feature_flag, is_enabled, get_flag, FeatureFlag
from .service import FeatureFlagService
from .models import FeatureFlag as FeatureFlagModel

__all__ = [
    "feature_flag",
    "is_enabled",
    "get_flag",
    "FeatureFlag",
    "FeatureFlagService",
    "FeatureFlagModel",
]
