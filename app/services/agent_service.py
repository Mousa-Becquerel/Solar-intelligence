"""
AI Agent coordination business logic.

This service handles all AI agent interactions including query routing,
response streaming, and agent management.
"""

from typing import Optional, AsyncGenerator, Tuple, Dict, Any, List
from datetime import datetime
from models import User, Conversation, Message, HiredAgent, db
from app.schemas.agent import AgentQuerySchema, AgentResponseSchema
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class AgentService:
    """Service for coordinating AI agent operations."""

    # Agent type constants
    AGENT_TYPES = {
        'market': 'Market Intelligence Agent',
        'price': 'Module Prices Agent',
        'news': 'News Agent',
        'digitalization': 'Digitalization Trends Agent',
        'leo_om': 'O&M Agent',
        'weaviate': 'Database Query Agent'
    }

    @staticmethod
    def validate_query(
        user: User,
        conversation_id: int,
        query: str,
        agent_type: str = 'market'
    ) -> Tuple[bool, Optional[str], Optional[Conversation]]:
        """
        Validate a user query before processing.

        Args:
            user: User making the query
            conversation_id: ID of the conversation
            query: Query text
            agent_type: Type of agent to use

        Returns:
            Tuple of (is_valid, error_message, conversation)
        """
        try:
            # Validate query length
            MAX_MESSAGE_LENGTH = 5000
            if len(query) > MAX_MESSAGE_LENGTH:
                return False, f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters.", None

            # Get and validate conversation
            conversation = db.session.get(Conversation, conversation_id)
            if not conversation or conversation.user_id != user.id:
                return False, "Conversation not found or access denied", None

            # Update conversation agent type if changed
            if conversation.agent_type != agent_type:
                conversation.agent_type = agent_type
                db.session.commit()

            # Check query limits
            if not user.can_make_query():
                queries_used = user.monthly_query_count
                query_limit = user.get_query_limit()
                error_msg = f"Query limit reached. You have used {queries_used}/{query_limit} queries this month."
                return False, error_msg, None

            return True, None, conversation

        except Exception as e:
            logger.error(f"Error validating query: {e}")
            db.session.rollback()
            return False, "Failed to validate query", None

    @staticmethod
    def increment_query_count(user: User) -> Tuple[bool, Optional[str]]:
        """
        Increment user's query count.

        This is called BEFORE processing to ensure billing accuracy.

        Args:
            user: User object

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user.increment_query_count()
            db.session.commit()
            logger.info(f"Query count incremented for user {user.id}: {user.monthly_query_count}/{user.get_query_limit()}")
            return True, None

        except Exception as e:
            logger.error(f"Error incrementing query count: {e}")
            db.session.rollback()
            return False, "Failed to track query usage"

    @staticmethod
    def save_user_message(
        conversation_id: int,
        message: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Save user message to database.

        Args:
            conversation_id: ID of the conversation
            message: User's message text

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user_msg = Message(
                conversation_id=conversation_id,
                sender='user',
                content=json.dumps({
                    "type": "string",
                    "value": message,
                    "comment": None
                })
            )
            db.session.add(user_msg)
            db.session.commit()
            return True, None

        except Exception as e:
            logger.error(f"Error saving user message: {e}")
            db.session.rollback()
            return False, "Failed to save message"

    @staticmethod
    def save_bot_response(
        conversation_id: int,
        response: str,
        response_type: str = "string",
        plot_data: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Save bot response to database.

        Args:
            conversation_id: ID of the conversation
            response: Bot's response text
            response_type: Type of response (string, plot, data)
            plot_data: Optional plot data

        Returns:
            Tuple of (success, error_message)
        """
        try:
            content = {
                "type": response_type,
                "value": response,
                "comment": None
            }

            if plot_data:
                content["plot_data"] = plot_data

            bot_msg = Message(
                conversation_id=conversation_id,
                sender='bot',
                content=json.dumps(content)
            )
            db.session.add(bot_msg)
            db.session.commit()
            return True, None

        except Exception as e:
            logger.error(f"Error saving bot response: {e}")
            db.session.rollback()
            return False, "Failed to save response"

    @staticmethod
    def determine_agent_type(query: str) -> str:
        """
        Automatically determine which agent should handle a query.

        Args:
            query: User's query text

        Returns:
            Agent type string
        """
        query_lower = query.lower()

        # Keywords for each agent type
        keywords = {
            'price': ['price', 'cost', 'module', 'wafer', 'polysilicon', 'cell', 'pv glass', 'usd', 'yuan', 'rmb'],
            'news': ['news', 'article', 'report', 'latest', 'update', 'announcement', 'press release'],
            'digitalization': ['digital', 'automation', 'ai', 'machine learning', 'iot', 'smart', 'technology'],
            'leo_om': ['operation', 'maintenance', 'o&m', 'om', 'monitoring', 'performance', 'efficiency']
        }

        # Check for keyword matches
        for agent_type, words in keywords.items():
            if any(word in query_lower for word in words):
                return agent_type

        # Default to market intelligence
        return 'market'

    @staticmethod
    def get_available_agents(user: User) -> List[Dict[str, Any]]:
        """
        Get list of available agents for a user.

        Args:
            user: User object

        Returns:
            List of agent information dictionaries
        """
        try:
            # Get hired agents for user
            hired_agents = HiredAgent.query.filter_by(
                user_id=user.id,
                is_active=True
            ).all()

            hired_types = {agent.agent_type for agent in hired_agents}

            agents = []
            for agent_type, display_name in AgentService.AGENT_TYPES.items():
                agents.append({
                    'agent_type': agent_type,
                    'display_name': display_name,
                    'is_hired': agent_type in hired_types,
                    'requires_subscription': agent_type in ['weaviate'],  # Premium only agents
                    'capabilities': AgentService._get_agent_capabilities(agent_type)
                })

            return agents

        except Exception as e:
            logger.error(f"Error getting available agents: {e}")
            return []

    @staticmethod
    def _get_agent_capabilities(agent_type: str) -> List[str]:
        """Get capabilities for an agent type."""
        capabilities = {
            'market': [
                'Market trend analysis',
                'Regional comparisons',
                'Forecast generation',
                'Supply chain insights'
            ],
            'price': [
                'Module price tracking',
                'Historical price data',
                'Price forecasting',
                'Regional price comparison'
            ],
            'news': [
                'Latest industry news',
                'Company announcements',
                'Policy updates',
                'Market reports'
            ],
            'digitalization': [
                'Digital transformation insights',
                'Automation trends',
                'AI/ML applications',
                'Smart grid technology'
            ],
            'leo_om': [
                'O&M best practices',
                'Performance optimization',
                'Maintenance scheduling',
                'Asset monitoring'
            ],
            'weaviate': [
                'Custom database queries',
                'Advanced data retrieval',
                'Complex analytics',
                'Data exploration'
            ]
        }
        return capabilities.get(agent_type, [])

    @staticmethod
    def hire_agent(user: User, agent_type: str) -> Tuple[bool, Optional[str]]:
        """
        Hire an agent for a user.

        Args:
            user: User object
            agent_type: Type of agent to hire

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Validate agent type
            if agent_type not in AgentService.AGENT_TYPES:
                return False, f"Invalid agent type: {agent_type}"

            # Check if already hired
            existing = HiredAgent.query.filter_by(
                user_id=user.id,
                agent_type=agent_type,
                is_active=True
            ).first()

            if existing:
                return False, "Agent already hired"

            # Create hired agent record
            hired = HiredAgent(
                user_id=user.id,
                agent_type=agent_type,
                hired_at=datetime.utcnow(),
                is_active=True
            )

            db.session.add(hired)
            db.session.commit()

            logger.info(f"User {user.id} hired {agent_type} agent")
            return True, None

        except Exception as e:
            logger.error(f"Error hiring agent: {e}")
            db.session.rollback()
            return False, "Failed to hire agent"

    @staticmethod
    def release_agent(user: User, agent_type: str) -> Tuple[bool, Optional[str]]:
        """
        Release (deactivate) an agent for a user.

        Args:
            user: User object
            agent_type: Type of agent to release

        Returns:
            Tuple of (success, error_message)
        """
        try:
            hired = HiredAgent.query.filter_by(
                user_id=user.id,
                agent_type=agent_type,
                is_active=True
            ).first()

            if not hired:
                return False, "Agent not hired"

            hired.is_active = False
            db.session.commit()

            logger.info(f"User {user.id} released {agent_type} agent")
            return True, None

        except Exception as e:
            logger.error(f"Error releasing agent: {e}")
            db.session.rollback()
            return False, "Failed to release agent"

    @staticmethod
    def get_user_hired_agents(user: User) -> List[HiredAgent]:
        """
        Get all hired agents for a user.

        Args:
            user: User object

        Returns:
            List of HiredAgent objects
        """
        try:
            return HiredAgent.query.filter_by(
                user_id=user.id,
                is_active=True
            ).all()

        except Exception as e:
            logger.error(f"Error getting hired agents: {e}")
            return []

    @staticmethod
    def format_conversation_history_for_agent(
        conversation_id: int,
        limit: int = 50
    ) -> List[Dict[str, str]]:
        """
        Format conversation history for agent consumption.

        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to include

        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        try:
            messages = Message.query.filter_by(
                conversation_id=conversation_id
            ).order_by(
                Message.timestamp.asc()
            ).limit(limit).all()

            formatted = []
            for msg in messages:
                try:
                    content = json.loads(msg.content)
                    if content.get('type') == 'string':
                        formatted.append({
                            'role': 'user' if msg.sender == 'user' else 'assistant',
                            'content': content.get('value', '')
                        })
                except (json.JSONDecodeError, KeyError):
                    continue

            return formatted

        except Exception as e:
            logger.error(f"Error formatting conversation history: {e}")
            return []

    @staticmethod
    def check_agent_availability(agent_type: str, user: User) -> Tuple[bool, Optional[str]]:
        """
        Check if an agent is available for a user.

        Args:
            agent_type: Type of agent
            user: User object

        Returns:
            Tuple of (is_available, reason_if_not)
        """
        try:
            # Check if agent type is valid
            if agent_type not in AgentService.AGENT_TYPES:
                return False, f"Invalid agent type: {agent_type}"

            # Check if agent requires premium subscription
            if agent_type == 'weaviate':
                if user.plan_type != 'premium' and user.role != 'admin':
                    return False, "This agent requires a premium subscription"

            # All checks passed
            return True, None

        except Exception as e:
            logger.error(f"Error checking agent availability: {e}")
            return False, "Failed to check availability"

    @staticmethod
    def get_agent_usage_stats(user: User) -> Dict[str, Any]:
        """
        Get usage statistics for agents.

        Args:
            user: User object

        Returns:
            Dictionary of usage statistics
        """
        try:
            # Count queries by agent type
            from sqlalchemy import func

            query_counts = db.session.query(
                Conversation.agent_type,
                func.count(Message.id).label('message_count')
            ).join(
                Message,
                Conversation.id == Message.conversation_id
            ).filter(
                Conversation.user_id == user.id,
                Message.sender == 'user'
            ).group_by(
                Conversation.agent_type
            ).all()

            stats = {
                'total_queries': user.query_count,
                'monthly_queries': user.monthly_query_count,
                'query_limit': user.get_query_limit(),
                'queries_remaining': user.get_query_limit() - user.monthly_query_count,
                'by_agent_type': {
                    agent_type: count
                    for agent_type, count in query_counts
                }
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting agent usage stats: {e}")
            return {
                'total_queries': 0,
                'monthly_queries': 0,
                'query_limit': 0,
                'queries_remaining': 0,
                'by_agent_type': {}
            }
