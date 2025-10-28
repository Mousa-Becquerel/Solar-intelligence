#!/usr/bin/env python3
"""
Test script to verify conversation deletion functionality
"""

import requests
import json

def test_delete_conversation():
    """Test conversation deletion with CSRF token"""
    base_url = 'http://localhost:5002'
    session = requests.Session()
    
    print("🔍 Testing Conversation Deletion...")
    
    # Step 1: Login
    print("\n1️⃣ Logging in...")
    login_page_response = session.get(f'{base_url}/login')
    
    # Extract CSRF token from login page
    csrf_token = None
    if 'csrf_token' in login_page_response.text:
        import re
        match = re.search(r'name="csrf_token" value="([^"]+)"', login_page_response.text)
        if match:
            csrf_token = match.group(1)
    
    if not csrf_token:
        print("❌ Could not extract CSRF token from login page")
        return
    
    login_data = {
        'username': 'admin',
        'password': 'BecqSight2024!',
        'csrf_token': csrf_token
    }
    
    response = session.post(f'{base_url}/login', data=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    print("✅ Login successful")
    
    # Step 2: Get conversations
    print("\n2️⃣ Getting conversations...")
    response = session.get(f'{base_url}/conversations')
    if response.status_code != 200:
        print(f"❌ Failed to get conversations: {response.status_code}")
        return
    
    conversations = response.json()
    print(f"✅ Found {len(conversations)} conversations")
    
    if not conversations:
        print("❌ No conversations to delete")
        return
    
    # Step 3: Try to delete the first conversation
    conv_to_delete = conversations[0]
    print(f"\n3️⃣ Attempting to delete conversation {conv_to_delete['id']}...")
    
    headers = {
        'X-CSRFToken': csrf_token
    }
    
    response = session.delete(f'{base_url}/conversations/{conv_to_delete["id"]}', headers=headers)
    
    if response.status_code == 200:
        print("✅ Conversation deleted successfully!")
        
        # Verify deletion
        response = session.get(f'{base_url}/conversations')
        if response.status_code == 200:
            remaining_conversations = response.json()
            print(f"✅ Verification: {len(remaining_conversations)} conversations remaining")
        else:
            print("⚠️ Could not verify deletion")
    else:
        print(f"❌ Delete failed: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_delete_conversation() 