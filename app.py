import os
import sys
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session, send_from_directory, Response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Conversation, Message, Waitlist, Feedback, UserSurvey, UserSurveyStage2, HiredAgent
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash, safe_join
from datetime import datetime, timedelta
# Import custom agents
from module_prices_agent import ModulePricesAgent, ModulePricesConfig, PlotResult, DataAnalysisResult, MultiResult, PlotDataResult
from news_agent import get_news_agent, close_news_agent
from leo_om_agent import get_leo_om_agent, close_leo_om_agent, LeoOMAgent
from digitalization_trend_agent import get_digitalization_agent
from market_intelligence_agent import get_market_intelligence_agent, close_market_intelligence_agent
import base64
import pandas as pd
import json
import math
import random
from dotenv import load_dotenv  # Disabled for production deployment
import uuid
import threading
import psutil
import gc
import logging
from sqlalchemy import text

# Logfire imports and configuration - MUST BE BEFORE AGENT IMPORTS
import logfire

# Configure Logfire IMMEDIATELY (before importing agents)
try:
    # ✅ SECURITY FIX: Load Logfire token from environment variable
    logfire_token = os.getenv('LOGFIRE_TOKEN')
    if not logfire_token:
        raise ValueError("LOGFIRE_TOKEN environment variable is required for monitoring")

    logfire.configure(token=logfire_token)
    print("✅ Logfire configured early (before agent imports)")

    # Instrument Pydantic AI before any agents are created
    logfire.instrument_pydantic_ai()
    print("✅ Pydantic AI instrumentation enabled early")

    # Suppress OpenTelemetry context errors (harmless in async streaming)
    otel_context_logger = logging.getLogger('opentelemetry.context')
    otel_context_logger.setLevel(logging.CRITICAL)  # Only show critical errors, not "Failed to detach context"
    print("✅ OpenTelemetry context logger configured")

except Exception as e:
    print(f"❌ Early Logfire configuration error: {e}")
    import traceback
    traceback.print_exc()

# Set matplotlib backend BEFORE importing pyplot
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web apps
import matplotlib.pyplot as plt

# Fix Unicode encoding issues on Windows
if sys.platform.startswith('win'):
    # Set console output encoding to UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    # Set environment variable for consistent UTF-8 handling
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Load environment variables
load_dotenv()  # Disabled for production deployment

# Configure logging for memory monitoring
memory_logger = logging.getLogger('memory_monitor')
memory_logger.setLevel(logging.WARNING)  # Only show warnings and errors (reduced from INFO)

# Configure logging handler with UTF-8 encoding
if not memory_logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors (reduced from INFO)
    
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

