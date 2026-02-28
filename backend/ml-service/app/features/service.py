"""
Feature Flag Service - Flag checking logic with database backing
"""
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from contextlib import contextmanager

from .models import FeatureFlag as FeatureFlagModel
from ..config import settings

logger = logging.getLogger(__name__)


class FeatureFlagService:
    """
    Service for managing and checking feature flags
    
    Provides:
    - Database-backed flag storage
    - In-memory caching for performance
    - User-based rollout support
    - Environment-based overrides
    """
    
    def __init__(self, db_session_factory=None):
        """
        Initialize the feature flag service
        
        Args:
            db_session_factory: Optional callable that returns a database session
        """
        self._db_session_factory = db_session_factory
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, float] = {}
    
    @contextmanager
    def _get_db_session(self):
        """Get a database session for querying flags"""
        if self._db_session_factory:
            with self._db_session_factory() as session:
                yield session
        else:
            # Fallback to creating session from settings
            from sqlalchemy.orm import sessionmaker
            engine = create_engine(settings.database_url)
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
            try:
                yield session
            finally:
                session.close()
    
    def _is_cache_valid(self, flag_name: str) -> bool:
        """Check if cached flag data is still valid"""
        if flag_name not in self._cache_timestamps:
            return False
        import time
        return (time.time() - self._cache_timestamps[flag_name]) < self._cache_ttl
    
    def _get_flag_from_db(self, flag_name: str) -> Optional[FeatureFlagModel]:
        """Get flag from database"""
        try:
            with self._get_db_session() as session:
                flag = session.query(FeatureFlagModel).filter(
                    FeatureFlagModel.name == flag_name
                ).first()
                return flag
        except Exception as e:
            logger.error(f"Error fetching flag '{flag_name}' from database: {e}")
            return None
    
    def _cache_flag(self, flag: FeatureFlagModel) -> None:
        """Cache flag data in memory"""
        import time
        self._cache[flag.name] = {
            "enabled": flag.enabled,
            "user_percentage": flag.user_percentage,
            "user_whitelist": flag.user_whitelist,
            "environment_override": flag.environment_override,
        }
        self._cache_timestamps[flag.name] = time.time()
    
    def get_flag(self, flag_name: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get feature flag configuration
        
        Args:
            flag_name: Name of the feature flag
            use_cache: Whether to use cached value (default: True)
        
        Returns:
            Dict with flag configuration or None if not found
        """
        # Check cache first
        if use_cache and flag_name in self._cache and self._is_cache_valid(flag_name):
            return self._cache[flag_name]
        
        # Fetch from database
        flag = self._get_flag_from_db(flag_name)
        if flag:
            self._cache_flag(flag)
            return {
                "enabled": flag.enabled,
                "user_percentage": flag.user_percentage,
                "user_whitelist": flag.user_whitelist,
                "environment_override": flag.environment_override,
            }
        
        return None
    
    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        environment: str = "production",
        default: bool = False
    ) -> bool:
        """
        Check if a feature flag is enabled for a specific user
        
        Args:
            flag_name: Name of the feature flag
            user_id: Optional user identifier for percentage-based rollout
            environment: Current environment (development, staging, production)
            default: Default value if flag doesn't exist
        
        Returns:
            bool: True if feature is enabled for the user
        """
        flag_config = self.get_flag(flag_name)
        
        if not flag_config:
            logger.warning(f"Feature flag '{flag_name}' not found, using default: {default}")
            return default
        
        # Environment override check
        if flag_config.get("environment_override"):
            if flag_config["environment_override"].lower() == environment.lower():
                return True
        
        # Basic enabled check
        if not flag_config.get("enabled", False):
            return False
        
        # Whitelist check
        whitelist = flag_config.get("user_whitelist")
        if user_id and whitelist and user_id in whitelist:
            return True
        
        # Percentage-based rollout
        percentage = flag_config.get("user_percentage", 0)
        if percentage >= 100:
            return True
        if percentage <= 0:
            return False
        
        # If no user_id provided, use conservative approach
        if not user_id:
            return False
        
        # Hash-based percentage rollout for consistent user experience
        import hashlib
        hash_value = int(hashlib.md5(f"{flag_name}:{user_id}".encode()).hexdigest(), 16)
        return (hash_value % 100) < percentage
    
    def list_all_flags(self) -> List[Dict[str, Any]]:
        """
        List all feature flags
        
        Returns:
            List of all feature flags with their configurations
        """
        try:
            with self._get_db_session() as session:
                flags = session.query(FeatureFlagModel).all()
                return [
                    {
                        "id": flag.id,
                        "name": flag.name,
                        "description": flag.description,
                        "enabled": flag.enabled,
                        "user_percentage": flag.user_percentage,
                        "user_whitelist": flag.user_whitelist,
                        "environment_override": flag.environment_override,
                        "created_at": flag.created_at.isoformat() if flag.created_at else None,
                        "updated_at": flag.updated_at.isoformat() if flag.updated_at else None,
                    }
                    for flag in flags
                ]
        except Exception as e:
            logger.error(f"Error listing feature flags: {e}")
            return []
    
    def create_flag(
        self,
        name: str,
        description: Optional[str] = None,
        enabled: bool = False,
        user_percentage: int = 0,
        user_whitelist: Optional[List[str]] = None,
        environment_override: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new feature flag
        
        Args:
            name: Unique name for the flag
            description: Optional description
            enabled: Whether the flag is enabled
            user_percentage: Percentage of users to enable (0-100)
            user_whitelist: List of user IDs to always enable
            environment_override: Environment to force enable
        
        Returns:
            Created flag data or None on error
        """
        try:
            with self._get_db_session() as session:
                # Check if flag already exists
                existing = session.query(FeatureFlagModel).filter(
                    FeatureFlagModel.name == name
                ).first()
                if existing:
                    logger.warning(f"Feature flag '{name}' already exists")
                    return None
                
                flag = FeatureFlagModel(
                    name=name,
                    description=description,
                    enabled=enabled,
                    user_percentage=user_percentage,
                    user_whitelist=user_whitelist,
                    environment_override=environment_override
                )
                session.add(flag)
                session.commit()
                session.refresh(flag)
                
                # Invalidate cache
                self._cache.pop(name, None)
                self._cache_timestamps.pop(name, None)
                
                logger.info(f"Created feature flag '{name}'")
                return {
                    "id": flag.id,
                    "name": flag.name,
                    "description": flag.description,
                    "enabled": flag.enabled,
                    "user_percentage": flag.user_percentage,
                    "user_whitelist": flag.user_whitelist,
                    "environment_override": flag.environment_override,
                }
        except Exception as e:
            logger.error(f"Error creating feature flag '{name}': {e}")
            return None
    
    def update_flag(
        self,
        name: str,
        enabled: Optional[bool] = None,
        user_percentage: Optional[int] = None,
        user_whitelist: Optional[List[str]] = None,
        environment_override: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing feature flag
        
        Args:
            name: Name of the flag to update
            enabled: New enabled state
            user_percentage: New percentage rollout
            user_whitelist: New whitelist
            environment_override: New environment override
            description: New description
        
        Returns:
            Updated flag data or None on error
        """
        try:
            with self._get_db_session() as session:
                flag = session.query(FeatureFlagModel).filter(
                    FeatureFlagModel.name == name
                ).first()
                
                if not flag:
                    logger.warning(f"Feature flag '{name}' not found")
                    return None
                
                if enabled is not None:
                    flag.enabled = enabled
                if user_percentage is not None:
                    flag.user_percentage = user_percentage
                if user_whitelist is not None:
                    flag.user_whitelist = user_whitelist
                if environment_override is not None:
                    flag.environment_override = environment_override
                if description is not None:
                    flag.description = description
                
                session.commit()
                session.refresh(flag)
                
                # Invalidate cache
                self._cache.pop(name, None)
                self._cache_timestamps.pop(name, None)
                
                logger.info(f"Updated feature flag '{name}'")
                return {
                    "id": flag.id,
                    "name": flag.name,
                    "description": flag.description,
                    "enabled": flag.enabled,
                    "user_percentage": flag.user_percentage,
                    "user_whitelist": flag.user_whitelist,
                    "environment_override": flag.environment_override,
                }
        except Exception as e:
            logger.error(f"Error updating feature flag '{name}': {e}")
            return None
    
    def delete_flag(self, name: str) -> bool:
        """
        Delete a feature flag
        
        Args:
            name: Name of the flag to delete
        
        Returns:
            bool: True if deleted successfully
        """
        try:
            with self._get_db_session() as session:
                flag = session.query(FeatureFlagModel).filter(
                    FeatureFlagModel.name == name
                ).first()
                
                if not flag:
                    logger.warning(f"Feature flag '{name}' not found")
                    return False
                
                session.delete(flag)
                session.commit()
                
                # Invalidate cache
                self._cache.pop(name, None)
                self._cache_timestamps.pop(name, None)
                
                logger.info(f"Deleted feature flag '{name}'")
                return True
        except Exception as e:
            logger.error(f"Error deleting feature flag '{name}': {e}")
            return False


# Global service instance
_service_instance: Optional[FeatureFlagService] = None


def get_feature_flag_service() -> FeatureFlagService:
    """Get or create the global feature flag service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = FeatureFlagService()
    return _service_instance


def set_feature_flag_service(service: FeatureFlagService) -> None:
    """Set the global feature flag service instance (useful for testing)"""
    global _service_instance
    _service_instance = service
