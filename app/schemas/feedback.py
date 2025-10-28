"""
Feedback and survey Pydantic schemas.

These schemas handle validation for user feedback and survey responses.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class FeedbackCreateSchema(BaseModel):
    """Schema for creating feedback."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    feedback_text: Optional[str] = Field(None, max_length=2000, description="Optional feedback text")
    allow_followup: bool = Field(default=False, description="Allow follow-up contact")

    @field_validator('feedback_text')
    @classmethod
    def validate_feedback_text(cls, v: Optional[str]) -> Optional[str]:
        """Validate feedback text is not just whitespace."""
        if v is not None and not v.strip():
            return None
        return v.strip() if v else None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating": 5,
                "feedback_text": "Great tool! Very helpful for market analysis.",
                "allow_followup": True
            }
        }
    )


class FeedbackSchema(FeedbackCreateSchema):
    """Schema for feedback response."""
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FeedbackListSchema(BaseModel):
    """Schema for list of feedback."""
    feedback: List[FeedbackSchema]
    total: int = Field(..., ge=0)
    average_rating: Optional[float] = Field(None, ge=1, le=5)

    model_config = ConfigDict(from_attributes=True)


class UserSurveyStage1CreateSchema(BaseModel):
    """Schema for creating Stage 1 user survey response."""
    role: str = Field(..., max_length=50, description="User's role")
    role_other: Optional[str] = Field(None, max_length=100, description="Custom role if 'other' selected")
    regions: str = Field(..., description="JSON array of regions of interest")
    familiarity: str = Field(
        ...,
        pattern="^(beginner|intermediate|advanced|expert)$",
        description="User's familiarity with PV market"
    )
    insights: str = Field(..., description="JSON array of insight types user is interested in")
    tailored: Optional[str] = Field(None, pattern="^(yes|no)$", description="Want tailored insights")

    @field_validator('regions', 'insights')
    @classmethod
    def validate_json_array(cls, v: str) -> str:
        """Validate that field contains valid JSON array."""
        import json
        try:
            data = json.loads(v)
            if not isinstance(data, list):
                raise ValueError('Must be a JSON array')
            return v
        except json.JSONDecodeError:
            raise ValueError('Must be valid JSON')

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "Market Analyst",
                "role_other": None,
                "regions": '["Europe", "Asia"]',
                "familiarity": "intermediate",
                "insights": '["pricing", "trends"]',
                "tailored": "yes"
            }
        }
    )


class UserSurveyStage1Schema(UserSurveyStage1CreateSchema):
    """Schema for Stage 1 survey response."""
    id: int
    user_id: int
    created_at: datetime
    bonus_queries_granted: int = Field(default=5, ge=0)

    model_config = ConfigDict(from_attributes=True)


class UserSurveyStage2CreateSchema(BaseModel):
    """Schema for creating Stage 2 user survey response."""
    work_focus: str = Field(..., max_length=100, description="Primary work focus")
    work_focus_other: Optional[str] = Field(None, max_length=100, description="Custom work focus if 'other'")
    pv_segments: str = Field(..., description="JSON array of PV market segments")
    technologies: str = Field(..., description="JSON array of technology interests")
    technologies_other: Optional[str] = Field(None, max_length=200, description="Other technologies")
    challenges: str = Field(..., description="JSON array of top 3 challenges")
    weekly_insight: Optional[str] = Field(None, max_length=1000, description="What weekly insight would be valuable")

    @field_validator('pv_segments', 'technologies', 'challenges')
    @classmethod
    def validate_json_array(cls, v: str) -> str:
        """Validate that field contains valid JSON array."""
        import json
        try:
            data = json.loads(v)
            if not isinstance(data, list):
                raise ValueError('Must be a JSON array')
            return v
        except json.JSONDecodeError:
            raise ValueError('Must be valid JSON')

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "work_focus": "Manufacturing",
                "work_focus_other": None,
                "pv_segments": '["Residential", "Commercial"]',
                "technologies": '["Mono-Si", "TOPCon"]',
                "technologies_other": None,
                "challenges": '["Supply chain", "Pricing", "Quality"]',
                "weekly_insight": "Weekly price updates for top technologies"
            }
        }
    )


class UserSurveyStage2Schema(UserSurveyStage2CreateSchema):
    """Schema for Stage 2 survey response."""
    id: int
    user_id: int
    created_at: datetime
    bonus_queries_granted: int = Field(default=5, ge=0)

    model_config = ConfigDict(from_attributes=True)


class UserSurveyCompleteSchema(BaseModel):
    """Schema for complete survey information."""
    stage1: Optional[UserSurveyStage1Schema] = None
    stage2: Optional[UserSurveyStage2Schema] = None
    total_bonus_queries: int = Field(default=0, ge=0)

    model_config = ConfigDict(from_attributes=True)