def get_memory_usage():
    """Get current memory usage information"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
            'memory_percent': process.memory_percent(),
            'available_memory_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024
        }
    except Exception as e:
        memory_logger.error(f"Error getting memory usage: {e}")
        return None

def log_memory_usage(context=""):
    """Log current memory usage (silently unless high)"""
    mem_info = get_memory_usage()
    if mem_info:
        # Removed verbose INFO logging - only log when memory is actually high

        # Alert if memory usage is getting high (increased thresholds)
        if mem_info['rss_mb'] > 600:  # Increased from 400MB
            memory_logger.warning(f"HIGH MEMORY USAGE: {mem_info['rss_mb']:.1f}MB RSS")

        if mem_info['rss_mb'] > 800:  # Increased from 500MB
            memory_logger.critical(f"CRITICAL MEMORY USAGE: {mem_info['rss_mb']:.1f}MB RSS")
    
    return mem_info

def cleanup_memory():
    """Perform memory cleanup operations while preserving conversation memory and agent instance"""
    try:
        # Aggressive matplotlib cleanup
        try:
            plt.close('all')  # Close all figures
            plt.clf()  # Clear current figure
            plt.cla()  # Clear current axes
        except Exception as e:
            memory_logger.error(f"Error cleaning matplotlib: {e}")
        
        # Clear pandas cache
        try:
            import pandas as pd
            # Clear any cached DataFrames
            pd.io.common._NA_VALUES = set()
        except Exception as e:
            memory_logger.error(f"Error cleaning pandas cache: {e}")
        
        # Force garbage collection multiple times
        collected = 0
        for _ in range(3):
            collected += gc.collect()

        # Removed verbose logging - only log if issues occur
        # Memory usage will be logged by log_memory_usage() if it's still high
        log_memory_usage("After memory cleanup")
        
        return True
    except Exception as e:
        memory_logger.error(f"Error during memory cleanup: {e}")
        return False

def clear_conversation_memory(conversation_id: str = None):
    """Clear conversation memory for specific conversation or all conversations"""
    try:
        # Market agent uses OpenAI Agents SDK (SQLite sessions) - no in-memory state to clear

        # Clear Leo O&M agent memory
        leo_om_agent.clear_conversation_memory(conversation_id)

        memory_logger.info(f"Cleared conversation memory for {conversation_id if conversation_id else 'all conversations'}")
        return True
    except Exception as e:
        memory_logger.error(f"Error clearing conversation memory: {e}")
        return False

def periodic_memory_cleanup():
    """Periodic memory cleanup to prevent accumulation"""
    try:
        mem_info = get_memory_usage()
        if mem_info and mem_info['rss_mb'] > 350:  # Increased from 200MB to 350MB
            # Silently cleanup - only log errors
            cleanup_memory()
            return True
        return False
    except Exception as e:
        memory_logger.error(f"Error in periodic cleanup: {e}")
        return False

def force_memory_cleanup():
    """Force immediate memory cleanup regardless of current usage"""
    try:
        # Silently cleanup - only log errors
        cleanup_memory()

        # Additional matplotlib-specific cleanup
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
            plt.clf()
            plt.cla()
        except Exception as e:
            memory_logger.error(f"Error in matplotlib cleanup: {e}")

        # Force garbage collection
        gc.collect()

        return True
    except Exception as e:
        memory_logger.error(f"Error in force cleanup: {e}")
        return False

def monitor_memory_usage():
    """Monitor memory usage and log only when there are issues"""
    try:
        mem_info = get_memory_usage()
        if mem_info:
            # Only log when memory usage is high
            if mem_info['rss_mb'] > 400:  # Increased from 300MB to 400MB
                memory_logger.warning(f"HIGH MEMORY USAGE: {mem_info['rss_mb']:.1f}MB RSS")
                # Trigger cleanup
                cleanup_memory()

            if mem_info['rss_mb'] > 500:  # Increased from 400MB to 500MB
                memory_logger.critical(f"CRITICAL MEMORY USAGE: {mem_info['rss_mb']:.1f}MB RSS")
                # Force cleanup
                force_memory_cleanup()

            return mem_info
        return None
    except Exception as e:
        memory_logger.error(f"Error in memory monitoring: {e}")
        return None

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Instrument Flask (Logfire was already configured early)
try:
    logfire.instrument_flask(app)
    print("✅ Flask instrumentation enabled")

    # Add debug logging for Logfire
    import logging
    logging.getLogger("logfire").setLevel(logging.DEBUG)
    print("🔍 Logfire debug logging enabled")

    # Test Logfire connection on startup
    with logfire.span("app_startup") as span:
        span.set_attribute("startup_time", datetime.utcnow().isoformat())
        span.set_attribute("app_name", "pv-market-analysis")
        print("🔍 Logfire startup span created and sent")

    # Send a test log
    logfire.info("Application startup complete", extra={"environment": "production"})
    print("✅ Logfire test log sent")

except Exception as e:
    print(f"❌ Logfire Flask instrumentation error: {e}")
    import traceback
    traceback.print_exc()

# Production security configuration
secret_key = os.getenv('FLASK_SECRET_KEY')
if not secret_key:
    raise ValueError("FLASK_SECRET_KEY environment variable must be set for production")
app.config['SECRET_KEY'] = secret_key

# ✅ SECURITY FIX: Secure session cookie configuration
# Only enforce SECURE flag in production (HTTPS), not in development (HTTP)
is_production = os.getenv('FLASK_ENV') != 'development'
app.config['SESSION_COOKIE_SECURE'] = is_production  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True         # Prevent JavaScript access (XSS protection)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'        # CSRF protection while allowing normal navigation

# Google Analytics configuration (optional)
app.config['GOOGLE_ANALYTICS_ID'] = os.getenv('GOOGLE_ANALYTICS_ID', None)

# Log initial memory usage
log_memory_usage("Application startup")

# Production-ready configuration with connection pooling
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///chat_history.db')

# Handle PostgreSQL URL format from Render
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Force psycopg3 for PostgreSQL connections (better Python 3.13 compatibility)
if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
    # Ensure we're using psycopg3
    try:
        import psycopg
        # Update the URL to explicitly use psycopg3
        if 'postgresql://' in app.config['SQLALCHEMY_DATABASE_URI']:
            app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgresql://', 'postgresql+psycopg://', 1)
    except ImportError:
        # Fallback to psycopg2 if psycopg3 is not available
        pass

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Optimized PostgreSQL configuration for Docker + Gunicorn
if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 300,  # Recycle connections after 5 minutes
        'pool_size': 5,  # Reduced from 10 - max persistent connections per worker
        'max_overflow': 10,  # Reduced from 20 - max temporary connections
        'pool_timeout': 30,  # Wait up to 30s for available connection
        'connect_args': {
            'connect_timeout': 10,  # Connection timeout
            'application_name': 'BecqSight',
            'options': '-c statement_timeout=60000'  # 60s query timeout
        }
    }
else:
    # SQLite configuration for local development
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access DH Agents.'
login_manager.login_message_category = 'info'

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize rate limiter - DISABLED default limits to fix 429 errors
# Individual routes will have their own limits
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],  # No default limits
    storage_uri="memory://"
)

# Global error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    memory_logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@app.errorhandler(Exception)
def handle_exception(error):
    memory_logger.error(f"Unhandled exception: {error}")
    return render_template('500.html'), 500

# CSRF error handler
@app.errorhandler(400)
def bad_request_error(error):
    if 'CSRF' in str(error):
        return jsonify({'error': 'CSRF token validation failed. Please refresh the page and try again.'}), 400
    return render_template('400.html'), 400

# Create static directory for plots if it doesn't exist
PLOTS_DIR = os.path.join('static', 'plots')
os.makedirs(PLOTS_DIR, exist_ok=True)

# Create exports directory for charts if it doesn't exist
EXPORTS_DIR = os.path.join('exports', 'charts')
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Thread-safe chart generation lock
chart_lock = threading.Lock()

db.init_app(app)  # Initialize db with app (db imported from models.py)

# ========================================
# Models imported from models.py:
# - User, Conversation, Message, Waitlist, Feedback
# ========================================

# ========================================
# Conversation Manager for Database Storage
# ========================================

class ConversationManager:
    """
    Manages conversation persistence in PostgreSQL database.
    This allows multiple Gunicorn workers to share conversation state.

    Benefits:
    - Conversations persist across worker restarts
    - Multiple workers can access same conversation
    - Users can see conversation history across sessions
    - No memory limitations
    """

    @staticmethod
    def save_message(conversation_id: int, sender: str, content: str) -> bool:
        """
        Save a message to the database.

        Args:
            conversation_id: ID of the conversation
            sender: 'user' or 'assistant'
            content: Message content

        Returns:
            True if successful, False otherwise
        """
        try:
            message = Message(
                conversation_id=conversation_id,
                sender=sender,
                content=content,
                timestamp=datetime.utcnow()
            )
            db.session.add(message)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            memory_logger.error(f"Error saving message to DB: {e}")
            return False

    @staticmethod
    def get_conversation_messages(conversation_id: int, limit: int = 50) -> list:
        """
        Get conversation messages from database.

        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to retrieve (default 50)

        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        try:
            messages = Message.query.filter_by(
                conversation_id=conversation_id
            ).order_by(
                Message.timestamp.asc()
            ).limit(limit).all()

            return [
                {
                    'role': 'user' if msg.sender == 'user' else 'assistant',
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        except Exception as e:
            memory_logger.error(f"Error getting messages from DB: {e}")
            return []

    @staticmethod
    def clear_conversation(conversation_id: int) -> bool:
        """
        Clear all messages for a conversation.

        Args:
            conversation_id: ID of the conversation

        Returns:
            True if successful, False otherwise
        """
        try:
            Message.query.filter_by(conversation_id=conversation_id).delete()
            db.session.commit()
            memory_logger.info(f"Cleared conversation {conversation_id}")
            return True
        except Exception as e:
            db.session.rollback()
            memory_logger.error(f"Error clearing conversation: {e}")
            return False

    @staticmethod
    def get_or_create_conversation(user_id: int, agent_type: str, title: str = None) -> int:
        """
        Get existing conversation or create new one.

        Args:
            user_id: ID of the user
            agent_type: Type of agent (market, price, om, news)
            title: Optional conversation title

        Returns:
            Conversation ID
        """
        try:
            conversation = Conversation(
                user_id=user_id,
                agent_type=agent_type,
                title=title or f"{agent_type.capitalize()} Chat",
                created_at=datetime.utcnow()
            )
            db.session.add(conversation)
            db.session.commit()
            memory_logger.info(f"Created new conversation {conversation.id} for user {user_id}")
            return conversation.id
        except Exception as e:
            db.session.rollback()
            memory_logger.error(f"Error creating conversation: {e}")
            return None

    @staticmethod
    def get_conversation(conversation_id: int):
        """Get conversation by ID"""
        try:
            return Conversation.query.get(conversation_id)
        except Exception as e:
            memory_logger.error(f"Error getting conversation: {e}")
            return None

    @staticmethod
    def get_user_conversations(user_id: int, agent_type: str = None, limit: int = 20):
        """
        Get user's recent conversations.

        Args:
            user_id: ID of the user
            agent_type: Optional filter by agent type
            limit: Maximum number of conversations

        Returns:
            List of conversations
        """
        try:
            query = Conversation.query.filter_by(user_id=user_id)
            if agent_type:
                query = query.filter_by(agent_type=agent_type)

            conversations = query.order_by(
                Conversation.created_at.desc()
            ).limit(limit).all()

            return conversations
        except Exception as e:
            memory_logger.error(f"Error getting user conversations: {e}")
            return []

# Predefined users - Add your users here
# SECURITY: Default users are disabled. Create admin users via environment variables or admin interface
# For local development, set ADMIN_EMAIL and ADMIN_PASSWORD environment variables
PREDEFINED_USERS = []

# Create admin from environment variables if provided (for initial setup only)
if os.getenv('ADMIN_EMAIL') and os.getenv('ADMIN_PASSWORD'):
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_password = os.getenv('ADMIN_PASSWORD')

    # Validate strong password
    if len(admin_password) < 12:
        print("WARNING: ADMIN_PASSWORD must be at least 12 characters long")
    else:
        PREDEFINED_USERS.append({
            'username': admin_email,
            'password': admin_password,
            'full_name': os.getenv('ADMIN_NAME', 'Administrator'),
            'role': 'admin'
        })
        print(f"✅ Admin user will be created from environment variables: {admin_email}")

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        memory_logger.error(f"Error loading user {user_id}: {e}")
        # If database connection fails, return None to force re-authentication
        db.session.rollback()
        return None

def migrate_database():
    """Handle database migrations for existing databases"""
    try:
        # Check if we're using PostgreSQL
        is_postgresql = 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']
        
        if is_postgresql:
            # For PostgreSQL, we can be more careful about migrations
            try:
                # Check if tables exist
                db.session.execute(text('SELECT COUNT(*) FROM "user"'))
                db.session.execute(text('SELECT COUNT(*) FROM conversation'))
                db.session.execute(text('SELECT COUNT(*) FROM message'))
                db.session.execute(text('SELECT COUNT(*) FROM feedback'))
                db.session.commit()
                print("SUCCESS: PostgreSQL database schema verified successfully")
                return True
            except Exception as e:
                print(f"PostgreSQL schema verification failed: {e}")
                # Create tables if they don't exist
                db.create_all()
                db.session.commit()
                print("SUCCESS: PostgreSQL tables created successfully")
                return True
        else:
            # For SQLite, use the existing logic with GDPR migration
            try:
                # Check if GDPR columns exist in user table
                result = db.session.execute(text("PRAGMA table_info(user)"))
                columns = [row[1] for row in result.fetchall()]

                # Check if we have the new GDPR columns
                gdpr_columns = ['gdpr_consent_given', 'gdpr_consent_date', 'terms_accepted',
                               'terms_accepted_date', 'marketing_consent', 'marketing_consent_date',
                               'privacy_policy_version', 'terms_version']

                missing_columns = [col for col in gdpr_columns if col not in columns]

                if missing_columns:
                    print(f"MIGRATION: Adding GDPR columns: {missing_columns}")

                    # Add the missing GDPR columns one by one (SQLite doesn't support multiple ADD COLUMN)
                    migration_sql = [
                        "ALTER TABLE user ADD COLUMN gdpr_consent_given BOOLEAN DEFAULT 0 NOT NULL",
                        "ALTER TABLE user ADD COLUMN gdpr_consent_date DATETIME",
                        "ALTER TABLE user ADD COLUMN terms_accepted BOOLEAN DEFAULT 0 NOT NULL",
                        "ALTER TABLE user ADD COLUMN terms_accepted_date DATETIME",
                        "ALTER TABLE user ADD COLUMN marketing_consent BOOLEAN DEFAULT 0 NOT NULL",
                        "ALTER TABLE user ADD COLUMN marketing_consent_date DATETIME",
                        "ALTER TABLE user ADD COLUMN privacy_policy_version VARCHAR(10) DEFAULT '1.0'",
                        "ALTER TABLE user ADD COLUMN terms_version VARCHAR(10) DEFAULT '1.0'"
                    ]

                    for sql in migration_sql:
                        try:
                            db.session.execute(text(sql))
                        except Exception as col_error:
                            # Column might already exist, continue
                            print(f"Column migration info: {col_error}")

                    db.session.commit()
                    print("SUCCESS: GDPR columns added to existing database")

                # Verify all tables exist and are accessible
                db.session.execute(text('SELECT COUNT(*) FROM "user"'))
                db.session.execute(text('SELECT COUNT(*) FROM conversation'))
                db.session.execute(text('SELECT COUNT(*) FROM message'))
                db.session.execute(text('SELECT COUNT(*) FROM feedback'))
                db.session.commit()
                print("SUCCESS: SQLite database schema verified successfully")
                return True

            except Exception as e:
                print(f"SQLite database schema verification failed: {e}")
                try:
                    # Rollback any failed transaction first
                    db.session.rollback()

                    print("REBUILDING: Recreating database tables...")
                    # Drop and recreate all tables if there's an issue
                    db.drop_all()
                    db.create_all()
                    db.session.commit()

                    print("SUCCESS: SQLite database tables recreated successfully")
                    print("WARNING: All previous data has been cleared due to schema changes.")
                    return True
                    
                except Exception as migrate_error:
                    print(f"ERROR: Migration failed: {migrate_error}")
                    db.session.rollback()
                    raise
        
    except Exception as e:
        print(f"ERROR: Database migration failed: {e}")
        return False

def create_predefined_users():
    """Create predefined users if they don't exist"""
    try:
        for user_data in PREDEFINED_USERS:
            try:
                existing_user = User.query.filter_by(username=user_data['username']).first()
                if not existing_user:
                    from datetime import datetime
                    user = User(
                        username=user_data['username'],
                        password_hash=generate_password_hash(user_data['password']),
                        full_name=user_data['full_name'],
                        role=user_data['role'],
                        gdpr_consent_given=True,
                        gdpr_consent_date=datetime.utcnow(),
                        terms_accepted=True,
                        terms_accepted_date=datetime.utcnow()
                    )
                    db.session.add(user)
                    print(f"CREATED: User {user_data['username']}")
                else:
                    print(f"EXISTS: User already exists: {user_data['username']}")
            except Exception as user_error:
                print(f"WARNING: Error checking/creating user {user_data['username']}: {user_error}")
                db.session.rollback()
                continue
        
        # Commit all user creations at once
        db.session.commit()
        print("SUCCESS: Predefined users setup complete")
        
    except Exception as e:
        print(f"ERROR: Error setting up predefined users: {e}")
        db.session.rollback()

# Ensure tables are created at startup (Flask 3.x compatible)
with app.app_context():
    try:
        # First, create all tables if they don't exist
        db.create_all()
        
        # Test database connection with a simple query
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        # Now try to migrate/verify schema
        migrate_database()
        
        # Finally, create predefined users
        create_predefined_users()
        
        print("SUCCESS: Database initialization completed successfully")
        
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
        # Rollback any failed transaction
        try:
            db.session.rollback()
        except Exception as rollback_error:
            memory_logger.error(f"Error during rollback: {rollback_error}")
        # Continue startup even if database init fails
        pass

# Load news once at startup
with open('zotero_news_full.json', encoding='utf-8') as f:
    NEWS_LIST = json.load(f)

# === GLOBAL SINGLETON FOR MODULE PRICES AGENT ===
# Import already done at top of file (line 12)
module_prices_agent = ModulePricesAgent(ModulePricesConfig(verbose=False))

# === GLOBAL SINGLETON FOR NEWS AGENT ===
news_agent = get_news_agent()

# === GLOBAL SINGLETON FOR LEO O&M AGENT ===
leo_om_agent = get_leo_om_agent()

# === GLOBAL SINGLETON FOR DIGITALIZATION TREND AGENT ===
digitalization_agent = get_digitalization_agent()

# === GLOBAL SINGLETON FOR MARKET INTELLIGENCE AGENT ===
market_intelligence_agent = get_market_intelligence_agent()

# ========================================
# Register Profile Blueprint
# ========================================
from routes.profile import profile_bp
app.register_blueprint(profile_bp)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('agents'))
    except Exception as e:
        memory_logger.error(f"Error checking authentication status: {e}")
        # If database connection fails, continue with login process
        db.session.rollback()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')
        
        try:
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                # Check if account is marked for deletion
                if user.deleted:
                    days_remaining = 30 - (datetime.utcnow() - user.deletion_requested_at).days
                    if days_remaining > 0:
                        flash(f'Your account is scheduled for deletion. You have {days_remaining} days remaining to cancel. Contact support to restore your account.', 'warning')
                    else:
                        flash('Your account has been deleted. Contact support if you believe this is an error.', 'error')
                    return render_template('login.html')

                if not user.is_active:
                    flash('Your account is pending administrator approval. Please wait for an admin to activate your account, or contact support if you\'ve been waiting more than 24 hours.', 'warning')
                    return render_template('login.html')

                login_user(user, remember=True)
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('agents')
                return redirect(next_page)
            else:
                flash('Invalid username or password.', 'error')
        except Exception as e:
            memory_logger.error(f"Database error during login: {e}")
            db.session.rollback()
            flash('Database connection error. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register():
    if request.method == 'POST':
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

        # Validate GDPR consent (required)
        if not terms_agreement:
            flash('You must agree to the terms of service and privacy policy to create an account.', 'error')
            return render_template('register.html')
        
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(username=email).first()
            if existing_user:
                flash('An account with this email already exists.', 'error')
                return render_template('register.html')
            
            # Create new user (inactive by default, requires admin approval)
            consent_timestamp = datetime.utcnow()
            new_user = User(
                username=email,  # Use email as username
                full_name=f"{first_name} {last_name}",
                role='user',
                is_active=False,  # Requires admin approval

                # GDPR Consent Tracking
                gdpr_consent_given=True,  # Required for account creation
                gdpr_consent_date=consent_timestamp,
                terms_accepted=True,  # Required for account creation
                terms_accepted_date=consent_timestamp,
                marketing_consent=bool(communications),  # Optional
                marketing_consent_date=consent_timestamp if communications else None,
                privacy_policy_version='1.0',
                terms_version='1.0'
            )
            new_user.set_password(password)
            
            # Add to database
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! Your account is pending approval. An administrator will review and activate your account shortly.', 'info')
            return redirect(url_for('login'))
            
        except Exception as e:
            memory_logger.error(f"Registration error: {e}")
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/current-user')
@login_required
def current_user_info():
    return jsonify({
        'username': current_user.username,
        'full_name': current_user.full_name,
        'role': current_user.role
    })

@app.route('/health')
def health_check():
    """Health check endpoint for AWS deployment"""
    # Test Logfire span
    with logfire.span("health_check") as span:
        span.set_attribute("test", True)
        span.set_attribute("timestamp", datetime.utcnow().isoformat())
        print("🔍 Logfire test span created")
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'memory': get_memory_usage(),
            'database': check_database_health()
        })

