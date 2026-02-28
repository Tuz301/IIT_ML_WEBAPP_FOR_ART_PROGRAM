"""
Cost Monitoring and Alerting System

Tracks and alerts on:
1. API usage costs per tenant
2. Infrastructure costs (compute, storage, database)
3. ML model inference costs
4. Third-party service costs (OpenAI, Pinecone, etc.)
5. Budget alerts and recommendations

Usage:
    from app.cost_monitoring import (
        CostTracker,
        BudgetMonitor,
        get_cost_tracker
    )
    
    tracker = get_cost_tracker()
    
    # Track API call cost
    await tracker.track_api_call(
        tenant_id="tenant123",
        endpoint="/api/predict",
        cost=0.001
    )
    
    # Check budget status
    budget_status = await tracker.check_budget("tenant123")
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from app.config import settings
from app.utils.database import DatabaseManager

logger = logging.getLogger(__name__)


class CostCategory(Enum):
    """Categories of costs"""
    API_CALLS = "api_calls"
    INFERENCE = "inference"
    STORAGE = "storage"
    DATABASE = "database"
    THIRD_PARTY = "third_party"
    BANDWIDTH = "bandwidth"
    COMPUTE = "compute"


class BudgetPeriod(Enum):
    """Budget periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class CostRecord:
    """Record of a cost incurred"""
    tenant_id: str
    category: CostCategory
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Budget:
    """Budget configuration"""
    tenant_id: str
    category: Optional[CostCategory]  # None = total budget
    period: BudgetPeriod
    amount: float
    alert_threshold: float = 0.8  # Alert at 80% of budget
    currency: str = "USD"


@dataclass
class BudgetStatus:
    """Status of budget vs actual spending"""
    tenant_id: str
    category: Optional[CostCategory]
    period: BudgetPeriod
    budget_amount: float
    spent_amount: float
    remaining_amount: float
    percentage_used: float
    is_over_budget: bool
    is_near_limit: bool
    projected_overage: float = 0.0


@dataclass
class CostAlert:
    """Alert about cost or budget"""
    tenant_id: str
    alert_type: str  # "budget_exceeded", "budget_warning", "anomaly_detected"
    category: Optional[CostCategory]
    message: str
    current_amount: float
    budget_amount: Optional[float]
    severity: str  # "info", "warning", "critical"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    recommendations: List[str] = field(default_factory=list)


