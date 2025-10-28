"""
Configuration Bridge Module

This module provides a bridge between the legacy app.py configuration
and the new modular app/config.py structure.

Usage in app.py:
    from app_config_bridge import apply_new_config

    # After creating Flask app:
    app = Flask(__name__)
    apply_new_config(app)
"""

from app.config import get_config, create_directories


def apply_new_config(app):
    """
    Apply new modular configuration to existing Flask app.

    This allows gradual migration by using new config module
    while keeping the existing app.py structure.

    Args:
        app: Flask application instance

    Returns:
        Configured Flask app
    """
    # Get configuration based on environment
    config = get_config()

    # Apply configuration to app
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SESSION_COOKIE_SECURE'] = config.SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = config.SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = config.SESSION_COOKIE_SAMESITE
    app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME
    app.config['WTF_CSRF_TIME_LIMIT'] = config.WTF_CSRF_TIME_LIMIT

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = config.SQLALCHEMY_ENGINE_OPTIONS

    # Other configuration
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    app.config['GOOGLE_ANALYTICS_ID'] = config.GOOGLE_ANALYTICS_ID

    # Create required directories
    create_directories(config)

    print("✅ New configuration applied to app")

    return app, config
