"""
Flask extensions initialization.

Extensions are initialized here and imported by routes/services.
This prevents circular imports and provides a single source of truth.

BRIDGE APPROACH: We import db from existing models.py to ensure
we use the same SQLAlchemy instance throughout the application.
"""

# BRIDGE: Import db from existing models.py instead of creating new instance
from models import db

from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

# Initialize other extensions without app binding
# These will be bound to the app in init_extensions()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[]  # No default limits - routes define their own
)

# Logging
memory_logger = logging.getLogger('memory_monitor')


def init_extensions(app):
    """
    Initialize Flask extensions with app instance.

    This function binds all extensions to the Flask app and configures them.
    Should be called during app factory initialization.

    Args:
        app: Flask application instance

    Returns:
        Configured Flask app
    """
    # Database
    db.init_app(app)

    # Authentication
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Will update when we create auth blueprint
    login_manager.login_message = 'Please log in to access DH Agents.'
    login_manager.login_message_category = 'info'

    # CSRF Protection
    csrf.init_app(app)

    # Rate Limiting
    limiter.init_app(app)

    # Configure memory logger
    configure_memory_logger(app.config.get('LOG_LEVEL', 'WARNING'))

    print("✅ Flask extensions initialized")

    return app


def configure_memory_logger(log_level='WARNING'):
    """
    Configure memory monitoring logger.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    import sys

    # Set log level
    level = getattr(logging, log_level.upper(), logging.WARNING)
    memory_logger.setLevel(level)

    # Only add handler if not already present
    if not memory_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Set encoding to UTF-8 if supported
        if hasattr(console_handler.stream, 'reconfigure'):
            console_handler.stream.reconfigure(encoding='utf-8', errors='replace')

        # Create formatter that handles Unicode safely
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        memory_logger.addHandler(console_handler)

    print(f"✅ Memory logger configured (level: {log_level})")


def setup_login_manager_user_loader(user_model):
    """
    Setup Flask-Login user loader callback.

    This must be called after models are defined to avoid circular imports.

    Args:
        user_model: User model class with query interface
    """
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        return user_model.query.get(int(user_id))

    print("✅ Login manager user loader configured")
