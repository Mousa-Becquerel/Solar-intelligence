#!/usr/bin/env python3
"""
Database connection test script for Python 3.13 compatibility
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connection with different drivers"""
    database_url = os.getenv('DATABASE_URL', 'sqlite:///test.db')
    
    print(f"Testing database connection with URL: {database_url}")
    
    if 'postgresql' in database_url or 'postgres' in database_url:
        print("Testing PostgreSQL connection...")
        
        # Test psycopg3 first
        try:
            import psycopg
            print("✓ psycopg3 is available")
            
            # Test connection
            from sqlalchemy import create_engine
            engine = create_engine(database_url.replace('postgresql://', 'postgresql+psycopg://', 1))
            with engine.connect() as conn:
                result = conn.execute("SELECT 1")
                print("✓ psycopg3 connection successful")
            return True
            
        except ImportError:
            print("✗ psycopg3 not available")
        except Exception as e:
            print(f"✗ psycopg3 connection failed: {e}")
        
        # Test psycopg2 as fallback
        try:
            import psycopg2
            print("✓ psycopg2 is available")
            
            # Test connection
            from sqlalchemy import create_engine
            engine = create_engine(database_url)
            with engine.connect() as conn:
                result = conn.execute("SELECT 1")
                print("✓ psycopg2 connection successful")
            return True
            
        except ImportError:
            print("✗ psycopg2 not available")
        except Exception as e:
            print(f"✗ psycopg2 connection failed: {e}")
        
        print("✗ No working PostgreSQL driver found")
        return False
    
    else:
        print("Testing SQLite connection...")
        try:
            from sqlalchemy import create_engine
            engine = create_engine(database_url)
            with engine.connect() as conn:
                result = conn.execute("SELECT 1")
                print("✓ SQLite connection successful")
            return True
        except Exception as e:
            print(f"✗ SQLite connection failed: {e}")
            return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1) 