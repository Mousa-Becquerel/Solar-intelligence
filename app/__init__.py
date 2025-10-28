"""
Solar Intelligence Application Package.

This package contains the refactored modular architecture for the
Solar Intelligence platform, preparing for eventual migration to FastAPI/React.
"""

from flask import Flask
from app.config import get_config, create_directories
from app.extensions import init_extensions, setup_login_manager_user_loader

__version__ = "2.0.0-refactor"


def create_app(config_name=None):
    """
    Application factory pattern for Flask app creation.

    This function creates and configures the Flask application with all
    necessary extensions, routes, and error handlers.

    Args:
        config_name: Configuration name ('development', 'production', 'testing')
                    If None, uses FLASK_ENV environment variable

    Returns:
        Configured Flask application instance
    """
    # Get configuration
    config = get_config(config_name)

    # Create Flask app
    # Point to parent directory for templates and static files
    import os
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(
        __name__,
        template_folder=os.path.join(root_path, 'templates'),
        static_folder=os.path.join(root_path, 'static'),
        static_url_path='/static'
    )

    # Load configuration
    app.config.from_object(config)

    # Initialize extensions
    init_extensions(app)

    # Create required directories
    create_directories(config)

    # Setup user loader (will be done after models are imported)
    # This is handled in the main app.py for now to avoid circular imports

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    register_blueprints(app)

    return app


def register_error_handlers(app):
    """
    Register Flask error handlers.

    Args:
        app: Flask application instance
    """
    from flask import render_template, jsonify

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        from app.extensions import db
        db.session.rollback()
        app.logger.error(f"Internal server error: {error}")
        return render_template('500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors."""
        return render_template('403.html'), 403

    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors."""
        if 'CSRF' in str(error):
            return jsonify({
                'error': 'CSRF token validation failed. Please refresh the page and try again.'
            }), 400
        return render_template('400.html'), 400

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all unhandled exceptions."""
        app.logger.error(f"Unhandled exception: {error}")
        return render_template('500.html'), 500

    print("✅ Error handlers registered")


def register_blueprints(app):
    """
    Register Flask blueprints.

    Registers all application blueprints with their URL prefixes:
    - static_bp: Static pages (no prefix, includes landing page)
    - auth_bp: Authentication (/auth)
    - chat_bp: Chat interface (no prefix for /chat and /api/agents/* routes)
    - conversation_bp: Conversation management (/conversations)
    - admin_bp: Admin panel (/admin)
    - profile_bp: Profile management (no prefix for /profile/* routes)

    Args:
        app: Flask application instance
    """
    from app.routes import auth_bp, chat_bp, conversation_bp, admin_bp, static_bp

    # Import profile blueprint from old routes location
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from routes.profile import profile_bp

    # Register static pages blueprint (no prefix for landing page)
    app.register_blueprint(static_bp)
    app.logger.info("✅ Registered static_bp")

    # Register auth blueprint
    app.register_blueprint(auth_bp)
    app.logger.info("✅ Registered auth_bp at /auth")

    # Register chat blueprint (no prefix to match original app.py routes)
    app.register_blueprint(chat_bp)
    app.logger.info("✅ Registered chat_bp")

    # Register conversation blueprint
    app.register_blueprint(conversation_bp)
    app.logger.info("✅ Registered conversation_bp at /conversations")

    # Register admin blueprint
    app.register_blueprint(admin_bp)
    app.logger.info("✅ Registered admin_bp at /admin")

    # Register profile blueprint (no prefix to match /profile/* routes)
    app.register_blueprint(profile_bp)
    app.logger.info("✅ Registered profile_bp")

    print("✅ All blueprints registered successfully")
