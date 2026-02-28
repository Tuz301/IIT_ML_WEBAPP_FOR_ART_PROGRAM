"""
Multi-Tenancy Architecture for ML Service

Provides tenant isolation at multiple levels:
1. Database-level isolation (separate schemas or row-level security)
2. API-level isolation (tenant context in requests)
3. Resource isolation (rate limiting, quotas per tenant)
4. Configuration isolation (tenant-specific settings)

Usage:
    from app.multi_tenancy import (
        TenantContext,
        get_current_tenant,
        require_tenant,
        TenantManager
    )
    
    # In an endpoint
    @router.get("/predictions")
    async def get_predictions(
        current_tenant: TenantContext = Depends(get_current_tenant)
    ):
        # All operations automatically scoped to tenant
        predictions = await db.get_predictions(tenant_id=current_tenant.id)
        return predictions
"""

import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from functools import wraps

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.utils.database import DatabaseManager

logger = logging.getLogger(__name__)


class TenantTier(Enum):
    """Tenant subscription tiers"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantStatus(Enum):
    """Tenant account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRIAL = "trial"


@dataclass
class TenantQuota:
    """Resource quotas for a tenant"""
    max_predictions_per_month: int = 1000
    max_storage_gb: float = 10.0
    max_api_calls_per_minute: int = 60
    max_users: int = 5
    max_models: int = 1
    enable_advanced_features: bool = False
    enable_rag: bool = False
    enable_custom_models: bool = False


@dataclass
class TenantConfig:
    """Tenant-specific configuration"""
    tenant_id: str
    name: str
    tier: TenantTier
    status: TenantStatus
    quota: TenantQuota
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TenantContext:
    """Context for the current tenant in a request"""
    tenant_id: str
    tenant_name: str
    tier: TenantTier
    status: TenantStatus
    quota: TenantQuota
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    
    @property
    def is_active(self) -> bool:
        """Check if tenant is active"""
        return self.status == TenantStatus.ACTIVE
    
    @property
    def is_enterprise(self) -> bool:
        """Check if tenant is enterprise tier"""
        return self.tier == TenantTier.ENTERPRISE
    
    @property
    def can_use_advanced_features(self) -> bool:
        """Check if tenant can use advanced features"""
        return self.quota.enable_advanced_features


class TenantMiddleware:
    """
    Middleware to extract and validate tenant context from requests
    
    Supports tenant identification via:
    - HTTP Header (X-Tenant-ID)
    - Subdomain (tenant.example.com)
    - API Key prefix
    """
    
    def __init__(self):
        self._tenant_cache: Dict[str, TenantConfig] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def get_tenant_from_header(
        self,
        x_tenant_id: Optional[str] = None
    ) -> Optional[TenantContext]:
        """Get tenant from X-Tenant-ID header"""
        if not x_tenant_id:
            return None
        
        config = await self._get_tenant_config(x_tenant_id)
        if not config:
            return None
        
        return self._create_context(config)
    
    async def get_tenant_from_subdomain(
        self,
        host: str
    ) -> Optional[TenantContext]:
        """Get tenant from subdomain"""
        # Extract subdomain from host
        parts = host.split(".")
        if len(parts) < 2:
            return None
        
        subdomain = parts[0]
        
        # Skip common subdomains
        if subdomain in ["www", "api", "admin", "staging", "dev"]:
            return None
        
        config = await self._get_tenant_config(subdomain)
        if not config:
            return None
        
        return self._create_context(config)
    
    async def get_tenant_from_api_key(
        self,
        api_key: Optional[str] = None
    ) -> Optional[TenantContext]:
        """Get tenant from API key prefix"""
        if not api_key:
            return None
        
        # Extract tenant ID from API key prefix
        # Format: tenant_id_rest_of_key
        parts = api_key.split("_", 1)
        if len(parts) != 2:
            return None
        
        tenant_id = parts[0]
        
        config = await self._get_tenant_config(tenant_id)
        if not config:
            return None
        
        return self._create_context(config)
    
    async def _get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Get tenant configuration from cache or database"""
        # Check cache first
        if tenant_id in self._tenant_cache:
            cache_time = self._cache_timestamps.get(tenant_id)
            if cache_time and (datetime.utcnow() - cache_time).seconds < self._cache_ttl:
                return self._tenant_cache[tenant_id]
        
        # Load from database
        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tenant_id, name, tier, status, quota_config, settings, created_at, updated_at
                    FROM tenants
                    WHERE tenant_id = ? AND status != 'cancelled'
                """, (tenant_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                import json
                quota_dict = json.loads(row[4]) if row[4] else {}
                settings_dict = json.loads(row[5]) if row[5] else {}
                
                config = TenantConfig(
                    tenant_id=row[0],
                    name=row[1],
                    tier=TenantTier(row[2]),
                    status=TenantStatus(row[3]),
                    quota=TenantQuota(**quota_dict),
                    settings=settings_dict,
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7])
                )
                
                # Cache the config
                self._tenant_cache[tenant_id] = config
                self._cache_timestamps[tenant_id] = datetime.utcnow()
                
                return config
        
        except Exception as e:
            logger.error(f"Failed to load tenant config: {e}")
            return None
    
    def _create_context(self, config: TenantConfig) -> TenantContext:
        """Create tenant context from config"""
        return TenantContext(
            tenant_id=config.tenant_id,
            tenant_name=config.name,
            tier=config.tier,
            status=config.status,
            quota=config.quota
        )
    
    def clear_cache(self, tenant_id: Optional[str] = None):
        """Clear tenant cache"""
        if tenant_id:
            self._tenant_cache.pop(tenant_id, None)
            self._cache_timestamps.pop(tenant_id, None)
        else:
            self._tenant_cache.clear()
            self._cache_timestamps.clear()


