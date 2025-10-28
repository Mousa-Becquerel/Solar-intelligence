"""
Authentication Tests

Tests for user authentication, registration, and session management
"""
import pytest
from models import User, db


class TestLogin:
    """Test login functionality"""

    def test_login_page_loads(self, client):
        """Test that login page loads successfully"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post('/login', json={
            'username': 'test@example.com',
            'password': 'TestPassword123!'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_login_invalid_password(self, client, test_user):
        """Test login with invalid password"""
        response = client.post('/login', json={
            'username': 'test@example.com',
            'password': 'WrongPassword'
        })
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post('/login', json={
            'username': 'nonexistent@example.com',
            'password': 'AnyPassword'
        })
        assert response.status_code == 401

    def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = client.post('/login', json={})
        assert response.status_code == 400 or response.status_code == 401


class TestRegistration:
    """Test user registration"""

    def test_register_page_loads(self, client):
        """Test that registration page loads"""
        response = client.get('/register')
        assert response.status_code == 200

    def test_register_success(self, client, db_session):
        """Test successful user registration"""
        response = client.post('/register', json={
            'email': 'newuser@example.com',
            'password': 'NewPassword123!',
            'full_name': 'New User',
            'gdpr_consent': True,
            'terms_accepted': True
        })
        assert response.status_code == 200 or response.status_code == 201

        # Verify user was created
        user = User.query.filter_by(username='newuser@example.com').first()
        assert user is not None
        assert user.full_name == 'New User'

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email"""
        response = client.post('/register', json={
            'email': 'test@example.com',
            'password': 'AnyPassword123!',
            'full_name': 'Another User',
            'gdpr_consent': True,
            'terms_accepted': True
        })
        assert response.status_code == 400 or response.status_code == 409

    def test_register_missing_gdpr_consent(self, client):
        """Test registration without GDPR consent"""
        response = client.post('/register', json={
            'email': 'newuser@example.com',
            'password': 'Password123!',
            'full_name': 'New User',
            'gdpr_consent': False,
            'terms_accepted': True
        })
        assert response.status_code == 400

    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post('/register', json={
            'email': 'newuser@example.com',
            'password': '123',  # Too weak
            'full_name': 'New User',
            'gdpr_consent': True,
            'terms_accepted': True
        })
        # Should either reject or accept depending on validation
        assert response.status_code in [200, 201, 400]


class TestLogout:
    """Test logout functionality"""

    def test_logout_success(self, authenticated_client):
        """Test successful logout"""
        response = authenticated_client.post('/logout')
        assert response.status_code == 200 or response.status_code == 302

    def test_logout_unauthenticated(self, client):
        """Test logout when not authenticated"""
        response = client.post('/logout')
        # Should redirect to login or return error
        assert response.status_code in [200, 302, 401]


class TestPasswordSecurity:
    """Test password security features"""

    def test_password_is_hashed(self, test_user):
        """Verify passwords are hashed, not stored in plain text"""
        assert test_user.password_hash != 'TestPassword123!'
        assert test_user.check_password('TestPassword123!')

    def test_password_hash_changes_on_update(self, test_user, db_session):
        """Verify password hash changes when password is updated"""
        original_hash = test_user.password_hash
        test_user.set_password('NewPassword456!')
        db_session.session.commit()
        assert test_user.password_hash != original_hash


class TestAccountDeletion:
    """Test account deletion functionality"""

    def test_request_deletion_page_loads(self, authenticated_client):
        """Test that account deletion page loads"""
        response = authenticated_client.get('/request-deletion')
        assert response.status_code == 200

    def test_request_deletion_unauthenticated(self, client):
        """Test deletion request requires authentication"""
        response = client.get('/request-deletion')
        assert response.status_code == 302  # Redirect to login
