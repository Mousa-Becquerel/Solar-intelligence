"""
Standalone database migration script to add profile-related columns
This script connects directly to PostgreSQL without importing the Flask app
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not found!")
    print("Please set DATABASE_URL in your .env file")
    exit(1)

def run_migration():
    """Add new columns to User table"""
    try:
        # Connect to database
        print(f"Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        print("✓ Connected to database")
        print()

        # Define columns to add
        columns = [
            ('plan_type', "VARCHAR(20) DEFAULT 'free'"),
            ('query_count', "INTEGER DEFAULT 0"),
            ('last_query_date', "TIMESTAMP"),
            ('plan_start_date', "TIMESTAMP"),
            ('plan_end_date', "TIMESTAMP"),
            ('monthly_query_count', "INTEGER DEFAULT 0"),
            ('last_reset_date', "TIMESTAMP"),
        ]

        print("Starting migration...")
        print("=" * 60)

        for column_name, column_type in columns:
            try:
                # Check if column exists
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='user' AND column_name=%s
                """, (column_name,))

                if cursor.fetchone():
                    print(f"↓ Column '{column_name}' already exists - skipping")
                else:
                    # Add column
                    cursor.execute(f'ALTER TABLE "user" ADD COLUMN {column_name} {column_type}')
                    conn.commit()
                    print(f"✓ Added column: {column_name}")

            except Exception as e:
                print(f"✗ Error adding column {column_name}: {e}")
                conn.rollback()

        print("=" * 60)
        print("✓ Migration completed successfully!")
        print()

        # Close connection
        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("User Profile Columns Migration")
    print("=" * 60)
    print()

    response = input("This will modify the database schema. Continue? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        success = run_migration()
        if success:
            print("\n🎉 Migration successful! Your profile page should now work.")
            print("   Restart your Flask app and navigate to /profile")
        else:
            print("\n❌ Migration failed. Please check the error messages above.")
    else:
        print("Migration cancelled.")
