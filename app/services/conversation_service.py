"""
Conversation management business logic.

This service handles all conversation and message operations including
creation, retrieval, updates, and deletion.
"""

from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import func
from models import Conversation, Message, User, db
from app.schemas.conversation import (
    ConversationCreateSchema,
    ConversationSchema,
    MessageCreateSchema,
    MessageSchema
)
import json
import logging

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for conversation and message operations."""

    @staticmethod
    def create_conversation(
        user_id: int,
        agent_type: str = "market",
        title: Optional[str] = None
    ) -> Tuple[Optional[Conversation], Optional[str]]:
        """
        Create a new conversation.

        Args:
            user_id: ID of the user creating the conversation
            agent_type: Type of agent for this conversation
            title: Optional conversation title

        Returns:
            Tuple of (Conversation object, error message)
        """
        try:
            conversation = Conversation(
                user_id=user_id,
                agent_type=agent_type,
                title=title or f"{agent_type.capitalize()} Chat",
                created_at=datetime.utcnow()
            )

            db.session.add(conversation)
            db.session.commit()

            logger.info(f"Created conversation {conversation.id} for user {user_id}")
            return conversation, None

        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            db.session.rollback()
            return None, "Failed to create conversation"

    @staticmethod
    def get_conversation(
        conversation_id: int,
        user_id: Optional[int] = None
    ) -> Tuple[Optional[Conversation], Optional[str]]:
        """
        Get conversation by ID.

        Args:
            conversation_id: ID of the conversation
            user_id: Optional user ID for authorization check

        Returns:
            Tuple of (Conversation object, error message)
        """
        try:
            if user_id:
                conversation = Conversation.query.filter_by(
                    id=conversation_id,
                    user_id=user_id
                ).first()
            else:
                conversation = Conversation.query.get(conversation_id)

            if not conversation:
                return None, "Conversation not found"

            return conversation, None

        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {e}")
            return None, "Failed to load conversation"

    @staticmethod
    def get_user_conversations(
        user_id: int,
        agent_type: Optional[str] = None,
        limit: int = 50,
        include_message_count: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get user's conversations with optional filtering.

        Args:
            user_id: ID of the user
            agent_type: Optional filter by agent type
            limit: Maximum number of conversations to return
            include_message_count: Whether to include message count

        Returns:
            List of conversation dictionaries with preview of last message
        """
        try:
            query = Conversation.query.filter_by(user_id=user_id)

            if agent_type:
                query = query.filter_by(agent_type=agent_type)

            conversations = query.order_by(
                Conversation.created_at.desc()
            ).limit(limit).all()

            result = []
            for conv in conversations:
                # Get last user message for preview
                last_message = Message.query.filter_by(
                    conversation_id=conv.id,
                    sender='user'
                ).order_by(Message.timestamp.desc()).first()

                # Create preview from last message (first 60 chars)
                preview = None
                if last_message:
                    try:
                        # Try to parse JSON content
                        content = json.loads(last_message.content)
                        if isinstance(content, dict) and 'value' in content:
                            preview = content['value']
                        else:
                            preview = str(content)
                    except:
                        preview = last_message.content

                    # Truncate to 60 characters
                    if preview and len(preview) > 60:
                        preview = preview[:60] + '...'

                # Get message count if requested
                message_count = 0
                if include_message_count:
                    message_count = Message.query.filter_by(
                        conversation_id=conv.id
                    ).count()

                result.append({
                    'id': conv.id,
                    'title': conv.title,
                    'preview': preview or conv.title or f'Conversation {conv.id}',
                    'agent_type': conv.agent_type,
                    'created_at': conv.created_at,
                    'message_count': message_count
                })

            return result

        except Exception as e:
            logger.error(f"Error getting conversations for user {user_id}: {e}")
            return []

    @staticmethod
    def get_or_create_fresh_conversation(
        user_id: int,
        agent_type: str = "market"
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Get an empty conversation or create a new one.

        This is optimized to reuse empty conversations to reduce database bloat.

        Args:
            user_id: ID of the user
            agent_type: Type of agent

        Returns:
            Tuple of (conversation_id, error message)
        """
        try:
            # Find empty conversation with efficient SQL query
            empty_conversation = db.session.query(Conversation).outerjoin(
                Message,
                Conversation.id == Message.conversation_id
            ).filter(
                Conversation.user_id == user_id,
                Message.id.is_(None)  # No messages
            ).first()

            if empty_conversation:
                logger.info(f"Reusing empty conversation {empty_conversation.id}")
                return empty_conversation.id, None

            # Create new conversation if no empty one exists
            conversation = Conversation(
                user_id=user_id,
                agent_type=agent_type,
                title=None,  # Will be set from first message
                created_at=datetime.utcnow()
            )

            db.session.add(conversation)
            db.session.commit()

            logger.info(f"Created fresh conversation {conversation.id} for user {user_id}")
            return conversation.id, None

        except Exception as e:
            logger.error(f"Error getting/creating fresh conversation: {e}")
            db.session.rollback()
            return None, "Failed to create conversation"

    @staticmethod
    def update_conversation_title(
        conversation_id: int,
        user_id: int,
        title: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Update conversation title.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)
            title: New title

        Returns:
            Tuple of (success, error message)
        """
        try:
            conversation = Conversation.query.filter_by(
                id=conversation_id,
                user_id=user_id
            ).first()

            if not conversation:
                return False, "Conversation not found"

            conversation.title = title
            db.session.commit()

            logger.info(f"Updated title for conversation {conversation_id}")
            return True, None

        except Exception as e:
            logger.error(f"Error updating conversation title: {e}")
            db.session.rollback()
            return False, "Failed to update title"

    @staticmethod
    def delete_conversation(
        conversation_id: int,
        user_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete a conversation and all its messages.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)

        Returns:
            Tuple of (success, error message)
        """
        try:
            conversation = Conversation.query.filter_by(
                id=conversation_id,
                user_id=user_id
            ).first()

            if not conversation:
                return False, "Conversation not found"

            # Delete all messages first
            Message.query.filter_by(conversation_id=conversation_id).delete()

            # Delete conversation
            db.session.delete(conversation)
            db.session.commit()

            logger.info(f"Deleted conversation {conversation_id} by user {user_id}")
            return True, None

        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            db.session.rollback()
            return False, "Failed to delete conversation"

    @staticmethod
    def save_message(
        conversation_id: int,
        sender: str,
        content: str,
        user_id: Optional[int] = None
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Save a message to a conversation.

        Args:
            conversation_id: ID of the conversation
            sender: 'user' or 'bot'
            content: Message content (JSON string)
            user_id: Optional user ID for authorization

        Returns:
            Tuple of (Message object, error message)
        """
        try:
            # Verify conversation ownership if user_id provided
            if user_id:
                conversation = Conversation.query.filter_by(
                    id=conversation_id,
                    user_id=user_id
                ).first()

                if not conversation:
                    return None, "Conversation not found"

            message = Message(
                conversation_id=conversation_id,
                sender=sender,
                content=content,
                timestamp=datetime.utcnow()
            )

            db.session.add(message)
            db.session.commit()

            logger.debug(f"Saved message to conversation {conversation_id}")
            return message, None

        except Exception as e:
            logger.error(f"Error saving message: {e}")
            db.session.rollback()
            return None, "Failed to save message"

    @staticmethod
    def get_conversation_messages(
        conversation_id: int,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> Tuple[List[Message], Optional[str]]:
        """
        Get messages for a conversation.

        Args:
            conversation_id: ID of the conversation
            user_id: Optional user ID for authorization
            limit: Maximum number of messages to return

        Returns:
            Tuple of (list of Message objects, error message)
        """
        try:
            # Verify conversation ownership if user_id provided
            if user_id:
                conversation = Conversation.query.filter_by(
                    id=conversation_id,
                    user_id=user_id
                ).first()

                if not conversation:
                    return [], "Conversation not found"

            messages = Message.query.filter_by(
                conversation_id=conversation_id
            ).order_by(
                Message.timestamp.asc()
            ).limit(limit).all()

            return messages, None

        except Exception as e:
            logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
            return [], "Failed to load messages"

    @staticmethod
    def get_messages_for_agent(
        conversation_id: int,
        limit: int = 50
    ) -> List[Dict[str, str]]:
        """
        Get messages formatted for AI agent consumption.

        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages

        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        try:
            messages = Message.query.filter_by(
                conversation_id=conversation_id
            ).order_by(
                Message.timestamp.asc()
            ).limit(limit).all()

            return [
                {
                    'role': 'user' if msg.sender == 'user' else 'assistant',
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ]

        except Exception as e:
            logger.error(f"Error getting messages for agent: {e}")
            return []

    @staticmethod
    def clear_conversation_messages(
        conversation_id: int,
        user_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Clear all messages from a conversation.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)

        Returns:
            Tuple of (success, error message)
        """
        try:
            # Verify conversation ownership
            conversation = Conversation.query.filter_by(
                id=conversation_id,
                user_id=user_id
            ).first()

            if not conversation:
                return False, "Conversation not found"

            # Delete all messages
            deleted_count = Message.query.filter_by(conversation_id=conversation_id).delete()
            db.session.commit()

            logger.info(f"Cleared {deleted_count} messages from conversation {conversation_id}")
            return True, None

        except Exception as e:
            logger.error(f"Error clearing conversation messages: {e}")
            db.session.rollback()
            return False, "Failed to clear messages"

    @staticmethod
    def auto_generate_conversation_title(
        conversation_id: int,
        user_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Auto-generate conversation title from first user message.

        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)

        Returns:
            Tuple of (success, error message)
        """
        try:
            conversation = Conversation.query.filter_by(
                id=conversation_id,
                user_id=user_id
            ).first()

            if not conversation:
                return False, "Conversation not found"

            # Don't override existing title
            if conversation.title:
                return True, None

            # Get first user message
            first_message = Message.query.filter_by(
                conversation_id=conversation_id,
                sender='user'
            ).order_by(Message.timestamp.asc()).first()

            if not first_message:
                return True, None  # No messages yet

            # Generate title from first message
            try:
                content = json.loads(first_message.content)
                if content.get('type') == 'string' and content.get('value'):
                    value = str(content['value'])
                    words = value.split()
                    title = ' '.join(words[:6]) + '...' if len(words) > 6 else value
                    conversation.title = title[:256]  # Limit to 256 chars
                    db.session.commit()
                    logger.info(f"Auto-generated title for conversation {conversation_id}")
            except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
                logger.debug(f"Could not parse message for title: {e}")
                # Fallback to generic title
                conversation.title = f"Conversation {conversation_id}"
                db.session.commit()

            return True, None

        except Exception as e:
            logger.error(f"Error auto-generating title: {e}")
            db.session.rollback()
            return False, "Failed to generate title"

    @staticmethod
    def cleanup_empty_conversations(
        user_id: Optional[int] = None,
        days_old: int = 7
    ) -> Tuple[int, Optional[str]]:
        """
        Clean up empty conversations older than specified days.

        Args:
            user_id: Optional user ID to limit cleanup to specific user
            days_old: Delete empty conversations older than this many days

        Returns:
            Tuple of (number deleted, error message)
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Find empty conversations
            query = db.session.query(Conversation).outerjoin(
                Message,
                Conversation.id == Message.conversation_id
            ).filter(
                Message.id.is_(None),  # No messages
                Conversation.created_at < cutoff_date
            )

            if user_id:
                query = query.filter(Conversation.user_id == user_id)

            deleted_count = query.delete(synchronize_session=False)
            db.session.commit()

            logger.info(f"Cleaned up {deleted_count} empty conversations")
            return deleted_count, None

        except Exception as e:
            logger.error(f"Error cleaning up empty conversations: {e}")
            db.session.rollback()
            return 0, "Failed to cleanup conversations"
