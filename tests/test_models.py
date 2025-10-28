"""
Model Tests

Tests for database models and their methods
"""
import pytest
from datetime import datetime, timedelta
from models import User, Conversation, Message, HiredAgent, Feedback


class TestUserModel:
    """Test User model"""

    def test_user_creation(self, db_session):
        """Test creating a user"""
        user = User(
            username='test@example.com',
            full_name='Test User',
            role='user'
        )
        user.set_password('TestPassword123!')

        db_session.session.add(user)
        db_session.session.commit()

        assert user.id is not None
        assert user.username == 'test@example.com'
        assert user.password_hash != 'TestPassword123!'

    def test_password_checking(self, test_user):
        """Test password verification"""
        assert test_user.check_password('TestPassword123!')
        assert not test_user.check_password('WrongPassword')

    def test_query_limit_free_user(self, test_user):
        """Test query limit for free users"""
        # Free user should have base limit of 5
        assert test_user.get_query_limit() == 5

    def test_query_limit_admin(self, admin_user):
        """Test query limit for admin users"""
        # Admin should have unlimited queries
        assert admin_user.get_query_limit() == float('inf')

    def test_query_limit_premium(self, test_user, db_session):
        """Test query limit for premium users"""
        test_user.plan_type = 'premium'
        db_session.session.commit()

        assert test_user.get_query_limit() == 1000

    def test_can_make_query_within_limit(self, test_user):
        """Test that user can make query within limit"""
        assert test_user.can_make_query()

    def test_can_make_query_at_limit(self, test_user, db_session):
        """Test that user cannot make query at limit"""
        test_user.monthly_query_count = 5  # At limit
        db_session.session.commit()

        assert not test_user.can_make_query()

    def test_increment_query_count(self, test_user, db_session):
        """Test incrementing query count"""
        initial_count = test_user.monthly_query_count
        test_user.increment_query_count()
        db_session.session.commit()

        assert test_user.monthly_query_count == initial_count + 1
        assert test_user.last_query_date is not None

    def test_monthly_reset(self, test_user, db_session):
        """Test monthly query count reset"""
        # Set last reset to 31 days ago
        test_user.last_reset_date = datetime.utcnow() - timedelta(days=31)
        test_user.monthly_query_count = 5
        db_session.session.commit()

        # Check if can make query (should trigger reset)
        test_user.can_make_query()
        db_session.session.commit()

        # Monthly count should be reset
        assert test_user.monthly_query_count == 0


class TestConversationModel:
    """Test Conversation model"""

    def test_conversation_creation(self, test_user, db_session):
        """Test creating a conversation"""
        conversation = Conversation(
            user_id=test_user.id,
            title='Test Conversation',
            agent_type='market'
        )

        db_session.session.add(conversation)
        db_session.session.commit()

        assert conversation.id is not None
        assert conversation.user_id == test_user.id
        assert conversation.created_at is not None

    def test_conversation_relationship(self, test_conversation, test_user):
        """Test conversation-user relationship"""
        assert test_conversation.user == test_user
        assert test_conversation in test_user.conversations.all()


class TestMessageModel:
    """Test Message model"""

    def test_message_creation(self, test_conversation, db_session):
        """Test creating a message"""
        message = Message(
            conversation_id=test_conversation.id,
            sender='user',
            content='Test message'
        )

        db_session.session.add(message)
        db_session.session.commit()

        assert message.id is not None
        assert message.timestamp is not None

    def test_message_relationship(self, test_message, test_conversation):
        """Test message-conversation relationship"""
        assert test_message.conversation == test_conversation
        assert test_message in test_conversation.messages.all()


class TestHiredAgentModel:
    """Test HiredAgent model"""

    def test_hire_agent(self, test_user, db_session):
        """Test hiring an agent"""
        hired = HiredAgent(
            user_id=test_user.id,
            agent_type='market'
        )

        db_session.session.add(hired)
        db_session.session.commit()

        assert hired.id is not None
        assert hired.is_active is True

    def test_unique_constraint(self, test_user, db_session):
        """Test that user cannot hire same agent twice"""
        # First hire
        hired1 = HiredAgent(user_id=test_user.id, agent_type='market')
        db_session.session.add(hired1)
        db_session.session.commit()

        # Second hire (should fail)
        hired2 = HiredAgent(user_id=test_user.id, agent_type='market')
        db_session.session.add(hired2)

        with pytest.raises(Exception):  # Should raise integrity error
            db_session.session.commit()

        db_session.session.rollback()


class TestFeedbackModel:
    """Test Feedback model"""

    def test_feedback_creation(self, test_user, db_session):
        """Test creating feedback"""
        feedback = Feedback(
            user_id=test_user.id,
            rating=5,
            feedback_text='Great app!',
            allow_followup=True
        )

        db_session.session.add(feedback)
        db_session.session.commit()

        assert feedback.id is not None
        assert feedback.created_at is not None

    def test_feedback_relationship(self, test_user, db_session):
        """Test feedback-user relationship"""
        feedback = Feedback(
            user_id=test_user.id,
            rating=4,
            feedback_text='Good'
        )

        db_session.session.add(feedback)
        db_session.session.commit()

        assert feedback.user == test_user
        assert feedback in test_user.feedbacks.all()
