#!/usr/bin/env python3
"""
Startup script for the enhanced BecqSight application with Pydantic-AI Weaviate integration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking environment configuration...")
    
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API Key',
        'FLASK_SECRET_KEY': 'Flask Secret Key'
    }
    
    optional_vars = {
        'WEAVIATE_URL': 'Weaviate Cluster URL',
        'WEAVIATE_API_KEY': 'Weaviate API Key'
    }
    
    missing_required = []
    missing_optional = []
    
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_required.append(f"  - {var}: {description}")
    
    for var, description in optional_vars.items():
        if not os.getenv(var):
            missing_optional.append(f"  - {var}: {description}")
    
    if missing_required:
        print("❌ Missing required environment variables:")
        for var in missing_required:
            print(var)
        print("\nPlease set these variables in your .env file")
        return False
    
    if missing_optional:
        print("⚠️  Missing optional environment variables (Pydantic-AI Weaviate agent will run in fallback mode):")
        for var in missing_optional:
            print(var)
        print("\nPydantic-AI Weaviate agent will still work but with limited functionality")
    
    print("✅ Environment check complete")
    return True

def test_agents():
    """Test agent initialization"""
    print("\n🧪 Testing agent initialization...")
    
    try:
        # Test Pydantic-AI Weaviate agent
        try:
            from pydantic_weaviate_agent import get_pydantic_weaviate_agent
            pydantic_agent = get_pydantic_weaviate_agent()
            agent_info = pydantic_agent.get_agent_info()
            
            if agent_info['status'] == 'ready':
                print("✅ Pydantic-AI Weaviate agent initialized successfully")
            else:
                print("⚠️  Pydantic-AI Weaviate agent initialized with warnings")
                print(f"   Status: {agent_info['status']}")
                print(f"   Weaviate Connected: {agent_info['weaviate_connected']}")
        
        except Exception as e:
            print(f"❌ Pydantic-AI Weaviate agent initialization failed: {str(e)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Agent initialization failed: {str(e)}")
        return False

def start_application():
    """Start the Flask application"""
    print("\n🚀 Starting Pydantic-AI Weaviate Agent Application...")
    print("=" * 60)
    print("📊 Available Agent:")
    print("   • Pydantic-AI Weaviate Agent (Pydantic-AI + Weaviate)")
    print("\n🌐 Access the application at: http://localhost:5000")
    print("📖 Default login credentials:")
    print("   Username: admin")
    print("   Password: BecqSight2024!")
    print("=" * 60)
    
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Failed to start application: {str(e)}")

def main():
    """Main startup function"""
    print("🌟 Pydantic-AI Weaviate Agent Application Startup")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test agents
    if not test_agents():
        print("\n❌ Agent initialization failed. Please check your configuration.")
        sys.exit(1)
    
    # Start application
    start_application()

if __name__ == "__main__":
    main() 