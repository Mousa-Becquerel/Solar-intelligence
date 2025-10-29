"""
Admin operations business logic.

This service handles all administrative operations including user management,
system maintenance, and monitoring.
"""

from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, exc
from models import User, Conversation, Message, Feedback, HiredAgent, db
import logging

logger = logging.getLogger(__name__)


class AdminService:
    """Service for administrative operations."""

    @staticmethod
    def verify_admin(user: User) -> bool:
        """
        Verify that a user has admin privileges.

        Args:
            user: User object to check

        Returns:
            True if user is admin, False otherwise
        """
        return user.role == 'admin'

    @staticmethod
    def get_all_users(
        include_inactive: bool = True,
        limit: Optional[int] = None
    ) -> List[User]:
        """
        Get all users in the system.

        Args:
            include_inactive: Whether to include inactive users
            limit: Optional limit on number of users

        Returns:
            List of User objects
        """
        try:
            query = User.query

            if not include_inactive:
                query = query.filter_by(is_active=True)

            query = query.order_by(User.created_at.desc())

            if limit:
                query = query.limit(limit)

            return query.all()

        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    @staticmethod
    def get_pending_users() -> List[User]:
        """
        Get all users pending approval.

        Returns:
            List of User objects with is_active=False and not deleted
        """
        try:
            from sqlalchemy import or_

            # DEBUG: Get all users to see database state
            all_users = User.query.all()
            logger.info(f"🔍 DEBUG - Total users in database: {len(all_users)}")
            for user in all_users:
                logger.info(f"  - ID {user.id}: {user.full_name} | is_active={user.is_active} | deleted={user.deleted}")

            # Get pending users (inactive AND not deleted)
            pending = User.query.filter(
                User.is_active == False,
                or_(User.deleted == False, User.deleted == None)
            ).order_by(User.created_at.asc()).all()

            logger.info(f"🔍 PENDING USERS QUERY: Found {len(pending)} pending users")
            for user in pending:
                logger.info(f"  ✅ PENDING: ID {user.id}: {user.full_name} ({user.username}) - is_active={user.is_active}, deleted={user.deleted}")

            return pending

        except Exception as e:
            logger.error(f"Error getting pending users: {e}")
            return []

    @staticmethod
    def approve_user(user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Approve a pending user account.

        Args:
            user_id: ID of the user to approve

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user = User.query.get(user_id)

            if not user:
                return False, "User not found"

            if user.is_active:
                return False, "User is already active"

            user.is_active = True
            db.session.commit()

            logger.info(f"User {user_id} ({user.username}) approved")
            return True, None

        except Exception as e:
            logger.error(f"Error approving user {user_id}: {e}")
            db.session.rollback()
            return False, "Failed to approve user"

    @staticmethod
    def create_user_by_admin(
        username: str,
        password: str,
        full_name: str,
        role: str = 'user',
        plan_type: str = 'free',
        is_active: bool = True
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Create a new user (admin function).

        Args:
            username: User's username (email)
            password: User's password
            full_name: User's full name
            role: User role (user, admin)
            plan_type: Plan type (free, premium)
            is_active: Whether user is active immediately

        Returns:
            Tuple of (User object, error_message)
        """
        try:
            # Check if user already exists
            existing = User.query.filter_by(username=username).first()
            if existing:
                return None, "User with this username already exists"

            # Create user
            user = User(
                username=username,
                full_name=full_name,
                role=role,
                plan_type=plan_type,
                is_active=is_active,
                gdpr_consent_given=True,  # Admin created
                terms_accepted=True,
                gdpr_consent_date=datetime.utcnow(),
                terms_accepted_date=datetime.utcnow()
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            logger.info(f"User created by admin: {username}")
            return user, None

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.session.rollback()
            return None, "Failed to create user"

    @staticmethod
    def update_user_by_admin(
        user_id: int,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        plan_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Update user information (admin function).

        Args:
            user_id: ID of the user
            full_name: Optional new full name
            role: Optional new role
            plan_type: Optional new plan type
            is_active: Optional new active status

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user = User.query.get(user_id)

            if not user:
                return False, "User not found"

            # Update fields if provided
            if full_name is not None:
                user.full_name = full_name

            if role is not None:
                if role not in ['user', 'admin']:
                    return False, "Invalid role"
                user.role = role

            if plan_type is not None:
                if plan_type not in ['free', 'premium']:
                    return False, "Invalid plan type"
                user.plan_type = plan_type

            if is_active is not None:
                user.is_active = is_active

            db.session.commit()

            logger.info(f"User {user_id} updated by admin")
            return True, None

        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            db.session.rollback()
            return False, "Failed to update user"

    @staticmethod
    def delete_user_by_admin(user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a user and all associated data (admin function).

        This is a permanent deletion with proper cascade handling.

        Args:
            user_id: ID of the user to delete

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user = User.query.get(user_id)

            if not user:
                return False, "User not found"

            # Get all conversation IDs for bulk delete
            conversation_ids = [c.id for c in user.conversations.all()]

            if conversation_ids:
                # Bulk delete all messages
                Message.query.filter(Message.conversation_id.in_(conversation_ids)).delete(
                    synchronize_session=False
                )

            # Delete all conversations
            Conversation.query.filter_by(user_id=user_id).delete(synchronize_session=False)

            # Delete related records
            Feedback.query.filter_by(user_id=user_id).delete(synchronize_session=False)
            HiredAgent.query.filter_by(user_id=user_id).delete(synchronize_session=False)

            # Delete the user
            db.session.delete(user)

            # Commit all changes in single transaction
            db.session.commit()

            logger.info(f"User {user_id} ({user.username}) deleted by admin")
            return True, None

        except exc.IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error deleting user {user_id}: {e}")
            return False, "Cannot delete user due to database constraints"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            return False, "Failed to delete user"

    @staticmethod
    def toggle_user_active_status(user_id: int) -> Tuple[bool, Optional[str], Optional[bool]]:
        """
        Toggle user's active status.

        Args:
            user_id: ID of the user

        Returns:
            Tuple of (success, error_message, new_status)
        """
        try:
            user = User.query.get(user_id)

            if not user:
                return False, "User not found", None

            # Toggle status
            user.is_active = not user.is_active
            db.session.commit()

            logger.info(f"User {user_id} active status toggled to {user.is_active}")
            return True, None, user.is_active

        except Exception as e:
            logger.error(f"Error toggling user status {user_id}: {e}")
            db.session.rollback()
            return False, "Failed to toggle user status", None

    @staticmethod
    def get_system_statistics() -> Dict[str, Any]:
        """
        Get system-wide statistics.

        Returns:
            Dictionary of system statistics
        """
        try:
            stats = {
                'total_users': User.query.count(),
                'active_users': User.query.filter_by(is_active=True).count(),
                'pending_users': User.query.filter_by(is_active=False).count(),
                'total_conversations': Conversation.query.count(),
                'total_messages': Message.query.count(),
                'total_feedback': Feedback.query.count(),
                'premium_users': User.query.filter_by(plan_type='premium').count(),
                'free_users': User.query.filter_by(plan_type='free').count()
            }

            # Get user registrations in last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            stats['new_users_this_week'] = User.query.filter(User.created_at >= week_ago).count()

            # Get most active users
            most_active = db.session.query(
                User.id,
                User.username,
                User.query_count
            ).order_by(User.query_count.desc()).limit(5).all()

            stats['most_active_users'] = [
                {'id': user_id, 'username': username, 'query_count': count}
                for user_id, username, count in most_active
            ]

            return stats

        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return {}

    @staticmethod
    def cleanup_empty_conversations(days_old: int = 7) -> Tuple[int, Optional[str]]:
        """
        Clean up empty conversations older than specified days.

        Args:
            days_old: Delete conversations older than this many days

        Returns:
            Tuple of (number_deleted, error_message)
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Find empty conversations
            empty_convs = db.session.query(Conversation).outerjoin(
                Message,
                Conversation.id == Message.conversation_id
            ).filter(
                Message.id.is_(None),  # No messages
                Conversation.created_at < cutoff_date
            ).all()

            count = len(empty_convs)

            # Delete them
            for conv in empty_convs:
                db.session.delete(conv)

            db.session.commit()

            logger.info(f"Cleaned up {count} empty conversations")
            return count, None

        except Exception as e:
            logger.error(f"Error cleaning up empty conversations: {e}")
            db.session.rollback()
            return 0, "Failed to cleanup conversations"

    @staticmethod
    def get_user_activity_report(
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get user activity report for specified period.

        Args:
            days: Number of days to include in report

        Returns:
            Dictionary with activity data
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Daily query counts
            daily_queries = db.session.query(
                func.date(Message.timestamp).label('date'),
                func.count(Message.id).label('count')
            ).filter(
                Message.timestamp >= cutoff_date,
                Message.sender == 'user'
            ).group_by(
                func.date(Message.timestamp)
            ).order_by(
                func.date(Message.timestamp).asc()
            ).all()

            # Queries by agent type
            queries_by_agent = db.session.query(
                Conversation.agent_type,
                func.count(Message.id).label('count')
            ).join(
                Message,
                Conversation.id == Message.conversation_id
            ).filter(
                Message.timestamp >= cutoff_date,
                Message.sender == 'user'
            ).group_by(
                Conversation.agent_type
            ).all()

            return {
                'period_days': days,
                'daily_queries': [
                    {'date': str(date), 'count': count}
                    for date, count in daily_queries
                ],
                'queries_by_agent': {
                    agent_type: count
                    for agent_type, count in queries_by_agent
                },
                'total_queries': sum(count for _, count in daily_queries)
            }

        except Exception as e:
            logger.error(f"Error getting activity report: {e}")
            return {'error': str(e)}

    @staticmethod
    def get_feedback_summary() -> Dict[str, Any]:
        """
        Get summary of user feedback.

        Returns:
            Dictionary with feedback statistics
        """
        try:
            total_feedback = Feedback.query.count()

            if total_feedback == 0:
                return {
                    'total_feedback': 0,
                    'average_rating': 0,
                    'rating_distribution': {}
                }

            # Average rating
            avg_rating = db.session.query(
                func.avg(Feedback.rating)
            ).scalar()

            # Rating distribution
            rating_dist = db.session.query(
                Feedback.rating,
                func.count(Feedback.id)
            ).group_by(Feedback.rating).all()

            return {
                'total_feedback': total_feedback,
                'average_rating': round(float(avg_rating), 2),
                'rating_distribution': {
                    rating: count
                    for rating, count in rating_dist
                }
            }

        except Exception as e:
            logger.error(f"Error getting feedback summary: {e}")
            return {'error': str(e)}

    @staticmethod
    def reset_user_query_count(user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Reset user's monthly query count (admin function).

        Args:
            user_id: ID of the user

        Returns:
            Tuple of (success, error_message)
        """
        try:
            user = User.query.get(user_id)

            if not user:
                return False, "User not found"

            user.monthly_query_count = 0
            user.last_reset_date = datetime.utcnow()
            db.session.commit()

            logger.info(f"Query count reset for user {user_id}")
            return True, None

        except Exception as e:
            logger.error(f"Error resetting query count for user {user_id}: {e}")
            db.session.rollback()
            return False, "Failed to reset query count"
