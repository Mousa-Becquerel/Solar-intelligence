import os
import sys
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from pydantic_weaviate_agent import get_pydantic_weaviate_agent, close_pydantic_weaviate_agent
import base64
import pandas as pd
import json
import math
import random
from dotenv import load_dotenv
import uuid
import threading
import psutil
import gc
import logging
from sqlalchemy import text

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
load_dotenv()

# Configure logging for memory monitoring
memory_logger = logging.getLogger('memory_monitor')
memory_logger.setLevel(logging.INFO)

# Configure logging handler with UTF-8 encoding
if not memory_logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
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
    """Log current memory usage"""
    mem_info = get_memory_usage()
    if mem_info:
        memory_logger.info(f"{context} - RSS: {mem_info['rss_mb']:.1f}MB, "
                          f"VMS: {mem_info['vms_mb']:.1f}MB, "
                          f"Memory%: {mem_info['memory_percent']:.1f}%, "
                          f"Available: {mem_info['available_memory_gb']:.1f}GB")
        
        # Alert if memory usage is getting high
        if mem_info['rss_mb'] > 400:
            memory_logger.warning(f"HIGH MEMORY USAGE: {mem_info['rss_mb']:.1f}MB RSS")
        
        if mem_info['rss_mb'] > 500:
            memory_logger.critical(f"CRITICAL MEMORY USAGE: {mem_info['rss_mb']:.1f}MB RSS")
    
    return mem_info

def cleanup_memory():
    """Perform memory cleanup operations while preserving conversation memory and agent instance"""
    try:
        # Don't close the agent completely - just clean up system resources
        # close_pydantic_weaviate_agent()  # REMOVED - this was clearing conversation memory
        
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
        
        memory_logger.info(f"Garbage collection completed: {collected} objects collected")
        
        # Log memory usage after cleanup
        log_memory_usage("After memory cleanup")
        
        return True
    except Exception as e:
        memory_logger.error(f"Error during memory cleanup: {e}")
        return False

def clear_conversation_memory(conversation_id: str = None):
    """Clear conversation memory for specific conversation or all conversations"""
    try:
        from pydantic_weaviate_agent import get_pydantic_weaviate_agent
        agent = get_pydantic_weaviate_agent()
        if agent:
            agent.clear_conversation_memory(conversation_id)
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
            memory_logger.info(f"Periodic cleanup triggered at {mem_info['rss_mb']:.1f}MB")
            cleanup_memory()
            return True
        return False
    except Exception as e:
        memory_logger.error(f"Error in periodic cleanup: {e}")
        return False

def force_memory_cleanup():
    """Force immediate memory cleanup regardless of current usage"""
    try:
        memory_logger.info("Forcing immediate memory cleanup")
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
        collected = gc.collect()
        memory_logger.info(f"Force cleanup completed: {collected} objects collected")
        
        return True
    except Exception as e:
        memory_logger.error(f"Error in force cleanup: {e}")
        return False

def monitor_memory_usage():
    """Monitor memory usage and log detailed information"""
    try:
        mem_info = get_memory_usage()
        if mem_info:
            memory_logger.info(f"Memory Monitor - RSS: {mem_info['rss_mb']:.1f}MB, "
                              f"VMS: {mem_info['vms_mb']:.1f}MB, "
                              f"Memory%: {mem_info['memory_percent']:.1f}%, "
                              f"Available: {mem_info['available_memory_gb']:.1f}GB")
            
            # Alert if memory usage is getting high
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

app = Flask(__name__, static_folder='static', static_url_path='/static')

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
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-in-production')

# Enhanced PostgreSQL configuration for Render
if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'BecqSight'
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
login_manager.login_message = 'Please log in to access BecqSight.'
login_manager.login_message_category = 'info'

# Create static directory for plots if it doesn't exist
PLOTS_DIR = os.path.join('static', 'plots')
os.makedirs(PLOTS_DIR, exist_ok=True)