class TenantIsolationMixin:
    """
    Mixin for adding tenant isolation to database queries
    
    Automatically filters queries by tenant_id
    """
    
    @staticmethod
    def add_tenant_filter(query, tenant_id: str, tenant_column: str = "tenant_id"):
        """Add tenant filter to SQLAlchemy query"""
        return query.filter(getattr(query.column_descriptions[0]["entity"], tenant_column) == tenant_id)
    
    @staticmethod
    def add_tenant_filter_sql(table_name: str, tenant_id: str):
        """Generate SQL WHERE clause for tenant isolation"""
        return f"{table_name}.tenant_id = '{tenant_id}'"


class TenantResourceTracker:
    """
    Track resource usage per tenant
    
    Monitors:
    - API call counts
    - Prediction counts
    - Storage usage
    - User counts
    """
    
    def __init__(self):
        self._usage_cache: Dict[str, Dict[str, int]] = {}
    
    async def record_api_call(self, tenant_id: str, endpoint: str):
        """Record an API call for a tenant"""
        if tenant_id not in self._usage_cache:
            self._usage_cache[tenant_id] = {}
        
        key = f"api_calls_{endpoint}"
        self._usage_cache[tenant_id][key] = self._usage_cache[tenant_id].get(key, 0) + 1
        
        # Persist to database periodically
        if self._usage_cache[tenant_id].get(key, 0) % 100 == 0:
            await self._persist_usage(tenant_id)
    
    async def record_prediction(self, tenant_id: str):
        """Record a prediction for a tenant"""
        if tenant_id not in self._usage_cache:
            self._usage_cache[tenant_id] = {}
        
        self._usage_cache[tenant_id]["predictions"] = self._usage_cache[tenant_id].get("predictions", 0) + 1
        
        # Persist to database periodically
        if self._usage_cache[tenant_id].get("predictions", 0) % 100 == 0:
            await self._persist_usage(tenant_id)
    
    async def get_usage(self, tenant_id: str) -> Dict[str, int]:
        """Get current usage for a tenant"""
        # Load from database if not in cache
        if tenant_id not in self._usage_cache:
            await self._load_usage(tenant_id)
        
        return self._usage_cache.get(tenant_id, {})
    
    async def check_quota(self, tenant_id: str, quota: TenantQuota) -> Dict[str, bool]:
        """Check if tenant is within quotas"""
        usage = await self.get_usage(tenant_id)
        
        return {
            "predictions_within_limit": usage.get("predictions", 0) < quota.max_predictions_per_month,
            "api_calls_within_limit": usage.get("api_calls", 0) < quota.max_api_calls_per_minute,
            "storage_within_limit": usage.get("storage_bytes", 0) < (quota.max_storage_gb * 1e9),
            "users_within_limit": usage.get("users", 0) < quota.max_users
        }
    
    async def _persist_usage(self, tenant_id: str):
        """Persist usage to database"""
        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                usage = self._usage_cache.get(tenant_id, {})
                
                # Update or insert usage record
                cursor.execute("""
                    INSERT OR REPLACE INTO tenant_usage (tenant_id, metric_name, value, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (tenant_id, "predictions", usage.get("predictions", 0)))
                
                cursor.execute("""
                    INSERT OR REPLACE INTO tenant_usage (tenant_id, metric_name, value, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (tenant_id, "api_calls", usage.get("api_calls", 0)))
                
                conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to persist usage: {e}")
    
    async def _load_usage(self, tenant_id: str):
        """Load usage from database"""
        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT metric_name, value
                    FROM tenant_usage
                    WHERE tenant_id = ?
                """, (tenant_id,))
                
                usage = {}
                for row in cursor.fetchall():
                    usage[row[0]] = row[1]
                
                self._usage_cache[tenant_id] = usage
        
        except Exception as e:
            logger.error(f"Failed to load usage: {e}")


# Global instances
_tenant_middleware = TenantMiddleware()
_resource_tracker = TenantResourceTracker()


# Dependency functions for FastAPI
async def get_current_tenant(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> TenantContext:
    """
    Get current tenant from request
    
    This dependency extracts tenant context from the request
    and ensures the tenant is active and within quotas.
    """
    # Try multiple methods to identify tenant
    context = await _tenant_middleware.get_tenant_from_header(x_tenant_id)
    
    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to identify tenant. Provide X-Tenant-ID header."
        )
    
    # Check if tenant is active
    if not context.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant account is {context.status.value}. Please contact support."
        )
    
    # Check quotas
    quota_status = await _resource_tracker.check_quota(context.tenant_id, context.quota)
    
    if not quota_status["predictions_within_limit"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly prediction quota exceeded. Please upgrade your plan."
        )
    
    if not quota_status["api_calls_within_limit"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API rate limit exceeded. Please wait before making more requests."
        )
    
    # Record API call
    await _resource_tracker.record_api_call(context.tenant_id, "api_call")
    
    return context


def require_tenant(tier: TenantTier = TenantTier.BASIC):
    """
    Decorator to require specific tenant tier or higher
    
    Usage:
        @require_tenant(TenantTier.PROFESSIONAL)
        async def advanced_feature():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_tenant: TenantContext = Depends(get_current_tenant), **kwargs):
            # Check tier
            tier_values = {
                TenantTier.FREE: 0,
                TenantTier.BASIC: 1,
                TenantTier.PROFESSIONAL: 2,
                TenantTier.ENTERPRISE: 3
            }
            
            if tier_values.get(current_tenant.tier, 0) < tier_values.get(tier, 0):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires {tier.value} tier or higher"
                )
            
            return await func(*args, current_tenant=current_tenant, **kwargs)
        
        return wrapper
    return decorator


