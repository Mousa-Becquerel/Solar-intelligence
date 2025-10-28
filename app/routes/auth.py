"""
Authentication routes blueprint.

This blueprint handles all authentication-related routes including
login, registration, and logout.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import AuthService
from app.extensions import limiter
import logging

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """
    Login route.

    GET: Display login form
    POST: Process login credentials
    """
    try:
        # Redirect if already authenticated
        if current_user.is_authenticated:
            return redirect(url_for('chat.agents'))
    except Exception as e:
        logger.error(f"Error checking authentication status: {e}")

    if request.method == 'GET':
        return render_template('login.html')

    # Process login
    try:
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')

        # Authenticate using service
        user, error = AuthService.authenticate_user(username, password)

        if user:
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('chat.agents')
            return redirect(next_page)
        else:
            flash(error, 'error')
            return render_template('login.html')

    except Exception as e:
        logger.error(f"Login error: {e}")
        flash('An error occurred during login. Please try again.', 'error')
        return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register():
    """
    Registration route.

    GET: Display registration form
    POST: Process registration
    """
    if request.method == 'GET':
        return render_template('register.html')

    # Process registration
    try:
        # Get form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        job_title = request.form.get('job_title')
        company_name = request.form.get('company_name')
        email = request.form.get('email')
        password = request.form.get('password')
        country = request.form.get('country')
        company_size = request.form.get('company_size')

        # GDPR Consent Fields
        terms_agreement = request.form.get('terms_agreement')
        communications = request.form.get('communications')

        # Validate required fields
        if not all([first_name, last_name, job_title, company_name, email, password, country, company_size]):
            flash('Please fill in all required fields.', 'error')
            return render_template('register.html')

        # Validate GDPR consent
        if not terms_agreement:
            flash('You must agree to the terms of service and privacy policy to create an account.', 'error')
            return render_template('register.html')

        # Register using service
        user, error = AuthService.register_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            job_title=job_title,
            company_name=company_name,
            country=country,
            company_size=company_size,
            terms_agreement=True,
            communications=bool(communications)
        )

        if user:
            flash('Registration successful! Your account is pending approval. An administrator will review and activate your account shortly.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'error')
            return render_template('register.html')

    except Exception as e:
        logger.error(f"Registration error: {e}")
        flash('Registration failed. Please try again.', 'error')
        return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout route."""
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """
    User profile page.

    Shows user information, plan details, usage statistics, and recent conversations.
    """
    try:
        from models import Conversation, Message
        from datetime import datetime, timedelta
        from sqlalchemy import func
        import logging
        logger = logging.getLogger(__name__)

        # Get plan information
        try:
            plan_info = {
                'type': current_user.plan_type,
                'status': 'active' if current_user.plan_end_date and current_user.plan_end_date > datetime.utcnow() else 'active',
                'end_date': current_user.plan_end_date
            }
            logger.info(f"✅ Plan info created: {plan_info}")
        except Exception as e:
            logger.error(f"❌ Error creating plan_info: {e}", exc_info=True)
            raise

        # Get usage statistics
        try:
            query_limit = current_user.get_query_limit()

            # Calculate queries remaining (handle unlimited case)
            if query_limit == float('inf'):
                queries_remaining = 'Unlimited'
                query_limit_display = 'Unlimited'
            else:
                queries_remaining = max(0, query_limit - current_user.monthly_query_count)
                query_limit_display = query_limit

            usage_stats = {
                'monthly_queries': current_user.monthly_query_count,
                'query_limit': query_limit_display,
                'queries_remaining': queries_remaining,
                'total_queries': current_user.query_count,
                'total_conversations': Conversation.query.filter_by(user_id=current_user.id).count(),
                'total_messages': Message.query.join(Conversation).filter(Conversation.user_id == current_user.id).count(),
                'account_age_days': (datetime.utcnow() - current_user.created_at).days if current_user.created_at else 0,
                'last_query_date': Message.query.join(Conversation).filter(
                    Conversation.user_id == current_user.id,
                    Message.sender == 'user'
                ).order_by(Message.timestamp.desc()).first()
            }
            logger.info(f"✅ Usage stats created")

            if usage_stats['last_query_date']:
                usage_stats['last_query_date'] = usage_stats['last_query_date'].timestamp
                logger.info(f"✅ Last query date: {usage_stats['last_query_date']}")
        except Exception as e:
            logger.error(f"❌ Error creating usage_stats: {e}", exc_info=True)
            raise

        # Get recent conversations (last 5)
        try:
            recent_conversations = Conversation.query.filter_by(
                user_id=current_user.id
            ).order_by(Conversation.created_at.desc()).limit(5).all()
            logger.info(f"✅ Recent conversations: {len(recent_conversations)} found")
        except Exception as e:
            logger.error(f"❌ Error getting recent conversations: {e}", exc_info=True)
            raise

        logger.info("✅ Rendering profile template")
        return render_template('profile.html',
                             user=current_user,
                             plan_info=plan_info,
                             usage_stats=usage_stats,
                             recent_conversations=recent_conversations)

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ PROFILE ROUTE ERROR: {e}", exc_info=True)
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500


@auth_bp.route('/current-user')
@login_required
def current_user_info():
    """
    Get current user information (API endpoint).

    Returns:
        JSON with user information
    """
    try:
        return jsonify({
            'id': current_user.id,
            'username': current_user.username,
            'full_name': current_user.full_name,
            'role': current_user.role,
            'plan_type': current_user.plan_type,
            'monthly_query_count': current_user.monthly_query_count,
            'query_limit': current_user.get_query_limit() if current_user.get_query_limit() != float('inf') else 'unlimited',
            'is_admin': current_user.role == 'admin'
        })
    except Exception as e:
        logger.error(f"Error getting current user info: {e}")
        return jsonify({'error': 'Failed to get user information'}), 500


@auth_bp.route('/update-password', methods=['POST'])
@login_required
def update_password():
    """
    Update user password (API endpoint).

    Returns:
        JSON with success status
    """
    try:
        current_password = request.json.get('current_password')
        new_password = request.json.get('new_password')

        if not current_password or not new_password:
            return jsonify({'error': 'Both current and new password are required'}), 400

        # Verify current password
        user, error = AuthService.authenticate_user(current_user.username, current_password)
        if not user:
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Update password
        success, error = AuthService.update_user_password(current_user, new_password)

        if success:
            return jsonify({'success': True, 'message': 'Password updated successfully'})
        else:
            return jsonify({'error': error}), 400

    except Exception as e:
        logger.error(f"Error updating password: {e}")
        return jsonify({'error': 'Failed to update password'}), 500


@auth_bp.route('/request-deletion', methods=['GET', 'POST'])
@login_required
def request_deletion():
    """
    Request account deletion (30-day grace period).

    GET: Display deletion request form
    POST: Process deletion request
    """
    if request.method == 'GET':
        return render_template('request_deletion.html')

    try:
        reason = request.form.get('deletion_reason', '')
        confirm = request.form.get('confirm')

        if not confirm:
            flash('You must confirm account deletion', 'error')
            return render_template('request_deletion.html')

        # Request deletion using service
        success, error = AuthService.request_account_deletion(current_user, reason)

        if success:
            logout_user()
            flash('Account deletion requested. You have 30 days to cancel before permanent deletion.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'error')
            return render_template('request_deletion.html')

    except Exception as e:
        logger.error(f"Error requesting deletion: {e}")
        flash('Failed to request account deletion', 'error')
        return render_template('request_deletion.html')