# Create exports directory for charts if it doesn't exist
EXPORTS_DIR = os.path.join('exports', 'charts')
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Thread-safe chart generation lock
chart_lock = threading.Lock()

db = SQLAlchemy(app)

# User model for authentication
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    agent_type = db.Column(db.String(16), default='market')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Link to user
    messages = db.relationship('Message', backref='conversation', lazy=True)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('conversations', lazy=True))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender = db.Column(db.String(16))  # 'user' or 'bot'
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Predefined users - Add your users here
# WARNING: Change these default passwords immediately after deployment in production!
PREDEFINED_USERS = [
    {
        'username': 'admin',
        'password': 'BecqSight2024!',
        'full_name': 'Administrator',
        'role': 'admin'
    },
    {
        'username': 'analyst',
        'password': 'PVMarket2024',
        'full_name': 'Market Analyst',
        'role': 'analyst'
    },
    {
        'username': 'researcher',
        'password': 'Research2024',
        'full_name': 'Research Team',
        'role': 'researcher'
    },
    {
        'username': 'demo',
        'password': 'demo123',
        'full_name': 'Demo User',
        'role': 'demo'
    }
]

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
            # For SQLite, use the existing logic
            try:
                # Simple check: try to query both tables
                db.session.execute(text('SELECT COUNT(*) FROM "user"'))
                db.session.execute(text('SELECT COUNT(*) FROM conversation'))
                db.session.execute(text('SELECT COUNT(*) FROM message'))
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
                    user = User(
                        username=user_data['username'],
                        password_hash=generate_password_hash(user_data['password']),
                        full_name=user_data['full_name'],
                        role=user_data['role']
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
        except:
            pass
        # Continue startup even if database init fails
        pass

# Load news once at startup
with open('zotero_news_full.json', encoding='utf-8') as f:
    NEWS_LIST = json.load(f)

# === GLOBAL SINGLETON FOR MODULE PRICES AGENT ===
from module_prices_agent import ModulePricesAgent, ModulePricesConfig
module_prices_agent = ModulePricesAgent(ModulePricesConfig(verbose=False))

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('home'))
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
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact an administrator.', 'error')
                    return render_template('login.html')
                
                login_user(user, remember=True)
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('home')
                return redirect(next_page)
            else:
                flash('Invalid username or password.', 'error')
        except Exception as e:
            memory_logger.error(f"Database error during login: {e}")
            db.session.rollback()
            flash('Database connection error. Please try again.', 'error')
    
    return render_template('login.html')

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

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/conversations/fresh', methods=['POST'])
@login_required
def get_fresh_conversation():
    """Get or create a fresh conversation for the user"""
    # Get all user conversations ordered by creation date (newest first)
    user_conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.created_at.desc()).all()
    
    empty_conversations = []
    for conv in user_conversations:
        # Check if conversation has no messages
        message_count = Message.query.filter_by(conversation_id=conv.id).count()
        if message_count == 0:
            empty_conversations.append(conv)
    
    # If we have empty conversations, use the most recent one
    if empty_conversations:
        # Keep the most recent empty conversation, delete the rest
        most_recent_empty = empty_conversations[0]
        
        # Delete older empty conversations (keep only the most recent)
        for conv in empty_conversations[1:]:
            db.session.delete(conv)
        
        db.session.commit()
        return jsonify({'id': most_recent_empty.id})
    
    # No empty conversation found, create a new one
    new_conversation = Conversation(user_id=current_user.id)
    db.session.add(new_conversation)
    db.session.commit()
    return jsonify({'id': new_conversation.id})

