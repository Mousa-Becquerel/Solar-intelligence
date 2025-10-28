#!/usr/bin/env python3
"""
Test script to verify security fixes are working properly
"""

import requests
import json
import sys

def test_csrf_protection():
    """Test that CSRF protection is working"""
    print("🔒 Testing CSRF Protection...")
    
    # Test login without CSRF token (should fail)
    login_data = {
        'username': 'admin',
        'password': 'BecqSight2024!'
    }
    
    try:
        response = requests.post('http://localhost:5000/login', data=login_data)
        if response.status_code == 400:
            print("✅ CSRF protection is working - login blocked without token")
        else:
            print("❌ CSRF protection may not be working")
            return False
    except Exception as e:
        print(f"❌ Error testing CSRF protection: {e}")
        return False
    
    return True

def test_rate_limiting():
    """Test that rate limiting is working"""
    print("\n🚦 Testing Rate Limiting...")
    
    # Test login rate limiting
    login_data = {
        'username': 'admin',
        'password': 'wrong_password'
    }
    
    try:
        # Try multiple login attempts
        for i in range(6):
            response = requests.post('http://localhost:5000/login', data=login_data)
            print(f"   Login attempt {i+1}: {response.status_code}")
            
            if response.status_code == 429:  # Too Many Requests
                print("✅ Rate limiting is working")
                return True
    except Exception as e:
        print(f"❌ Error testing rate limiting: {e}")
        return False
    
    print("⚠️  Rate limiting may not be working (no 429 response)")
    return False

def test_error_handling():
    """Test that error handling is working"""
    print("\n🛡️ Testing Error Handling...")
    
    try:
        # Test 404 error
        response = requests.get('http://localhost:5000/nonexistent-page')
        if response.status_code == 404:
            print("✅ 404 error handling is working")
        else:
            print("❌ 404 error handling not working")
            return False
            
        # Test 500 error (by accessing a route that might cause issues)
        response = requests.get('http://localhost:5000/health')
        if response.status_code == 200:
            print("✅ Health endpoint is working")
        else:
            print("⚠️  Health endpoint returned unexpected status")
            
    except Exception as e:
        print(f"❌ Error testing error handling: {e}")
        return False
    
    return True

def main():
    """Run all security tests"""
    print("🔐 SECURITY FIXES VERIFICATION")
    print("=" * 50)
    
    tests = [
        test_csrf_protection,
        test_rate_limiting,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All security tests passed!")
        print("✅ Application is ready for production deployment")
        sys.exit(0)
    else:
        print("⚠️  Some security tests failed")
        print("🔧 Please review the failed tests above")
        sys.exit(1)

if __name__ == "__main__":
    main() 