@app.route('/')
def index():
    """Root route - Show waitlist page or redirect to agents for authenticated users"""
    # Check if user is authenticated
    if current_user.is_authenticated:
        # Authenticated users go to agents page
        return redirect(url_for('agents'))

    # Show waitlist page as the main landing page
    return redirect(url_for('waitlist_page'))

@app.route('/waitlist')
def waitlist_page():
    """Waitlist landing page"""
    # Get current waitlist count
    waitlist_count = Waitlist.query.count()

    # Check if admin access should be shown (via query parameter)
    show_admin_access = request.args.get('admin') == 'true'

    return render_template('waitlist.html',
                         waitlist_count=waitlist_count,
                         show_admin_access=show_admin_access)

@app.route('/api/waitlist/join', methods=['POST'])
@limiter.limit("5 per hour")  # Rate limit waitlist signups
def join_waitlist():
    """API endpoint to join waitlist"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()

        # Validate email
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email address is required'
            }), 400

        # Basic email validation
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400

        # Get interested agents (optional)
        interested_agents = data.get('interested_agents', [])
        interested_agents_json = json.dumps(interested_agents) if interested_agents else None

        # Check if email already exists
        existing = Waitlist.query.filter_by(email=email).first()
        if existing:
            # Update interested agents if provided
            if interested_agents_json:
                existing.interested_agents = interested_agents_json
                db.session.commit()
            return jsonify({
                'success': True,
                'message': 'You\'re already on the waitlist! We\'ll notify you at launch.',
                'waitlist_count': Waitlist.query.count()
            })

        # Add to waitlist
        waitlist_entry = Waitlist(
            email=email,
            interested_agents=interested_agents_json,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:256]
        )
        db.session.add(waitlist_entry)
        db.session.commit()

        agents_str = ', '.join(interested_agents) if interested_agents else 'none selected'
        memory_logger.info(f"New waitlist signup: {email} - Interested in: {agents_str}")

        return jsonify({
            'success': True,
            'message': 'Thank you! We\'ll notify you when we launch.',
            'waitlist_count': Waitlist.query.count()
        })

    except Exception as e:
        memory_logger.error(f"Error joining waitlist: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again later.'
        }), 500

@app.route('/landing')
def landing():
    """Landing page - accessible to everyone"""
    if current_user.is_authenticated:
        return redirect(url_for('agents'))
    return render_template('landing.html')

@app.route('/contact')
def contact():
    """Contact page - accessible to everyone"""
    return render_template('contact.html')

@app.route('/submit-contact', methods=['POST'])
def submit_contact():
    """Handle contact form submission"""
    try:
        # Get form data
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = request.form.get('email')
        company = request.form.get('company', '')
        phone = request.form.get('phone', '')
        message = request.form.get('message')

        # Here you can add email sending logic or save to database
        # For now, we'll just log it
        print(f"Contact form submission from {first_name} {last_name} ({email})")
        print(f"Company: {company}, Phone: {phone}")
        print(f"Message: {message}")

        # You can add email notification here using Flask-Mail or similar

        return jsonify({'success': True, 'message': 'Thank you for your message! We will get back to you soon.'})
    except Exception as e:
        print(f"Error processing contact form: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    """Main chat interface - requires login"""
    # Get user's hired agents
    hired_agents = HiredAgent.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    hired_agent_types = [agent.agent_type for agent in hired_agents]

    return render_template('index.html', hired_agents=hired_agent_types)

@app.route('/agents')
@login_required
def agents():
    """Agent selection page - requires login"""
    # Get user's hired agents
    hired_agents = HiredAgent.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    hired_agent_types = [agent.agent_type for agent in hired_agents]

    return render_template('agents.html', hired_agents=hired_agent_types)


@app.route('/api/agents/hire', methods=['POST'])
@login_required
def hire_agent():
    """Hire an agent for the current user"""
    try:
        data = request.get_json()
        agent_type = data.get('agent_type')

        # Validate agent type
        valid_agents = ['market', 'price', 'news', 'digitalization', 'om']
        if agent_type not in valid_agents:
            return jsonify({'success': False, 'message': 'Invalid agent type'}), 400

        # Check if agent exists (active or inactive)
        existing = HiredAgent.query.filter_by(
            user_id=current_user.id,
            agent_type=agent_type
        ).first()

        if existing:
            # If already active, return error
            if existing.is_active:
                return jsonify({'success': False, 'message': 'Agent already hired'}), 400
            # If inactive, reactivate it
            else:
                existing.is_active = True
                existing.hired_at = db.func.now()
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Agent hired successfully',
                    'agent_type': agent_type
                })

        # Create new hired agent record
        hired_agent = HiredAgent(
            user_id=current_user.id,
            agent_type=agent_type
        )
        db.session.add(hired_agent)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Agent hired successfully',
            'agent_type': agent_type
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error hiring agent: {str(e)}")
        print(f"Traceback: {error_traceback}")
        return jsonify({'success': False, 'message': f'Failed to hire agent: {str(e)}'}), 500


@app.route('/api/agents/unhire', methods=['POST'])
@login_required
def unhire_agent():
    """Unhire an agent for the current user"""
    try:
        data = request.get_json()
        agent_type = data.get('agent_type')

        # Find hired agent
        hired_agent = HiredAgent.query.filter_by(
            user_id=current_user.id,
            agent_type=agent_type,
            is_active=True
        ).first()

        if not hired_agent:
            return jsonify({'success': False, 'message': 'Agent not found'}), 404

        # Mark as inactive (soft delete)
        hired_agent.is_active = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Agent removed successfully',
            'agent_type': agent_type
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error unhiring agent: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to remove agent'}), 500


@app.route('/api/agents/hired', methods=['GET'])
@login_required
def get_hired_agents():
    """Get list of hired agents for current user"""
    hired_agents = HiredAgent.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    agent_types = [agent.agent_type for agent in hired_agents]

    return jsonify({
        'success': True,
        'hired_agents': agent_types
    })

@app.route('/conversations/fresh', methods=['POST'])
@login_required
def get_fresh_conversation():
    """Get or create a fresh conversation for the user - OPTIMIZED"""
    # Use efficient SQL query to find empty conversations
    # This avoids N+1 query problem by using a subquery
    empty_conversation = db.session.query(Conversation).outerjoin(
        Message, Conversation.id == Message.conversation_id
    ).filter(
        Conversation.user_id == current_user.id,
        Message.id.is_(None)  # No messages
    ).order_by(Conversation.created_at.desc()).first()

    if empty_conversation:
        # Found an empty conversation, reuse it
        return jsonify({'id': empty_conversation.id})

    # No empty conversation found, create a new one
    new_conversation = Conversation(user_id=current_user.id)
    db.session.add(new_conversation)
    db.session.commit()
    return jsonify({'id': new_conversation.id})

@app.route('/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get conversations for current user - OPTIMIZED with single SQL query and preview"""
    from sqlalchemy import func

    # Subquery to get LAST user message ID for each conversation (for preview)
    last_msg_subquery = db.session.query(
        Message.conversation_id,
        func.max(Message.id).label('last_msg_id')
    ).filter(
        Message.sender == 'user'
    ).group_by(Message.conversation_id).subquery()

    # Single query: Get all conversations with their last user message in ONE query
    conversations_with_msgs = db.session.query(
        Conversation.id,
        Conversation.title,
        Conversation.agent_type,
        Conversation.created_at,
        Message.content
    ).outerjoin(
        last_msg_subquery,
        Conversation.id == last_msg_subquery.c.conversation_id
    ).outerjoin(
        Message,
        Message.id == last_msg_subquery.c.last_msg_id
    ).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.created_at.desc()).all()

    result = []
    for conv_id, conv_title, agent_type, created_at, last_msg_content in conversations_with_msgs:
        # Generate preview from last message
        preview = None
        if last_msg_content:
            try:
                content = json.loads(last_msg_content)
                if isinstance(content, dict) and 'value' in content:
                    preview = content['value']
                else:
                    preview = str(content)
            except:
                preview = last_msg_content

            # Truncate to 60 characters
            if preview and len(preview) > 60:
                preview = preview[:60] + '...'

        # Use preview for title if no title exists
        if not conv_title and preview:
            words = preview.split()
            title = ' '.join(words[:4]) + '...' if len(words) > 4 else preview
        else:
            title = conv_title or f"Conversation {conv_id}"

        result.append({
            'id': conv_id,
            'title': title,
            'preview': preview or title,
            'agent_type': agent_type,
            'created_at': created_at.isoformat()
        })

    return jsonify({'conversations': result})

@app.route('/conversations', methods=['POST'])
@login_required
def new_conversation():
    """Create or reuse an empty conversation for the user - OPTIMIZED"""
    # Use efficient SQL query to find empty conversations (same as /conversations/fresh)
    empty_conversation = db.session.query(Conversation).outerjoin(
        Message, Conversation.id == Message.conversation_id
    ).filter(
        Conversation.user_id == current_user.id,
        Message.id.is_(None)  # No messages
    ).order_by(Conversation.created_at.desc()).first()

    if empty_conversation:
        # Found an empty conversation, reuse it
        return jsonify({'id': empty_conversation.id})

    # No empty conversation found, create a new one
    c = Conversation(user_id=current_user.id)
    db.session.add(c)
    db.session.commit()
    return jsonify({'id': c.id})

@app.route('/conversations/<int:conv_id>', methods=['GET'])
@login_required
def get_conversation(conv_id):
    # Get conversation and validate user access
    try:
        conversation = db.session.get(Conversation, conv_id)
        if not conversation or conversation.user_id != current_user.id:
            return jsonify({'error': 'Conversation not found or access denied'}), 404
    except Exception as e:
        memory_logger.error(f"Database error accessing conversation {conv_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Database connection error'}), 500

    # Get limit from query parameters (default: all messages, max: 500)
    limit = request.args.get('limit', type=int)
    if limit and limit > 500:
        limit = 500

    # Get messages ordered by timestamp to ensure proper chronological order
    query = Message.query.filter_by(conversation_id=conv_id).order_by(Message.timestamp.asc())

    if limit:
        # Get the most recent N messages
        total_count = query.count()
        if total_count > limit:
            # Skip older messages, keep only recent ones
            query = query.offset(total_count - limit)

    messages = query.all()

    return jsonify({
        'messages': [
            {
                'id': m.id,
                'sender': m.sender,
                'content': m.content,
                'timestamp': m.timestamp.isoformat(),
                'agent_type': conversation.agent_type  # Include agent type from conversation
            } for m in messages
        ],
        'total_count': Message.query.filter_by(conversation_id=conv_id).count(),
        'returned_count': len(messages)
    })

@app.route('/conversations/<int:conv_id>', methods=['DELETE'])
@login_required
def delete_conversation(conv_id):
    # Ensure user can only delete their own conversations
    c = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not c:
        return jsonify({'error': 'Conversation not found or access denied'}), 404
    
    # Clear conversation memory from the agents
    try:
        # Market agent uses OpenAI Agents SDK - no in-memory state to clear
        pass
    except Exception as e:
        memory_logger.error(f"Error clearing conversation memory: {e}")
    
    try:
        if news_agent:
            news_agent.clear_conversation_memory(conversation_id=str(conv_id))
    except Exception as e:
        memory_logger.error(f"Error clearing news agent memory: {e}")

    try:
        if leo_om_agent:
            leo_om_agent.clear_conversation_memory(conversation_id=str(conv_id))
    except Exception as e:
        memory_logger.error(f"Error clearing Leo O&M agent memory: {e}")
    
    Message.query.filter_by(conversation_id=conv_id).delete()
    db.session.delete(c)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/conversations/<int:conv_id>/debug', methods=['GET'])
@login_required
def debug_conversation(conv_id):
    # Ensure user can only debug their own conversations
    conversation = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not conversation:
        return jsonify({'error': 'Conversation not found or access denied'}), 404
    
    # Get messages ordered by timestamp to ensure proper chronological order
    ordered_messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.timestamp.asc()).all()
    
    # Get all messages with their content
    messages = []
    for msg in ordered_messages:
        try:
            content = json.loads(msg.content)
            messages.append({
                'id': msg.id,
                'sender': msg.sender,
                'timestamp': msg.timestamp.isoformat(),
                'content': content,
                'raw_content': msg.content
            })
        except (json.JSONDecodeError, TypeError) as e:
            memory_logger.warning(f"Error parsing message content (id={msg.id}): {e}")
            messages.append({
                'id': msg.id,
                'sender': msg.sender,
                'timestamp': msg.timestamp.isoformat(),
                'content': 'Error parsing content',
                'raw_content': msg.content
            })
    
    # Get the conversation history that would be used by the agent
    history = []
    for msg in ordered_messages:
        try:
            content = json.loads(msg.content)
            if content.get('type') == 'string':
                history.append(content['value'])
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            memory_logger.debug(f"Skipping message in history (id={msg.id}): {e}")
            continue
    
    return jsonify({
        'conversation_id': conversation.id,
        'title': conversation.title,
        'created_at': conversation.created_at.isoformat(),
        'messages': messages,
        'agent_history': history[-5:] if history else []  # Show last 5 messages that would be used by agent
    })

