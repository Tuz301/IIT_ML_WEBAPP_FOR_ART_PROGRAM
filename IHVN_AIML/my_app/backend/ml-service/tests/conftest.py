"""
Pytest configuration and shared fixtures
"""
import pytest
import sys
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))


@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        "test_mode": True,
        "redis_enabled": False,
        "model_path": "./tests/fixtures/mock_model.txt"
    }


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    class MockRedis:
        async def get(self, key):
            return None
        
        async def setex(self, key, ttl, value):
            pass
        
        async def delete(self, key):
            pass
        
        async def ping(self):
            return True
    
    return MockRedis()
