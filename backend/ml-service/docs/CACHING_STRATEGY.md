# Caching Strategy Documentation

## Overview
The IIT ML Service uses a multi-layered caching strategy to optimize performance:

1. **Redis Cache** (Primary) - Distributed cache for production
2. **In-Memory Cache** (Fallback) - Simple LRU cache for development
3. **Database Query Cache** - SQLAlchemy-level query result caching

## Cache Layers

### 1. API Response Caching
Implemented in [`app/middleware/caching.py`](../app/middleware/caching.py)

**Features:**
- Automatic caching of GET requests
- Configurable TTL per endpoint
- Cache invalidation on data changes
- Hit/miss tracking with metrics

**Cacheable Endpoints:**
- `/health` - 60s TTL
- `/metrics` - 30s TTL
- `/patients` - 300s TTL
- `/predictions` - 180s TTL
- `/analytics` - 600s TTL

**Excluded Paths:**
- `/docs` - API documentation
- `/openapi.json` - OpenAPI schema

### 2. In-Memory Cache (Fallback)
Implemented in [`app/middleware/simple_cache.py`](../app/middleware/simple_cache.py)

**Features:**
- LRU (Least Recently Used) eviction
- Configurable max size (default: 1000 entries)
- Automatic expiration cleanup
- Hit/miss statistics

**Usage:**
```python
from app.middleware.simple_cache import SimpleMemoryCache

# Create cache instance
cache = SimpleMemoryCache(max_size=1000, default_ttl=300)

# Get value
value = cache.get("my_key")

# Set value
cache.set("my_key", {"data": "value"}, ttl=300)

# Get statistics
stats = cache.get_stats()
```

### 3. Hybrid Cache
Combines Redis and in-memory cache for resilience:

```python
from app.middleware.simple_cache import HybridCache

# Create hybrid cache
hybrid = HybridCache(redis_cache=redis_cache)

# Automatically tries Redis first, falls back to memory
value = await hybrid.get("my_key")
```

### 4. Feature Store Cache
Implemented in [`app/feature_store.py`](../app/feature_store.py)

**Features:**
- Cached patient features for ML predictions
- TTL: 24 hours (86400 seconds)
- Automatic refresh on data updates
- Reduces database load for predictions

## Cache Configuration

### Environment Variables
```bash
# Enable/disable caching
CACHE_ENABLED=true

# Redis connection
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Cache settings
CACHE_DEFAULT_TTL=300
CACHE_MAX_SIZE=1000
CACHE_EXCLUDE_PATHS=/health,/metrics,/docs
```

### Config File (config.py)
```python
class Settings(BaseSettings):
    # Caching Configuration
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5 minutes default TTL
    cache_max_size: int = 1000  # Maximum cache entries
    cache_exclude_patterns: list[str] = ["/health", "/metrics", "/docs"]
    
    # Feature Store Configuration
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    feature_store_ttl: int = 86400  # 24 hours
```

## Cache Invalidation

### Automatic Invalidation
Cache is automatically invalidated when:
- Data is updated (patients, observations, predictions)
- TTL expires
- Cache size limit reached

### Manual Invalidation
```python
from app.middleware.caching import cache_manager

# Invalidate specific patient cache
await cache_manager.invalidate_patient_cache(patient_uuid="abc-123")

# Invalidate endpoint cache
await cache_manager.invalidate_endpoint_cache("/predictions")

# Invalidate all cache
await cache_manager.invalidate_all_cache()
```

## Cache Statistics

### Monitoring
Cache metrics are exposed at `/metrics`:
- `api_cache_hits_total` - Total cache hits
- `api_cache_misses_total` - Total cache misses
- `api_cache_hit_ratio` - Cache hit rate percentage

### View Statistics
```python
from app.middleware.caching import cache_manager

# Get cache statistics
stats = await cache_manager.get_cache_stats()
print(stats)
```

**Response:**
```json
{
  "status": "connected",
  "size": 1250,
  "max_size": 1000,
  "hit_ratio": 0.85,
  "total_requests": 5000,
  "hits": 4250,
  "misses": 750
}
```

## Best Practices

### 1. Cache Key Design
- Include request method, path, and query parameters
- Include relevant headers (accept-language, user-agent)
- Use MD5 hash for consistent keys

### 2. TTL Selection
- Short TTL for frequently changing data (30-60s)
- Medium TTL for reference data (300-600s)
- Long TTL for computed results (86400s+)

### 3. Cache Size Management
- Monitor cache hit ratio (target: > 80%)
- Set appropriate max size to prevent memory issues
- Use LRU eviction for automatic cleanup

### 4. Redis Configuration
- Enable maxmemory-policy for automatic eviction
- Configure persistence for durability
- Use connection pooling for performance

## Troubleshooting

### Low Cache Hit Ratio
**Problem:** Cache hit ratio < 50%

**Solutions:**
1. Check if cache is enabled: `CACHE_ENABLED=true`
2. Verify Redis connection
3. Review exclude patterns
4. Increase TTL for stable data

### High Memory Usage
**Problem:** Cache using too much memory

**Solutions:**
1. Reduce max cache size
2. Decrease TTL values
3. Enable Redis maxmemory-policy
4. Monitor cache size regularly

### Cache Not Working
**Problem:** Responses not being cached

**Solutions:**
1. Check request method (only GET is cached)
2. Verify response status code (200, 201, 202)
3. Check content-type header
4. Review exclude paths configuration

## Performance Impact

### Expected Improvements
- **API Response Time**: 50-80% reduction for cached requests
- **Database Load**: 60-90% reduction for cached queries
- **Prediction Latency**: 30-50% reduction with feature store cache
- **Throughput**: 2-3x increase for cacheable endpoints

## Development vs Production

### Development (In-Memory Cache)
- No Redis required
- Simpler setup
- Data lost on restart
- Use for local testing

### Production (Redis Cache)
- Distributed cache across instances
- Persistent storage
- Better scalability
- Required for multi-instance deployments
