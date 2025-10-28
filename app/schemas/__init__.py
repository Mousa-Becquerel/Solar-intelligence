"""
Pydantic schemas package.

This package contains Pydantic schemas for:
- Input validation
- Output serialization
- API documentation (FastAPI-ready)
- Type safety across the application
"""

# User schemas
from app.schemas.user import (
    UserBase,
    UserCreateSchema,
    UserLoginSchema,
    UserUpdateSchema,
    UserGDPRConsentSchema,
    UserUsageStatsSchema,
    UserSchema,
    UserDetailSchema,
    UserDeleteRequestSchema,
    WaitlistSchema,
    WaitlistResponseSchema,
)

# Conversation schemas
from app.schemas.conversation import (
    MessageContentSchema,
    MessageCreateSchema,
    MessageSchema,
    MessageWithParsedContentSchema,
    ConversationCreateSchema,
    ConversationUpdateSchema,
    ConversationSchema,
    ConversationWithMessagesSchema,
    ConversationListSchema,
    ConversationDeleteSchema,
)

# Agent schemas
from app.schemas.agent import (
    AgentQuerySchema,
    PlotDataSchema,
    DataAnalysisSchema,
    AgentResponseSchema,
    HiredAgentCreateSchema,
    HiredAgentSchema,
    HiredAgentListSchema,
    AgentAvailableSchema,
    StreamEventSchema,
)

# Feedback schemas
from app.schemas.feedback import (
    FeedbackCreateSchema,
    FeedbackSchema,
    FeedbackListSchema,
    UserSurveyStage1CreateSchema,
    UserSurveyStage1Schema,
    UserSurveyStage2CreateSchema,
    UserSurveyStage2Schema,
    UserSurveyCompleteSchema,
)

__all__ = [
    # User
    "UserBase",
    "UserCreateSchema",
    "UserLoginSchema",
    "UserUpdateSchema",
    "UserGDPRConsentSchema",
    "UserUsageStatsSchema",
    "UserSchema",
    "UserDetailSchema",
    "UserDeleteRequestSchema",
    "WaitlistSchema",
    "WaitlistResponseSchema",
    # Conversation
    "MessageContentSchema",
    "MessageCreateSchema",
    "MessageSchema",
    "MessageWithParsedContentSchema",
    "ConversationCreateSchema",
    "ConversationUpdateSchema",
    "ConversationSchema",
    "ConversationWithMessagesSchema",
    "ConversationListSchema",
    "ConversationDeleteSchema",
    # Agent
    "AgentQuerySchema",
    "PlotDataSchema",
    "DataAnalysisSchema",
    "AgentResponseSchema",
    "HiredAgentCreateSchema",
    "HiredAgentSchema",
    "HiredAgentListSchema",
    "AgentAvailableSchema",
    "StreamEventSchema",
    # Feedback
    "FeedbackCreateSchema",
    "FeedbackSchema",
    "FeedbackListSchema",
    "UserSurveyStage1CreateSchema",
    "UserSurveyStage1Schema",
    "UserSurveyStage2CreateSchema",
    "UserSurveyStage2Schema",
    "UserSurveyCompleteSchema",
]