def clean_nan_values(obj):
    """Recursively clean NaN values from nested dictionaries and lists"""
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    else:
        return obj

def convert_datetime_columns_to_str(df):
    if not isinstance(df, pd.DataFrame):
        return df
    # Convert datetime columns to string
    for col in df.select_dtypes(include=['datetime', 'datetimetz']):
        df[col] = df[col].dt.strftime('%Y-%m-%d')
    # Replace NaN values with None (which becomes null in JSON)
    df = df.where(pd.notnull(df), None)
    return df

@app.route('/chat', methods=['POST'])
@login_required
@limiter.exempt  # Temporarily disable rate limiting to fix 429 errors
def chat():
    # Logfire span for chat request
    with logfire.span("chat_request") as span:
        span.set_attribute("user_id", current_user.id)
        span.set_attribute("agent_type", request.json.get('agent_type', 'market'))
        
        # Log memory usage at start of request
        log_memory_usage("Chat request start")
    
    data = request.json
    user_message = data.get('message', '')

    # ✅ SECURITY FIX: Input validation
    # Trim whitespace and ignore empty messages to prevent agents from processing empty queries
    if not user_message or not user_message.strip():
        return jsonify({'error': 'Empty message'}), 400

    # Validate message length to prevent abuse and memory issues
    MAX_MESSAGE_LENGTH = 5000  # Reasonable limit for chat messages
    if len(user_message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            'error': f'Message too long. Maximum length is {MAX_MESSAGE_LENGTH} characters. Your message is {len(user_message)} characters.'
        }), 400

    conv_id = data.get('conversation_id')
    agent_type = data.get('agent_type', 'market')
    
    if not conv_id:
        return jsonify({'error': 'conversation_id required'}), 400
    
    # Get conversation and validate user access
    try:
        conversation = db.session.get(Conversation, conv_id)
        if not conversation or conversation.user_id != current_user.id:
            return jsonify({'error': 'Conversation not found or access denied'}), 404
    except Exception as e:
        memory_logger.error(f"Database error accessing conversation {conv_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Database connection error'}), 500
    
    # Update conversation agent type if changed
    if conversation.agent_type != agent_type:
        conversation.agent_type = agent_type
        db.session.commit()

    # Check if user can make a query based on their plan limits
    # Admins: unlimited, Free: 10/month, Premium: 1000/month
    if not current_user.can_make_query():
        queries_used = current_user.monthly_query_count
        query_limit = current_user.get_query_limit()
        plan_type = current_user.plan_type
        return jsonify({
            'error': f'Query limit reached. You have used {queries_used}/{query_limit} queries this month.',
            'plan_type': plan_type,
            'queries_used': queries_used,
            'query_limit': query_limit if query_limit != float('inf') else 'unlimited',
            'upgrade_required': plan_type == 'free'
        }), 429  # 429 Too Many Requests

    # Increment query count BEFORE processing to prevent free queries on failure
    # This ensures proper billing even if the query processing fails
    try:
        current_user.increment_query_count()
        db.session.commit()
        memory_logger.info(f"Query count incremented for user {current_user.id}: {current_user.monthly_query_count}/{current_user.get_query_limit()}")
    except Exception as e:
        memory_logger.error(f"Error incrementing query count: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to track query usage. Please try again.'}), 500

    # Check memory before processing
    mem_info = get_memory_usage()
    if mem_info and mem_info['rss_mb'] > 400:  # Increased from 300MB to 400MB
        # Perform cleanup if memory usage is high
        memory_logger.warning(f"High memory usage detected ({mem_info['rss_mb']:.1f}MB), performing cleanup")
        cleanup_memory()
    
        # Check again after cleanup
        mem_info_after = get_memory_usage()
        if mem_info_after and mem_info_after['rss_mb'] > 500:  # Increased from 400MB to 500MB
            memory_logger.critical(f"Memory usage still high after cleanup ({mem_info_after['rss_mb']:.1f}MB)")
            # Force additional cleanup
            cleanup_memory()
    
    try:
        # Store user message
        try:
            user_msg = Message(conversation_id=conv_id, sender='user', content=json.dumps({
                "type": "string",
                "value": user_message,
                "comment": None
            }))
            db.session.add(user_msg)
            db.session.commit()
        except Exception as e:
            memory_logger.error(f"Database error storing user message: {e}")
            db.session.rollback()
            return jsonify({'error': 'Database error storing message'}), 500
        
        # Log memory before agent call
        log_memory_usage("Before agent call")
        
        # Handle different agent types directly
        try:
            if agent_type == "price":
                # Logfire span for price agent
                with logfire.span("price_agent_call") as agent_span:
                    agent_span.set_attribute("agent_type", "price")
                    agent_span.set_attribute("conversation_id", str(conv_id))
                    agent_span.set_attribute("message_length", len(user_message))
                    
                    # Add detailed LLM interaction tracking
                    with logfire.span("llm_interaction") as llm_span:
                        llm_span.set_attribute("model", "gpt-4o")  # or whatever model you're using
                        llm_span.set_attribute("user_message", user_message)
                        llm_span.set_attribute("agent_type", "price")
                        
                        # Use the global singleton instance
                        price_agent = module_prices_agent

                        # ✅ IMPROVED: Use asyncio.run() instead of manual event loop
                        # This properly handles loop creation and cleanup automatically
                        import asyncio
                        result = asyncio.run(price_agent.analyze(user_message, conversation_id=str(conv_id)))

                        if result["success"]:
                            analysis_output = result["analysis"]
                            agent_span.set_attribute("success", True)

                            # Log the response based on type
                            if hasattr(analysis_output, 'content'):
                                llm_span.set_attribute("assistant_response", analysis_output.content)
                                llm_span.set_attribute("response_length", len(analysis_output.content))
                                memory_logger.info(f"Module Prices Agent response: {analysis_output.content}")
                            elif isinstance(analysis_output, str):
                                llm_span.set_attribute("assistant_response", analysis_output)
                                llm_span.set_attribute("response_length", len(analysis_output))
                                memory_logger.info(f"Module Prices Agent response: {analysis_output}")
                            else:
                                llm_span.set_attribute("assistant_response", str(analysis_output))
                                memory_logger.info(f"Module Prices Agent response: {str(analysis_output)}")
                        else:
                            analysis_output = f"Error analyzing prices: {result['error']}"
                            agent_span.set_attribute("success", False)
                            agent_span.set_attribute("error", result['error'])
                            llm_span.set_attribute("error", result['error'])
                            memory_logger.info(f"Module Prices Agent error: {analysis_output}")
            
                # Handle structured output from the analyze method
                if result["success"]:
                    output = analysis_output
                    
                    # Check if it's a PlotResult
                    if hasattr(output, 'plot_type') and hasattr(output, 'url_path'):
                        if output.success:
                            # Include the description from PlotResult if available
                            description = getattr(output, 'description', '')
                            response_data = [{
                                'type': 'chart',
                                'value': description,
                                'artifact': output.url_path,
                                'comment': None
                            }]
                        else:
                            response_data = [{
                                'type': 'string',
                                'value': f"Error generating plot: {output.error_message}",
                                'comment': None
                            }]
                    
                    # Check if it's a DataAnalysisResult
                    elif hasattr(output, 'result_type') and hasattr(output, 'content'):
                        memory_logger.info(f"🔍 DataAnalysisResult detected - result_type: {output.result_type}, has_dataframe_data: {hasattr(output, 'dataframe_data')}, dataframe_data_len: {len(output.dataframe_data) if hasattr(output, 'dataframe_data') and output.dataframe_data else 0}")

                        if output.result_type == "dataframe" and output.dataframe_data:
                            # Use the original summary from the agent (same as what agent sees)
                            response_data = [{
                                'type': 'table',
                                'value': output.content,  # Original long summary
                                'table_data': output.dataframe_data,
                                'full_data': output.dataframe_data,
                                'comment': None
                            }]
                            memory_logger.info(f"✅ Created table response with {len(output.dataframe_data)} rows")
                        else:
                            # Text response
                            response_data = [{
                                'type': 'string',
                                'value': output.content,
                                'comment': None
                            }]
                            memory_logger.info(f"⚠️ Falling back to string response - result_type: {output.result_type}, dataframe_data: {output.dataframe_data if hasattr(output, 'dataframe_data') else 'N/A'}")

                    # Check if it's a MultiResult (multiple plots/data)
                    elif hasattr(output, 'primary_result_type') and hasattr(output, 'plots'):
                        response_data = []
                        
                        # Add meaningful data results (only tables, not redundant text)
                        for data_result in output.data_results:
                            if data_result.result_type == "dataframe" and data_result.dataframe_data:
                                response_data.append({
                                    'type': 'table',
                                    'value': data_result.content,
                                    'table_data': data_result.dataframe_data,
                                    'full_data': data_result.dataframe_data,
                                    'comment': None
                                })
                            # Skip text-only data results that are just error messages
                        
                        # Add all plots with summary as description
                        for plot in output.plots:
                            if plot.success:
                                # Use the overall summary as the plot description instead of individual plot description
                                description = output.summary if output.summary else (plot.description or plot.title)
                                response_data.append({
                                    'type': 'chart',
                                    'value': description,
                                    'artifact': plot.url_path,
                                    'comment': None
                                })
                        
                        # If no meaningful results, show the summary as text
                        if not response_data and output.summary:
                            response_data = [{
                                'type': 'string',
                                'value': output.summary,
                                'comment': None
                            }]
                    
                    # Check if it's a PlotDataResult (D3/JSON plot data)
                    elif hasattr(output, 'plot_type') and hasattr(output, 'data') and isinstance(output.data, list):
                        if output.success:
                            response_data = [{
                                'type': 'interactive_chart',
                                'value': output.title,
                                'plot_data': {
                                    'plot_type': output.plot_type,
                                    'title': output.title,
                                    'x_axis_label': output.x_axis_label,
                                    'y_axis_label': output.y_axis_label,
                                    'unit': output.unit,
                                    'data': output.data,
                                    'series_info': output.series_info
                                },
                                'comment': None
                            }]
                        else:
                            response_data = [{
                                'type': 'string',
                                'value': f"Error generating interactive chart: {output.error_message}",
                                'comment': None
                            }]
                    
                    # Check if output is a string (most common case now - natural responses)
                    elif isinstance(output, str):
                        # Regular natural language response from the agent
                        response_data = [{
                            'type': 'string',
                            'value': output,
                            'comment': None
                        }]
                    
                    # Fallback if output structure is unexpected
                    else:
                        response_data = [{
                            'type': 'string',
                            'value': str(output),
                            'comment': None
                        }]
                
                # Handle error case
                else:
                    response_data = [{
                        'type': 'string',
                        'value': analysis_output,  # This will be the error message
                        'comment': None
                    }]
                
                # Continue with memory cleanup only if needed
                if response_data and response_data[0].get('type') == 'chart':
                    # Only cleanup if memory usage is high
                    mem_info = get_memory_usage()
                    if mem_info and mem_info['rss_mb'] > 450:
                        cleanup_memory()
                
                # Store bot response
                try:
                    for resp in response_data:
                        cleaned_resp = clean_nan_values(resp)
                        bot_msg = Message(conversation_id=conv_id, sender='bot', content=json.dumps(cleaned_resp))
                        db.session.add(bot_msg)
                    db.session.commit()
                except Exception as e:
                    memory_logger.error(f"Database error storing bot messages: {e}")
                    db.session.rollback()
                    
                # Log memory after agent call
                log_memory_usage("After agent call")

                # Only monitor memory usage, don't automatically cleanup
                monitor_memory_usage()

                # Query count already incremented before processing (line 1477)

                return jsonify({'response': response_data})
            
            elif agent_type == "news":
                # News agent with streaming support
                # Logfire tracking in main thread context
                with logfire.span("news_agent_stream") as agent_span:
                    agent_span.set_attribute("agent_type", "news")
                    agent_span.set_attribute("conversation_id", str(conv_id))
                    agent_span.set_attribute("message_length", len(user_message))

                    # Add nested llm_interaction span for Logfire UI
                    with logfire.span("llm_interaction") as llm_span:
                        llm_span.set_attribute("model", "gpt-4o")
                        llm_span.set_attribute("user_message", user_message)
                        llm_span.set_attribute("agent_type", "news")

                        # Capture user_id before entering generator context
                        user_id = current_user.id

                        def generate_streaming_response():
                            """Generator function for Server-Sent Events streaming"""
                            import asyncio

                            async def stream_agent():
                                try:
                                    full_response = ""
                                    news_ag = news_agent

                                    # Stream text chunks as they arrive
                                    async for chunk in news_ag.analyze_stream(user_message, conversation_id=str(conv_id)):
                                        full_response += chunk
                                        # Send chunk as SSE event
                                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                                    # Save the complete response to database BEFORE sending done event
                                    try:
                                        # Use application context for database operations
                                        with app.app_context():
                                            try:
                                                bot_msg = Message(
                                                    conversation_id=conv_id,
                                                    sender='bot',
                                                    content=json.dumps({
                                                        'type': 'string',
                                                        'value': full_response,
                                                        'comment': None
                                                    })
                                                )
                                                db.session.add(bot_msg)
                                                db.session.commit()
                                                memory_logger.info(f"News agent message saved to database: {len(full_response)} chars")
                                            except Exception as db_error:
                                                memory_logger.error(f"Error saving news agent message to database: {db_error}")
                                                db.session.rollback()
                                                raise
                                            finally:
                                                # Explicitly close session to prevent leaks
                                                db.session.close()
                                    except Exception as outer_error:
                                        memory_logger.error(f"Failed to save message: {outer_error}")

                                    # Query count already incremented before processing (line 1477)

                                    # Send completion event (after saving)
                                    yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"

                                    # Log complete interaction to Logfire
                                    logfire.info(
                                        "news_complete_interaction",
                                        agent_type="news",
                                        model="gpt-4o",
                                        conversation_id=str(conv_id),
                                        user_message=user_message,
                                        assistant_response=full_response,
                                        response_length=len(full_response)
                                    )

                                    # Log success
                                    memory_logger.info(f"News agent streaming completed: {len(full_response)} chars")

                                except Exception as e:
                                    error_msg = f"Streaming error: {str(e)}"
                                    memory_logger.error(error_msg)
                                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

                            # Run the async generator with proper cleanup
                            loop = asyncio.new_event_loop()
                            try:
                                asyncio.set_event_loop(loop)
                                async_gen = stream_agent()
                                while True:
                                    try:
                                        chunk = loop.run_until_complete(async_gen.__anext__())
                                        yield chunk
                                    except StopAsyncIteration:
                                        break
                            finally:
                                # Clear global event loop reference to prevent pollution
                                asyncio.set_event_loop(None)
                                # Ensure loop is properly closed
                                try:
                                    loop.close()
                                except Exception as e:
                                    memory_logger.error(f"Error closing event loop: {e}")

                        # Return streaming response with HTTP/2 compatible headers
                        return Response(
                            generate_streaming_response(),
                            mimetype='text/event-stream',
                            headers={
                                'Cache-Control': 'no-cache, no-transform',
                                'X-Accel-Buffering': 'no',  # For Nginx
                                'Connection': 'keep-alive',  # Keep connection alive
                                'Content-Type': 'text/event-stream; charset=utf-8',
                                'X-Content-Type-Options': 'nosniff'
                            }
                        )
            
            elif agent_type == "om":
                # Logfire span for Leo O&M agent
                with logfire.span("leo_om_agent_call") as agent_span:
                    agent_span.set_attribute("agent_type", "om")
                    agent_span.set_attribute("conversation_id", str(conv_id))
                    agent_span.set_attribute("message_length", len(user_message))

                    # Add detailed LLM interaction tracking
                    with logfire.span("llm_interaction") as llm_span:
                        llm_span.set_attribute("model", "gpt-4o")
                        llm_span.set_attribute("user_message", user_message)
                        llm_span.set_attribute("agent_type", "om")

                        # Use the global Leo O&M agent instance
                        # ✅ IMPROVED: Use asyncio.run() instead of manual event loop
                        import asyncio
                        result = asyncio.run(leo_om_agent.analyze(user_message, conversation_id=str(conv_id)))

                        if result["success"]:
                            analysis_output = result["analysis"]
                            agent_span.set_attribute("success", True)

                            # Log the response
                            llm_span.set_attribute("assistant_response", analysis_output)
                            llm_span.set_attribute("response_length", len(analysis_output))
                            llm_span.set_attribute("category", result.get("category", "general"))
                            memory_logger.info(f"Leo O&M Agent response: {analysis_output}")
                        else:
                            analysis_output = f"Error analyzing O&M query: {result['error']}"
                            agent_span.set_attribute("success", False)
                            agent_span.set_attribute("error", result['error'])
                            llm_span.set_attribute("error", result['error'])
                            memory_logger.info(f"Leo O&M Agent error: {analysis_output}")

                # Simple string response for O&M analysis
                response_data = [{
                    'type': 'string',
                    'value': analysis_output,
                    'comment': None
                }]

            elif agent_type == "digitalization":
                # Digitalization agent with STREAMING support
                # Logfire tracking in main thread context
                with logfire.span("digitalization_agent_stream") as agent_span:
                    agent_span.set_attribute("agent_type", "digitalization")
                    agent_span.set_attribute("conversation_id", str(conv_id))
                    agent_span.set_attribute("message_length", len(user_message))

                    # Add nested llm_interaction span for Logfire UI
                    with logfire.span("llm_interaction") as llm_span:
                        llm_span.set_attribute("model", "gpt-4o")
                        llm_span.set_attribute("user_message", user_message)
                        llm_span.set_attribute("agent_type", "digitalization")

                        # Capture user_id before entering generator context
                        user_id = current_user.id

                        def generate_streaming_response():
                            """Generator function for Server-Sent Events streaming"""
                            import asyncio

                            async def stream_agent():
                                try:
                                    full_response = ""
                                    digi_agent = digitalization_agent

                                    # Stream text chunks as they arrive
                                    async for chunk in digi_agent.analyze_stream(user_message, conversation_id=str(conv_id)):
                                        full_response += chunk
                                        # Send chunk as SSE event
                                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                                    # Save the complete response to database BEFORE sending done event
                                    try:
                                        # Use application context for database operations
                                        with app.app_context():
                                            try:
                                                bot_msg = Message(
                                                    conversation_id=conv_id,
                                                    sender='bot',
                                                    content=json.dumps({
                                                        'type': 'string',
                                                        'value': full_response,
                                                        'comment': None
                                                    })
                                                )
                                                db.session.add(bot_msg)
                                                db.session.commit()
                                                memory_logger.info(f"Digitalization agent message saved to database: {len(full_response)} chars")
                                            except Exception as db_error:
                                                memory_logger.error(f"Error saving digitalization agent message to database: {db_error}")
                                                db.session.rollback()
                                                raise
                                            finally:
                                                # Explicitly close session to prevent leaks
                                                db.session.close()
                                    except Exception as outer_error:
                                        memory_logger.error(f"Failed to save message: {outer_error}")

                                    # Query count already incremented before processing (line 1477)

                                    # Send completion event (after saving)
                                    yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"

                                    # Log complete interaction to Logfire
                                    logfire.info(
                                        "digitalization_complete_interaction",
                                        agent_type="digitalization",
                                        model="gpt-4o",
                                        conversation_id=str(conv_id),
                                        user_message=user_message,
                                        assistant_response=full_response,
                                        response_length=len(full_response)
                                    )

                                except Exception as e:
                                    error_msg = f"Streaming error: {str(e)}"
                                    memory_logger.error(error_msg)
                                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

                            # Run async generator in sync context with proper cleanup
                            loop = asyncio.new_event_loop()
                            try:
                                asyncio.set_event_loop(loop)
                                async_gen = stream_agent()
                                while True:
                                    try:
                                        chunk = loop.run_until_complete(async_gen.__anext__())
                                        yield chunk
                                    except StopAsyncIteration:
                                        break
                            finally:
                                # Clear global event loop reference to prevent pollution
                                asyncio.set_event_loop(None)
                                # Ensure loop is properly closed
                                try:
                                    loop.close()
                                except Exception as e:
                                    memory_logger.error(f"Error closing event loop: {e}")

                        # Return SSE response with HTTP/2 compatible headers
                        return Response(
                            generate_streaming_response(),
                            mimetype='text/event-stream',
                            headers={
                                'Cache-Control': 'no-cache, no-transform',
                                'X-Accel-Buffering': 'no',  # For Nginx
                                'Connection': 'keep-alive',  # Keep connection alive
                                'Content-Type': 'text/event-stream; charset=utf-8',
                                'X-Content-Type-Options': 'nosniff'
                            }
                        )

            elif agent_type == "market":
                # Market agent with STREAMING support (upgraded to use Market Intelligence implementation)
                # Logfire tracking in main thread context
                with logfire.span("market_agent_stream") as agent_span:
                    agent_span.set_attribute("agent_type", "market")
                    agent_span.set_attribute("conversation_id", str(conv_id))
                    agent_span.set_attribute("message_length", len(user_message))

                    # Add nested llm_interaction span for Logfire UI
                    with logfire.span("llm_interaction") as llm_span:
                        llm_span.set_attribute("model", "gpt-5")
                        llm_span.set_attribute("user_message", user_message)
                        llm_span.set_attribute("agent_type", "market")

                        # Capture user_id before entering generator context
                        user_id = current_user.id

                        def generate_streaming_response():
                            """Generator function for Server-Sent Events streaming"""
                            import asyncio

                            async def stream_agent():
                                try:
                                    full_response = ""
                                    plot_data = None
                                    response_type = "text"
                                    mi_agent = market_intelligence_agent

                                    if not mi_agent:
                                        error_msg = "Market Intelligence agent not available"
                                        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                                        return

                                    # Stream response using analyze_stream method
                                    # Send initial processing message to keep AWS load balancer connection alive
                                    yield f"data: {json.dumps({'type': 'processing', 'message': 'Analyzing your query...'})}\n\n"

                                    async for chunk in mi_agent.analyze_stream(user_message, conversation_id=str(conv_id)):
                                        # Check if chunk is JSON (plot data)
                                        try:
                                            response_json = json.loads(chunk)
                                            # It's a plot - verify it's a dictionary
                                            if isinstance(response_json, dict):
                                                event_type = response_json.get('type')

                                                # Handle new streaming format
                                                if event_type == 'plot':
                                                    # Plot JSON from plotting agent
                                                    response_type = "plot"
                                                    plot_data = response_json['content']
                                                    full_response = f"Generated plot: {plot_data.get('title', 'Untitled')}"

                                                    # Log plot details for debugging
                                                    memory_logger.info(f"📊 PLOT GENERATED:")
                                                    memory_logger.info(f"  - Type: {plot_data.get('plot_type')}")
                                                    memory_logger.info(f"  - Title: {plot_data.get('title')}")
                                                    memory_logger.info(f"  - Stack By: {plot_data.get('stack_by')}")
                                                    if 'filters_applied' in plot_data:
                                                        memory_logger.info(f"  - Filters: {json.dumps(plot_data['filters_applied'], indent=4)}")
                                                    if 'data' in plot_data:
                                                        memory_logger.info(f"  - Data Points: {len(plot_data['data'])}")
                                                        # Log first 3 data points for inspection
                                                        for i, dp in enumerate(plot_data['data'][:3]):
                                                            memory_logger.info(f"    Data[{i}]: {json.dumps(dp, indent=6)}")

                                                    # Send plot JSON for D3 rendering
                                                    yield f"data: {json.dumps({'type': 'plot', 'content': plot_data})}\n\n"

                                                elif 'plot_type' in response_json:
                                                    # Legacy format - direct plot JSON (backward compatibility)
                                                    response_type = "plot"
                                                    plot_data = response_json
                                                    full_response = f"Generated plot: {plot_data.get('title', 'Untitled')}"

                                                    # Log plot details for debugging
                                                    memory_logger.info(f"📊 PLOT GENERATED (legacy format):")
                                                    memory_logger.info(f"  - Type: {plot_data.get('plot_type')}")
                                                    memory_logger.info(f"  - Title: {plot_data.get('title')}")
                                                    memory_logger.info(f"  - Stack By: {plot_data.get('stack_by')}")
                                                    if 'filters_applied' in plot_data:
                                                        memory_logger.info(f"  - Filters: {json.dumps(plot_data['filters_applied'], indent=4)}")
                                                    if 'data' in plot_data:
                                                        memory_logger.info(f"  - Data Points: {len(plot_data['data'])}")
                                                        # Log first 3 data points for inspection
                                                        for i, dp in enumerate(plot_data['data'][:3]):
                                                            memory_logger.info(f"    Data[{i}]: {json.dumps(dp, indent=6)}")

                                                    yield f"data: {json.dumps({'type': 'plot', 'content': plot_data})}\n\n"

                                                else:
                                                    # JSON but not a plot - treat as text
                                                    full_response += str(response_json)
                                                    yield f"data: {json.dumps({'type': 'chunk', 'content': str(response_json)})}\n\n"
                                            else:
                                                # JSON but not a dict - treat as text
                                                full_response += str(chunk)
                                                yield f"data: {json.dumps({'type': 'chunk', 'content': str(chunk)})}\n\n"
                                        except (json.JSONDecodeError, ValueError):
                                            # It's a text chunk - stream it immediately
                                            if chunk:
                                                full_response += chunk
                                                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                                    # Save the complete response to database BEFORE sending done event
                                    try:
                                        # Use application context for database operations
                                        with app.app_context():
                                            try:
                                                # Store plot data as JSON if it's a plot, otherwise store text
                                                content_to_save = {
                                                    'type': 'plot' if response_type == "plot" else 'string',
                                                    'value': plot_data if response_type == "plot" else full_response
                                                }

                                                bot_msg = Message(
                                                    conversation_id=conv_id,
                                                    sender='bot',
                                                    content=json.dumps(content_to_save)
                                                )
                                                db.session.add(bot_msg)
                                                db.session.commit()
                                                memory_logger.info(f"Market Intelligence agent message saved to database: type={response_type}")
                                            except Exception as db_error:
                                                memory_logger.error(f"Error saving market intelligence agent message to database: {db_error}")
                                                db.session.rollback()
                                                raise
                                            finally:
                                                # Explicitly close session to prevent leaks
                                                db.session.close()
                                    except Exception as outer_error:
                                        memory_logger.error(f"Failed to save message: {outer_error}")

                                    # Query count already incremented before processing (line 1477)

                                    # Send completion event (after saving)
                                    if response_type == "plot":
                                        yield f"data: {json.dumps({'type': 'done', 'response_type': 'plot', 'plot_data': plot_data})}\n\n"
                                    else:
                                        yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"

                                    # Log complete interaction to Logfire
                                    logfire.info(
                                        "market_complete_interaction",
                                        agent_type="market",
                                        model="gpt-5",
                                        conversation_id=str(conv_id),
                                        user_message=user_message,
                                        assistant_response=full_response,
                                        response_length=len(full_response),
                                        response_type=response_type
                                    )

                                except Exception as e:
                                    error_msg = f"Streaming error: {str(e)}"
                                    memory_logger.error(error_msg)
                                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

                            # Run async generator in sync context with proper cleanup
                            loop = asyncio.new_event_loop()
                            try:
                                asyncio.set_event_loop(loop)
                                async_gen = stream_agent()
                                while True:
                                    try:
                                        chunk = loop.run_until_complete(async_gen.__anext__())
                                        yield chunk
                                    except StopAsyncIteration:
                                        break
                            finally:
                                # Clear global event loop reference to prevent pollution
                                asyncio.set_event_loop(None)
                                # Ensure loop is properly closed
                                try:
                                    loop.close()
                                except Exception as e:
                                    memory_logger.error(f"Error closing event loop: {e}")

                        # Return SSE response with HTTP/2 compatible headers
                        return Response(
                            generate_streaming_response(),
                            mimetype='text/event-stream',
                            headers={
                                'Cache-Control': 'no-cache, no-transform',
                                'X-Accel-Buffering': 'no',  # For Nginx
                                'Connection': 'keep-alive',  # Keep connection alive
                                'Content-Type': 'text/event-stream; charset=utf-8',
                                'X-Content-Type-Options': 'nosniff'
                            }
                        )

            else:
                # Unknown agent type
                return jsonify({'error': f'Unknown agent type: {agent_type}'}), 400
        
        except Exception as e:
            memory_logger.error(f"Error in agent processing: {e}")
            return jsonify({'error': f'Agent error: {str(e)}'}), 500
        
    except Exception as e:
        memory_logger.error(f"Error in chat endpoint: {e}")
        # Only cleanup if memory usage is high
        mem_info = get_memory_usage()
        if mem_info and mem_info['rss_mb'] > 450:
            cleanup_memory()
        # Log memory after error cleanup
        log_memory_usage("After error cleanup")
        return jsonify({'error': 'An error occurred processing your request'}), 500

@app.route('/guide')
@login_required
def get_guide():
    try:
        with open('docs/pv-market-analysis-user-guide.md', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error loading guide: {str(e)}", 500

@app.route('/random-news')
@login_required
def random_news():
    if not NEWS_LIST:
        return jsonify({}), 404
    news = random.choice(NEWS_LIST)
    return jsonify({
        "title": news.get("title", ""),
        "description": news.get("description", ""),
        "url": news.get("url", "")
    })

# Legacy file serving routes removed - application now uses D3.js for client-side rendering

@app.route('/download-table-data', methods=['POST'])
@login_required
def download_table_data():
    """Download table data as CSV"""
    try:
        data = request.json
        table_data = data.get('table_data')
        filename = data.get('filename', 'table_data.csv')
        
        if not table_data:
            return jsonify({'error': 'No table data provided'}), 400
        
        # Convert JSON data back to DataFrame
        import pandas as pd
        df = pd.DataFrame(table_data)
        
        # Create CSV content
        csv_content = df.to_csv(index=False)
        
        # Return CSV as response
        from io import StringIO
        output = StringIO()
        output.write(csv_content)
        output.seek(0)
        
        from flask import Response
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        memory_logger.error(f"Error generating CSV download: {e}")
        return jsonify({'error': 'Failed to generate CSV'}), 500

@app.route('/generate-ppt', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def generate_ppt():
    """Generate PowerPoint presentation from selected messages"""
    try:
        import tempfile
        import os
        from flask import send_file
        from ppt_gen import create_powerpoint_from_json_all_plots
        
        data = request.json
        if not data or 'items' not in data:
            return jsonify({'error': 'No conversation data provided'}), 400
        
        # Filter for plot items only
        plot_items = [item for item in data['items'] if item.get('type') == 'plot']
        if not plot_items:
            return jsonify({'error': 'No plots found in selected messages'}), 400
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_json:
            # Prepare data in the format expected by ppt_gen.py
            ppt_data = {
                'conversation_id': data.get('conversation_id'),
                'export_timestamp': data.get('export_timestamp'),
                'total_messages': len(plot_items),
                'total_downloaded_files': 0,
                'export_note': f'{len(plot_items)} plot(s) for PPT generation',
                'items': plot_items
            }
            
            json.dump(ppt_data, temp_json, indent=2)
            temp_json_path = temp_json.name
        
        # Create temporary output file
        temp_ppt_path = tempfile.mktemp(suffix='.pptx')
        
        try:
            # Check if template exists
            template_path = 'template.pptx'
            if not os.path.exists(template_path):
                return jsonify({'error': 'PowerPoint template not found'}), 500
            
            # Generate PowerPoint
            result_path = create_powerpoint_from_json_all_plots(
                template_path=template_path,
                json_file_path=temp_json_path,
                output_path=temp_ppt_path
            )
            
            if not os.path.exists(result_path):
                return jsonify({'error': 'Failed to generate PowerPoint file'}), 500
            
            # Generate filename
            conversation_id = data.get('conversation_id', 'export')
            timestamp = datetime.now().strftime('%Y-%m-%d')
            filename = f'presentation_{conversation_id}_{timestamp}.pptx'
            
            # Log the generation
            memory_logger.info(f"PPT generated by user {current_user.username}: {filename} with {len(plot_items)} plots")
            
            # Return the file
            return send_file(
                result_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )
            
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_json_path):
                    os.unlink(temp_json_path)
                if os.path.exists(temp_ppt_path):
                    os.unlink(temp_ppt_path)
            except Exception as cleanup_error:
                memory_logger.warning(f"Failed to cleanup temp files: {cleanup_error}")
        
    except ImportError as e:
        memory_logger.error(f"PPT generation import error: {e}")
        return jsonify({'error': 'PowerPoint generation dependencies not available'}), 500
    except Exception as e:
        memory_logger.error(f"PPT generation error: {e}")
        return jsonify({'error': f'PPT generation failed: {str(e)}'}), 500

@app.route('/submit-feedback', methods=['POST'])
@login_required
@limiter.limit("10 per hour")
def submit_feedback():
    """Handle user feedback submissions"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data or 'rating' not in data:
            return jsonify({'error': 'Rating is required'}), 400

        rating = data.get('rating')
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400

        # Create feedback record
        feedback = Feedback(
            user_id=current_user.id if current_user.is_authenticated else None,
            rating=rating,
            feedback_text=data.get('feedback_text', ''),
            allow_followup=data.get('allow_followup', False),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:256]
        )

        db.session.add(feedback)
        db.session.commit()

        memory_logger.info(f"Feedback submitted: user_id={current_user.id}, rating={rating}")

        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!'
        }), 200

    except Exception as e:
        db.session.rollback()
        memory_logger.error(f"Error submitting feedback: {e}")
        return jsonify({'error': 'Failed to submit feedback'}), 500


@app.route('/submit-user-survey', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def submit_user_survey():
    """Handle user profiling survey submission (FIRST survey - Simple) and grant 5 extra queries"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['role', 'regions', 'familiarity', 'insights']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({'error': f'{field} is required'}), 400

        # Check if user has already submitted this survey
        existing_survey = UserSurvey.query.filter_by(user_id=current_user.id).first()
        if existing_survey:
            return jsonify({
                'success': False,
                'message': 'You have already completed the survey and received your bonus queries.'
            }), 400

        # Create survey record
        import json
        survey = UserSurvey(
            user_id=current_user.id,
            role=data.get('role'),
            role_other=data.get('role_other'),
            regions=json.dumps(data.get('regions')),
            familiarity=data.get('familiarity'),
            insights=json.dumps(data.get('insights')),
            tailored=data.get('tailored'),
            bonus_queries_granted=5
        )

        db.session.add(survey)
        db.session.commit()

        # Calculate new query count (the get_query_limit() method now includes survey bonuses)
        new_query_limit = current_user.get_query_limit()
        new_query_count = new_query_limit - current_user.monthly_query_count

        memory_logger.info(f"User survey submitted: user_id={current_user.id}, bonus_queries=5, new_limit={new_query_limit}")

        return jsonify({
            'success': True,
            'message': 'Survey completed! 5 extra queries unlocked.',
            'new_query_count': int(new_query_count) if new_query_count != float('inf') else 'unlimited',
            'new_query_limit': int(new_query_limit) if new_query_limit != float('inf') else 'unlimited'
        }), 200

    except Exception as e:
        db.session.rollback()
        memory_logger.error(f"Error submitting user survey: {e}")
        return jsonify({'error': 'Failed to submit survey'}), 500


@app.route('/submit-user-survey-stage2', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def submit_user_survey_stage2():
    """Handle Stage 2 survey submission (Market Activity & Behaviour) - SECOND survey (Advanced) - and grant 5 extra queries"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['work_focus', 'pv_segments', 'technologies', 'challenges']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({'error': f'{field} is required'}), 400

        # Check if user has completed Stage 1 (User Profiling) first - this is now required
        stage1_survey = UserSurvey.query.filter_by(user_id=current_user.id).first()
        if not stage1_survey:
            return jsonify({
                'success': False,
                'message': 'Please complete the User Profiling survey before accessing this survey.'
            }), 400

        # Check if user has already submitted Stage 2 survey
        existing_survey = UserSurveyStage2.query.filter_by(user_id=current_user.id).first()
        if existing_survey:
            return jsonify({
                'success': False,
                'message': 'You have already completed the Stage 2 survey and received your bonus queries.'
            }), 400

        # Validate challenges (must be exactly 3 or allow less)
        challenges = data.get('challenges', [])
        if len(challenges) > 3:
            return jsonify({'error': 'Please select a maximum of 3 challenges'}), 400

        # Create Stage 2 survey record
        import json
        survey = UserSurveyStage2(
            user_id=current_user.id,
            work_focus=data.get('work_focus'),
            work_focus_other=data.get('work_focus_other'),
            pv_segments=json.dumps(data.get('pv_segments')),
            technologies=json.dumps(data.get('technologies')),
            technologies_other=data.get('technologies_other'),
            challenges=json.dumps(challenges),
            weekly_insight=data.get('weekly_insight'),
            bonus_queries_granted=5
        )

        db.session.add(survey)
        db.session.commit()

        # Calculate new query count (the get_query_limit() method now includes survey bonuses)
        new_query_limit = current_user.get_query_limit()
        new_query_count = new_query_limit - current_user.monthly_query_count

        memory_logger.info(f"User Stage 2 survey submitted: user_id={current_user.id}, bonus_queries=5, new_limit={new_query_limit}")

        return jsonify({
            'success': True,
            'message': 'Stage 2 survey completed! 5 extra queries unlocked.',
            'new_query_count': int(new_query_count) if new_query_count != float('inf') else 'unlimited',
            'new_query_limit': int(new_query_limit) if new_query_limit != float('inf') else 'unlimited'
        }), 200

    except Exception as e:
        db.session.rollback()
        memory_logger.error(f"Error submitting Stage 2 survey: {e}")
        return jsonify({'error': 'Failed to submit survey'}), 500


@app.route('/check-survey-status', methods=['GET'])
@login_required
def check_survey_status():
    """Check which surveys the user has completed"""
    try:
        stage1_completed = UserSurvey.query.filter_by(user_id=current_user.id).first() is not None
        stage2_completed = UserSurveyStage2.query.filter_by(user_id=current_user.id).first() is not None

        return jsonify({
            'stage1_completed': stage1_completed,
            'stage2_completed': stage2_completed
        }), 200

    except Exception as e:
        memory_logger.error(f"Error checking survey status: {e}")
        return jsonify({'error': 'Failed to check survey status'}), 500


@app.route('/admin/users')
@login_required
@limiter.limit("100 per hour")
def admin_users():
    """Admin interface for user management"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    users = User.query.all()
    pending_users = User.query.filter_by(is_active=False).all()
    active_users = User.query.filter_by(is_active=True).all()

    return render_template('admin_users.html',
                         users=users,
                         pending_users=pending_users,
                         active_users=active_users)

@app.route('/admin/users/pending')
@login_required
@limiter.limit("100 per hour")
def admin_pending_users():
    """View pending user approvals"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    pending_users = User.query.filter_by(is_active=False).order_by(User.created_at.desc()).all()
    return render_template('admin_pending_users.html', pending_users=pending_users)

@app.route('/admin/users/<int:user_id>/approve', methods=['POST'])
@login_required
@limiter.limit("50 per hour")  # ✅ SECURITY FIX: Rate limit admin actions
def admin_approve_user(user_id):
    """Approve a pending user account"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    user = User.query.get_or_404(user_id)
    
    try:
        user.is_active = True
        db.session.commit()
        return jsonify({'success': True, 'message': f'User {user.full_name} approved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to approve user: {str(e)}'})

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per hour")
def admin_create_user():
    """Create new user"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        full_name = data.get('full_name')
        role = data.get('role', 'demo')
        
        # Validate input
        if not username or not password or not full_name:
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': 'Username already exists'})
        
        # Create new user
        try:
            new_user = User(
                username=username,
                full_name=full_name,
                role=role,
                is_active=True
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'User created successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Failed to create user: {str(e)}'})
    
    return render_template('admin_create_user.html')

@app.route('/admin/users/<int:user_id>/update', methods=['POST'])
@login_required
@limiter.limit("50 per hour")  # ✅ SECURITY FIX: Rate limit admin actions
def admin_update_user(user_id):
    """Update user information"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    try:
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'User updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to update user: {str(e)}'})

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@limiter.limit("20 per hour")  # ✅ SECURITY FIX: Rate limit dangerous admin actions
def admin_delete_user(user_id):
    """Delete user"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot delete your own account'})
    
    try:
        # Use explicit transaction with proper error handling
        # Delete in correct order: messages -> conversations -> user

        # Get all conversation IDs for this user (for efficient bulk delete)
        conversation_ids = [c.id for c in user.conversations.all()]

        if conversation_ids:
            # Bulk delete all messages for user's conversations
            # Using synchronize_session=False for better performance in bulk operations
            Message.query.filter(Message.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)

        # Delete all conversations for this user
        Conversation.query.filter_by(user_id=user.id).delete(synchronize_session=False)

        # Delete related records (feedback, surveys, hired agents)
        Feedback.query.filter_by(user_id=user.id).delete(synchronize_session=False)

        # Check for user surveys (might not exist)
        from sqlalchemy import exc
        try:
            db.session.execute(db.text('DELETE FROM user_survey WHERE user_id = :uid'), {'uid': user.id})
            db.session.execute(db.text('DELETE FROM user_survey_stage2 WHERE user_id = :uid'), {'uid': user.id})
        except exc.OperationalError:
            # Tables might not exist, that's okay
            pass

        HiredAgent.query.filter_by(user_id=user.id).delete(synchronize_session=False)

        # Finally, delete the user
        db.session.delete(user)

        # Commit all changes in single transaction
        db.session.commit()

        memory_logger.info(f"Admin user {current_user.id} deleted user {user.id} ({user.username})")
        return jsonify({'success': True, 'message': 'User deleted successfully'})

    except exc.IntegrityError as e:
        db.session.rollback()
        memory_logger.error(f"Integrity error deleting user {user_id}: {e}")
        return jsonify({'success': False, 'error': 'Cannot delete user due to database constraints'}), 409
    except Exception as e:
        db.session.rollback()
        memory_logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({'success': False, 'error': f'Failed to delete user: {str(e)}'}), 500

@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@limiter.limit("50 per hour")  # ✅ SECURITY FIX: Rate limit admin actions
def admin_toggle_user(user_id):
    """Toggle user active status"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deactivating themselves
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot deactivate your own account'})
    
    try:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        return jsonify({'success': True, 'message': f'User {status} successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to update user: {str(e)}'})

@app.route('/admin/cleanup-empty-conversations', methods=['POST'])
@login_required
def admin_cleanup_empty_conversations():
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Find conversations with no messages
        empty_conversations = db.session.query(Conversation).outerjoin(Message).filter(Message.id == None).all()
        count = len(empty_conversations)
        
        # Delete empty conversations
        for conv in empty_conversations:
            db.session.delete(conv)
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Cleaned up {count} empty conversations'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/memory-status')
@login_required
@limiter.limit("100 per hour")  # ✅ SECURITY FIX: Rate limit admin routes
def admin_memory_status():
    """Get current memory status (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        mem_info = get_memory_usage()
        if not mem_info:
            return jsonify({'error': 'Could not retrieve memory information'}), 500
        
        # Add additional system information
        process = psutil.Process()
        mem_info.update({
            'num_threads': process.num_threads(),
            'open_files': len(process.open_files()),
            'cpu_percent': process.cpu_percent(),
            'uptime_seconds': (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds()
        })
        
        return jsonify({
            'success': True,
            'memory_info': mem_info,
            'status': 'critical' if mem_info['rss_mb'] > 500 else 'warning' if mem_info['rss_mb'] > 400 else 'normal'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/memory-cleanup', methods=['POST'])
@login_required
def admin_memory_cleanup():
    """Force memory cleanup (admin only)"""
    # Logfire span for admin memory cleanup
    with logfire.span("admin_memory_cleanup") as span:
        span.set_attribute("user_id", current_user.id)
        span.set_attribute("user_role", current_user.role)
        
        if current_user.role != 'admin':
            span.set_attribute("success", False)
            span.set_attribute("error", "Access denied")
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            # Get memory usage before cleanup
            mem_before = get_memory_usage()
            span.set_attribute("memory_before_mb", mem_before['rss_mb'] if mem_before else 0)
            
            # Perform cleanup
            success = cleanup_memory()
            span.set_attribute("cleanup_success", success)
            
            # Get memory usage after cleanup
            mem_after = get_memory_usage()
            span.set_attribute("memory_after_mb", mem_after['rss_mb'] if mem_after else 0)
            
            if success and mem_before and mem_after:
                memory_freed = mem_before['rss_mb'] - mem_after['rss_mb']
                span.set_attribute("memory_freed_mb", memory_freed)
                span.set_attribute("success", True)
                return jsonify({
                    'success': True,
                    'message': f'Memory cleanup completed. Freed {memory_freed:.1f}MB',
                    'memory_before_mb': mem_before['rss_mb'],
                    'memory_after_mb': mem_after['rss_mb'],
                    'memory_freed_mb': memory_freed
                })
            else:
                span.set_attribute("success", False)
                span.set_attribute("error", "Could not measure memory results")
                return jsonify({
                    'success': success,
                    'message': 'Memory cleanup attempted but could not measure results'
                })
        except Exception as e:
            span.set_attribute("success", False)
            span.set_attribute("error", str(e))
            return jsonify({'error': str(e)}), 500

@app.route('/admin/conversation-memory-info')
@login_required
def admin_conversation_memory_info():
    """
    DEPRECATED: Get conversation memory information (admin only)

    This endpoint is deprecated as the market agent now uses OpenAI Agents SDK
    with SQLite-based session storage instead of in-memory conversation tracking.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'success': False,
        'error': 'Endpoint deprecated - Market agent uses OpenAI Agents SDK with SQLite sessions (no in-memory state)'
    }), 410  # 410 Gone - indicates the resource is no longer available

