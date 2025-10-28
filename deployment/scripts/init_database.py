#!/usr/bin/env python3
"""
Database initialization script for Solar Intelligence platform on AWS.
This script sets up the database schema and creates initial users.
"""

import os
import sys
import secrets
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import db, User, Conversation, Message, app

def generate_secure_password(length=16):
    """Generate a secure random password."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def init_database():
    """Initialize the database with tables and admin user."""
    
    print("🔧 Initializing Solar Intelligence Database...")
    
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ ERROR: DATABASE_URL environment variable not set!")
            return False
            
        print(f"📊 Connecting to database...")
        
        with app.app_context():
            # Test database connection
            try:
                db.session.execute(text('SELECT 1'))
                db.session.commit()
                print("✅ Database connection successful")
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                return False
            
            # Create all tables
            print("📋 Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Create admin user with secure password
            admin_password = generate_secure_password(20)
            
            # Check if admin user already exists
            existing_admin = User.query.filter_by(username='admin').first()
            if existing_admin:
                print("⚠️  Admin user already exists - updating password")
                existing_admin.set_password(admin_password)
                db.session.commit()
            else:
                print("👤 Creating admin user...")
                admin_user = User(
                    username='admin',
                    full_name='System Administrator',
                    role='admin'
                )
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Admin user created successfully")
            
            # Print admin credentials (save these securely!)
            print("\n" + "="*60)
            print("🔐 ADMIN CREDENTIALS (SAVE THESE SECURELY!):")
            print("="*60)
            print(f"Username: admin")
            print(f"Password: {admin_password}")
            print("="*60)
            print("⚠️  IMPORTANT: Save these credentials in a secure location!")
            print("⚠️  Change the password after first login!")
            print("="*60 + "\n")
            
            return True
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def verify_database():
    """Verify database setup and health."""
    
    print("🔍 Verifying database setup...")
    
    try:
        with app.app_context():
            # Check table counts
            user_count = db.session.execute(text('SELECT COUNT(*) FROM "user"')).fetchone()[0]
            conv_count = db.session.execute(text('SELECT COUNT(*) FROM conversation')).fetchone()[0]
            msg_count = db.session.execute(text('SELECT COUNT(*) FROM message')).fetchone()[0]
            
            print(f"📊 Database Statistics:")
            print(f"   Users: {user_count}")
            print(f"   Conversations: {conv_count}")
            print(f"   Messages: {msg_count}")
            
            # Verify admin user exists
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                print(f"✅ Admin user exists: {admin_user.full_name}")
            else:
                print("❌ Admin user not found!")
                return False
                
            print("✅ Database verification completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def main():
    """Main function to run database initialization."""
    
    print("🚀 Solar Intelligence Database Setup")
    print("="*50)
    
    # Check environment variables
    required_vars = ['DATABASE_URL', 'FLASK_SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    # Initialize database
    if not init_database():
        print("❌ Database initialization failed!")
        return False
    
    # Verify setup
    if not verify_database():
        print("❌ Database verification failed!")
        return False
    
    print("🎉 Database setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Save the admin credentials in a secure location")
    print("2. Deploy your application")
    print("3. Test the application health endpoint")
    print("4. Create additional users through the registration system")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)