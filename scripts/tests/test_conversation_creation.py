#!/usr/bin/env python3
"""
Test script to verify conversation creation endpoint
"""

import requests
import json
import sys

def test_conversation_creation():
    """Test the conversation creation endpoint"""
    
    base_url = "http://localhost:5002"
    
    # First, try to login
    print("🔐 Testing login...")
    login_data = {
        'username': 'admin',
        'password': 'BecqSight2024!'
    }
    
    try:
        # Get CSRF token first
        session = requests.Session()
        login_page = session.get(f"{base_url}/login")
        
        # Extract CSRF token from the login page
        csrf_token = None
        if 'csrf_token' in login_page.text:
            # Simple extraction - in production you'd use BeautifulSoup
            import re
            match = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text)
            if match:
                csrf_token = match.group(1)
                print(f"✅ Found CSRF token: {csrf_token[:10]}...")
            else:
                print("⚠️  Could not extract CSRF token")
        
        # Login
        login_response = session.post(
            f"{base_url}/login",
            data=login_data,
            headers={'X-CSRFToken': csrf_token} if csrf_token else {}
        )
        
        if login_response.status_code == 200:
            print("✅ Login successful")
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Test conversation creation
    print("\n🔄 Testing conversation creation...")
    try:
        # Create a fresh conversation
        fresh_response = session.post(
            f"{base_url}/conversations/fresh",
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status: {fresh_response.status_code}")
        print(f"Response: {fresh_response.text}")
        
        if fresh_response.status_code == 200:
            data = fresh_response.json()
            if 'id' in data:
                print(f"✅ Conversation created successfully with ID: {data['id']}")
                return True
            else:
                print("❌ No conversation ID in response")
                return False
        else:
            print(f"❌ Failed to create conversation: {fresh_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Conversation creation error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Conversation Creation")
    print("=" * 40)
    
    success = test_conversation_creation()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1) 