"""
Run script for refactored application.

This script uses the new app factory pattern while maintaining
compatibility with existing agents and special configurations.
"""

import os
import sys
import logging

# Fix Unicode encoding issues on Windows
if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Set matplotlib backend BEFORE importing pyplot (delayed until needed)
def setup_matplotlib():
    """Setup matplotlib backend when needed."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        return True
    except Exception as e:
        print(f"⚠️  Matplotlib setup failed: {e}")
        print("    Charts may not work, but app will run.")
        return False

# Logfire configuration (if enabled)
try:
    import logfire
    logfire_token = os.getenv('LOGFIRE_TOKEN')
    if logfire_token:
        logfire.configure(token=logfire_token)
        logfire.instrument_pydantic_ai()
        print("✅ Logfire configured")

        # Suppress OpenTelemetry context errors
        otel_context_logger = logging.getLogger('opentelemetry.context')
        otel_context_logger.setLevel(logging.CRITICAL)
    else:
        print("⚠️  LOGFIRE_TOKEN not set - monitoring disabled")
except ImportError:
    print("⚠️  Logfire not installed - monitoring disabled")
except Exception as e:
    print(f"❌ Logfire configuration error: {e}")

# Create app using factory pattern
from app import create_app

# Determine environment
config_name = os.getenv('FLASK_ENV', 'production')
if config_name == 'development':
    config_name = 'development'
elif config_name == 'testing':
    config_name = 'testing'
else:
    config_name = 'production'

print(f"Creating app with config: {config_name}")
app = create_app(config_name)

# Setup login manager user loader (needed for Flask-Login)
from models import User
from app.extensions import login_manager

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    from models import db
    return db.session.get(User, int(user_id))

print("✅ User loader configured")

# Instrument Flask with Logfire (if enabled)
try:
    if 'logfire' in sys.modules and logfire_token:
        logfire.instrument_flask(app)
        print("✅ Flask instrumentation enabled")

        # Test Logfire connection
        from datetime import datetime
        with logfire.span("app_startup") as span:
            span.set_attribute("startup_time", datetime.utcnow().isoformat())
            span.set_attribute("app_name", "pv-market-analysis-refactored")
        logfire.info("Refactored application startup complete")
        print("✅ Logfire test log sent")
except Exception as e:
    print(f"❌ Logfire instrumentation error: {e}")

# Initialize database tables
with app.app_context():
    from models import db
    try:
        db.create_all()
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

if __name__ == '__main__':
    # Development server settings
    debug_mode = config_name == 'development'
    port = int(os.getenv('PORT', 5000))

    print(f"\n{'='*60}")
    print(f"Starting Refactored PV Market Analysis Application")
    print(f"{'='*60}")
    print(f"Environment: {config_name}")
    print(f"Debug Mode: {debug_mode}")
    print(f"Port: {port}")
    print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')[:50]}...")
    print(f"{'='*60}\n")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        use_reloader=debug_mode
    )
