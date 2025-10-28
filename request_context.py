#!/usr/bin/env python3
"""
Request Context for Isolated Per-Request State

This module provides request-scoped context to eliminate race conditions
when multiple users access the same agent instance concurrently.

Each request gets its own isolated context containing:
- conversation_id: Unique conversation identifier
- user_query: Current user's query
- dataframe: Request-specific DataFrame cache
- plot_result: Request-specific plot data cache

Usage:
    from request_context import request_context, RequestContext

    # Create context for this request
    ctx = RequestContext(conversation_id="123", user_query="Show me data")
    request_context.set(ctx)

    # Access anywhere in the request lifecycle
    ctx = request_context.get()
    print(ctx.user_query)
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

# Import MarketPlotDataResult type hint (will be available after pydantic_weaviate_agent imports this)
try:
    from pydantic_weaviate_agent import MarketPlotDataResult
except ImportError:
    # Avoid circular import - use TYPE_CHECKING pattern
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from pydantic_weaviate_agent import MarketPlotDataResult
    else:
        MarketPlotDataResult = None


@dataclass
class RequestContext:
    """
    Isolated context for each request - eliminates shared state race conditions.

    Attributes:
        conversation_id: Unique identifier for this conversation
        user_query: The user's current query/message
        dataframe: Cached DataFrame from data analysis tools
        plot_result: Cached plot data from visualization tools
    """
    conversation_id: str
    user_query: str = ""
    dataframe: Optional[pd.DataFrame] = None
    plot_result: Optional['MarketPlotDataResult'] = None


# Context variable - thread-safe, async-safe storage
request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    'request_context',
    default=None
)


def get_current_context() -> Optional[RequestContext]:
    """
    Get the current request context.

    Returns:
        RequestContext if set, None otherwise
    """
    return request_context.get()


def set_current_context(ctx: RequestContext) -> None:
    """
    Set the current request context.

    Args:
        ctx: RequestContext instance for this request
    """
    request_context.set(ctx)


def clear_current_context() -> None:
    """Clear the current request context (cleanup)."""
    request_context.set(None)


# Convenience functions for backward compatibility
def get_user_query() -> str:
    """Get current user query from context (replaces self.last_user_query)."""
    ctx = request_context.get()
    return ctx.user_query if ctx else ""


def set_user_query(query: str) -> None:
    """Set current user query in context."""
    ctx = request_context.get()
    if ctx:
        ctx.user_query = query


def get_dataframe() -> Optional[pd.DataFrame]:
    """Get current DataFrame from context (replaces self.last_dataframe)."""
    ctx = request_context.get()
    return ctx.dataframe if ctx else None


def set_dataframe(df: Optional[pd.DataFrame]) -> None:
    """Set current DataFrame in context."""
    ctx = request_context.get()
    if ctx:
        ctx.dataframe = df


def get_plot_result() -> Optional['MarketPlotDataResult']:
    """Get current plot result from context (replaces self.last_market_plot_data_result)."""
    ctx = request_context.get()
    return ctx.plot_result if ctx else None


def set_plot_result(result: Optional['MarketPlotDataResult']) -> None:
    """Set current plot result in context."""
    ctx = request_context.get()
    if ctx:
        ctx.plot_result = result
