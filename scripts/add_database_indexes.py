"""
Database Index Migration Script

This script adds performance indexes to the database for frequently queried columns.
Run this script to add indexes to an existing database without losing data.

Usage:
    python scripts/add_database_indexes.py

Note: This script is idempotent - it can be run multiple times safely.
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text, inspect

def check_index_exists(engine, table_name, index_name):
    """Check if an index exists on a table"""
    inspector = inspect(engine)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)

def create_index_if_not_exists(engine, table_name, index_name, columns):
    """Create an index if it doesn't already exist"""
    try:
        if check_index_exists(engine, table_name, index_name):
            print(f"✓ Index {index_name} already exists on {table_name}")
            return True

        # Build CREATE INDEX statement
        column_list = ', '.join(columns) if isinstance(columns, list) else columns
        sql = f"CREATE INDEX {index_name} ON {table_name} ({column_list})"

        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()

        print(f"✅ Created index {index_name} on {table_name}({column_list})")
        return True

    except Exception as e:
        print(f"⚠️  Error creating index {index_name}: {e}")
        return False

def add_all_indexes():
    """Add all performance indexes to the database"""
    print("\n🔧 Starting database index migration...")
    print("=" * 60)

    engine = db.engine

    # Define all indexes to create
    indexes = [
        # User table indexes
        ('user', 'idx_user_username', 'username'),
        ('user', 'idx_user_role', 'role'),
        ('user', 'idx_user_created_at', 'created_at'),
        ('user', 'idx_user_is_active', 'is_active'),

        # Conversation table indexes
        ('conversation', 'idx_conversation_user_id', 'user_id'),
        ('conversation', 'idx_conversation_created_at', 'created_at'),
        ('conversation', 'idx_conversation_agent_type', 'agent_type'),
        ('conversation', 'idx_conversation_user_created', ['user_id', 'created_at']),

        # Message table indexes
        ('message', 'idx_message_conversation_id', 'conversation_id'),
        ('message', 'idx_message_timestamp', 'timestamp'),
        ('message', 'idx_message_sender', 'sender'),
        ('message', 'idx_message_conv_timestamp', ['conversation_id', 'timestamp']),

        # Feedback table indexes
        ('feedback', 'idx_feedback_user_id', 'user_id'),
        ('feedback', 'idx_feedback_created_at', 'created_at'),
        ('feedback', 'idx_feedback_rating', 'rating'),

        # HiredAgent table indexes
        ('hired_agent', 'idx_hired_agent_user_id', 'user_id'),
        ('hired_agent', 'idx_hired_agent_is_active', 'is_active'),
        ('hired_agent', 'idx_hired_agent_user_active', ['user_id', 'is_active']),
    ]

    success_count = 0
    skip_count = 0
    error_count = 0

    for table_name, index_name, columns in indexes:
        result = create_index_if_not_exists(engine, table_name, index_name, columns)
        if result:
            if check_index_exists(engine, table_name, index_name):
                success_count += 1
            else:
                skip_count += 1
        else:
            error_count += 1

    print("=" * 60)
    print(f"\n📊 Migration Summary:")
    print(f"   ✅ Indexes created: {success_count}")
    print(f"   ✓  Already existed: {skip_count}")
    print(f"   ⚠️  Errors: {error_count}")
    print(f"\n✨ Total indexes in place: {success_count + skip_count}/{len(indexes)}")

    if error_count == 0:
        print("\n🎉 Database index migration completed successfully!")
    else:
        print(f"\n⚠️  Migration completed with {error_count} errors. Check logs above.")

    return error_count == 0

if __name__ == '__main__':
    with app.app_context():
        try:
            success = add_all_indexes()
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
