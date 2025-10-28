#!/usr/bin/env python3
"""
Load Testing Script for Concurrent User Support

Tests the chatbot's ability to handle multiple concurrent users.
Validates that async architecture eliminates blocking behavior.

Usage:
    python scripts/test_concurrent_users.py [num_users]

Example:
    python scripts/test_concurrent_users.py 10  # Test with 10 concurrent users
"""

import asyncio
import aiohttp
import time
from datetime import datetime
import sys
import json

# Configuration
BASE_URL = "http://localhost:5000"
LOGIN_URL = f"{BASE_URL}/login"
CHAT_URL = f"{BASE_URL}/chat"

# Test credentials (adjust these for your setup)
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "test123"


async def login_user(session):
    """Login and get session cookie"""
    async with session.post(LOGIN_URL, data={
        'email': TEST_EMAIL,
        'password': TEST_PASSWORD
    }, allow_redirects=False) as resp:
        if resp.status in [200, 302]:
            print(f"✓ Login successful")
            return True
        else:
            print(f"✗ Login failed: {resp.status}")
            return False


async def simulate_user(session, user_id, conversation_id, query):
    """Simulate a single user sending a message"""
    start_time = time.time()

    try:
        async with session.post(CHAT_URL, json={
            'message': query,
            'conversation_id': conversation_id,
            'agent_type': 'market'
        }) as resp:
            duration = time.time() - start_time
            status = resp.status

            if status == 200:
                data = await resp.json()
                success = data.get('success', False)
                result_type = data.get('type', 'unknown')

                print(f"✓ User {user_id}: {status} in {duration:.2f}s (type: {result_type}, success: {success})")
                return {
                    'user_id': user_id,
                    'status': status,
                    'duration': duration,
                    'success': success,
                    'error': None
                }
            else:
                print(f"✗ User {user_id}: {status} in {duration:.2f}s")
                text = await resp.text()
                return {
                    'user_id': user_id,
                    'status': status,
                    'duration': duration,
                    'success': False,
                    'error': text[:200]
                }

    except Exception as e:
        duration = time.time() - start_time
        print(f"✗ User {user_id}: ERROR in {duration:.2f}s - {str(e)}")
        return {
            'user_id': user_id,
            'status': 0,
            'duration': duration,
            'success': False,
            'error': str(e)
        }


async def run_load_test(num_users=10):
    """Run load test with specified number of concurrent users"""

    print("=" * 60)
    print(f"CONCURRENT USER LOAD TEST")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing {num_users} concurrent users")
    print("=" * 60)
    print()

    # Create session with cookie jar
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:

        # Login first
        print("Logging in...")
        if not await login_user(session):
            print("Cannot proceed without login")
            return

        print(f"\nStarting {num_users} concurrent requests...")
        print("-" * 60)

        # Create tasks for all users
        tasks = []
        test_queries = [
            "Show me China market data for 2024",
            "What is the total capacity for India?",
            "Compare Germany and France markets",
            "Show me solar trends in the USA",
            "What are the forecasts for 2025?",
        ]

        start_time = time.time()

        for i in range(num_users):
            # Use different queries to simulate real users
            query = test_queries[i % len(test_queries)]
            # Each user gets their own conversation ID
            conv_id = 1000 + i

            task = simulate_user(session, i + 1, conv_id, query)
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        total_duration = time.time() - start_time

        # Analyze results
        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)

        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]

        print(f"\nTotal requests: {num_users}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print(f"\nTotal time: {total_duration:.2f}s")
        print(f"Requests/second: {num_users / total_duration:.2f}")

        if successful:
            avg_duration = sum(r['duration'] for r in successful) / len(successful)
            min_duration = min(r['duration'] for r in successful)
            max_duration = max(r['duration'] for r in successful)

            print(f"\nResponse times:")
            print(f"  Average: {avg_duration:.2f}s")
            print(f"  Min: {min_duration:.2f}s")
            print(f"  Max: {max_duration:.2f}s")

        # Check for blocking behavior
        print(f"\n📊 Concurrency Analysis:")
        if total_duration < max_duration * 1.5:
            print(f"✅ TRUE CONCURRENCY: Requests processed in parallel")
            print(f"   (Total time {total_duration:.1f}s ≈ Max response {max_duration:.1f}s)")
        else:
            print(f"⚠️ SEQUENTIAL PROCESSING: Requests queued/blocked")
            print(f"   (Total time {total_duration:.1f}s >> Max response {max_duration:.1f}s)")

        if failed:
            print(f"\n❌ Failed Requests:")
            for r in failed[:5]:  # Show first 5 failures
                print(f"   User {r['user_id']}: {r['error'][:100]}")

        return {
            'total': num_users,
            'successful': len(successful),
            'failed': len(failed),
            'total_duration': total_duration,
            'avg_duration': avg_duration if successful else 0,
            'is_concurrent': total_duration < max_duration * 1.5
        }


def main():
    """Main entry point"""
    num_users = 10  # Default

    if len(sys.argv) > 1:
        try:
            num_users = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number: {sys.argv[1]}")
            sys.exit(1)

    # Run the async load test
    results = asyncio.run(run_load_test(num_users))

    # Exit with appropriate code
    if results and results['is_concurrent']:
        print(f"\n✅ SUCCESS: Async architecture working correctly!")
        sys.exit(0)
    else:
        print(f"\n⚠️ WARNING: Sequential processing detected")
        sys.exit(1)


if __name__ == "__main__":
    main()
