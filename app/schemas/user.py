"""
User-related Pydantic schemas.

These schemas provide validation for user operations and work with both
Flask and FastAPI. They ensure type safety and data validation.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
import re


class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=80, description="Unique username")
    full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")


class UserCreateSchema(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=200, description="User password (will be hashed)")

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "full_name": "John Doe",
                "password": "SecurePass123!"
            }
        }
    )


class UserLoginSchema(BaseModel):
    """Schema for user login."""
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=1, max_length=200)
    remember: bool = Field(default=False, description="Remember user session")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "password": "SecurePass123!",
                "remember": False
            }
        }
    )


class UserUpdateSchema(BaseModel):
    """Schema for user profile updates."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    plan_type: Optional[str] = Field(None, pattern="^(free|premium)$")

    model_config = ConfigDict(from_attributes=True)


class UserGDPRConsentSchema(BaseModel):
    """Schema for GDPR consent updates."""
    gdpr_consent_given: bool = Field(..., description="User consent for GDPR")
    terms_accepted: bool = Field(..., description="Terms of service accepted")
    marketing_consent: bool = Field(default=False, description="Marketing communications consent")
    privacy_policy_version: str = Field(default="1.0", max_length=10)
    terms_version: str = Field(default="1.0", max_length=10)


class UserUsageStatsSchema(BaseModel):
    """Schema for user usage statistics."""
    total_queries: int = Field(..., ge=0)
    monthly_queries: int = Field(..., ge=0)
    query_limit: float = Field(..., ge=0)  # Can be float('inf') for unlimited
    queries_remaining: float = Field(..., ge=0)
    total_conversations: int = Field(..., ge=0)
    total_messages: int = Field(..., ge=0)
    last_query_date: Optional[datetime] = None
    account_age_days: int = Field(..., ge=0)

    model_config = ConfigDict(from_attributes=True)


class UserSchema(UserBase):
    """Schema for user response (public information)."""
    id: int
    role: str = Field(default="user")
    created_at: datetime
    is_active: bool = True
    plan_type: str = Field(default="free")
    monthly_query_count: int = Field(default=0, ge=0)
    query_count: int = Field(default=0, ge=0)
    last_query_date: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "username": "john_doe",
                "full_name": "John Doe",
                "role": "user",
                "created_at": "2024-01-01T00:00:00",
                "is_active": True,
                "plan_type": "free",
                "monthly_query_count": 5,
                "query_count": 42,
                "last_query_date": "2024-01-15T10:30:00"
            }
        }
    )


class UserDetailSchema(UserSchema):
    """Schema for detailed user information (admin/self only)."""
    gdpr_consent_given: bool = False
    gdpr_consent_date: Optional[datetime] = None
    terms_accepted: bool = False
    terms_accepted_date: Optional[datetime] = None
    marketing_consent: bool = False
    privacy_policy_version: str = "1.0"
    terms_version: str = "1.0"
    plan_start_date: Optional[datetime] = None
    plan_end_date: Optional[datetime] = None
    last_reset_date: Optional[datetime] = None
    deleted: bool = False
    deletion_requested_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserDeleteRequestSchema(BaseModel):
    """Schema for user account deletion request."""
    deletion_reason: Optional[str] = Field(None, max_length=500, description="Optional reason for deletion")
    confirm: bool = Field(..., description="Confirmation that user wants to delete account")

    @field_validator('confirm')
    @classmethod
    def validate_confirmation(cls, v: bool) -> bool:
        """Ensure user confirms deletion."""
        if not v:
            raise ValueError('You must confirm account deletion')
        return v


class WaitlistSchema(BaseModel):
    """Schema for waitlist signup."""
    email: str = Field(..., description="Email address for waitlist", max_length=120)
    interested_agents: Optional[str] = Field(None, max_length=500, description="JSON string of interested agents")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email address format')
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "interested_agents": '["market", "news", "prices"]'
            }
        }
    )


class WaitlistResponseSchema(WaitlistSchema):
    """Schema for waitlist response."""
    id: int
    created_at: datetime
    notified: bool = False
    notified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
