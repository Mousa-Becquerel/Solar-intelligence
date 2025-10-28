"""
Admin panel routes blueprint.

This blueprint handles all administrative operations.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService
from app.extensions import limiter
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))

        if not AdminService.verify_admin(current_user):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('chat.agents'))

        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/users')
@login_required
@admin_required
@limiter.limit("100 per hour")
def users():
    """Admin interface for user management."""
    try:
        users = AdminService.get_all_users(include_inactive=True, limit=100)
        return render_template('admin_users.html', users=users)

    except Exception as e:
        logger.error(f"Error loading admin users page: {e}")
        flash('Failed to load users', 'error')
        return redirect(url_for('chat.agents'))


@admin_bp.route('/users/pending')
@login_required
@admin_required
@limiter.limit("100 per hour")
def pending_users():
    """View pending user approvals."""
    try:
        pending = AdminService.get_pending_users()
        return render_template('admin_pending_users.html', users=pending)

    except Exception as e:
        logger.error(f"Error loading pending users: {e}")
        flash('Failed to load pending users', 'error')
        return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
@limiter.limit("50 per hour")
def approve_user(user_id):
    """Approve a pending user account."""
    try:
        success, error = AdminService.approve_user(user_id)

        if success:
            return jsonify({'success': True, 'message': 'User approved successfully'})
        else:
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        logger.error(f"Error approving user {user_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to approve user'}), 500


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
@limiter.limit("10 per hour")
def create_user():
    """Create new user."""
    if request.method == 'GET':
        return render_template('admin_create_user.html')

    try:
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'user')
        plan_type = request.form.get('plan_type', 'free')

        if not all([username, password, full_name]):
            flash('All fields are required', 'error')
            return render_template('admin_create_user.html')

        # Create user
        user, error = AdminService.create_user_by_admin(
            username=username,
            password=password,
            full_name=full_name,
            role=role,
            plan_type=plan_type,
            is_active=True
        )

        if user:
            flash(f'User {username} created successfully', 'success')
            return redirect(url_for('admin.users'))
        else:
            flash(error, 'error')
            return render_template('admin_create_user.html')

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        flash('Failed to create user', 'error')
        return render_template('admin_create_user.html')


@admin_bp.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
@admin_required
@limiter.limit("50 per hour")
def update_user(user_id):
    """Update user information."""
    try:
        data = request.get_json()

        success, error = AdminService.update_user_by_admin(
            user_id=user_id,
            full_name=data.get('full_name'),
            role=data.get('role'),
            plan_type=data.get('plan_type'),
            is_active=data.get('is_active')
        )

        if success:
            return jsonify({'success': True, 'message': 'User updated successfully'})
        else:
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to update user'}), 500


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
@limiter.limit("20 per hour")
def delete_user(user_id):
    """Delete user."""
    try:
        # Prevent self-deletion
        if user_id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400

        success, error = AdminService.delete_user_by_admin(user_id)

        if success:
            return jsonify({'success': True, 'message': 'User deleted successfully'})
        else:
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete user'}), 500


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
@limiter.limit("50 per hour")
def toggle_user(user_id):
    """Toggle user active status."""
    try:
        # Prevent self-toggle
        if user_id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot toggle your own status'}), 400

        success, error, new_status = AdminService.toggle_user_active_status(user_id)

        if success:
            return jsonify({
                'success': True,
                'message': f'User {"activated" if new_status else "deactivated"}',
                'is_active': new_status
            })
        else:
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        logger.error(f"Error toggling user {user_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to toggle user status'}), 500


@admin_bp.route('/stats')
@login_required
@admin_required
@limiter.limit("100 per hour")
def stats():
    """Get system statistics."""
    try:
        statistics = AdminService.get_system_statistics()
        return jsonify(statistics)

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'error': 'Failed to load statistics'}), 500


@admin_bp.route('/activity-report')
@login_required
@admin_required
@limiter.limit("100 per hour")
def activity_report():
    """Get user activity report."""
    try:
        days = int(request.args.get('days', 30))
        report = AdminService.get_user_activity_report(days=days)
        return jsonify(report)

    except Exception as e:
        logger.error(f"Error getting activity report: {e}")
        return jsonify({'error': 'Failed to load activity report'}), 500


@admin_bp.route('/feedback-summary')
@login_required
@admin_required
@limiter.limit("100 per hour")
def feedback_summary():
    """Get feedback summary."""
    try:
        summary = AdminService.get_feedback_summary()
        return jsonify(summary)

    except Exception as e:
        logger.error(f"Error getting feedback summary: {e}")
        return jsonify({'error': 'Failed to load feedback summary'}), 500


@admin_bp.route('/cleanup-empty-conversations', methods=['POST'])
@login_required
@admin_required
@limiter.limit("10 per hour")
def cleanup_empty_conversations():
    """Clean up empty conversations."""
    try:
        days_old = int(request.json.get('days_old', 7))

        count, error = AdminService.cleanup_empty_conversations(days_old=days_old)

        if error:
            return jsonify({'error': error}), 500

        return jsonify({
            'success': True,
            'message': f'Cleaned up {count} empty conversations',
            'count': count
        })

    except Exception as e:
        logger.error(f"Error cleaning up conversations: {e}")
        return jsonify({'error': 'Failed to cleanup conversations'}), 500


@admin_bp.route('/users/<int:user_id>/reset-queries', methods=['POST'])
@login_required
@admin_required
@limiter.limit("50 per hour")
def reset_user_queries(user_id):
    """Reset user's monthly query count."""
    try:
        success, error = AdminService.reset_user_query_count(user_id)

        if success:
            return jsonify({'success': True, 'message': 'Query count reset successfully'})
        else:
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        logger.error(f"Error resetting queries for user {user_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to reset query count'}), 500