@app.route('/conversations', methods=['GET'])
@login_required
def get_conversations():
    # Only get conversations for the current user
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.created_at.desc()).all()
    def get_title(c):
        if c.title:
            return c.title
        if c.messages:
            # Find the last text-based message by iterating backwards
            for msg in reversed(c.messages):
                try:
                    content = json.loads(msg.content)
                    # Only use messages that have a string value
                    if content.get('type') == 'string' and content.get('value'):
                        value = str(content['value'])
                        words = value.split()
                        if len(words) > 4:
                            return ' '.join(words[:4]) + '...'
                        return value
                except Exception:
                    # If JSON parsing fails, try to use the raw content
                    if msg.content and not msg.content.startswith('{'):
                        return msg.content[:40]
            # If no suitable message found, use the conversation ID
            return f"Conversation {c.id}"
        return f"Conversation {c.id}"
    return jsonify([
        {
            'id': c.id,
            'title': get_title(c),
            'created_at': c.created_at.isoformat()
        } for c in conversations
    ])

@app.route('/conversations', methods=['POST'])
@login_required
def new_conversation():
    """Create or reuse an empty conversation for the user"""
    # Check if user already has an empty conversation
    user_conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.created_at.desc()).all()
    
    for conv in user_conversations:
        # Check if conversation has no messages
        message_count = Message.query.filter_by(conversation_id=conv.id).count()
        if message_count == 0:
            # Found an empty conversation, reuse it
            return jsonify({'id': conv.id})
    
    # No empty conversation found, create a new one
    c = Conversation(user_id=current_user.id)  # Assign to current user
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
    
    # Get messages ordered by timestamp to ensure proper chronological order
    messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.timestamp.asc()).all()
    
    return jsonify([
        {
            'id': m.id,
            'sender': m.sender,
            'content': m.content,
            'timestamp': m.timestamp.isoformat()
        } for m in messages
    ])

