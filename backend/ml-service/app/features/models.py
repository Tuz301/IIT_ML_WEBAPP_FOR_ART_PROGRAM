"""
Database models for Feature Flags system
"""
import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from typing import Optional, List
from datetime import datetime

from ..core.db import Base


class FeatureFlag(Base):
    """
    Feature flag model for database-backed feature flags
    
    Supports:
    - Boolean enable/disable
    - User percentage-based rollout (0-100)
    - User whitelist (specific user IDs) - stored as JSON string for SQLite compatibility
    - Audit logging via created_at/updated_at
    """
    __tablename__ = "feature_flags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=False, nullable=False)
    user_percentage = Column(Integer, default=0, nullable=False)
    user_whitelist = Column(Text, nullable=True)  # JSON string for SQLite compatibility
    environment_override = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    @property
    def whitelist_list(self) -> List[str]:
        """Get user whitelist as a list"""
        if not self.user_whitelist:
            return []
        try:
            return json.loads(self.user_whitelist)
        except (json.JSONDecodeError, TypeError):
            return []
    
    @whitelist_list.setter
    def whitelist_list(self, value: List[str]):
        """Set user whitelist from a list"""
        self.user_whitelist = json.dumps(value) if value else None
    
    def __repr__(self) -> str:
        return f"<FeatureFlag(name={self.name}, enabled={self.enabled}, percentage={self.user_percentage})>"
    
    def is_enabled_for_user(self, user_id: Optional[str], environment: str = "production") -> bool:
        """
        Check if feature is enabled for a specific user
        
        Args:
            user_id: Optional user identifier for percentage-based rollout
            environment: Current environment (development, staging, production)
        
        Returns:
            bool: True if feature is enabled for the user
        """
        # Environment override check
        if self.environment_override and self.environment_override.lower() == environment.lower():
            return True
        
        if not self.enabled:
            return False
        
        # Whitelist check - if user is in whitelist, always enable
        whitelist = self.whitelist_list
        if user_id and whitelist and user_id in whitelist:
            return True
        
        # Percentage-based rollout
        if self.user_percentage >= 100:
            return True
        if self.user_percentage <= 0:
            return False
        
        # If no user_id provided, use conservative approach (disable)
        if not user_id:
            return False
        
        # Hash-based percentage rollout for consistent user experience
        import hashlib
        hash_value = int(hashlib.md5(f"{self.name}:{user_id}".encode()).hexdigest(), 16)
        return (hash_value % 100) < self.user_percentage
