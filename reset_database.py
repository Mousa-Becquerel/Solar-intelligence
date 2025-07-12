#!/usr/bin/env python3
"""
Reset PostgreSQL database tables with correct column sizes
Run this to fix the VARCHAR(120) -> VARCHAR(255) issue
"""

import os
from sqlalchemy import create_engine, text

def reset_database():
    """Drop and recreate all tables with correct column sizes"""
    
    postgres_url = os.getenv('DATABASE_URL')
    if not postgres_url:
        print("❌ DATABASE_URL environment variable not set")
        return
    
    if postgres_url.startswith('postgres://'):
        postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        engine = create_engine(postgres_url)
        
        print("🔗 Connected to PostgreSQL")
        
        with engine.connect() as conn:
            # Drop all tables
            print("🗑️  Dropping existing tables...")
            conn.execute(text('DROP TABLE IF EXISTS message CASCADE'))
            conn.execute(text('DROP TABLE IF EXISTS conversation CASCADE'))
            conn.execute(text('DROP TABLE IF EXISTS "user" CASCADE'))
            
            # Create tables with correct column sizes
            print("🏗️  Creating tables with correct column sizes...")
            
            # Create users table with VARCHAR(255) for password_hash
            conn.execute(text("""
                CREATE TABLE "user" (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100) NOT NULL,
                    role VARCHAR(50) DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """))
            
            # Create conversations table
            conn.execute(text("""
                CREATE TABLE conversation (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(256),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    agent_type VARCHAR(16) DEFAULT 'market',
                    user_id INTEGER REFERENCES "user"(id) NOT NULL
                )
            """))
            
            # Create messages table
            conn.execute(text("""
                CREATE TABLE message (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER REFERENCES conversation(id) NOT NULL,
                    sender VARCHAR(16),
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            conn.commit()
            print("✅ Database reset complete!")
            print("🚀 Deploy your app again - it should work now!")
            
    except Exception as e:
        print(f"❌ Reset failed: {e}")

if __name__ == "__main__":
    print("🔄 Resetting PostgreSQL database...")
    print("=" * 50)
    reset_database()
    print("=" * 50) 