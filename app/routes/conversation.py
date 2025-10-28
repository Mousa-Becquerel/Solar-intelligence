"""
Conversation management routes blueprint.

This blueprint handles conversation CRUD operations.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.conversation_service import ConversationService
from app.extensions import limiter
import logging

logger = logging.getLogger(__name__)

# Create blueprint
conversation_bp = Blueprint('conversation', __name__, url_prefix='/conversations')


@conversation_bp.route('/', methods=['GET', 'POST'])
@login_required
@limiter.limit("100 per minute")
def handle_conversations():
    """
    Handle conversation operations.

    GET: Get user's conversations with message counts
    POST: Create or reuse an empty conversation

    Query parameters (GET):
        agent_type: Optional filter by agent type
        limit: Maximum number of conversations (default 50)

    Returns:
        JSON: List of conversations (GET) or conversation ID (POST)
    """
    if request.method == 'POST':
        # Same logic as /fresh endpoint
        try:
            from models import Conversation, Message
            from app.extensions import db

            # Use efficient SQL query to find empty conversations
            empty_conversation = db.session.query(Conversation).outerjoin(
                Message, Conversation.id == Message.conversation_id
            ).filter(
                Conversation.user_id == current_user.id,
                Message.id.is_(None)
            ).order_by(Conversation.created_at.desc()).first()

            if empty_conversation:
                logger.info(f"Reusing empty conversation {empty_conversation.id} for user {current_user.id}")
                return jsonify({'id': empty_conversation.id})

            # Create new conversation
            new_conversation = Conversation(user_id=current_user.id)
            db.session.add(new_conversation)
            db.session.commit()

            logger.info(f"Created new conversation {new_conversation.id} for user {current_user.id}")
            return jsonify({'id': new_conversation.id})

        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            db.session.rollback()
            return jsonify({'error': 'Failed to create conversation'}), 500

    # GET request
    try:
        agent_type = request.args.get('agent_type')
        limit = int(request.args.get('limit', 50))

        conversations = ConversationService.get_user_conversations(
            user_id=current_user.id,
            agent_type=agent_type,
            limit=limit,
            include_message_count=True
        )

        return jsonify({
            'conversations': conversations,
            'total': len(conversations)
        })

    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return jsonify({'error': 'Failed to load conversations'}), 500


@conversation_bp.route('/fresh', methods=['GET', 'POST'])
@login_required
@limiter.limit("100 per minute")
def fresh_conversation():
    """
    Get or create a fresh conversation for the user.

    This endpoint finds an empty conversation (no messages) or creates a new one.
    Optimized to avoid N+1 query problem.

    Returns:
        JSON: {'id': conversation_id}
    """
    try:
        from models import Conversation, Message
        from app.extensions import db

        # Use efficient SQL query to find empty conversations
        # This avoids N+1 query problem by using a subquery
        empty_conversation = db.session.query(Conversation).outerjoin(
            Message, Conversation.id == Message.conversation_id
        ).filter(
            Conversation.user_id == current_user.id,
            Message.id.is_(None)  # No messages
        ).order_by(Conversation.created_at.desc()).first()

        if empty_conversation:
            # Found an empty conversation, reuse it
            logger.info(f"Reusing empty conversation {empty_conversation.id} for user {current_user.id}")
            return jsonify({'id': empty_conversation.id})

        # No empty conversation found, create a new one
        new_conversation = Conversation(user_id=current_user.id)
        db.session.add(new_conversation)
        db.session.commit()

        logger.info(f"Created fresh conversation {new_conversation.id} for user {current_user.id}")
        return jsonify({'id': new_conversation.id})

    except Exception as e:
        logger.error(f"Error getting fresh conversation: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create conversation'}), 500


@conversation_bp.route('/<int:conv_id>', methods=['GET'])
@login_required
@limiter.limit("100 per minute")
def get_conversation(conv_id):
    """
    Get conversation with messages.

    Args:
        conv_id: Conversation ID

    Returns:
        JSON: Conversation details with messages
    """
    try:
        # Get conversation
        conversation, error = ConversationService.get_conversation(
            conversation_id=conv_id,
            user_id=current_user.id
        )

        if not conversation:
            return jsonify({'error': error or 'Conversation not found'}), 404

        # Get messages
        messages, error = ConversationService.get_conversation_messages(
            conversation_id=conv_id,
            user_id=current_user.id
        )

        if error:
            return jsonify({'error': error}), 500

        return jsonify({
            'id': conversation.id,
            'title': conversation.title,
            'agent_type': conversation.agent_type,
            'created_at': conversation.created_at.isoformat(),
            'messages': [
                {
                    'id': msg.id,
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        })

    except Exception as e:
        logger.error(f"Error getting conversation {conv_id}: {e}")
        return jsonify({'error': 'Failed to load conversation'}), 500


@conversation_bp.route('/new', methods=['POST'])
@login_required
@limiter.limit("100 per minute")
def new_conversation():
    """
    Create a new conversation.

    Request JSON:
        title: Optional conversation title
        agent_type: Optional agent type (default: 'market')

    Returns:
        JSON: New conversation details
    """
    try:
        data = request.get_json() or {}
        title = data.get('title')
        agent_type = data.get('agent_type', 'market')

        conversation, error = ConversationService.create_conversation(
            user_id=current_user.id,
            agent_type=agent_type,
            title=title
        )

        if not conversation:
            return jsonify({'error': error or 'Failed to create conversation'}), 500

        return jsonify({
            'id': conversation.id,
            'title': conversation.title,
            'agent_type': conversation.agent_type,
            'created_at': conversation.created_at.isoformat()
        })

    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        return jsonify({'error': 'Failed to create conversation'}), 500


@conversation_bp.route('/<int:conv_id>', methods=['DELETE'])
@login_required
@limiter.limit("100 per minute")
def delete_conversation(conv_id):
    """
    Delete a conversation and all its messages.

    Args:
        conv_id: Conversation ID

    Returns:
        JSON: Success status
    """
    try:
        success, error = ConversationService.delete_conversation(
            conversation_id=conv_id,
            user_id=current_user.id
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'Conversation deleted successfully'
            })
        else:
            return jsonify({'error': error or 'Failed to delete conversation'}), 400

    except Exception as e:
        logger.error(f"Error deleting conversation {conv_id}: {e}")
        return jsonify({'error': 'Failed to delete conversation'}), 500


@conversation_bp.route('/<int:conv_id>/title', methods=['PUT'])
@login_required
@limiter.limit("100 per minute")
def update_conversation_title(conv_id):
    """
    Update conversation title.

    Args:
        conv_id: Conversation ID

    Request JSON:
        title: New title

    Returns:
        JSON: Success status
    """
    try:
        data = request.get_json()
        title = data.get('title')

        if not title:
            return jsonify({'error': 'Title is required'}), 400

        success, error = ConversationService.update_conversation_title(
            conversation_id=conv_id,
            user_id=current_user.id,
            title=title
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'Title updated successfully'
            })
        else:
            return jsonify({'error': error or 'Failed to update title'}), 400

    except Exception as e:
        logger.error(f"Error updating title for conversation {conv_id}: {e}")
        return jsonify({'error': 'Failed to update title'}), 500


@conversation_bp.route('/<int:conv_id>/clear', methods=['POST'])
@login_required
@limiter.limit("50 per minute")
def clear_conversation(conv_id):
    """
    Clear all messages from a conversation.

    Args:
        conv_id: Conversation ID

    Returns:
        JSON: Success status
    """
    try:
        success, error = ConversationService.clear_conversation_messages(
            conversation_id=conv_id,
            user_id=current_user.id
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'Conversation cleared successfully'
            })
        else:
            return jsonify({'error': error or 'Failed to clear conversation'}), 400

    except Exception as e:
        logger.error(f"Error clearing conversation {conv_id}: {e}")
        return jsonify({'error': 'Failed to clear conversation'}), 500


@conversation_bp.route('/<int:conv_id>/debug', methods=['GET'])
@login_required
def debug_conversation(conv_id):
    """
    Debug conversation (shows raw message data).

    Args:
        conv_id: Conversation ID

    Returns:
        JSON: Conversation debug information
    """
    try:
        # Verify ownership
        conversation, error = ConversationService.get_conversation(
            conversation_id=conv_id,
            user_id=current_user.id
        )

        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        # Get messages
        messages, error = ConversationService.get_conversation_messages(
            conversation_id=conv_id,
            user_id=current_user.id
        )

        if error:
            return jsonify({'error': error}), 500

        return jsonify({
            'conversation': {
                'id': conversation.id,
                'title': conversation.title,
                'agent_type': conversation.agent_type,
                'user_id': conversation.user_id,
                'created_at': conversation.created_at.isoformat()
            },
            'messages': [
                {
                    'id': msg.id,
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ],
            'message_count': len(messages)
        })

    except Exception as e:
        logger.error(f"Error debugging conversation {conv_id}: {e}")
        return jsonify({'error': 'Failed to debug conversation'}), 500
