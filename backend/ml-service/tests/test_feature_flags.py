"""
Tests for Feature Flags System
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.features.service import FeatureFlagService
from app.features.flags import feature_flag, is_enabled, get_flag, with_feature_flag
from app.features.models import FeatureFlag as FeatureFlagModel


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def feature_flag_service(mock_db_session):
    """Create feature flag service with mocked DB"""
    service = FeatureFlagService(db_session_factory=lambda: mock_db_session)
    return service


class TestFeatureFlagService:
    """Test FeatureFlagService"""
    
    def test_create_flag(self, feature_flag_service, mock_db_session):
        """Test creating a new feature flag"""
        # Mock the query to return None (flag doesn't exist)
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        result = feature_flag_service.create_flag(
            name="test_flag",
            description="Test flag",
            enabled=True,
            user_percentage=50
        )
        
        assert result is not None
        assert result["name"] == "test_flag"
        assert result["enabled"] is True
        assert result["user_percentage"] == 50
    
    def test_create_duplicate_flag(self, feature_flag_service, mock_db_session):
        """Test creating a duplicate flag returns None"""
        # Mock the query to return an existing flag
        existing_flag = FeatureFlagModel(name="test_flag", enabled=True, user_percentage=0)
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_flag
        
        result = feature_flag_service.create_flag(name="test_flag")
        
        assert result is None
    
    def test_is_enabled_with_enabled_flag(self, feature_flag_service, mock_db_session):
        """Test checking enabled flag"""
        # Mock flag data
        flag = FeatureFlagModel(
            name="test_flag",
            enabled=True,
            user_percentage=100,
            user_whitelist=None
        )
        mock_db_session.query.return_value.filter.return_value.first.return_value = flag
        
        result = feature_flag_service.is_enabled("test_flag")
        
        assert result is True
    
    def test_is_enabled_with_disabled_flag(self, feature_flag_service, mock_db_session):
        """Test checking disabled flag"""
        # Mock flag data
        flag = FeatureFlagModel(
            name="test_flag",
            enabled=False,
            user_percentage=0,
            user_whitelist=None
        )
        mock_db_session.query.return_value.filter.return_value.first.return_value = flag
        
        result = feature_flag_service.is_enabled("test_flag")
        
        assert result is False
    
    def test_is_enabled_with_whitelist(self, feature_flag_service, mock_db_session):
        """Test whitelist functionality"""
        # Mock flag data
        flag = FeatureFlagModel(
            name="test_flag",
            enabled=True,
            user_percentage=0,
            user_whitelist=["user123", "user456"]
        )
        mock_db_session.query.return_value.filter.return_value.first.return_value = flag
        
        # User in whitelist
        assert feature_flag_service.is_enabled("test_flag", user_id="user123") is True
        
        # User not in whitelist
        assert feature_flag_service.is_enabled("test_flag", user_id="user789") is False
    
    def test_update_flag(self, feature_flag_service, mock_db_session):
        """Test updating a flag"""
        # Mock existing flag
        flag = FeatureFlagModel(
            name="test_flag",
            enabled=False,
            user_percentage=0,
            user_whitelist=None
        )
        mock_db_session.query.return_value.filter.return_value.first.return_value = flag
        mock_db_session.commit = Mock()
        mock_db_session.refresh = Mock()
        
        result = feature_flag_service.update_flag("test_flag", enabled=True, user_percentage=75)
        
        assert result is not None
        assert result["enabled"] is True
        assert result["user_percentage"] == 75
    
    def test_delete_flag(self, feature_flag_service, mock_db_session):
        """Test deleting a flag"""
        # Mock existing flag
        flag = FeatureFlagModel(name="test_flag", enabled=True, user_percentage=0)
        mock_db_session.query.return_value.filter.return_value.first.return_value = flag
        mock_db_session.delete = Mock()
        mock_db_session.commit = Mock()
        
        result = feature_flag_service.delete_flag("test_flag")
        
        assert result is True


class TestFeatureFlagDecorators:
    """Test feature flag decorators"""
    
    @patch('app.features.flags.get_feature_flag_service')
    def test_feature_flag_decorator_enabled(self, mock_service):
        """Test decorator with enabled flag"""
        # Mock service
        mock_service_instance = Mock()
        mock_service_instance.is_enabled.return_value = True
        mock_service.return_value = mock_service_instance
        
        @feature_flag("test_feature")
        def test_function():
            return "success"
        
        result = test_function()
        
        assert result == "success"
        mock_service_instance.is_enabled.assert_called_once_with("test_feature", None, "production", False)
    
    @patch('app.features.flags.get_feature_flag_service')
    def test_feature_flag_decorator_disabled(self, mock_service):
        """Test decorator with disabled flag"""
        # Mock service
        mock_service_instance = Mock()
        mock_service_instance.is_enabled.return_value = False
        mock_service.return_value = mock_service_instance
        
        @feature_flag("test_feature")
        def test_function():
            return "success"
        
        result = test_function()
        
        assert result is None
    
    @patch('app.features.flags.get_feature_flag_service')
    def test_is_enabled_function(self, mock_service):
        """Test is_enabled helper function"""
        mock_service_instance = Mock()
        mock_service_instance.is_enabled.return_value = True
        mock_service.return_value = mock_service_instance
        
        result = is_enabled("test_feature", user_id="user123")
        
        assert result is True
        mock_service_instance.is_enabled.assert_called_once_with("test_feature", "user123", "production", False)
    
    @patch('app.features.flags.get_feature_flag_service')
    def test_with_feature_flag(self, mock_service):
        """Test with_feature_flag helper"""
        mock_service_instance = Mock()
        mock_service_instance.is_enabled.return_value = True
        mock_service.return_value = mock_service_instance
        
        result = with_feature_flag(
            "test_feature",
            enabled_value="new_value",
            disabled_value="old_value"
        )
        
        assert result == "new_value"


class TestFeatureFlagModel:
    """Test FeatureFlag model"""
    
    def test_is_enabled_for_user_with_percentage(self):
        """Test percentage-based rollout"""
        flag = FeatureFlagModel(
            name="test_flag",
            enabled=True,
            user_percentage=50,
            user_whitelist=None
        )
        
        # Test with different user IDs - should be consistent
        result1 = flag.is_enabled_for_user("user123")
        result2 = flag.is_enabled_for_user("user123")
        
        # Same user should get same result
        assert result1 == result2
    
    def test_is_enabled_for_user_with_whitelist(self):
        """Test whitelist in model"""
        flag = FeatureFlagModel(
            name="test_flag",
            enabled=True,
            user_percentage=0,
            user_whitelist=["user123"]
        )
        
        assert flag.is_enabled_for_user("user123") is True
        assert flag.is_enabled_for_user("user456") is False
    
    def test_is_enabled_for_user_disabled(self):
        """Test disabled flag"""
        flag = FeatureFlagModel(
            name="test_flag",
            enabled=False,
            user_percentage=100,
            user_whitelist=None
        )
        
        assert flag.is_enabled_for_user("user123") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