@app.route('/conversations/<int:conv_id>', methods=['DELETE'])
@login_required
def delete_conversation(conv_id):
    # Ensure user can only delete their own conversations
    c = Conversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not c:
        return jsonify({'error': 'Conversation not found or access denied'}), 404
    
    # Clear conversation memory from the agent
    try:
        pydantic_agent = get_pydantic_weaviate_agent()
        if pydantic_agent:
            pydantic_agent.clear_conversation_memory(conversation_id=str(conv_id))
    except Exception as e:
        memory_logger.error(f"Error clearing conversation memory: {e}")
    
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
        except:
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
        except:
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
def chat():
    # Log memory usage at start of request
    log_memory_usage("Chat request start")
    
    data = request.json
    user_message = data.get('message', '')
    # Trim whitespace and ignore empty messages to prevent agents from processing empty queries
    if not user_message or not user_message.strip():
        return jsonify({'error': 'Empty message'}), 400
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
                # Use the global singleton instance
                price_agent = module_prices_agent
                # Run async analysis
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(price_agent.analyze(user_message, conversation_id=str(conv_id)))
                    if result["success"]:
                        response_text = result["analysis"]
                    else:
                        response_text = f"Error analyzing prices: {result['error']}"
                    memory_logger.info(f"Module Prices Agent response: {response_text}")
                finally:
                    loop.close()
                
                # Parse response to handle different formats
                if response_text.startswith("DATAFRAME_RESULT|"):
                    # Parse DataFrame response: DATAFRAME_RESULT|text_response|display_data|full_data
                    try:
                        parts = response_text.split("|", 3)
                        if len(parts) >= 4:
                            text_response = parts[1]
                            display_json_data = parts[2]
                            full_json_data = parts[3]
                            
                            # Parse the JSON data
                            table_data = json.loads(display_json_data)
                            full_data = json.loads(full_json_data)
                            
                            # Create table response structure
                            response_data = [{
                                'type': 'table',
                                'value': text_response,
                                'table_data': table_data,
                                'full_data': full_data,
                                'comment': None
                            }]
                        else:
                            # Fallback to string if parsing fails
                            response_data = [{
                                'type': 'string',
                                'value': response_text,
                                'comment': None
                            }]
                    except Exception as e:
                        memory_logger.error(f"Error parsing DataFrame response: {e}")
                        # Fallback to string if JSON parsing fails
                        response_data = [{
                            'type': 'string',
                            'value': response_text,
                            'comment': None
                        }]
                elif response_text.startswith("PLOT_GENERATED|"):
                    # Parse plot response: PLOT_GENERATED|path|description
                    parts = response_text.split("|", 2)
                    if len(parts) >= 2:
                        plot_path = parts[1]
                        response_data = [{
                            'type': 'chart',
                            'value': '',  # Remove 'Generated chart' text
                            'artifact': plot_path,
                            'comment': None
                        }]
                    else:
                        # Fallback to string if parsing fails
                        response_data = [{
                            'type': 'string',
                            'value': response_text,
                            'comment': None
                        }]
                else:
                    # Regular text response
                    response_data = [{
                        'type': 'string',
                        'value': response_text,
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
                
                return jsonify({'response': response_data})
            
            else:
                # Use Market Analysis Agent (default)
                pydantic_agent = get_pydantic_weaviate_agent()
                if not pydantic_agent:
                    return jsonify({'error': 'Market Analysis agent not available'}), 400
                
                # Get structured response from the agent
                agent_result = pydantic_agent.process_query(user_message, conversation_id=str(conv_id))
                
                # Debug: Log response type and content
                memory_logger.info(f"Agent result type: {type(agent_result)}")
                memory_logger.info(f"Agent result: {str(agent_result)[:200]}...")
                
                # Handle structured output from Pydantic AI
                if hasattr(agent_result, 'output'):
                    # Extract the actual output from the agent result
                    output = agent_result.output
                    
                    # Check if it's a PlotResult
                    if hasattr(output, 'plot_type') and hasattr(output, 'url_path'):
                        if output.success:
                            response_data = [{
                                'type': 'chart',
                                'value': '',  # Remove 'Generated chart' text
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
                        if output.result_type == "dataframe" and output.dataframe_data:
                            # Create table response structure
                            response_data = [{
                                'type': 'table',
                                'value': output.content,
                                'table_data': output.dataframe_data,
                                'full_data': output.dataframe_data,
                                'comment': None
                            }]
                        else:
                            # Text response
                            response_data = [{
                                'type': 'string',
                                'value': output.content,
                                'comment': None
                            }]
                    
                    # Check if output is a string (most common case now - natural responses or PLOT_GENERATED)
                    elif isinstance(output, str):
                        # Parse string-based responses
                        if output.startswith("PLOT_GENERATED|"):
                            # Parse plot response: PLOT_GENERATED|path|description
                            parts = output.split("|", 2)
                            if len(parts) >= 2:
                                plot_path = parts[1]
                                response_data = [{
                                    'type': 'chart',
                                    'value': '',  # Remove 'Generated chart' text
                                    'artifact': plot_path,
                                    'comment': None
                                }]
                            else:
                                # Fallback to string if parsing fails
                                response_data = [{
                                    'type': 'string',
                                    'value': output,
                                    'comment': None
                                }]
                        else:
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
                
                # Fallback for old string-based responses (backward compatibility)
                elif isinstance(agent_result, str):
                    response_text = agent_result
                    memory_logger.info(f"Response format detection - starts with: {response_text[:50]}...")
                    
                    # Check if response contains a plot
                    if response_text.startswith("PLOT_GENERATED|"):
                        # Parse plot response: PLOT_GENERATED|path|description
                        parts = response_text.split("|", 2)
                        if len(parts) >= 3:
                            plot_path = parts[1]
                            description = parts[2]
                            
                            # Convert to web-accessible URL
                            web_path = f"/static/plots/{os.path.basename(plot_path)}"
                            
                            # Create chart response structure - ONLY this, no additional string response
                            response_data = [{
                                'type': 'chart',
                                'value': '',  # Remove 'Generated chart' text
                                'artifact': web_path,
                                'comment': None
                            }]
                        else:
                            # Fallback to string if parsing fails
                            response_data = [{
                                'type': 'string',
                                'value': response_text,
                                'comment': None
                            }]
                    elif response_text.startswith("DATAFRAME_RESULT|"):
                        # Parse DataFrame response: DATAFRAME_RESULT|text_response|display_data|full_data
                        try:
                            parts = response_text.split("|", 3)
                            if len(parts) >= 4:
                                text_response = parts[1]
                                display_json_data = parts[2]
                                full_json_data = parts[3]
                                
                                # Parse the JSON data
                                table_data = json.loads(display_json_data)
                                full_data = json.loads(full_json_data)
                                
                                # Create table response structure
                                response_data = [{
                                    'type': 'table',
                                    'value': text_response,
                                    'table_data': table_data,
                                    'full_data': full_data,  # Add full data for download
                                    'comment': None
                                }]
                            elif len(parts) >= 3:
                                # Fallback for old format
                                text_response = parts[1]
                                json_data = parts[2]
                                
                                # Parse the JSON data
                                table_data = json.loads(json_data)
                                
                                # Create table response structure
                                response_data = [{
                                    'type': 'table',
                                    'value': text_response,
                                    'table_data': table_data,
                                    'full_data': table_data,  # Use same data for download
                                    'comment': None
                                }]
                        except Exception as e:
                            memory_logger.error(f"Error parsing DataFrame response: {e}")
                            # Fallback to string if JSON parsing fails
                            response_data = [{
                                'type': 'string',
                                'value': response_text,
                                'comment': None
                            }]
                    else:
                        # Regular text response
                        response_data = [{
                            'type': 'string',
                            'value': response_text,
                            'comment': None
                        }]
                
                # Final fallback
                else:
                    response_data = [{
                        'type': 'string',
                        'value': str(agent_result),
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
            
            return jsonify({'response': response_data})
        
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
        with open('pv-market-analysis-user-guide.md', 'r', encoding='utf-8') as f:
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

@app.route('/static/plots/<path:filename>')
def serve_plot(filename):
    return send_file(os.path.join(PLOTS_DIR, filename))

# Add route to serve chart files
@app.route('/exports/charts/<path:filename>')
def serve_chart(filename):
    try:
        return send_from_directory(os.path.join(os.getcwd(), 'exports', 'charts'), filename)
    except Exception as e:
        print(f"Error serving chart file: {e}")
        return "File not found", 404

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

@app.route('/admin/users')
@login_required
def admin_users():
    """Admin interface for user management"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
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
def admin_delete_user(user_id):
    """Delete user"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot delete your own account'})
    
    try:
        # Delete user's messages through their conversations
        for conversation in user.conversations:
            Message.query.filter_by(conversation_id=conversation.id).delete()
        
        # Delete user's conversations
        Conversation.query.filter_by(user_id=user.id).delete()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to delete user: {str(e)}'})

@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
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
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
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

@app.route('/admin/conversation-memory-info')
@login_required
def admin_conversation_memory_info():
    """Get conversation memory information (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        pydantic_agent = get_pydantic_weaviate_agent()
        if pydantic_agent:
            memory_info = pydantic_agent.get_conversation_memory_info()
            return jsonify({
                'success': True,
                'conversation_memory': memory_info
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Pydantic-AI agent not available'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        db_status = check_database_connection()
        db_health = check_database_health()
        
        # Get memory usage
        memory_info = get_memory_usage()
        
        # Count active conversations
        try:
            conversation_count = Conversation.query.count()
            message_count = Message.query.count()
        except Exception as e:
            memory_logger.error(f"Error counting database records: {e}")
            conversation_count = "unknown"
            message_count = "unknown"
        
        health_data = {
            'status': 'healthy' if db_status else 'degraded',
            'database': {
                'connected': db_status,
                'health': db_health
            },
            'memory': memory_info,
            'stats': {
                'conversations': conversation_count,
                'messages': message_count
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        status_code = 200 if db_status else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        memory_logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

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