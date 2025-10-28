"""
Pytest configuration and fixtures for Solar Intelligence tests
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app, db
from models import User, Conversation, Message, HiredAgent


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['SERVER_NAME'] = 'localhost.localdomain'

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing"""
    with app.app_context():
        # Clean up before test
        db.session.remove()
        db.drop_all()
        db.create_all()

        yield db

        # Clean up after test
        db.session.rollback()
        db.session.remove()


@pytest.fixture(scope='function')
def test_user(db_session):
    """Create a test user"""
    user = User(
        username='test@example.com',
        full_name='Test User',
        role='user',
        gdpr_consent_given=True,
        terms_accepted=True
    )
    user.set_password('TestPassword123!')
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture(scope='function')
def admin_user(db_session):
    """Create an admin user"""
    user = User(
        username='admin@example.com',
        full_name='Admin User',
        role='admin',
        gdpr_consent_given=True,
        terms_accepted=True
    )
    user.set_password('AdminPassword123!')
    db_session.session.add(user)
    db_session.session.commit()
    return user


@pytest.fixture(scope='function')
def authenticated_client(client, test_user):
    """Create authenticated test client"""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
    return client


@pytest.fixture(scope='function')
def test_conversation(db_session, test_user):
    """Create a test conversation"""
    conversation = Conversation(
        user_id=test_user.id,
        title='Test Conversation',
        agent_type='market'
    )
    db_session.session.add(conversation)
    db_session.session.commit()
    return conversation


@pytest.fixture(scope='function')
def test_message(db_session, test_conversation):
    """Create a test message"""
    message = Message(
        conversation_id=test_conversation.id,
        sender='user',
        content='Test message content'
    )
    db_session.session.add(message)
    db_session.session.commit()
    return message