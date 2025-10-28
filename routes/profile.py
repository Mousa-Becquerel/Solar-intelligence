"""
Profile routes for user account management
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
from models import db, User, Conversation, Message
import json

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile')
@login_required
def profile():
    """Display user profile page"""
    # Get usage statistics
    usage_stats = current_user.get_usage_stats()

    # Calculate plan details
    plan_info = {
        'type': current_user.plan_type,
        'status': 'Active' if current_user.is_active else 'Inactive',
        'start_date': current_user.plan_start_date,
        'end_date': current_user.plan_end_date,
    }

    # Recent activity
    recent_conversations = Conversation.query.filter_by(
        user_id=current_user.id
    ).order_by(Conversation.created_at.desc()).limit(5).all()

    return render_template(
        'profile.html',
        user=current_user,
        usage_stats=usage_stats,
        plan_info=plan_info,
        recent_conversations=recent_conversations
    )


@profile_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        # Validation
        if not all([current_password, new_password, confirm_password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400

        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'New passwords do not match'}), 400

        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters long'}), 400

        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401

        # Update password
        current_user.set_password(new_password)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Password changed successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error changing password: {str(e)}'}), 500


@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        data = request.get_json()
        full_name = data.get('full_name')

        # Validation
        if not full_name or len(full_name.strip()) == 0:
            return jsonify({'success': False, 'message': 'Full name is required'}), 400

        # Update profile
        current_user.full_name = full_name.strip()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Profile updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating profile: {str(e)}'}), 500


@profile_bp.route('/profile/export-data')
@login_required
def export_data():
    """Export user data (GDPR compliance)"""
    try:
        # Gather all user data
        conversations = Conversation.query.filter_by(user_id=current_user.id).all()

        user_data = {
            'user_info': {
                'username': current_user.username,
                'full_name': current_user.full_name,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
                'plan_type': current_user.plan_type,
                'query_count': current_user.query_count,
            },
            'conversations': []
        }

        for conv in conversations:
            messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.timestamp).all()
            user_data['conversations'].append({
                'title': conv.title,
                'created_at': conv.created_at.isoformat() if conv.created_at else None,
                'agent_type': conv.agent_type,
                'messages': [{
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None
                } for msg in messages]
            })

        return jsonify({'success': True, 'data': user_data}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error exporting data: {str(e)}'}), 500


@profile_bp.route('/profile/usage-stats')
@login_required
def get_usage_stats():
    """Get real-time usage statistics (for AJAX updates)"""
    try:
        usage_stats = current_user.get_usage_stats()
        return jsonify({'success': True, 'stats': usage_stats}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching stats: {str(e)}'}), 500


@profile_bp.route('/profile/upgrade-plan', methods=['POST'])
@login_required
def upgrade_plan():
    """Upgrade user plan (placeholder for payment integration)"""
    try:
        data = request.get_json()
        plan_type = data.get('plan_type', 'premium')

        if plan_type not in ['free', 'premium']:
            return jsonify({'success': False, 'message': 'Invalid plan type'}), 400

        # TODO: Integrate with payment processor (Stripe, PayPal, etc.)
        # For now, this is a placeholder

        current_user.plan_type = plan_type
        current_user.plan_start_date = datetime.utcnow()

        # Set plan end date (1 month from now for premium)
        if plan_type == 'premium':
            from datetime import timedelta
            current_user.plan_end_date = datetime.utcnow() + timedelta(days=30)
        else:
            current_user.plan_end_date = None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Plan upgraded to {plan_type} successfully',
            'plan_type': plan_type
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error upgrading plan: {str(e)}'}), 500
