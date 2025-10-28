"""
Conversation and message Pydantic schemas.

These schemas handle validation for chat conversations and messages.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime
import json


class MessageContentSchema(BaseModel):
    """Schema for message content structure."""
    type: str = Field(..., pattern="^(string|plot|data|multi)$", description="Type of content")
    value: Any = Field(..., description="Content value (can be string, dict, list, etc.)")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment about the content")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "string",
                "value": "Here is the market analysis...",
                "comment": None
            }
        }
    )


class MessageCreateSchema(BaseModel):
    """Schema for creating a new message."""
    conversation_id: int = Field(..., gt=0, description="ID of the conversation")
    sender: str = Field(..., pattern="^(user|bot)$", description="Message sender")
    content: str = Field(..., min_length=1, description="Message content (JSON string)")

    @field_validator('content')
    @classmethod
    def validate_content_json(cls, v: str) -> str:
        """Validate that content is valid JSON."""
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError:
            raise ValueError('Content must be valid JSON string')

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": 1,
                "sender": "user",
                "content": '{"type": "string", "value": "What are module prices?", "comment": null}'
            }
        }
    )


class MessageSchema(BaseModel):
    """Schema for message response."""
    id: int
    conversation_id: int
    sender: str = Field(..., pattern="^(user|bot)$")
    content: str = Field(..., description="Message content as JSON string")
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageWithParsedContentSchema(MessageSchema):
    """Schema for message with parsed content."""
    parsed_content: Optional[MessageContentSchema] = None

    @classmethod
    def from_message(cls, message):
        """Create schema from Message model with parsed content."""
        try:
            parsed = json.loads(message.content) if isinstance(message.content, str) else message.content
            parsed_content = MessageContentSchema(**parsed) if parsed else None
        except (json.JSONDecodeError, ValueError):
            parsed_content = None

        return cls(
            id=message.id,
            conversation_id=message.conversation_id,
            sender=message.sender,
            content=message.content,
            timestamp=message.timestamp,
            parsed_content=parsed_content
        )


class ConversationCreateSchema(BaseModel):
    """Schema for creating a new conversation."""
    title: Optional[str] = Field(None, max_length=256, description="Conversation title")
    agent_type: str = Field(
        default="market",
        pattern="^(market|price|news|digitalization|leo_om|weaviate)$",
        description="Type of agent for this conversation"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Market Analysis Q1 2024",
                "agent_type": "market"
            }
        }
    )


class ConversationUpdateSchema(BaseModel):
    """Schema for updating a conversation."""
    title: Optional[str] = Field(None, max_length=256)

    model_config = ConfigDict(from_attributes=True)


class ConversationSchema(BaseModel):
    """Schema for conversation response."""
    id: int
    title: Optional[str] = None
    created_at: datetime
    agent_type: str = "market"
    user_id: int
    message_count: int = Field(default=0, ge=0)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Market Analysis Q1 2024",
                "created_at": "2024-01-01T00:00:00",
                "agent_type": "market",
                "user_id": 1,
                "message_count": 5
            }
        }
    )


class ConversationWithMessagesSchema(ConversationSchema):
    """Schema for conversation with all messages."""
    messages: List[MessageSchema] = Field(default_factory=list)

    @classmethod
    def from_conversation(cls, conversation, include_messages: bool = True):
        """Create schema from Conversation model."""
        message_count = conversation.messages.count() if hasattr(conversation.messages, 'count') else len(conversation.messages)

        data = {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "agent_type": conversation.agent_type,
            "user_id": conversation.user_id,
            "message_count": message_count,
            "messages": []
        }

        if include_messages:
            messages = conversation.messages.all() if hasattr(conversation.messages, 'all') else conversation.messages
            data["messages"] = [
                MessageSchema(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    sender=msg.sender,
                    content=msg.content,
                    timestamp=msg.timestamp
                )
                for msg in messages
            ]

        return cls(**data)


class ConversationListSchema(BaseModel):
    """Schema for list of conversations."""
    conversations: List[ConversationSchema]
    total: int = Field(..., ge=0)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=100)

    model_config = ConfigDict(from_attributes=True)


class ConversationDeleteSchema(BaseModel):
    """Schema for conversation deletion confirmation."""
    conversation_id: int = Field(..., gt=0)
    confirm: bool = Field(..., description="Confirmation of deletion")

    @field_validator('confirm')
    @classmethod
    def validate_confirmation(cls, v: bool) -> bool:
        """Ensure user confirms deletion."""
        if not v:
            raise ValueError('You must confirm conversation deletion')
        return v