class CostTracker:
    """
    Track costs and spending for tenants
    
    Monitors:
    - API call costs
    - Inference costs
    - Storage costs
    - Third-party service costs
    """
    
    # Default cost per unit (in USD)
    DEFAULT_COSTS = {
        CostCategory.API_CALLS: 0.0001,  # Per call
        CostCategory.INFERENCE: 0.001,   # Per prediction
        CostCategory.STORAGE: 0.023,     # Per GB/month
        CostCategory.DATABASE: 0.015,    # Per GB/month
        CostCategory.BANDWIDTH: 0.09,    # Per GB
        CostCategory.COMPUTE: 0.05,      # Per hour
    }
    
    def __init__(self):
        self._cost_cache: Dict[str, List[CostRecord]] = defaultdict(list)
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def track_api_call(
        self,
        tenant_id: str,
        endpoint: str,
        method: str = "GET",
        response_size_bytes: int = 0
    ):
        """Track cost of an API call"""
        # Calculate cost based on endpoint complexity
        base_cost = self.DEFAULT_COSTS[CostCategory.API_CALLS]
        
        # Adjust for endpoint type
        if "predict" in endpoint.lower():
            base_cost = self.DEFAULT_COSTS[CostCategory.INFERENCE]
        elif "upload" in endpoint.lower() or "file" in endpoint.lower():
            base_cost += (response_size_bytes / 1e9) * self.DEFAULT_COSTS[CostCategory.STORAGE]
        
        record = CostRecord(
            tenant_id=tenant_id,
            category=CostCategory.API_CALLS,
            amount=base_cost,
            description=f"{method} {endpoint}",
            metadata={"endpoint": endpoint, "method": method, "response_size": response_size_bytes}
        )
        
        await self._record_cost(record)
    
    async def track_inference(
        self,
        tenant_id: str,
        model_name: str,
        prediction_count: int = 1
    ):
        """Track cost of ML inference"""
        cost_per_prediction = self.DEFAULT_COSTS[CostCategory.INFERENCE]
        
        # Adjust for model complexity
        if "ensemble" in model_name.lower():
            cost_per_prediction *= 3
        elif "deep" in model_name.lower() or "neural" in model_name.lower():
            cost_per_prediction *= 2
        
        total_cost = cost_per_prediction * prediction_count
        
        record = CostRecord(
            tenant_id=tenant_id,
            category=CostCategory.INFERENCE,
            amount=total_cost,
            description=f"{prediction_count} predictions using {model_name}",
            metadata={"model": model_name, "count": prediction_count}
        )
        
        await self._record_cost(record)
    
    async def track_storage(
        self,
        tenant_id: str,
        storage_type: str,  # "database", "file", "vector_db"
        size_gb: float
    ):
        """Track storage costs"""
        if storage_type == "database":
            category = CostCategory.DATABASE
            cost_per_gb = self.DEFAULT_COSTS[CostCategory.DATABASE]
        elif storage_type == "vector_db":
            category = CostCategory.THIRD_PARTY
            cost_per_gb = 0.05  # Pinecone/Weaviate typically more expensive
        else:
            category = CostCategory.STORAGE
            cost_per_gb = self.DEFAULT_COSTS[CostCategory.STORAGE]
        
        record = CostRecord(
            tenant_id=tenant_id,
            category=category,
            amount=cost_per_gb * size_gb,
            description=f"{size_gb:.2f} GB of {storage_type}",
            metadata={"type": storage_type, "size_gb": size_gb}
        )
        
        await self._record_cost(record)
    
    async def track_third_party_service(
        self,
        tenant_id: str,
        service_name: str,
        usage_units: int,
        cost_per_unit: float
    ):
        """Track third-party service costs (OpenAI, Pinecone, etc.)"""
        record = CostRecord(
            tenant_id=tenant_id,
            category=CostCategory.THIRD_PARTY,
            amount=usage_units * cost_per_unit,
            description=f"{usage_units} units of {service_name}",
            metadata={"service": service_name, "units": usage_units, "unit_cost": cost_per_unit}
        )
        
        await self._record_cost(record)
    
    async def get_spending(
        self,
        tenant_id: str,
        category: Optional[CostCategory] = None,
        period: BudgetPeriod = BudgetPeriod.MONTHLY,
        start_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """Get spending breakdown for a tenant"""
        db = DatabaseManager()
        
        # Determine date range
        if not start_date:
            start_date = self._get_period_start(period)
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query
                if category:
                    cursor.execute("""
                        SELECT category, SUM(amount) as total
                        FROM cost_records
                        WHERE tenant_id = ? AND category = ? AND timestamp >= ?
                        GROUP BY category
                    """, (tenant_id, category.value, start_date.isoformat()))
                else:
                    cursor.execute("""
                        SELECT category, SUM(amount) as total
                        FROM cost_records
                        WHERE tenant_id = ? AND timestamp >= ?
                        GROUP BY category
                    """, (tenant_id, start_date.isoformat()))
                
                spending = {}
                for row in cursor.fetchall():
                    spending[row[0]] = row[1]
                
                return spending
        
        except Exception as e:
            logger.error(f"Failed to get spending: {e}")
            return {}
    
    async def get_total_spending(
        self,
        tenant_id: str,
        period: BudgetPeriod = BudgetPeriod.MONTHLY
    ) -> float:
        """Get total spending for a tenant in a period"""
        spending = await self.get_spending(tenant_id, period=period)
        return sum(spending.values())
    
    async def _record_cost(self, record: CostRecord):
        """Record a cost to database and cache"""
        # Add to cache
        self._cost_cache[record.tenant_id].append(record)
        self._cache_timestamps[record.tenant_id] = datetime.utcnow()
        
        # Persist to database
        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO cost_records (
                        tenant_id, category, amount, currency, description, metadata, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.tenant_id,
                    record.category.value,
                    record.amount,
                    record.currency,
                    record.description,
                    str(record.metadata),
                    record.timestamp.isoformat()
                ))
                
                conn.commit()
        
        except Exception as e:
            logger.error(f"Failed to record cost: {e}")
    
    def _get_period_start(self, period: BudgetPeriod) -> datetime:
        """Get start date for a budget period"""
        now = datetime.utcnow()
        
        if period == BudgetPeriod.DAILY:
            return now - timedelta(days=1)
        elif period == BudgetPeriod.WEEKLY:
            return now - timedelta(weeks=1)
        elif period == BudgetPeriod.MONTHLY:
            # First day of current month
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == BudgetPeriod.QUARTERLY:
            # First day of current quarter
            quarter = (now.month - 1) // 3
            return now.replace(month=(quarter * 3) + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # YEARLY
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


class BudgetMonitor:
    """
    Monitor budgets and send alerts
    
    Checks:
    - If spending exceeds budget
    - If spending is near budget threshold
    - Projects if budget will be exceeded
    """
    
    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self.cost_tracker = cost_tracker or CostTracker()
        self._budgets: Dict[str, List[Budget]] = {}
    
    async def check_budget(
        self,
        tenant_id: str,
        category: Optional[CostCategory] = None,
        period: BudgetPeriod = BudgetPeriod.MONTHLY
    ) -> BudgetStatus:
        """Check budget status for a tenant"""
        # Get budget
        budget = await self._get_budget(tenant_id, category, period)
        
        if not budget:
            # No budget set, return default status
            spent = await self.cost_tracker.get_total_spending(tenant_id, period)
            return BudgetStatus(
                tenant_id=tenant_id,
                category=category,
                period=period,
                budget_amount=0,
                spent_amount=spent,
                remaining_amount=0,
                percentage_used=0,
                is_over_budget=False,
                is_near_limit=False
            )
        
        # Get spending
        spent = await self.cost_tracker.get_total_spending(tenant_id, period)
        
        # Calculate status
        remaining = budget.amount - spent
        percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
        
        return BudgetStatus(
            tenant_id=tenant_id,
            category=category,
            period=period,
            budget_amount=budget.amount,
            spent_amount=spent,
            remaining_amount=remaining,
            percentage_used=percentage,
            is_over_budget=spent > budget.amount,
            is_near_limit=percentage >= (budget.alert_threshold * 100)
        )
    
    async def get_alerts(
        self,
        tenant_id: str
    ) -> List[CostAlert]:
        """Get cost/budget alerts for a tenant"""
        alerts = []
        
        # Check all budget categories
        for category in [None] + list(CostCategory):
            for period in BudgetPeriod:
                status = await self.check_budget(tenant_id, category, period)
                
                if status.is_over_budget:
                    alerts.append(CostAlert(
                        tenant_id=tenant_id,
                        alert_type="budget_exceeded",
                        category=category,
                        message=f"Budget exceeded for {category.value if category else 'total'} ({period.value})",
                        current_amount=status.spent_amount,
                        budget_amount=status.budget_amount,
                        severity="critical",
                        recommendations=self._get_over_budget_recommendations(status)
                    ))
                elif status.is_near_limit:
                    alerts.append(CostAlert(
                        tenant_id=tenant_id,
                        alert_type="budget_warning",
                        category=category,
                        message=f"Approaching budget limit for {category.value if category else 'total'} ({period.value}): {status.percentage_used:.1f}% used",
                        current_amount=status.spent_amount,
                        budget_amount=status.budget_amount,
                        severity="warning",
                        recommendations=self._get_near_limit_recommendations(status)
                    ))
        
        # Check for spending anomalies
        anomaly_alerts = await self._detect_spending_anomalies(tenant_id)
        alerts.extend(anomaly_alerts)
        
        return alerts
    
    async def set_budget(
        self,
        tenant_id: str,
        category: Optional[CostCategory],
        period: BudgetPeriod,
        amount: float,
        alert_threshold: float = 0.8
    ):
        """Set a budget for a tenant"""
        budget = Budget(
            tenant_id=tenant_id,
            category=category,
            period=period,
            amount=amount,
            alert_threshold=alert_threshold
        )
        
        # Store in database
        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO budgets 
                    (tenant_id, category, period, amount, alert_threshold, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, (tenant_id, category.value if category else None, period.value, amount, alert_threshold))
                
                conn.commit()
                
                # Update cache
                key = f"{tenant_id}_{category}_{period}"
                if key not in self._budgets:
                    self._budgets[key] = []
                self._budgets[key].append(budget)
                
                logger.info(f"Set budget for {tenant_id}: {amount} for {period.value}")
        
        except Exception as e:
            logger.error(f"Failed to set budget: {e}")
    
    async def _get_budget(
        self,
        tenant_id: str,
        category: Optional[CostCategory],
        period: BudgetPeriod
    ) -> Optional[Budget]:
        """Get budget from database"""
        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT tenant_id, category, period, amount, alert_threshold
                    FROM budgets
                    WHERE tenant_id = ? AND (category = ? OR category IS NULL) AND period = ?
                    ORDER BY category DESC
                    LIMIT 1
                """, (tenant_id, category.value if category else None, period.value))
                
                row = cursor.fetchone()
                if row:
                    return Budget(
                        tenant_id=row[0],
                        category=CostCategory(row[1]) if row[1] else None,
                        period=BudgetPeriod(row[2]),
                        amount=row[3],
                        alert_threshold=row[4]
                    )
                
                return None
        
        except Exception as e:
            logger.error(f"Failed to get budget: {e}")
            return None
    
    async def _detect_spending_anomalies(self, tenant_id: str) -> List[CostAlert]:
        """Detect unusual spending patterns"""
        alerts = []
        
        # Compare current month to previous month
        current_spending = await self.cost_tracker.get_total_spending(tenant_id, BudgetPeriod.MONTHLY)
        
        # Get previous month spending
        last_month_start = (datetime.utcnow() - timedelta(days=32)).replace(day=1)
        db = DatabaseManager()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT SUM(amount)
                    FROM cost_records
                    WHERE tenant_id = ? AND timestamp >= ? AND timestamp < ?
                """, (tenant_id, last_month_start.isoformat(), datetime.utcnow().replace(day=1).isoformat()))
                
                result = cursor.fetchone()
                last_month_spending = result[0] if result and result[0] else 0
                
                # Check for significant increase
                if last_month_spending > 0:
                    increase_ratio = current_spending / last_month_spending
                    
                    if increase_ratio > 2.0:  # More than 2x increase
                        alerts.append(CostAlert(
                            tenant_id=tenant_id,
                            alert_type="anomaly_detected",
                            category=None,
                            message=f"Spending increased by {(increase_ratio - 1) * 100:.0f}% compared to last month",
                            current_amount=current_spending,
                            budget_amount=last_month_spending,
                            severity="warning",
                            recommendations=[
                                "Review recent API usage and inference patterns",
                                "Check for unexpected third-party service usage",
                                "Consider setting up tighter budget alerts"
                            ]
                        ))
        
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}")
        
        return alerts
    
    def _get_over_budget_recommendations(self, status: BudgetStatus) -> List[str]:
        """Get recommendations for over-budget situations"""
        recommendations = [
            "Immediately review and reduce non-essential API usage",
            "Consider upgrading to a higher tier plan",
            "Contact support to discuss budget options"
        ]
        
        if status.category == CostCategory.INFERENCE:
            recommendations.extend([
                "Review prediction volume and consider batching",
                "Evaluate if all predictions are necessary",
                "Consider using a more cost-effective model"
            ])
        elif status.category == CostCategory.STORAGE:
            recommendations.extend([
                "Clean up old data and files",
                "Implement data retention policies",
                "Archive unused data to cheaper storage"
            ])
        
        return recommendations
    
    def _get_near_limit_recommendations(self, status: BudgetStatus) -> List[str]:
        """Get recommendations for near-budget-limit situations"""
        return [
            f"You've used {status.percentage_used:.1f}% of your {status.period.value} budget",
            "Monitor usage closely for the rest of the period",
            "Consider upgrading your plan if you need more capacity"
        ]


# Singleton instance
_cost_tracker: Optional[CostTracker] = None
_budget_monitor: Optional[BudgetMonitor] = None


def get_cost_tracker() -> CostTracker:
    """Get the singleton CostTracker instance"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


def get_budget_monitor() -> BudgetMonitor:
    """Get the singleton BudgetMonitor instance"""
    global _budget_monitor
    if _budget_monitor is None:
        _budget_monitor = BudgetMonitor(get_cost_tracker())
    return _budget_monitor
