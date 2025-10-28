"""
Agent-related Pydantic schemas.

These schemas handle validation for AI agent queries and responses.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class AgentQuerySchema(BaseModel):
    """Schema for agent query request."""
    query: str = Field(..., min_length=1, max_length=5000, description="User query text")
    conversation_id: int = Field(..., gt=0, description="ID of the conversation")
    agent_type: Optional[str] = Field(
        None,
        pattern="^(market|price|news|digitalization|leo_om|weaviate)$",
        description="Specific agent type (auto-detected if None)"
    )

    @field_validator('query')
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        """Ensure query is not just whitespace."""
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What are the current module prices in China?",
                "conversation_id": 1,
                "agent_type": "price"
            }
        }
    )


class PlotDataSchema(BaseModel):
    """Schema for plot data in responses."""
    image_base64: str = Field(..., description="Base64 encoded plot image")
    description: Optional[str] = Field(None, max_length=500, description="Plot description")
    data: Optional[Dict[str, Any]] = Field(None, description="Underlying data for the plot")
    filename: Optional[str] = Field(None, max_length=255, description="Plot filename")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
                "description": "Module prices trend in China 2024",
                "data": {"labels": ["Jan", "Feb"], "values": [0.15, 0.14]},
                "filename": "module_prices_china_2024.png"
            }
        }
    )


class DataAnalysisSchema(BaseModel):
    """Schema for data analysis results."""
    summary: str = Field(..., description="Summary of analysis")
    data: Dict[str, Any] = Field(..., description="Analysis data")
    insights: Optional[List[str]] = Field(None, description="Key insights from analysis")

    model_config = ConfigDict(from_attributes=True)


class AgentResponseSchema(BaseModel):
    """Schema for agent response."""
    type: str = Field(
        ...,
        pattern="^(string|plot|data|multi)$",
        description="Response type"
    )
    value: Union[str, PlotDataSchema, DataAnalysisSchema, List[Any]] = Field(
        ...,
        description="Response value (type depends on 'type' field)"
    )
    comment: Optional[str] = Field(None, max_length=1000, description="Additional comment")
    agent_type: str = Field(..., description="Agent that generated the response")
    processing_time: Optional[float] = Field(None, ge=0, description="Processing time in seconds")
    tokens_used: Optional[int] = Field(None, ge=0, description="Tokens used for generation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "string",
                "value": "Based on the latest data, module prices in China...",
                "comment": None,
                "agent_type": "market",
                "processing_time": 2.5,
                "tokens_used": 450
            }
        }
    )


class HiredAgentCreateSchema(BaseModel):
    """Schema for hiring an agent."""
    agent_type: str = Field(
        ...,
        pattern="^(market|price|news|digitalization|leo_om|weaviate)$",
        description="Type of agent to hire"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_type": "market"
            }
        }
    )


class HiredAgentSchema(BaseModel):
    """Schema for hired agent response."""
    id: int
    user_id: int
    agent_type: str
    hired_at: datetime
    is_active: bool = True

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 1,
                "agent_type": "market",
                "hired_at": "2024-01-01T00:00:00",
                "is_active": True
            }
        }
    )


class HiredAgentListSchema(BaseModel):
    """Schema for list of hired agents."""
    agents: List[HiredAgentSchema]
    total: int = Field(..., ge=0)

    model_config = ConfigDict(from_attributes=True)


class AgentAvailableSchema(BaseModel):
    """Schema for available agent information."""
    agent_type: str = Field(..., description="Agent type identifier")
    display_name: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="Agent description")
    capabilities: List[str] = Field(..., description="List of agent capabilities")
    is_hired: bool = Field(default=False, description="Whether user has hired this agent")
    requires_subscription: bool = Field(default=False, description="Whether agent requires premium subscription")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_type": "market",
                "display_name": "Market Intelligence Agent",
                "description": "Provides comprehensive market analysis and insights",
                "capabilities": [
                    "Market trend analysis",
                    "Regional market comparison",
                    "Forecast generation"
                ],
                "is_hired": True,
                "requires_subscription": False
            }
        }
    )


class StreamEventSchema(BaseModel):
    """Schema for Server-Sent Event streaming."""
    event: str = Field(..., description="Event type (content, plot, done, error)")
    data: Any = Field(..., description="Event data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event": "content",
                "data": {"chunk": "Based on the data..."}
            }
        }
    )
