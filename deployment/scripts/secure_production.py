#!/usr/bin/env python3
"""
Production security configuration script for Solar Intelligence platform.
This script addresses security vulnerabilities before AWS deployment.
"""

import os
import sys
import secrets
import re

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def generate_flask_secret_key():
    """Generate a secure Flask secret key."""
    return secrets.token_hex(32)  # 64 character hex string

def remove_hardcoded_credentials():
    """Remove or comment out hardcoded credentials from the codebase."""
    
    print("🔒 Securing hardcoded credentials...")
    
    app_py_path = os.path.join(os.path.dirname(__file__), '..', '..', 'app.py')
    
    try:
        with open(app_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Comment out the PREDEFINED_USERS section
        pattern = r'(PREDEFINED_USERS = \[.*?\])'
        replacement = '''# PREDEFINED_USERS commented out for security - use environment variables instead
# PREDEFINED_USERS = [
#     # Users should be created through the registration system or admin interface
#     # Default admin user is created by init_database.py script
# ]
PREDEFINED_USERS = []  # Empty for production security'''
        
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        with open(app_py_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ Hardcoded credentials removed from app.py")
        return True
        
    except Exception as e:
        print(f"❌ Failed to secure app.py: {e}")
        return False

def secure_test_files():
    """Remove API keys from test files."""
    
    print("🔑 Securing test files...")
    
    test_files = [
        'scripts/tests/test_custom_agents_logfire.py',
        'scripts/tests/test_standard_agent.py'
    ]
    
    for test_file in test_files:
        file_path = os.path.join(os.path.dirname(__file__), '..', '..', test_file)
        
        if not os.path.exists(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace hardcoded API keys with environment variable references
            content = re.sub(
                r"os\.environ\['OPENAI_API_KEY'\] = 'sk-[^']*'",
                "# os.environ['OPENAI_API_KEY'] = 'your-api-key-here'  # Use environment variable instead",
                content
            )
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"✅ Secured {test_file}")
            
        except Exception as e:
            print(f"❌ Failed to secure {test_file}: {e}")
    
    return True

def create_env_template():
    """Create a .env.template file with required environment variables."""
    
    print("📝 Creating environment template...")
    
    env_template = """# Solar Intelligence Platform - Environment Variables Template
# Copy this file to .env and fill in the actual values

# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database

# Flask Configuration
FLASK_SECRET_KEY=your-64-character-secret-key-here
FLASK_ENV=production

# AI Services
OPENAI_API_KEY=your-openai-api-key-here
WEAVIATE_URL=your-weaviate-instance-url
WEAVIATE_API_KEY=your-weaviate-api-key

# AWS/Deployment
PORT=80

# Optional: Admin User (for initial setup)
ADMIN_PASSWORD=your-secure-admin-password-here
"""
    
    env_template_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env.template')
    
    try:
        with open(env_template_path, 'w', encoding='utf-8') as f:
            f.write(env_template)
        print("✅ Created .env.template file")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env.template: {e}")
        return False

def update_requirements():
    """Add PostgreSQL dependencies to requirements.txt if missing."""
    
    print("📦 Checking PostgreSQL dependencies...")
    
    requirements_path = os.path.join(os.path.dirname(__file__), '..', '..', 'requirements.txt')
    
    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if PostgreSQL dependencies are present
        postgres_deps = ['psycopg', 'SQLAlchemy']
        missing_deps = []
        
        if 'psycopg' not in content and 'psycopg2' not in content:
            missing_deps.append('psycopg[binary]==3.1.8')
        
        if 'flask-sqlalchemy' not in content.lower():
            missing_deps.append('flask-sqlalchemy==3.0.5')
            
        if missing_deps:
            with open(requirements_path, 'a', encoding='utf-8') as f:
                f.write('\n# PostgreSQL dependencies for AWS deployment\n')
                for dep in missing_deps:
                    f.write(f'{dep}\n')
            print(f"✅ Added PostgreSQL dependencies: {missing_deps}")
        else:
            print("✅ PostgreSQL dependencies already present")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to update requirements.txt: {e}")
        return False

def create_gitignore_additions():
    """Add security-related entries to .gitignore."""
    
    print("🛡️  Updating .gitignore for security...")
    
    gitignore_path = os.path.join(os.path.dirname(__file__), '..', '..', '.gitignore')
    
    security_entries = """
# Security and Environment Files
.env
.env.local
.env.production
*.key
*.pem
secrets/
credentials/

# Database Files
*.db
*.sqlite
*.sqlite3

# AWS Credentials
.aws/
aws-credentials.json

# Backup Files
*.backup
*.dump
*.sql.gz
"""
    
    try:
        # Read existing .gitignore if it exists
        existing_content = ""
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        
        # Add security entries if not already present
        if '.env' not in existing_content:
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                f.write(security_entries)
            print("✅ Added security entries to .gitignore")
        else:
            print("✅ Security entries already in .gitignore")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to update .gitignore: {e}")
        return False

def main():
    """Main function to secure the application for production."""
    
    print("🔐 Solar Intelligence Production Security Setup")
    print("="*60)
    
    success = True
    
    # Generate Flask secret key
    secret_key = generate_flask_secret_key()
    print(f"🔑 Generated Flask Secret Key: {secret_key}")
    print("⚠️  Save this key securely and set it as FLASK_SECRET_KEY environment variable!")
    print()
    
    # Remove hardcoded credentials
    if not remove_hardcoded_credentials():
        success = False
    
    # Secure test files
    if not secure_test_files():
        success = False
    
    # Create environment template
    if not create_env_template():
        success = False
    
    # Update requirements
    if not update_requirements():
        success = False
    
    # Update .gitignore
    if not create_gitignore_additions():
        success = False
    
    if success:
        print("\n🎉 Security setup completed successfully!")
        print("\n📋 Next Steps:")
        print("1. Set the generated Flask secret key as FLASK_SECRET_KEY environment variable")
        print("2. Update your API keys in environment variables")
        print("3. Review and customize .env.template for your deployment")
        print("4. Run init_database.py to set up the production database")
        print("5. Deploy to AWS with secure environment variables")
        print("\n⚠️  CRITICAL: Never commit .env files or API keys to version control!")
    else:
        print("\n❌ Some security setup steps failed. Please review the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)