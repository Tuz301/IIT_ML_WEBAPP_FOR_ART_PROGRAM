"""
Redis-based caching middleware for FastAPI
"""
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from ..config import get_settings
from ..monitoring import MetricsManager

logger = logging.getLogger(__name__)
settings = get_settings()

class CacheConfig:
    """Configuration for caching behavior"""

    def __init__(self):
        self.enabled = getattr(settings, 'cache_enabled', True)
        self.redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379')
        self.default_ttl = getattr(settings, 'cache_default_ttl', 300)  # 5 minutes
        self.max_cache_size = getattr(settings, 'cache_max_size', 1000)  # Max cache entries
        self.cacheable_methods = getattr(settings, 'cacheable_methods', ['GET'])
        self.cacheable_status_codes = getattr(settings, 'cacheable_status_codes', [200, 201, 202])
        self.exclude_paths = getattr(settings, 'cache_exclude_paths', ['/health', '/metrics', '/docs'])
        self.include_headers = getattr(settings, 'cache_include_headers', ['content-type', 'content-length'])

class RedisCache:
    """Redis-based cache implementation"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """Establish Redis connection"""
        if not self.config.enabled:
            return

        try:
            self.redis = redis.Redis.from_url(self.config.redis_url, decode_responses=True)
            await self.redis.ping()
            self._connected = True
            logger.info("Redis cache connection established")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis cache: {e}")
            self._connected = False

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self._connected = False

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._connected and self.redis is not None

    def _generate_cache_key(self, request: Request) -> str:
        """Generate a unique cache key for the request"""
        # Include method, path, query params, and relevant headers
        key_parts = [
            request.method,
            str(request.url.path),
            str(request.url.query),
        ]

        # Include specific headers that affect response
        for header_name in ['accept', 'accept-language', 'user-agent']:
            header_value = request.headers.get(header_name)
            if header_value:
                key_parts.append(f"{header_name}:{header_value}")

        # Create hash of the key parts
        key_string = "|".join(key_parts)
        cache_key = f"api_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
        return cache_key

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        if not self.is_connected():
            return None

        try:
            cached_data = await self.redis.get(key)
            if cached_data:
                # Parse JSON data
                cache_entry = json.loads(cached_data)
                # Check if cache entry is still valid
                if datetime.fromisoformat(cache_entry['expires_at']) > datetime.utcnow():
                    MetricsManager.record_cache_hit()
                    logger.debug(f"Cache hit for key: {key}")
                    return cache_entry
                else:
                    # Cache expired, remove it
                    await self.delete(key)
                    MetricsManager.record_cache_miss()
                    return None

            MetricsManager.record_cache_miss()
            return None

        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            MetricsManager.record_cache_miss()
            return None

    async def set(self, key: str, response_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set cached response"""
        if not self.is_connected():
            return False

        try:
            ttl_value = ttl or self.config.default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_value)

            cache_entry = {
                'data': response_data,
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': expires_at.isoformat(),
                'ttl': ttl_value
            }

            # Check cache size limit
            current_size = await self.redis.dbsize()
            if current_size >= self.config.max_cache_size:
                # Remove oldest entries (simple LRU approximation)
                await self._cleanup_old_entries()

            success = await self.redis.setex(key, ttl_value, json.dumps(cache_entry))
            if success:
                logger.debug(f"Cache set for key: {key}, TTL: {ttl_value}s")
            return bool(success)

        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete cached entry"""
        if not self.is_connected():
            return False

        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching a pattern"""
        if not self.is_connected():
            return 0

        try:
            keys = await self.redis.keys(pattern)
            if keys:
                result = await self.redis.delete(*keys)
                logger.info(f"Cleared {result} cache entries matching pattern: {pattern}")
                return result
            return 0
        except Exception as e:
            logger.warning(f"Cache clear pattern error for {pattern}: {e}")
            return 0

    async def clear_all(self) -> bool:
        """Clear all cache entries"""
        if not self.is_connected():
            return False

        try:
            result = await self.redis.flushdb()
            logger.info("Cleared all cache entries")
            return result
        except Exception as e:
            logger.warning(f"Cache clear all error: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.is_connected():
            return {"status": "disconnected"}

        try:
            info = await self.redis.info()
            dbsize = await self.redis.dbsize()

            return {
                "status": "connected",
                "size": dbsize,
                "max_size": self.config.max_cache_size,
                "redis_info": {
                    "used_memory": info.get('used_memory_human', 'unknown'),
                    "connected_clients": info.get('connected_clients', 0),
                    "uptime_days": info.get('uptime_in_days', 0)
                }
            }
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return {"status": "error", "error": str(e)}

    async def _cleanup_old_entries(self):
        """Clean up old cache entries when approaching size limit"""
        try:
            # Get all cache keys
            keys = await self.redis.keys("api_cache:*")
            if len(keys) > self.config.max_cache_size * 0.8:  # 80% of max size
                # Remove 20% of entries (oldest first approximation)
                remove_count = int(len(keys) * 0.2)
                # In a real implementation, you'd track access times
                # For now, just remove some entries
                keys_to_remove = keys[:remove_count]
                if keys_to_remove:
                    await self.redis.delete(*keys_to_remove)
                    logger.info(f"Cleaned up {len(keys_to_remove)} old cache entries")
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")

class APICachingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for API response caching"""

    def __init__(self, app, cache_config: Optional[CacheConfig] = None):
        super().__init__(app)
        self.cache_config = cache_config or CacheConfig()
        self.cache = RedisCache(self.cache_config)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip caching for non-cacheable requests
        if not self._should_cache_request(request):
            return await call_next(request)

        cache_key = self.cache._generate_cache_key(request)

        # Try to get cached response
        cached_response = await self.cache.get(cache_key)
        if cached_response:
            # Return cached response
            response_data = cached_response['data']
            response = Response(
                content=response_data.get('body', ''),
                status_code=response_data.get('status_code', 200),
                headers=response_data.get('headers', {}),
                media_type=response_data.get('media_type')
            )
            return response

        # Process the request
        response = await call_next(request)

        # Cache the response if it's cacheable
        if self._should_cache_response(response):
            await self._cache_response(cache_key, request, response)

        return response

    def _should_cache_request(self, request: Request) -> bool:
        """Determine if request should be cached"""
        if not self.cache_config.enabled:
            return False

        # Check method
        if request.method not in self.cache_config.cacheable_methods:
            return False

        # Check path
        if any(excluded in request.url.path for excluded in self.cache_config.exclude_paths):
            return False

        # Check if Redis is connected
        if not self.cache.is_connected():
            return False

        return True

    def _should_cache_response(self, response: Response) -> bool:
        """Determine if response should be cached"""
        # Check status code
        if response.status_code not in self.cache_config.cacheable_status_codes:
            return False

        # Check content type (only cache JSON/HTML responses)
        content_type = response.headers.get('content-type', '')
        if not (content_type.startswith('application/json') or content_type.startswith('text/html')):
            return False

        return True

    async def _cache_response(self, cache_key: str, request: Request, response: Response):
        """Cache the response data"""
        try:
            # Get response body
            body = b''
            if hasattr(response, 'body'):
                body = response.body
            elif hasattr(response, 'render'):
                # For streaming responses, we might not cache
                return

            # Prepare cache data
            headers = {}
            for header_name in self.cache_config.include_headers:
                header_value = response.headers.get(header_name)
                if header_value:
                    headers[header_name] = header_value

            response_data = {
                'body': body.decode('utf-8') if isinstance(body, bytes) else str(body),
                'status_code': response.status_code,
                'headers': headers,
                'media_type': response.media_type
            }

            # Determine TTL based on endpoint
            ttl = self._get_endpoint_ttl(request.url.path)

            # Cache the response
            await self.cache.set(cache_key, response_data, ttl)

        except Exception as e:
            logger.warning(f"Failed to cache response for {cache_key}: {e}")

    def _get_endpoint_ttl(self, path: str) -> int:
        """Get TTL for specific endpoint"""
        # Define TTL based on endpoint type
        ttl_config = {
            '/health': 60,  # Health checks - short TTL
            '/metrics': 30,  # Metrics - very short TTL
            '/patients': 300,  # Patient data - 5 minutes
            '/predictions': 180,  # Predictions - 3 minutes
            '/analytics': 600,  # Analytics - 10 minutes
        }

        for endpoint, ttl in ttl_config.items():
            if path.startswith(endpoint):
                return ttl

        return self.cache_config.default_ttl

class CacheManager:
    """High-level cache management interface"""

    def __init__(self, cache: RedisCache):
        self.cache = cache

    async def invalidate_patient_cache(self, patient_uuid: str):
        """Invalidate cache for a specific patient"""
        pattern = f"api_cache:*patients*{patient_uuid}*"
        cleared = await self.cache.clear_pattern(pattern)
        logger.info(f"Invalidated {cleared} cache entries for patient {patient_uuid}")

    async def invalidate_endpoint_cache(self, endpoint: str):
        """Invalidate cache for a specific endpoint"""
        pattern = f"api_cache:*{endpoint}*"
        cleared = await self.cache.clear_pattern(pattern)
        logger.info(f"Invalidated {cleared} cache entries for endpoint {endpoint}")

    async def invalidate_all_cache(self):
        """Invalidate all cache entries"""
        success = await self.cache.clear_all()
        if success:
            logger.info("Invalidated all cache entries")
        else:
            logger.warning("Failed to invalidate all cache entries")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        cache_stats = await self.cache.get_stats()

        # Add hit/miss ratios from metrics
        total_requests = MetricsManager.get_cache_total_requests()
        hit_ratio = MetricsManager.get_cache_hit_ratio()

        cache_stats.update({
            "hit_ratio": hit_ratio,
            "total_requests": total_requests,
            "hits": MetricsManager.get_cache_hits(),
            "misses": MetricsManager.get_cache_misses()
        })

        return cache_stats

# Global instances
cache_config = CacheConfig()
redis_cache = RedisCache(cache_config)
cache_manager = CacheManager(redis_cache)

# Middleware instance
caching_middleware = APICachingMiddleware(None, cache_config)
