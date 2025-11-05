"""
Authentication and authorization business logic.

This service handles all authentication-related operations including
registration, login, logout, and user management.
"""

from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db
from app.schemas.user import (
    UserCreateSchema,
    UserLoginSchema,
    UserSchema,
    UserGDPRConsentSchema
)
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and authorization operations."""

    @staticmethod
    def register_user(
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        job_title: str,
        company_name: str,
        country: str,
        company_size: str,
        terms_agreement: bool,
        communications: bool = False
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user account.

        Args:
            first_name: User's first name
            last_name: User's last name
            email: User's email (used as username)
            password: User's password (will be hashed)
            job_title: User's job title
            company_name: User's company name
            country: User's country
            company_size: Company size category
            terms_agreement: Agreement to terms (required)
            communications: Opt-in for marketing communications (optional)

        Returns:
            Tuple of (User object, error message)
            - (User, None) on success
            - (None, error_message) on failure
        """
        try:
            # Validate required fields
            if not all([first_name, last_name, email, password, job_title,
                       company_name, country, company_size]):
                return None, "All fields are required"

            # Validate terms agreement
            if not terms_agreement:
                return None, "You must agree to the terms of service and privacy policy"

            # Check if user already exists
            existing_user = User.query.filter_by(username=email).first()
            if existing_user:
                return None, "An account with this email already exists"

            # Check if email is in waitlist (auto-approve if found)
            from models import Waitlist
            waitlist_entry = Waitlist.query.filter_by(email=email).first()
            is_active_status = True if waitlist_entry else False

            # Create new user
            consent_timestamp = datetime.utcnow()
            new_user = User(
                username=email,  # Use email as username
                full_name=f"{first_name} {last_name}",
                role='user',
                is_active=is_active_status,  # Auto-approve if in waitlist

                # GDPR Consent Tracking
                gdpr_consent_given=True,  # Required for account creation
                gdpr_consent_date=consent_timestamp,
                terms_accepted=True,  # Required for account creation
                terms_accepted_date=consent_timestamp,
                marketing_consent=bool(communications),  # Optional
                marketing_consent_date=consent_timestamp if communications else None,
                privacy_policy_version='1.0',
                terms_version='1.0'
            )
            new_user.set_password(password)

            # Add to database
            db.session.add(new_user)
            db.session.commit()

            logger.info(f"User registered successfully: {email}")
            return new_user, None

        except Exception as e:
            logger.error(f"Registration error: {e}")
            db.session.rollback()
            return None, "Registration failed. Please try again."

    @staticmethod
    def authenticate_user(
        username: str,
        password: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate a user with username and password.

        Args:
            username: User's username (email)
            password: User's password

        Returns:
            Tuple of (User object, error message)
            - (User, None) on success
            - (None, error_message) on failure
        """
        try:
            # Validate inputs
            if not username or not password:
                return None, "Please fill in all fields"

            # Find user
            user = User.query.filter_by(username=username).first()

            if not user:
                return None, "Invalid username or password"

            # Verify user has a password hash
            if not user.password_hash:
                logger.error(f"User {username} has no password hash set")
                return None, "Invalid username or password"

            # Check password
            if not user.check_password(password):
                return None, "Invalid username or password"

            # Check if account is marked for deletion
            if user.deleted:
                if user.deletion_requested_at:
                    days_remaining = 30 - (datetime.utcnow() - user.deletion_requested_at).days
                    if days_remaining > 0:
                        return None, f"Your account is scheduled for deletion. You have {days_remaining} days remaining to cancel. Contact support to restore your account."
                    else:
                        return None, "Your account has been deleted. Contact support if you believe this is an error."
                return None, "Your account has been deleted"

            # Check if account is active
            if not user.is_active:
                return None, "Your account is pending administrator approval. Please wait for an admin to activate your account, or contact support if you've been waiting more than 24 hours."

            logger.info(f"User authenticated successfully: {username}")
            return user, None

        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            # No rollback needed - this is a read-only operation
            # Rollback can interfere with Flask-Login session management
            return None, "An error occurred during authentication. Please try again."

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User's ID

        Returns:
            User object or None
        """
        try:
            return User.query.get(user_id)
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username: User's username

        Returns:
            User object or None
        """
        try:
            return User.query.filter_by(username=username).first()
        except Exception as e:
            logger.error(f"Error fetching user by username {username}: {e}")
            return None

    @staticmethod
    def update_user_password(
        user: User,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Update user's password.

        Args:
            user: User object
            new_password: New password (will be hashed)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not new_password or len(new_password) < 8:
                return False, "Password must be at least 8 characters"

            user.set_password(new_password)
            db.session.commit()

            logger.info(f"Password updated for user {user.id}")
            return True, None

        except Exception as e:
            logger.error(f"Error updating password for user {user.id}: {e}")
            db.session.rollback()
            return False, "Failed to update password"

    @staticmethod
    def update_gdpr_consent(
        user: User,
        gdpr_consent: bool,
        terms_accepted: bool,
        marketing_consent: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Update user's GDPR consent settings.

        Args:
            user: User object
            gdpr_consent: GDPR consent status
            terms_accepted: Terms acceptance status
            marketing_consent: Marketing communications consent

        Returns:
            Tuple of (success, error_message)
        """
        try:
            timestamp = datetime.utcnow()

            user.gdpr_consent_given = gdpr_consent
            if gdpr_consent:
                user.gdpr_consent_date = timestamp

            user.terms_accepted = terms_accepted
            if terms_accepted:
                user.terms_accepted_date = timestamp

            user.marketing_consent = marketing_consent
            if marketing_consent:
                user.marketing_consent_date = timestamp

            db.session.commit()

            logger.info(f"GDPR consent updated for user {user.id}")
            return True, None

        except Exception as e:
            logger.error(f"Error updating GDPR consent for user {user.id}: {e}")
            db.session.rollback()
            return False, "Failed to update consent settings"

    @staticmethod
    def activate_user(user: User) -> Tuple[bool, Optional[str]]:
        """
        Activate a user account (admin function).

        Args:
            user: User object to activate

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user.is_active = True
            db.session.commit()

            logger.info(f"User {user.id} activated")
            return True, None

        except Exception as e:
            logger.error(f"Error activating user {user.id}: {e}")
            db.session.rollback()
            return False, "Failed to activate user"

    @staticmethod
    def deactivate_user(user: User) -> Tuple[bool, Optional[str]]:
        """
        Deactivate a user account (admin function).

        Args:
            user: User object to deactivate

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user.is_active = False
            db.session.commit()

            logger.info(f"User {user.id} deactivated")
            return True, None

        except Exception as e:
            logger.error(f"Error deactivating user {user.id}: {e}")
            db.session.rollback()
            return False, "Failed to deactivate user"

    @staticmethod
    def request_account_deletion(
        user: User,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Request account deletion (30-day grace period).

        Args:
            user: User object
            reason: Optional reason for deletion

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user.deleted = True
            user.deletion_requested_at = datetime.utcnow()
            user.deletion_reason = reason

            db.session.commit()

            logger.info(f"Deletion requested for user {user.id}")
            return True, None

        except Exception as e:
            logger.error(f"Error requesting deletion for user {user.id}: {e}")
            db.session.rollback()
            return False, "Failed to request account deletion"

    @staticmethod
    def cancel_account_deletion(user: User) -> Tuple[bool, Optional[str]]:
        """
        Cancel account deletion request.

        Args:
            user: User object

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user.deleted = False
            user.deletion_requested_at = None
            user.deletion_reason = None

            db.session.commit()

            logger.info(f"Deletion cancelled for user {user.id}")
            return True, None

        except Exception as e:
            logger.error(f"Error cancelling deletion for user {user.id}: {e}")
            db.session.rollback()
            return False, "Failed to cancel account deletion"

    @staticmethod
    def upgrade_to_premium(user: User, duration_days: int = 30) -> Tuple[bool, Optional[str]]:
        """
        Upgrade user to premium plan.

        Args:
            user: User object
            duration_days: Duration of premium subscription in days

        Returns:
            Tuple of (success, error_message)
        """
        try:
            from datetime import timedelta

            user.plan_type = 'premium'
            user.plan_start_date = datetime.utcnow()
            user.plan_end_date = datetime.utcnow() + timedelta(days=duration_days)

            db.session.commit()

            logger.info(f"User {user.id} upgraded to premium for {duration_days} days")
            return True, None

        except Exception as e:
            logger.error(f"Error upgrading user {user.id} to premium: {e}")
            db.session.rollback()
            return False, "Failed to upgrade to premium"

    @staticmethod
    def check_and_reset_monthly_queries(user: User) -> bool:
        """
        Check if monthly query reset is needed and perform reset.

        Args:
            user: User object

        Returns:
            True if reset was performed, False otherwise

        Note:
            This method updates the user object but does NOT commit.
            The caller is responsible for committing the transaction.
        """
        try:
            if user.last_reset_date is None or \
               (datetime.utcnow() - user.last_reset_date).days >= 30:
                user.monthly_query_count = 0
                user.last_reset_date = datetime.utcnow()
                logger.info(f"Monthly query count reset for user {user.id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error checking/resetting queries for user {user.id}: {e}")
            return False
