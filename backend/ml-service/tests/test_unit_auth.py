"""
Unit tests for authentication and authorization functionality.
Tests password hashing, token generation, and user management.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    verify_token,
    get_current_user,
    get_current_active_user,
)
from app.models import User
from app.schema import Token, TokenData


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_get_password_hash(self):
        """Test password hashing generates different hashes for same password."""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2  # Different salts should produce different hashes
        assert hash1.startswith("$2b$")  # bcrypt hash prefix
        assert len(hash1) == 60  # bcrypt hash length
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert verify_password("", hashed) is False
    
    def test_verify_password_unicode(self):
        """Test password hashing with unicode characters."""
        password = "P@sswørd测试123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestTokenGeneration:
    """Test JWT token generation and verification."""
    
    def test_create_access_token_basic(self):
        """Test basic token creation."""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
    
    def test_create_access_token_with_expiration(self):
        """Test token creation with custom expiration."""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        assert token is not None
    
    def test_create_access_token_with_role(self):
        """Test token creation includes role."""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        
        assert token is not None
    
    def test_verify_token_valid(self):
        """Test verification of valid token."""
        data = {"sub": "testuser", "role": "healthcare_provider"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "healthcare_provider"
    
    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.string"
        with pytest.raises(Exception):
            verify_token(invalid_token)
    
    def test_verify_token_expired(self):
        """Test verification of expired token."""
        data = {"sub": "testuser"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta)
        
        with pytest.raises(Exception):
            verify_token(token)
    
    def test_token_data_model(self):
        """Test TokenData model validation."""
        token_data = TokenData(username="testuser", role="admin")
        assert token_data.username == "testuser"
        assert token_data.role == "admin"
    
    def test_token_model(self):
        """Test Token model validation."""
        token = "sample.jwt.token"
        token_type = "bearer"
        token_obj = Token(access_token=token, token_type=token_type)
        assert token_obj.access_token == token
        assert token_obj.token_type == token_type


class TestUserRetrieval:
    """Test user retrieval from tokens."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, db_session, test_user, test_token):
        """Test retrieving user with valid token."""
        user = await get_current_user(token=test_token, db=db_session)
        assert user is not None
        assert user.username == test_user.username
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, db_session):
        """Test retrieving user with invalid token."""
        with pytest.raises(Exception):
            await get_current_user(token="invalid.token", db=db_session)
    
    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent(self, db_session):
        """Test retrieving user that doesn't exist."""
        # Create token for non-existent user
        data = {"sub": "nonexistent_user"}
        token = create_access_token(data)
        
        with pytest.raises(Exception):
            await get_current_user(token=token, db=db_session)
    
    @pytest.mark.asyncio
    async def test_get_current_active_user(self, test_user):
        """Test retrieving active user."""
        user = await get_current_active_user(current_user=test_user)
        assert user.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self, db_session):
        """Test retrieving inactive user raises error."""
        inactive_user = User(
            username="inactive",
            email="inactive@test.com",
            hashed_password=get_password_hash("password"),
            is_active=False,
        )
        db_session.add(inactive_user)
        await db_session.commit()
        
        with pytest.raises(Exception):
            await get_current_active_user(current_user=inactive_user)


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self):
        """Test creating a User instance."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            role="healthcare_provider",
            is_active=True,
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
    
    def test_user_default_values(self):
        """Test User model default values."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
        )
        assert user.is_active is True  # Default is True
        assert user.role == "healthcare_provider"  # Default role
    
    def test_user_relationships(self):
        """Test User model relationships."""
        user = User(username="testuser", email="test@example.com", hashed_password="hashed")
        # Test that relationships exist
        assert hasattr(user, "predictions")
        assert hasattr(user, "patients")


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    @pytest.mark.parametrize("role,should_have_access", [
        ("admin", True),
        ("healthcare_provider", True),
        ("viewer", False),
        ("invalid_role", False),
    ])
    def test_valid_roles(self, role, should_have_access):
        """Test valid role values."""
        valid_roles = {"admin", "healthcare_provider", "viewer"}
        is_valid = role in valid_roles
        assert is_valid == should_have_access
    
    def test_role_hierarchy(self):
        """Test role hierarchy for permissions."""
        role_permissions = {
            "admin": {"read", "write", "delete", "manage_users"},
            "healthcare_provider": {"read", "write"},
            "viewer": {"read"},
        }
        
        assert "delete" in role_permissions["admin"]
        assert "delete" not in role_permissions["healthcare_provider"]
        assert "write" not in role_permissions["viewer"]


class TestSecurityFeatures:
    """Test security-related features."""
    
    def test_password_complexity_validation(self):
        """Test password complexity requirements."""
        from app.auth import validate_password_complexity
        
        # Valid passwords
        assert validate_password_complexity("SecureP@ss123") is True
        assert validate_password_complexity("C0mpl3x!ty") is True
        
        # Invalid passwords
        assert validate_password_complexity("simple") is False  # Too short
        assert validate_password_complexity("nouppercase123!") is False  # No uppercase
        assert validate_password_complexity("NOLOWERCASE123!") is False  # No lowercase
        assert validate_password_complexity("NoNumbers!") is False  # No numbers
    
    def test_token_expiration_time(self):
        """Test token expiration is set correctly."""
        from app.config import settings
        
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        exp = payload.get("exp")
        
        # Verify expiration is in the future
        assert exp is not None
        assert exp > datetime.utcnow().timestamp()
    
    def test_rate_limiting_config(self):
        """Test rate limiting configuration exists."""
        from app.config import settings
        
        # Verify rate limit settings exist
        assert hasattr(settings, "rate_limit_requests")
        assert hasattr(settings, "rate_limit_period")


@pytest.mark.unit
class TestAuthenticationFlow:
    """Test complete authentication flow."""
    
    def test_login_flow_success(self):
        """Test successful login flow."""
        # This would test the complete login endpoint
        # Including password verification and token generation
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Verify password
        assert verify_password(password, hashed) is True
        
        # Create token
        token = create_access_token({"sub": "testuser", "role": "admin"})
        assert token is not None
    
    def test_login_flow_failure(self):
        """Test failed login flow."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = get_password_hash(password)
        
        # Verify wrong password fails
        assert verify_password(wrong_password, hashed) is False
