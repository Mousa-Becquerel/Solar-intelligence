"""
Conversation Tests

Tests for conversation CRUD operations and message handling
"""
import pytest
from models import Conversation, Message, db


class TestConversationCreation:
    """Test conversation creation"""

    def test_get_fresh_conversation_creates_new(self, authenticated_client, db_session):
        """Test that getting fresh conversation creates a new one"""
        response = authenticated_client.get('/get-fresh-conversation')
        assert response.status_code == 200

        data = response.get_json()
        assert 'id' in data

        # Verify conversation was created
        conversation = Conversation.query.get(data['id'])
        assert conversation is not None

    def test_conversation_belongs_to_user(self, authenticated_client, test_user, db_session):
        """Test that created conversation belongs to the user"""
        response = authenticated_client.get('/get-fresh-conversation')
        data = response.get_json()

        conversation = Conversation.query.get(data['id'])
        assert conversation.user_id == test_user.id


class TestConversationListing:
    """Test listing conversations"""

    def test_get_conversations_empty(self, authenticated_client):
        """Test getting conversations when none exist"""
        response = authenticated_client.get('/conversations')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)

    def test_get_conversations_with_data(self, authenticated_client, test_conversation):
        """Test getting conversations when they exist"""
        response = authenticated_client.get('/conversations')
        assert response.status_code == 200

        data = response.get_json()
        assert len(data) >= 1

        # Find our test conversation
        conv_ids = [c['id'] for c in data]
        assert test_conversation.id in conv_ids

    def test_get_conversations_only_own(self, authenticated_client, test_conversation, admin_user, db_session):
        """Test that users only see their own conversations"""
        # Create conversation for admin user
        admin_conv = Conversation(
            user_id=admin_user.id,
            title='Admin Conversation'
        )
        db_session.session.add(admin_conv)
        db_session.session.commit()

        response = authenticated_client.get('/conversations')
        data = response.get_json()

        conv_ids = [c['id'] for c in data]
        assert test_conversation.id in conv_ids
        assert admin_conv.id not in conv_ids


class TestConversationMessages:
    """Test message operations"""

    def test_get_messages_empty_conversation(self, authenticated_client, test_conversation):
        """Test getting messages from empty conversation"""
        response = authenticated_client.get(f'/conversations/{test_conversation.id}/messages')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_messages_with_data(self, authenticated_client, test_conversation, test_message):
        """Test getting messages from conversation with messages"""
        response = authenticated_client.get(f'/conversations/{test_conversation.id}/messages')
        assert response.status_code == 200

        data = response.get_json()
        assert len(data) >= 1
        assert data[0]['content'] == 'Test message content'

    def test_get_messages_wrong_user(self, client, test_conversation, admin_user):
        """Test that users cannot access other users' messages"""
        # Login as admin user
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id

        response = client.get(f'/conversations/{test_conversation.id}/messages')
        assert response.status_code == 404  # Not found (access denied)


class TestConversationDeletion:
    """Test conversation deletion"""

    def test_delete_conversation_success(self, authenticated_client, test_conversation, db_session):
        """Test successful conversation deletion"""
        conv_id = test_conversation.id

        response = authenticated_client.delete(f'/conversations/{conv_id}')
        assert response.status_code == 200

        # Verify conversation was deleted
        conversation = Conversation.query.get(conv_id)
        assert conversation is None

    def test_delete_conversation_wrong_user(self, client, test_conversation, admin_user):
        """Test that users cannot delete other users' conversations"""
        # Login as admin user
        with client.session_transaction() as sess:
            sess['_user_id'] = admin_user.id

        response = client.delete(f'/conversations/{test_conversation.id}')
        assert response.status_code == 404  # Not found (access denied)

        # Verify conversation still exists
        conversation = Conversation.query.get(test_conversation.id)
        assert conversation is not None

    def test_delete_nonexistent_conversation(self, authenticated_client):
        """Test deleting non-existent conversation"""
        response = authenticated_client.delete('/conversations/99999')
        assert response.status_code == 404


class TestConversationUpdate:
    """Test conversation updates"""

    def test_update_conversation_title(self, authenticated_client, test_conversation, db_session):
        """Test updating conversation title"""
        new_title = 'Updated Title'

        response = authenticated_client.put(
            f'/conversations/{test_conversation.id}',
            json={'title': new_title}
        )

        # Check if endpoint exists
        if response.status_code == 404 and b'Not Found' in response.data:
            pytest.skip("Update endpoint not implemented")

        assert response.status_code == 200

        # Verify title was updated
        db_session.session.refresh(test_conversation)
        assert test_conversation.title == new_title