@app.route('/admin/debug-memory/<conversation_id>')
@login_required
def admin_debug_memory(conversation_id):
    """
    DEPRECATED: Debug specific conversation memory content (admin only)

    This endpoint is deprecated as the market agent now uses OpenAI Agents SDK
    with SQLite-based session storage instead of in-memory conversation tracking.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'error': 'Endpoint deprecated - Market agent uses OpenAI Agents SDK with SQLite sessions (no in-memory state)'
    }), 410  # 410 Gone - indicates the resource is no longer available

@app.route('/admin/clear-conversation-memory', methods=['POST'])
@login_required
def admin_clear_conversation_memory():
    """Clear conversation memory (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id')  # Optional - if None, clears all
        
        success = clear_conversation_memory(conversation_id)
        
        if success:
            if conversation_id:
                message = f"Cleared conversation memory for conversation {conversation_id}"
            else:
                message = "Cleared all conversation memory"
            
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to clear conversation memory'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memory-status')
def memory_status():
    """Get current memory status (public endpoint)"""
    try:
        mem_info = get_memory_usage()
        if not mem_info:
            return jsonify({'error': 'Could not retrieve memory information'}), 500
        
        return jsonify({
            'success': True,
            'memory_mb': mem_info['rss_mb'],
            'memory_percent': mem_info['memory_percent'],
            'available_gb': mem_info['available_memory_gb'],
            'status': 'critical' if mem_info['rss_mb'] > 500 else 'warning' if mem_info['rss_mb'] > 400 else 'normal',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memory-cleanup', methods=['POST'])
def memory_cleanup():
    """Trigger memory cleanup (public endpoint)"""
    try:
        # Get memory usage before cleanup
        mem_before = get_memory_usage()
        
        # Perform cleanup
        success = cleanup_memory()
        
        # Get memory usage after cleanup
        mem_after = get_memory_usage()
        
        if success and mem_before and mem_after:
            memory_freed = mem_before['rss_mb'] - mem_after['rss_mb']
            return jsonify({
                'success': True,
                'message': f'Memory cleanup completed. Freed {memory_freed:.1f}MB',
                'memory_before_mb': mem_before['rss_mb'],
                'memory_after_mb': mem_after['rss_mb'],
                'memory_freed_mb': memory_freed
            })
        else:
            return jsonify({
                'success': success,
                'message': 'Memory cleanup attempted but could not measure results'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/force-memory-cleanup', methods=['POST'])
def force_memory_cleanup_endpoint():
    """Force immediate memory cleanup (public endpoint)"""
    try:
        # Get memory usage before cleanup
        mem_before = get_memory_usage()
        
        # Perform force cleanup
        success = force_memory_cleanup()
        
        # Get memory usage after cleanup
        mem_after = get_memory_usage()
        
        if success and mem_before and mem_after:
            memory_freed = mem_before['rss_mb'] - mem_after['rss_mb']
            return jsonify({
                'success': True,
                'message': f'Force memory cleanup completed. Freed {memory_freed:.1f}MB',
                'memory_before_mb': mem_before['rss_mb'],
                'memory_after_mb': mem_after['rss_mb'],
                'memory_freed_mb': memory_freed
            })
        else:
            return jsonify({
                'success': success,
                'message': 'Force memory cleanup attempted but could not measure results'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memory-monitor')
def memory_monitor():
    """Get detailed memory monitoring information"""
    try:
        mem_info = monitor_memory_usage()
        if mem_info:
            return jsonify({
                'success': True,
                'memory_info': mem_info,
                'status': 'critical' if mem_info['rss_mb'] > 400 else 'warning' if mem_info['rss_mb'] > 300 else 'normal',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({'error': 'Could not retrieve memory information'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats')
def get_stats():
    """Basic usage statistics"""
    try:
        total_conversations = Conversation.query.count()
        total_messages = Message.query.count()
        recent_conversations = Conversation.query.filter(
            Conversation.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return jsonify({
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'conversations_24h': recent_conversations,
            'status': 'active'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/database-health')
def database_health():
    """Get database health status"""
    try:
        health_info = check_database_health()
        return jsonify({
            'success': True,
            'database': health_info,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Database connection health check
def check_database_connection():
    """Check if database connection is healthy and attempt to reconnect if needed"""
    try:
        # Simple query to test connection
        db.session.execute(text("SELECT 1"))
        db.session.commit()
        return True
    except Exception as e:
        memory_logger.error(f"Database connection check failed: {e}")
        try:
            # Attempt to rollback and reconnect
            db.session.rollback()
            db.session.close()
            # Force a new connection
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            memory_logger.info("Database connection restored")
            return True
        except Exception as e2:
            memory_logger.error(f"Failed to restore database connection: {e2}")
            return False

def check_database_health():
    """Check database health and connection status"""
    try:
        # Test basic connection
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        # Get database info
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            # PostgreSQL specific checks
            result = db.session.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            
            # Get table counts
            user_count = db.session.execute(text('SELECT COUNT(*) FROM "user"')).fetchone()[0]
            conv_count = db.session.execute(text('SELECT COUNT(*) FROM conversation')).fetchone()[0]
            msg_count = db.session.execute(text('SELECT COUNT(*) FROM message')).fetchone()[0]
            
            return {
                'status': 'healthy',
                'type': 'postgresql',
                'version': version,
                'tables': {
                    'users': user_count,
                    'conversations': conv_count,
                    'messages': msg_count
                }
            }
        else:
            # SQLite specific checks
            user_count = db.session.execute(text('SELECT COUNT(*) FROM "user"')).fetchone()[0]
            conv_count = db.session.execute(text('SELECT COUNT(*) FROM conversation')).fetchone()[0]
            msg_count = db.session.execute(text('SELECT COUNT(*) FROM message')).fetchone()[0]
            
            return {
                'status': 'healthy',
                'type': 'sqlite',
                'tables': {
                    'users': user_count,
                    'conversations': conv_count,
                    'messages': msg_count
                }
            }
            
    except Exception as e:
        memory_logger.error(f"Database health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'type': 'unknown'
        }

# CSRF exemptions for routes that don't need CSRF protection
try:
    csrf.exempt(app.view_functions['get_fresh_conversation'])
    csrf.exempt(app.view_functions['get_conversations'])
    csrf.exempt(app.view_functions['get_conversation'])
    csrf.exempt(app.view_functions['delete_conversation'])
    csrf.exempt(app.view_functions['chat.approval_response'])
    print("✅ CSRF exemptions applied successfully")
except KeyError as e:
    print(f"⚠️  Warning: Could not exempt route {e} from CSRF protection")

@app.route('/test-logfire')
def test_logfire():
    """Test endpoint to verify detailed Logfire spans"""
    with logfire.span("test_detailed_span") as span:
        span.set_attribute("test_type", "detailed_llm_interaction")
        span.set_attribute("user_message", "Test message for Logfire")
        
        # Simulate LLM interaction
        with logfire.span("llm_interaction") as llm_span:
            llm_span.set_attribute("model", "gpt-4o")
            llm_span.set_attribute("user_message", "Test message for Logfire")
            llm_span.set_attribute("assistant_response", "This is a test response from the LLM")
            llm_span.set_attribute("response_length", 45)
            llm_span.set_attribute("token_count", 15)
            llm_span.set_attribute("cost_usd", 0.0001)
        
        return jsonify({
            'status': 'success',
            'message': 'Test spans created - check Logfire dashboard',
            'timestamp': datetime.utcnow().isoformat()
        })

# =============================================================================
# GDPR & European Market Compliance Routes
# =============================================================================

@app.route('/privacy-policy')
def privacy_policy():
    """Privacy Policy page - GDPR compliant"""
    return render_template('privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    """Terms of Service page - EU legal compliance"""
    return render_template('terms_of_service.html')

@app.route('/gdpr/export-data', methods=['GET', 'POST'])
@login_required
def export_user_data():
    """Export all user data in JSON format - GDPR Article 20 (Right to Data Portability)"""
    try:
        user_id = current_user.id

        # Collect all user data
        user_data = {
            'account_info': {
                'id': current_user.id,
                'username': current_user.username,
                'full_name': current_user.full_name,
                'role': current_user.role,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
                'is_active': current_user.is_active
            },
            'conversations': [],
            'export_metadata': {
                'export_date': datetime.utcnow().isoformat(),
                'export_version': '1.0',
                'data_format': 'JSON',
                'gdpr_article': 'Article 20 - Right to Data Portability'
            }
        }

        # ✅ PERFORMANCE FIX: Get all conversations with messages in one query (avoid N+1)
        from sqlalchemy.orm import joinedload
        conversations = Conversation.query.options(
            joinedload(Conversation.messages)
        ).filter_by(user_id=user_id).all()

        for conv in conversations:
            # Messages are already loaded via joinedload (no additional query)
            messages = sorted(conv.messages, key=lambda m: m.timestamp if m.timestamp else datetime.min)

            conversation_data = {
                'conversation_id': conv.id,
                'title': conv.title,
                'agent_type': conv.agent_type,
                'created_at': conv.created_at.isoformat() if conv.created_at else None,
                'messages': []
            }

            for msg in messages:
                message_data = {
                    'id': msg.id,
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None
                }
                conversation_data['messages'].append(message_data)

            user_data['conversations'].append(conversation_data)

        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"solar_intelligence_data_export_{current_user.username}_{timestamp}.json"

        # Log the data export for compliance
        memory_logger.info(f"GDPR data export requested by user {current_user.username} (ID: {user_id})")

        # Return as downloadable file
        response = jsonify(user_data)
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Type'] = 'application/json'

        return response

    except Exception as e:
        memory_logger.error(f"Error exporting user data for user {current_user.id}: {e}")
        return jsonify({'error': 'Failed to export data'}), 500

@app.route('/gdpr/request-deletion', methods=['GET', 'POST'])
@login_required
def request_account_deletion():
    """Request account deletion - GDPR Article 17 (Right to Erasure)

    Uses soft delete with 30-day grace period:
    - Account is marked as deleted immediately
    - User has 30 days to cancel the deletion
    - After 30 days, account is permanently deleted by cleanup job
    """
    if request.method == 'GET':
        # Check if user already has a pending deletion
        if current_user.deleted:
            days_remaining = 30 - (datetime.utcnow() - current_user.deletion_requested_at).days
            from datetime import timedelta
            permanent_deletion_date = current_user.deletion_requested_at + timedelta(days=30)
            return render_template('request_deletion.html',
                                   already_deleted=True,
                                   days_remaining=max(0, days_remaining),
                                   deletion_date=current_user.deletion_requested_at,
                                   permanent_deletion_date=permanent_deletion_date)
        return render_template('request_deletion.html', already_deleted=False)

    try:
        user_id = current_user.id
        username = current_user.username

        # Get optional deletion reason from form
        deletion_reason = request.form.get('deletion_reason', '')

        # Log the deletion request for compliance
        memory_logger.info(f"GDPR soft delete requested by user {username} (ID: {user_id})")

        # Mark account as deleted (soft delete)
        current_user.deleted = True
        current_user.deletion_requested_at = datetime.utcnow()
        current_user.deletion_reason = deletion_reason
        current_user.is_active = False  # Prevent login during grace period

        db.session.commit()

        # Log the completed soft delete
        memory_logger.info(f"GDPR soft delete completed for user {username} (ID: {user_id}). Grace period: 30 days")

        # Logout the user
        logout_user()

        flash('Your account deletion has been scheduled. You have 30 days to cancel if you change your mind. Check your email for instructions.', 'success')
        return redirect(url_for('landing'))

    except Exception as e:
        db.session.rollback()
        memory_logger.error(f"Error marking user account for deletion {current_user.id}: {e}")
        flash('An error occurred while processing your deletion request. Please contact support.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/gdpr/cancel-deletion', methods=['POST'])
def cancel_account_deletion():
    """Cancel account deletion during 30-day grace period

    This endpoint allows users to restore their account if they change their mind
    within 30 days of requesting deletion. Can be accessed via email link with token.
    """
    try:
        # Get user identifier (could be from token in production)
        user_id = request.form.get('user_id')
        token = request.form.get('token')  # For future email-based recovery

        if not user_id:
            flash('Invalid cancellation request.', 'error')
            return redirect(url_for('landing'))

        user = User.query.get(int(user_id))

        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('landing'))

        # Check if account is marked for deletion
        if not user.deleted:
            flash('Your account is not scheduled for deletion.', 'info')
            return redirect(url_for('landing'))

        # Check if grace period has expired
        days_elapsed = (datetime.utcnow() - user.deletion_requested_at).days
        if days_elapsed >= 30:
            flash('The 30-day grace period has expired. Your account cannot be restored.', 'error')
            return redirect(url_for('landing'))

        # Restore the account
        user.deleted = False
        user.deletion_requested_at = None
        user.deletion_reason = None
        user.is_active = True

        db.session.commit()

        # Log the cancellation for compliance
        memory_logger.info(f"GDPR deletion cancelled by user {user.username} (ID: {user.id}). Account restored.")

        flash('Your account has been successfully restored! You can now log in.', 'success')
        return redirect(url_for('login'))

    except Exception as e:
        db.session.rollback()
        memory_logger.error(f"Error cancelling account deletion: {e}")
        flash('An error occurred while restoring your account. Please contact support.', 'error')
        return redirect(url_for('landing'))

@app.route('/cookie-consent/revoke', methods=['POST'])
def revoke_cookie_consent():
    """Revoke cookie consent - for cookie management"""
    user_id = current_user.id if current_user.is_authenticated else 'anonymous'
    memory_logger.info(f"Cookie consent revoked by user {user_id}")
    return jsonify({'status': 'success', 'message': 'Cookie consent revoked'})

if __name__ == '__main__':
    # Development server configuration
    try:
        with app.app_context():
            # Test database connection at startup
            if check_database_connection():
                memory_logger.info("SUCCESS: Database connection verified at startup")
            else:
                memory_logger.error("ERROR: Database connection failed at startup")
                
            # Initialize database
            migrate_database()
            
            # Create predefined users
            create_predefined_users()
            
        # Run the development server
        app.run(
            host='0.0.0.0', 
            port=int(os.environ.get('PORT', 10000)), 
            debug=False  # Disable debug mode for production-like behavior
        )
    except Exception as e:
        memory_logger.error(f"Application startup failed: {e}")
        raise 