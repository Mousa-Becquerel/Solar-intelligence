#!/usr/bin/env python3
"""
Test script to debug CSRF token issues
"""

import requests
import json
import sys

def test_csrf_token():
    """Test CSRF token functionality"""
    
    base_url = "http://localhost:5002"
    
    print("🔐 Testing CSRF token functionality...")
    
    try:
        # First, get the login page to extract CSRF token
        session = requests.Session()
        login_page = session.get(f"{base_url}/login")
        
        print(f"Login page status: {login_page.status_code}")
        
        # Extract CSRF token from login page
        csrf_token = None
        if 'csrf_token' in login_page.text:
            import re
            match = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text)
            if match:
                csrf_token = match.group(1)
                print(f"✅ Found CSRF token: {csrf_token[:20]}...")
            else:
                print("⚠️  Could not extract CSRF token from login page")
                return False
        else:
            print("❌ No CSRF token found in login page")
            return False
        
        # Login first
        print("\n🔐 Logging in...")
        login_data = {
            'username': 'admin',
            'password': 'BecqSight2024!',
            'csrf_token': csrf_token
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data)
        print(f"Login status: {login_response.status_code}")
        
        if login_response.status_code != 200:
            print("❌ Login failed")
            return False
        
        # Now get the main page (should be authenticated)
        main_page = session.get(f"{base_url}/")
        print(f"Main page status: {main_page.status_code}")
        
        # Extract CSRF token from main page
        csrf_token = None
        if 'csrf_token' in main_page.text:
            import re
            match = re.search(r'name="csrf_token" value="([^"]+)"', main_page.text)
            if match:
                csrf_token = match.group(1)
                print(f"✅ Found CSRF token from main page: {csrf_token[:20]}...")
            else:
                print("⚠️  Could not extract CSRF token from main page")
                return False
        else:
            print("❌ No CSRF token found in main page")
            return False
        
        # Test conversation creation with CSRF token
        print("\n🔄 Testing conversation creation with CSRF token...")
        fresh_response = session.post(
            f"{base_url}/conversations/fresh",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token
            }
        )
        
        print(f"Conversation creation status: {fresh_response.status_code}")
        print(f"Response: {fresh_response.text}")
        
        if fresh_response.status_code == 200:
            data = fresh_response.json()
            conversation_id = data.get('id')
            print(f"✅ Conversation created with ID: {conversation_id}")
            
            # Test chat endpoint with CSRF token
            print(f"\n💬 Testing chat endpoint with CSRF token...")
            chat_response = session.post(
                f"{base_url}/chat",
                headers={
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf_token
                },
                json={
                    'message': 'Hello',
                    'conversation_id': conversation_id,
                    'agent_type': 'market'
                }
            )
            
            print(f"Chat endpoint status: {chat_response.status_code}")
            print(f"Chat response: {chat_response.text[:200]}...")
            
            if chat_response.status_code == 200:
                print("✅ Chat endpoint works with CSRF token")
                return True
            else:
                print(f"❌ Chat endpoint failed: {chat_response.status_code}")
                return False
        else:
            print(f"❌ Conversation creation failed: {fresh_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during CSRF test: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing CSRF Token Functionality")
    print("=" * 40)
    
    success = test_csrf_token()
    
    if success:
        print("\n✅ CSRF token functionality works!")
    else:
        print("\n❌ CSRF token functionality failed!")
        sys.exit(1) 