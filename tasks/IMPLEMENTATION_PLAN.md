# Implementation Plan: Queue System, Retry Mechanism, Feature Flags

## Overview
Implement three missing production-ready systems for the IHVN ML Service backend.

## Design Principles
- **Simplicity First**: Use lightweight, well-maintained libraries
- **Production Ready**: Include error handling, monitoring, and graceful degradation
- **Minimal Impact**: Build on existing code without breaking changes
- **Elegant Solutions**: Clean, tested, documented code

---

## 1. Queue System (RQ-based)

### Choice: RQ (Redis Queue)
**Why RQ over Celery?**
- Simpler setup (no broker needed, uses existing Redis)
- Better for smaller teams/quick implementation
- Built-in dashboard for monitoring
- Python-native, async-friendly

### Components to Implement
1. **Job Queue** (`app/queue/`)
   - `jobs.py` - Job definitions and task functions
   - `worker.py` - RQ worker configuration
   - `scheduler.py` - Scheduled task configuration

2. **API Endpoints** (`app/api/queue.py`)
   - GET /queue/stats - Queue statistics
   - POST /queue/jobs/{job_id}/cancel - Cancel job
   - GET /queue/workers - Worker status

3. **Integration Points**
   - ETL pipeline → Queue for async processing
   - Batch predictions → Queue for async execution
   - Report generation → Queue for background processing

### Dependencies
```txt
rq>=2.0.0
rq-scheduler>=0.13.0
```

### Configuration
```python
# config.py
redis_queue_enabled: bool = True
queue_name: str = "ihvn_ml_tasks"
default_job_timeout: int = 600  # 10 minutes
```

---

## 2. Retry Mechanism (tenacity)

### Choice: Tenacity
**Why Tenacity?**
- Declarative retry logic
- Exponential backoff built-in
- Jitter support
- Excellent for external API calls

### Components to Implement
1. **Retry Decorators** (`app/utils/retry.py`)
   - `@database_retry` - For database operations
   - `@api_retry` - For external API calls
   - `@redis_retry` - For Redis operations

2. **Configuration**
   ```python
   # config.py
   retry_max_attempts: int = 3
   retry_wait_min: float = 1.0  # seconds
   retry_wait_max: float = 10.0
   ```

3. **Integration Points**
   - All database queries
   - External API calls (if any)
   - Redis operations
   - Feature store access

### Dependencies
```txt
tenacity>=8.2.0
```

---

## 3. Feature Flags (Custom Lightweight)

### Choice: Custom Implementation
**Why Custom?**
- No external dependencies
- Full control over behavior
- Can be as simple or complex as needed
- Database-backed (already have PostgreSQL schema)

### Components to Implement
1. **Feature Flag System** (`app/features/`)
   - `flags.py` - Feature flag definitions
   - `service.py` - Flag checking logic
   - `models.py` - Database models for flags

2. **API Endpoints** (`app/api/features.py`)
   - GET /features - List all flags
   - PUT /features/{flag_name} - Update flag
   - POST /features - Create new flag

3. **Integration Points**
   - New ML models (gradual rollout)
   - API endpoints (kill switch)
   - UI features (A/B testing)
   - Experimental features

### Database Schema
```sql
CREATE TABLE feature_flags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT FALSE,
    user_percentage INTEGER DEFAULT 0,  -- For gradual rollout
    user_whitelist TEXT[],  -- Specific user IDs
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Usage Example
```python
from app.features import feature_flag, is_enabled

@feature_flag("new_prediction_model", rollout_percentage=50)
def predict_with_new_model(data):
    return model.predict(data)

# In code
if is_enabled("experimental_analytics"):
    run_experimental_analytics()
```

---

## Implementation Order

1. **Feature Flags** (Simplest, no new dependencies)
2. **Retry Mechanism** (Add library, wrap existing code)
3. **Queue System** (Most complex, requires Redis worker)

---

## Testing Strategy

1. **Unit Tests** for each component
2. **Integration Tests** for queue jobs
3. **E2E Tests** for feature flag flows
4. **Performance Tests** for retry overhead

---

## Rollout Plan

1. Deploy to staging first
2. Monitor metrics for 1 week
3. Gradual rollout to production
4. Document lessons learned
