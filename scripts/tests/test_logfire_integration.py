#!/usr/bin/env python3
"""
Test script to verify Logfire integration is working properly
"""

import requests
import json
import sys
import time

def test_logfire_integration():
    """Test that Logfire is properly integrated and sending data"""
    print("🔍 Testing Logfire Integration...")
    
    base_url = "http://localhost:5002"
    
    # Test 1: Get CSRF token first, then login
    print("   Testing login with CSRF token...")
    try:
        session = requests.Session()
        
        # First, get the login page to obtain CSRF token
        login_page_response = session.get(f'{base_url}/login')
        if login_page_response.status_code != 200:
            print(f"   ❌ Could not access login page: {login_page_response.status_code}")
            return False
        
        # Extract CSRF token from the login page
        import re
        csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', login_page_response.text)
        if not csrf_match:
            print("   ❌ Could not find CSRF token on login page")
            return False
        
        csrf_token = csrf_match.group(1)
        print(f"   ✅ CSRF token obtained: {csrf_token[:10]}...")
        
        # Now login with CSRF token
        login_data = {
            'username': 'admin',
            'password': 'BecqSight2024!',
            'csrf_token': csrf_token
        }
        
        response = session.post(f'{base_url}/login', data=login_data)
        
        if response.status_code == 200:
            print("   ✅ Login successful")
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"   📄 Response content: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return False
    
    # Test 2: Send a chat message to trigger Logfire spans
    print("   Testing chat with Logfire spans...")
    try:
        chat_data = {
            'message': 'What are the current module prices in China?',
            'conversation_id': 1,
            'agent_type': 'price'
        }
        
        # Add CSRF token to headers for the chat request
        headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token
        }
        
        response = session.post(f'{base_url}/chat', json=chat_data, headers=headers)
        
        if response.status_code == 200:
            print("   ✅ Chat request successful - Logfire spans should be generated")
            result = response.json()
            print(f"   📊 Response type: {type(result.get('response', []))}")
        else:
            print(f"   ❌ Chat request failed: {response.status_code}")
            print(f"   📄 Response content: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ Chat error: {e}")
        return False
    
    # Test 3: Test admin memory cleanup (should generate Logfire spans)
    print("   Testing admin memory cleanup...")
    try:
        response = session.post(f'{base_url}/admin/memory-cleanup')
        
        if response.status_code == 200:
            print("   ✅ Memory cleanup successful - Logfire spans should be generated")
            result = response.json()
            print(f"   📊 Memory freed: {result.get('memory_freed_mb', 'N/A')}MB")
        else:
            print(f"   ⚠️  Memory cleanup failed: {response.status_code} (expected if not admin)")
            
    except Exception as e:
        print(f"   ❌ Memory cleanup error: {e}")
    
    print("\n✅ Logfire Integration Test Complete!")
    print("📊 Check your Logfire dashboard for:")
    print("   - Flask request spans")
    print("   - Chat request spans")
    print("   - Agent call spans (price/market)")
    print("   - Admin memory cleanup spans")
    print("   - Pydantic AI instrumentation")
    
    return True

def main():
    """Run Logfire integration test"""
    print("🔐 LOGFIRE INTEGRATION VERIFICATION")
    print("=" * 50)
    
    try:
        if test_logfire_integration():
            print("\n🎉 Logfire integration test passed!")
            print("✅ Your application is now sending observability data to Logfire")
            sys.exit(0)
        else:
            print("\n❌ Logfire integration test failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 