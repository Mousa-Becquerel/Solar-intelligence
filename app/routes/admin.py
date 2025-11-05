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
        # Template expects 'pending_users' variable, not 'users'
        return render_template('admin_pending_users.html', pending_users=pending)

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


# ==================== Agent Access Control Routes ====================

@admin_bp.route('/agent-access')
@login_required
@admin_required
@limiter.limit("100 per hour")
def agent_access():
    """Agent access control management page."""
    try:
        from models import AgentAccess
        from app.services.agent_access_service import AgentAccessService

        # Get all agent configurations
        agents = AgentAccess.query.all()

        return render_template('admin_agent_access.html', agents=agents)

    except Exception as e:
        logger.error(f"Error loading agent access page: {e}")
        flash('Failed to load agent access management', 'error')
        return redirect(url_for('admin.users'))


@admin_bp.route('/agent-access/<string:agent_type>/config', methods=['GET'])
@login_required
@admin_required
@limiter.limit("100 per hour")
def get_agent_config(agent_type):
    """Get agent access configuration."""
    try:
        from models import AgentAccess
        from app.services.agent_access_service import AgentAccessService

        agent_config = AgentAccess.query.filter_by(agent_type=agent_type).first()

        if not agent_config:
            return jsonify({'error': 'Agent not found'}), 404

        # Get whitelisted users
        whitelisted_users = AgentAccessService.get_whitelisted_users(agent_type)

        return jsonify({
            'agent_type': agent_config.agent_type,
            'required_plan': agent_config.required_plan,
            'is_enabled': agent_config.is_enabled,
            'description': agent_config.description,
            'whitelisted_users': whitelisted_users
        })

    except Exception as e:
        logger.error(f"Error getting agent config for {agent_type}: {e}")
        return jsonify({'error': 'Failed to get agent configuration'}), 500


@admin_bp.route('/agent-access/<string:agent_type>/update', methods=['POST'])
@login_required
@admin_required
@limiter.limit("50 per hour")
def update_agent_config(agent_type):
    """Update agent access configuration."""
    try:
        from app.services.agent_access_service import AgentAccessService

        data = request.get_json()

        success, error = AgentAccessService.update_agent_config(
            agent_type=agent_type,
            required_plan=data.get('required_plan'),
            is_enabled=data.get('is_enabled'),
            description=data.get('description')
        )

        if success:
            return jsonify({'success': True, 'message': 'Agent configuration updated successfully'})
        else:
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        logger.error(f"Error updating agent config for {agent_type}: {e}")
        return jsonify({'success': False, 'error': 'Failed to update agent configuration'}), 500


@admin_bp.route('/agent-access/<string:agent_type>/whitelist', methods=['POST'])
@login_required
@admin_required
@limiter.limit("50 per hour")
def add_to_whitelist(agent_type):
    """Add user to agent whitelist."""
    try:
        from app.services.agent_access_service import AgentAccessService
        from datetime import datetime

        data = request.get_json()
        user_id = data.get('user_id')
        reason = data.get('reason')
        expires_at = data.get('expires_at')

        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        # Parse expiration date if provided
        expires_datetime = None
        if expires_at:
            try:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except:
                return jsonify({'error': 'Invalid expiration date format'}), 400

        success, error = AgentAccessService.grant_user_access(
            agent_type=agent_type,
            user_id=user_id,
            granted_by_id=current_user.id,
            expires_at=expires_datetime,
            reason=reason
        )

        if success:
            return jsonify({'success': True, 'message': 'User added to whitelist successfully'})
        else:
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        logger.error(f"Error adding user to whitelist for {agent_type}: {e}")
        return jsonify({'success': False, 'error': 'Failed to add user to whitelist'}), 500


@admin_bp.route('/agent-access/<string:agent_type>/whitelist/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
@limiter.limit("50 per hour")
def remove_from_whitelist(agent_type, user_id):
    """Remove user from agent whitelist."""
    try:
        from app.services.agent_access_service import AgentAccessService

        success, error = AgentAccessService.revoke_user_access(
            agent_type=agent_type,
            user_id=user_id
        )

        if success:
            return jsonify({'success': True, 'message': 'User removed from whitelist successfully'})
        else:
            return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        logger.error(f"Error removing user from whitelist for {agent_type}: {e}")
        return jsonify({'success': False, 'error': 'Failed to remove user from whitelist'}), 500
