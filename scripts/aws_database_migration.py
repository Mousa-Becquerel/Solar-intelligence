#!/usr/bin/env python3
"""
AWS Database Migration Script for Solar Intelligence Platform
Adds missing GDPR columns to the User table
"""

import os
import sys
import psycopg
from datetime import datetime

def get_database_url():
    """Get database URL from environment"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL environment variable is not set")
        sys.exit(1)
    
    # Handle PostgreSQL URL format
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    return db_url

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s
    """, (table_name, column_name))
    return cursor.fetchone() is not None

def add_gdpr_columns(cursor):
    """Add missing GDPR columns to the User table"""
    
    print("📊 Checking existing User table structure...")
    
    # List of GDPR columns to add
    gdpr_columns = [
        ('gdpr_consent_given', 'BOOLEAN DEFAULT FALSE NOT NULL'),
        ('gdpr_consent_date', 'TIMESTAMP'),
        ('terms_accepted', 'BOOLEAN DEFAULT FALSE NOT NULL'),
        ('terms_accepted_date', 'TIMESTAMP'),
        ('marketing_consent', 'BOOLEAN DEFAULT FALSE NOT NULL'),
        ('marketing_consent_date', 'TIMESTAMP'),
        ('privacy_policy_version', 'VARCHAR(10) DEFAULT \'1.0\''),
        ('terms_version', 'VARCHAR(10) DEFAULT \'1.0\'')
    ]
    
    columns_added = 0
    
    for column_name, column_definition in gdpr_columns:
        if not check_column_exists(cursor, 'user', column_name):
            print(f"➕ Adding column: {column_name}")
            try:
                cursor.execute(f'ALTER TABLE "user" ADD COLUMN {column_name} {column_definition}')
                columns_added += 1
                print(f"✅ Added {column_name}")
            except Exception as e:
                print(f"❌ Failed to add {column_name}: {e}")
        else:
            print(f"✅ Column {column_name} already exists")
    
    return columns_added

def update_existing_users(cursor):
    """Update existing users to have proper GDPR defaults"""
    print("🔄 Updating existing users with GDPR defaults...")
    
    try:
        # Set default values for existing users who don't have GDPR consent
        cursor.execute("""
            UPDATE "user" 
            SET 
                gdpr_consent_given = FALSE,
                terms_accepted = FALSE,
                marketing_consent = FALSE,
                privacy_policy_version = '1.0',
                terms_version = '1.0'
            WHERE 
                gdpr_consent_given IS NULL 
                OR terms_accepted IS NULL 
                OR marketing_consent IS NULL
        """)
        
        rows_updated = cursor.rowcount
        print(f"✅ Updated {rows_updated} existing users with GDPR defaults")
        return rows_updated
        
    except Exception as e:
        print(f"❌ Failed to update existing users: {e}")
        return 0

def verify_migration(cursor):
    """Verify the migration was successful"""
    print("🔍 Verifying migration...")
    
    try:
        # Test query to make sure all columns exist
        cursor.execute("""
            SELECT 
                id, username, full_name, role, created_at, is_active,
                gdpr_consent_given, gdpr_consent_date, terms_accepted, 
                terms_accepted_date, marketing_consent, marketing_consent_date,
                privacy_policy_version, terms_version
            FROM "user" 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        print("✅ Migration verification successful - all columns accessible")
        
        # Count total users
        cursor.execute('SELECT COUNT(*) FROM "user"')
        user_count = cursor.fetchone()[0]
        print(f"📊 Total users in database: {user_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Starting AWS Database Migration for Solar Intelligence Platform")
    print("=" * 60)
    
    # Get database connection
    try:
        db_url = get_database_url()
        print("🔗 Connecting to PostgreSQL database...")
        
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cursor:
                print("✅ Database connection successful")
                
                # Check current database info
                cursor.execute("SELECT version()")
                db_version = cursor.fetchone()[0]
                print(f"📊 Database version: {db_version}")
                
                # Add missing columns
                columns_added = add_gdpr_columns(cursor)
                
                # Update existing users
                users_updated = update_existing_users(cursor)
                
                # Commit changes
                conn.commit()
                print("💾 Changes committed to database")
                
                # Verify migration
                if verify_migration(cursor):
                    print("\n🎉 Migration completed successfully!")
                    print(f"✅ Columns added: {columns_added}")
                    print(f"✅ Users updated: {users_updated}")
                    print("\n🔧 Next steps:")
                    print("1. Restart your AWS ECS service")
                    print("2. Test login functionality")
                    print("3. Verify all features work correctly")
                else:
                    print("\n❌ Migration verification failed!")
                    sys.exit(1)
                
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check DATABASE_URL environment variable")
        print("2. Verify database connectivity")
        print("3. Ensure proper permissions")
        sys.exit(1)

if __name__ == "__main__":
    main()