class TenantManager:
    """
    Manager for tenant operations
    
    Provides utilities for:
    - Creating new tenants
    - Updating tenant configurations
    - Managing tenant quotas
    - Tenant analytics
    """
    
    @staticmethod
    async def create_tenant(
        tenant_id: str,
        name: str,
        tier: TenantTier = TenantTier.FREE,
        admin_email: str = None,
        quota: Optional[TenantQuota] = None
    ) -> TenantConfig:
        """Create a new tenant"""
        quota = quota or TenantQuota()
        
        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                import json
                quota_json = json.dumps({
                    "max_predictions_per_month": quota.max_predictions_per_month,
                    "max_storage_gb": quota.max_storage_gb,
                    "max_api_calls_per_minute": quota.max_api_calls_per_minute,
                    "max_users": quota.max_users,
                    "max_models": quota.max_models,
                    "enable_advanced_features": quota.enable_advanced_features,
                    "enable_rag": quota.enable_rag,
                    "enable_custom_models": quota.enable_custom_models
                })
                
                cursor.execute("""
                    INSERT INTO tenants (tenant_id, name, tier, status, quota_config, settings, created_at, updated_at)
                    VALUES (?, ?, ?, 'active', ?, '{}', datetime('now'), datetime('now'))
                """, (tenant_id, name, tier.value, quota_json))
                
                conn.commit()
                
                logger.info(f"Created tenant: {tenant_id} ({name})")
                
                return TenantConfig(
                    tenant_id=tenant_id,
                    name=name,
                    tier=tier,
                    status=TenantStatus.ACTIVE,
                    quota=quota
                )
        
        except Exception as e:
            logger.error(f"Failed to create tenant: {e}")
            raise
    
    @staticmethod
    async def update_tenant_tier(tenant_id: str, new_tier: TenantTier) -> bool:
        """Update tenant tier"""
        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE tenants
                    SET tier = ?, updated_at = datetime('now')
                    WHERE tenant_id = ?
                """, (new_tier.value, tenant_id))
                
                conn.commit()
                
                # Clear cache
                _tenant_middleware.clear_cache(tenant_id)
                
                logger.info(f"Updated tenant {tenant_id} to {new_tier.value} tier")
                return True
        
        except Exception as e:
            logger.error(f"Failed to update tenant tier: {e}")
            return False
    
    @staticmethod
    async def get_tenant_analytics(tenant_id: str) -> Dict[str, Any]:
        """Get analytics for a tenant"""
        usage = await _resource_tracker.get_usage(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "usage": usage,
            "predictions_this_month": usage.get("predictions", 0),
            "api_calls_this_month": usage.get("api_calls", 0),
            "storage_used_bytes": usage.get("storage_bytes", 0),
            "active_users": usage.get("users", 0)
        }


def get_tenant_manager() -> TenantManager:
    """Get the TenantManager instance"""
    return TenantManager()
