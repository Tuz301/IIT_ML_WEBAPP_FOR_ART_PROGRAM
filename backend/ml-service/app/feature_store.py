"""
Redis-backed feature store for consistent feature engineering
"""
import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from .config import get_settings
from .monitoring import track_redis_operation, feature_store_cache_hits, feature_store_cache_misses
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class FeatureStore:
    """Redis-backed feature store for caching extracted features"""
    
    def __init__(self):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None
        self._connection_healthy = False
    
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            await self.redis_client.ping()
            self._connection_healthy = True
            logger.info("Successfully connected to Redis feature store")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Operating without feature store cache.")
            self._connection_healthy = False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Closed Redis connection")
    
    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy"""
        return self._connection_healthy
    
    def _generate_feature_key(self, patient_uuid: str, data_hash: str) -> str:
        """Generate unique feature key for a patient"""
        return f"features:iit:{patient_uuid}:{data_hash}"
    
    def _hash_patient_data(self, patient_data: Dict[str, Any]) -> str:
        """Generate hash of patient data for cache key"""
        # Create deterministic hash from patient data
        data_str = json.dumps(patient_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    @track_redis_operation("get_features")
    async def get_features(self, patient_uuid: str, data_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached features from Redis"""
        if not self._connection_healthy or not self.redis_client:
            return None
        
        try:
            key = self._generate_feature_key(patient_uuid, data_hash)
            cached_data = await self.redis_client.get(key)
            
            if cached_data:
                feature_store_cache_hits.inc()
                logger.debug(f"Cache HIT for patient {patient_uuid}")
                return json.loads(cached_data)
            else:
                feature_store_cache_misses.inc()
                logger.debug(f"Cache MISS for patient {patient_uuid}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving features from cache: {e}")
            return None
    
    @track_redis_operation("set_features")
    async def set_features(
        self, 
        patient_uuid: str, 
        data_hash: str, 
        features: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Store extracted features in Redis with TTL"""
        if not self._connection_healthy or not self.redis_client:
            return
        
        try:
            key = self._generate_feature_key(patient_uuid, data_hash)
            ttl = ttl or self.settings.feature_store_ttl
            
            # Add metadata
            cache_entry = {
                "features": features,
                "cached_at": datetime.utcnow().isoformat(),
                "patient_uuid": patient_uuid
            }
            
            await self.redis_client.setex(
                key,
                ttl,
                json.dumps(cache_entry)
            )
            logger.debug(f"Cached features for patient {patient_uuid} with TTL {ttl}s")
        except Exception as e:
            logger.error(f"Error storing features in cache: {e}")
    
    @track_redis_operation("invalidate_patient")
    async def invalidate_patient_cache(self, patient_uuid: str):
        """Invalidate all cached features for a patient"""
        if not self._connection_healthy or not self.redis_client:
            return
        
        try:
            pattern = f"features:iit:{patient_uuid}:*"
            async for key in self.redis_client.scan_iter(match=pattern):
                await self.redis_client.delete(key)
            logger.info(f"Invalidated cache for patient {patient_uuid}")
        except Exception as e:
            logger.error(f"Error invalidating patient cache: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get feature store cache statistics"""
        if not self._connection_healthy or not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis_client.info("stats")
            keyspace = await self.redis_client.info("keyspace")
            
            # Count IIT feature keys
            iit_keys_count = 0
            async for _ in self.redis_client.scan_iter(match="features:iit:*", count=100):
                iit_keys_count += 1
            
            return {
                "status": "connected",
                "total_keys": keyspace.get('db0', {}).get('keys', 0),
                "iit_feature_keys": iit_keys_count,
                "used_memory_human": info.get('used_memory_human', 'N/A'),
                "total_commands_processed": info.get('total_commands_processed', 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}


# Global feature store instance
_feature_store: Optional[FeatureStore] = None


async def get_feature_store() -> FeatureStore:
    """Get or create global feature store instance"""
    global _feature_store
    if _feature_store is None:
        _feature_store = FeatureStore()
        await _feature_store.connect()
    return _feature_store
