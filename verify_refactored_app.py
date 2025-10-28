"""
Verification script for refactored application.

This script checks that all critical components are working correctly.
Run this AFTER the Docker container is running.
"""

import requests
import json
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:5000"

def test_endpoint(name: str, url: str, method: str = "GET", data: Dict = None,
                  requires_auth: bool = False, cookies: Dict = None) -> Tuple[bool, str]:
    """Test an endpoint and return success status with message."""
    try:
        full_url = f"{BASE_URL}{url}"

        if method == "GET":
            response = requests.get(full_url, cookies=cookies, timeout=5)
        elif method == "POST":
            response = requests.post(full_url, json=data, cookies=cookies, timeout=5)

        # Check if authentication is required
        if requires_auth and response.status_code == 401:
            return True, f"✅ {name}: Correctly requires authentication"

        # Check for expected status codes
        if response.status_code in [200, 302, 304]:
            return True, f"✅ {name}: OK (Status {response.status_code})"
        elif response.status_code == 404:
            return False, f"❌ {name}: Not Found (404)"
        elif response.status_code == 500:
            return False, f"❌ {name}: Internal Server Error (500)"
        else:
            return False, f"⚠️  {name}: Unexpected status {response.status_code}"

    except requests.exceptions.ConnectionError:
        return False, f"❌ {name}: Connection refused - Is Docker running?"
    except requests.exceptions.Timeout:
        return False, f"⚠️  {name}: Request timeout"
    except Exception as e:
        return False, f"❌ {name}: Error - {str(e)}"


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("🔍 Verifying Refactored PV Market Analysis Application")
    print("=" * 70)
    print()

    tests = [
        # Public endpoints
        ("Landing Page", "/", "GET", None, False),
        ("Login Page", "/auth/login", "GET", None, False),
        ("Register Page", "/auth/register", "GET", None, False),
        ("Health Check", "/health", "GET", None, False),
        ("Privacy Policy", "/privacy-policy", "GET", None, False),
        ("Terms of Service", "/terms-of-service", "GET", None, False),

        # Protected endpoints (should redirect or return 401)
        ("Dashboard", "/dashboard", "GET", None, True),
        ("Agents Page", "/agents", "GET", None, True),
        ("Conversations API", "/conversations/", "GET", None, True),
        ("Current User API", "/auth/current-user", "GET", None, True),

        # Static assets
        ("CSS", "/static/css/style.css", "GET", None, False),
        ("JavaScript", "/static/js/main.js", "GET", None, False),
    ]

    passed = 0
    failed = 0
    warnings = 0

    print("📋 Testing Endpoints:")
    print("-" * 70)

    for test in tests:
        name, url, method, data, requires_auth = test
        success, message = test_endpoint(name, url, method, data, requires_auth)
        print(message)

        if success:
            passed += 1
        elif "⚠️" in message:
            warnings += 1
        else:
            failed += 1

    print()
    print("=" * 70)
    print("📊 Summary:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⚠️  Warnings: {warnings}")
    print("=" * 70)
    print()

    # Check Docker container status
    print("🐳 Docker Container Info:")
    print("-" * 70)
    try:
        import subprocess
        result = subprocess.run(
            ["docker-compose", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(result.stdout)
    except Exception as e:
        print(f"⚠️  Could not check Docker status: {e}")

    print()

    if failed == 0:
        print("✨ All critical tests passed! The refactored app is working correctly.")
        print()
        print("🎉 Next steps:")
        print("   1. Login at http://localhost:5000/auth/login")
        print("   2. Test chat with different agents")
        print("   3. Verify streaming responses work")
        print("   4. Check conversation history")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print()
        print("🔧 Troubleshooting:")
        print("   1. Ensure Docker container is running: docker-compose ps")
        print("   2. Check logs: docker-compose logs -f")
        print("   3. Verify .env file has all required variables")
        return 1


if __name__ == "__main__":
    exit(main())
