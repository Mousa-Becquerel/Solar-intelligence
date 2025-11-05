"""
Static pages routes blueprint.

This blueprint handles all static/informational pages including
landing page, waitlist, privacy policy, terms of service, and contact.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.extensions import limiter, db, csrf
from models import Waitlist  # Import from root models.py
from app.schemas.user import WaitlistSchema
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

# Create blueprint
static_bp = Blueprint('static', __name__)


@static_bp.route('/')
def landing():
    """
    Landing page route.

    Redirects non-authenticated users to waitlist.
    If user is authenticated, redirects to chat interface.
    """
    try:
        if current_user.is_authenticated:
            return redirect(url_for('chat.agents'))

        return redirect(url_for('static.waitlist'))

    except Exception as e:
        logger.error(f"Error loading landing page: {e}")
        return redirect(url_for('static.waitlist'))


@static_bp.route('/landing_page')
def landing_page():
    """
    Marketing landing page with full features showcase.

    Shows the complete landing page with all sections.
    """
    return render_template('landing.html')


@static_bp.route('/login')
def login_redirect():
    """Redirect /login to /auth/login for convenience."""
    return redirect(url_for('auth.login'))


@static_bp.route('/register')
def register_redirect():
    """Redirect /register to /auth/register for convenience."""
    return redirect(url_for('auth.register'))


@static_bp.route('/waitlist', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def waitlist():
    """
    Waitlist signup route.

    GET: Display waitlist signup form
    POST: Process waitlist signup
    """
    if request.method == 'GET':
        return render_template('waitlist.html')

    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            email = data.get('email', '').strip()
            interested_agents = data.get('interested_agents', [])
        else:
            email = request.form.get('email', '').strip()
            interested_agents = []

        if not email:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Email address is required'}), 400
            flash('Email address is required', 'error')
            return render_template('waitlist.html')

        # Validate using Pydantic schema
        try:
            waitlist_data = WaitlistSchema(email=email)
        except ValidationError as e:
            error_messages = '; '.join([err['msg'] for err in e.errors()])
            if request.is_json:
                return jsonify({'success': False, 'error': error_messages}), 400
            flash(f'Validation error: {error_messages}', 'error')
            return render_template('waitlist.html')

        # Check if email already exists
        existing = Waitlist.query.filter_by(email=waitlist_data.email).first()
        if existing:
            if request.is_json:
                return jsonify({'success': False, 'error': 'This email is already on the waitlist'}), 409
            flash('This email is already on the waitlist', 'info')
            return render_template('waitlist.html')

        # Add to waitlist
        import json
        waitlist_entry = Waitlist(
            email=waitlist_data.email,
            interested_agents=json.dumps(interested_agents) if interested_agents else None
        )
        db.session.add(waitlist_entry)
        db.session.commit()

        logger.info(f"New waitlist signup: {waitlist_data.email}")

        if request.is_json:
            return jsonify({'success': True, 'message': 'Thank you! You have been added to the waitlist.'}), 200

        flash('Thank you! You have been added to the waitlist.', 'success')
        return redirect(url_for('static.landing'))

    except Exception as e:
        logger.error(f"Error processing waitlist signup: {e}")
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': 'An error occurred. Please try again.'}), 500
        flash('An error occurred. Please try again.', 'error')
        return render_template('waitlist.html')


@static_bp.route('/privacy')
def privacy_policy():
    """
    Privacy policy page.

    Displays the application's privacy policy and GDPR information.
    """
    try:
        return render_template('privacy_policy.html')
    except Exception as e:
        logger.error(f"Error loading privacy policy: {e}")
        return "Privacy Policy page unavailable", 500


@static_bp.route('/terms')
def terms_of_service():
    """
    Terms of service page.

    Displays the application's terms of service.
    """
    try:
        return render_template('terms_of_service.html')
    except Exception as e:
        logger.error(f"Error loading terms of service: {e}")
        return "Terms of Service page unavailable", 500


@static_bp.route('/contact', methods=['GET', 'POST'])
@limiter.limit("20 per hour")
def contact():
    """
    Contact page route.

    GET: Display contact form
    POST: Process contact form submission
    """
    if request.method == 'GET':
        return render_template('contact.html')

    try:
        # Get form data
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        # Validate required fields
        if not all([name, email, subject, message]):
            flash('All fields are required', 'error')
            return render_template('contact.html')

        # Validate email using Pydantic schema
        try:
            WaitlistSchema(email=email)
        except ValidationError:
            flash('Invalid email address', 'error')
            return render_template('contact.html')

        # Log contact submission (in production, send email or save to database)
        logger.info(f"Contact form submission from {name} ({email}): {subject}")

        # TODO: In production, implement email sending or database storage
        # For now, just log and show success message

        flash('Thank you for your message. We will get back to you soon!', 'success')
        return redirect(url_for('static.contact'))

    except Exception as e:
        logger.error(f"Error processing contact form: {e}")
        flash('An error occurred. Please try again.', 'error')
        return render_template('contact.html')


@static_bp.route('/about')
def about():
    """
    About page route.

    Displays information about the application and company.
    """
    try:
        return render_template('about.html')
    except Exception as e:
        logger.error(f"Error loading about page: {e}")
        # Fallback content
        return """
        <h1>About Solar Intelligence Platform</h1>
        <p>Your comprehensive solution for solar market analysis and intelligence.</p>
        """, 200


@static_bp.route('/health')
def health_check():
    """
    Health check endpoint for monitoring.

    Returns JSON with application status.
    """
    try:
        # Check database connection
        db.session.execute(db.text('SELECT 1'))

        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 503


@static_bp.route('/submit-contact', methods=['POST'])
@csrf.exempt  # Exempt from CSRF protection for public contact form
def submit_contact():
    """Handle contact form submission (JSON API version)"""
    try:
        # Get form data
        first_name = request.form.get('firstName', '').strip()
        last_name = request.form.get('lastName', '').strip()
        email = request.form.get('email', '').strip()
        company = request.form.get('company', '').strip()
        phone = request.form.get('phone', '').strip()
        message = request.form.get('message', '').strip()

        # Validate required fields
        if not all([first_name, last_name, email, message]):
            return jsonify({'success': False, 'message': 'Name, email, and message are required'}), 400

        # Save to database
        from models import ContactRequest

        full_name = f"{first_name} {last_name}"
        contact_request = ContactRequest(
            user_id=None,  # Public form, no user ID
            name=full_name,
            email=email,
            company=company if company else None,
            phone=phone if phone else None,
            message=message,
            source='landing_page'
        )
        db.session.add(contact_request)
        db.session.commit()

        logger.info(f"Landing page contact request saved: ID {contact_request.id} from {full_name} ({email})")

        # TODO: In production, implement:
        # 1. Send notification email to sales team
        # 2. Send confirmation email to user

        return jsonify({'success': True, 'message': 'Thank you for your message! We will get back to you soon.'})
    except Exception as e:
        logger.error(f"Error processing contact form: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'}), 500


@static_bp.route('/guide')
def get_guide():
    """Get user guide markdown content"""
    from flask_login import login_required
    try:
        import os
        guide_path = os.path.join('docs', 'pv-market-analysis-user-guide.md')
        if os.path.exists(guide_path):
            with open(guide_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        else:
            return "User guide not found.", 404
    except Exception as e:
        logger.error(f"Error loading guide: {str(e)}")
        return f"Error loading guide: {str(e)}", 500


@static_bp.route('/random-news')
def random_news():
    """Get a random news article"""
    from flask_login import login_required
    import random

    # News list would normally be loaded from a database or external source
    # For now, return empty if no news available
    NEWS_LIST = []  # TODO: Implement news loading

    if not NEWS_LIST:
        return jsonify({}), 404

    news = random.choice(NEWS_LIST)
    return jsonify({
        "title": news.get("title", ""),
        "description": news.get("description", ""),
        "url": news.get("url", "")
    })


# Error handlers for this blueprint
@static_bp.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404


@static_bp.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {e}")
    return render_template('500.html'), 500
