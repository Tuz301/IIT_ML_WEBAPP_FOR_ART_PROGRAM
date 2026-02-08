"""
Simple in-memory cache fallback for development
Used when Redis is not available
"""
import json
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger(__name__)

class SimpleMemoryCache:
    """
    Simple in-memory cache with LRU eviction
    Fallback when Redis is not available
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value"""
        if key in self.cache:
            entry = self.cache[key]
            # Check if expired
            if datetime.fromisoformat(entry['expires_at']) > datetime.utcnow():
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                logger.debug(f"Cache hit for key: {key}")
                return entry['data']
            else:
                # Expired, remove it
                del self.cache[key]
        
        self.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value"""
        ttl_value = ttl or self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_value)

        # Check size limit
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (LRU)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Evicted oldest cache entry: {oldest_key}")

        self.cache[key] = {
            'data': value,
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.utcnow().isoformat(),
            'ttl': ttl_value
        }
        logger.debug(f"Cache set for key: {key}, TTL: {ttl_value}s")
        return True

    def delete(self, key: str) -> bool:
        """Delete cached value"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Cleared all cache entries")

    def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern"""
        keys_to_delete = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.cache[key]
        logger.info(f"Cleared {len(keys_to_delete)} cache entries matching pattern: {pattern}")
        return len(keys_to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_ratio = (self.hits / total_requests) if total_requests > 0 else 0

        return {
            "status": "connected",
            "type": "memory",
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": round(hit_ratio * 100, 2)
        }

    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        now = datetime.utcnow()
        expired_keys = [
            k for k, v in self.cache.items()
            if datetime.fromisoformat(v['expires_at']) < now
        ]
        for key in expired_keys:
            del self.cache[key]
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        return len(expired_keys)


class HybridCache:
    """
    Hybrid cache that tries Redis first, falls back to memory cache
    """

    def __init__(self, redis_cache=None, max_size: int = 1000, default_ttl: int = 300):
        self.redis_cache = redis_cache
        self.memory_cache = SimpleMemoryCache(max_size, default_ttl)
        self.redis_available = redis_cache is not None

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value - try Redis first, then memory"""
        if self.redis_available:
            try:
                # Try to get from Redis
                result = await self.redis_cache.get(key)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Redis get failed, falling back to memory cache: {e}")
                self.redis_available = False

        # Fall back to memory cache
        return self.memory_cache.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value - try Redis first, then memory"""
        if self.redis_available:
            try:
                # Try to set in Redis
                result = await self.redis_cache.set(key, value, ttl)
                if result:
                    return True
            except Exception as e:
                logger.warning(f"Redis set failed, falling back to memory cache: {e}")
                self.redis_available = False

        # Fall back to memory cache
        return self.memory_cache.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete cached value - try Redis first, then memory"""
        if self.redis_available:
            try:
                await self.redis_cache.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
                self.redis_available = False

        # Also delete from memory cache
        return self.memory_cache.delete(key)

    async def clear(self) -> None:
        """Clear all cache entries"""
        if self.redis_available:
            try:
                await self.redis_cache.clear_all()
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")
        self.memory_cache.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.memory_cache.get_stats()
        stats["redis_available"] = self.redis_available
        return stats


# Global instance
hybrid_cache = HybridCache()
