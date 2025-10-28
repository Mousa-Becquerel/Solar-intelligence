#!/usr/bin/env python3
"""
Comprehensive Test Suite for DH Agents Application
Tests all critical functionality before deployment
"""

import requests
import json
import sys
import time
import random
from datetime import datetime

class ComprehensiveTestSuite:
    def __init__(self):
        self.base_url = "http://localhost:5002"
        self.session = requests.Session()
        self.test_results = []
        self.csrf_token = None
        self.current_conversation_id = None
        
    def log_test(self, test_name, success, details=""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        result = f"[{timestamp}] {status}: {test_name}"
        if details:
            result += f" - {details}"
        print(result)
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': timestamp
        })
        return success
    
    def get_csrf_token(self, page_url="/"):
        """Extract CSRF token from a page"""
        try:
            response = self.session.get(f"{self.base_url}{page_url}")
            if 'csrf_token' in response.text:
                import re
                match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
                    return True
        except Exception as e:
            print(f"Error getting CSRF token: {e}")
        return False
    
    def login(self):
        """Test login functionality"""
        print("\n🔐 Testing Authentication...")
        
        # Get login page and CSRF token
        if not self.get_csrf_token("/login"):
            return self.log_test("Login - Get CSRF Token", False, "Could not extract CSRF token")
        
        # Test login
        login_data = {
            'username': 'admin',
            'password': 'BecqSight2024!',
            'csrf_token': self.csrf_token
        }
        
        try:
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            if response.status_code == 200:
                return self.log_test("Login - Admin User", True)
            else:
                return self.log_test("Login - Admin User", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Login - Admin User", False, str(e))
    
    def test_conversation_management(self):
        """Test conversation creation, listing, and deletion"""
        print("\n💬 Testing Conversation Management...")
        
        # Get main page CSRF token
        if not self.get_csrf_token():
            return self.log_test("Conversation - Get CSRF Token", False)
        
        # Test conversation creation
        try:
            response = self.session.post(
                f"{self.base_url}/conversations/fresh",
                headers={
                    'Content-Type': 'application/json',
                    'X-CSRFToken': self.csrf_token
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.current_conversation_id = data.get('id')
                if self.current_conversation_id:
                    self.log_test("Conversation - Create New", True, f"ID: {self.current_conversation_id}")
                else:
                    return self.log_test("Conversation - Create New", False, "No conversation ID returned")
            else:
                return self.log_test("Conversation - Create New", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Conversation - Create New", False, str(e))
        
        # Test conversation listing
        try:
            response = self.session.get(f"{self.base_url}/conversations")
            if response.status_code == 200:
                conversations = response.json()
                self.log_test("Conversation - List All", True, f"Found {len(conversations)} conversations")
            else:
                return self.log_test("Conversation - List All", False, f"Status: {response.status_code}")
        except Exception as e:
            return self.log_test("Conversation - List All", False, str(e))
        
        return True
    
    def test_market_agent(self):
        """Test Market Analysis Agent"""
        print("\n📊 Testing Market Analysis Agent...")
        
        test_queries = [
            "What is the solar capacity in Germany?",
            "Show me a market share chart for France",
            "Compare solar capacity between Germany and Italy",
            "Generate a cumulative capacity trend for Spain"
        ]
        
        for i, query in enumerate(test_queries, 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/chat",
                    headers={
                        'Content-Type': 'application/json',
                        'X-CSRFToken': self.csrf_token
                    },
                    json={
                        'message': query,
                        'conversation_id': self.current_conversation_id,
                        'agent_type': 'market'
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'response' in data:
                        self.log_test(f"Market Agent - Query {i}", True, f"'{query[:30]}...'")
                    else:
                        self.log_test(f"Market Agent - Query {i}", False, "No response data")
                else:
                    self.log_test(f"Market Agent - Query {i}", False, f"Status: {response.status_code}")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                self.log_test(f"Market Agent - Query {i}", False, str(e))
    
    def test_module_prices_agent(self):
        """Test Module Prices Agent"""
        print("\n💰 Testing Module Prices Agent...")
        
        test_queries = [
            "Show module prices in China",
            "Create a chart of wafer prices in EU",
            "What are the current cell prices?",
            "Generate a boxplot of module prices by region"
        ]
        
        for i, query in enumerate(test_queries, 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/chat",
                    headers={
                        'Content-Type': 'application/json',
                        'X-CSRFToken': self.csrf_token
                    },
                    json={
                        'message': query,
                        'conversation_id': self.current_conversation_id,
                        'agent_type': 'price'
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'response' in data:
                        self.log_test(f"Module Prices Agent - Query {i}", True, f"'{query[:30]}...'")
                    else:
                        self.log_test(f"Module Prices Agent - Query {i}", False, "No response data")
                else:
                    self.log_test(f"Module Prices Agent - Query {i}", False, f"Status: {response.status_code}")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                self.log_test(f"Module Prices Agent - Query {i}", False, str(e))
    
    def test_news_agent(self):
        """Test News Agent"""
        print("\n📰 Testing News Agent...")
        
        test_queries = [
            "What are the latest developments in solar technology?",
            "Show me recent news about solar panel manufacturing",
            "Find news about major solar companies",
            "What's happening with solar energy policy in Europe?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/chat",
                    headers={
                        'Content-Type': 'application/json',
                        'X-CSRFToken': self.csrf_token
                    },
                    json={
                        'message': query,
                        'conversation_id': self.current_conversation_id,
                        'agent_type': 'news'
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'response' in data:
                        self.log_test(f"News Agent - Query {i}", True, f"'{query[:30]}...'")
                    else:
                        self.log_test(f"News Agent - Query {i}", False, "No response data")
                else:
                    self.log_test(f"News Agent - Query {i}", False, f"Status: {response.status_code}")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                self.log_test(f"News Agent - Query {i}", False, str(e))
    
    def test_agent_switching(self):
        """Test switching between agents in the same conversation"""
        print("\n🔄 Testing Agent Switching...")
        
        agents = ['market', 'price', 'news']
        
        for i, agent in enumerate(agents, 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/chat",
                    headers={
                        'Content-Type': 'application/json',
                        'X-CSRFToken': self.csrf_token
                    },
                    json={
                        'message': f"Test message for {agent} agent",
                        'conversation_id': self.current_conversation_id,
                        'agent_type': agent
                    }
                )
                
                if response.status_code == 200:
                    self.log_test(f"Agent Switching - {agent.title()}", True)
                else:
                    self.log_test(f"Agent Switching - {agent.title()}", False, f"Status: {response.status_code}")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                self.log_test(f"Agent Switching - {agent.title()}", False, str(e))
    
    def test_error_handling(self):
        """Test error handling and edge cases"""
        print("\n⚠️ Testing Error Handling...")
        
        # Test invalid conversation ID
        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                headers={
                    'Content-Type': 'application/json',
                    'X-CSRFToken': self.csrf_token
                },
                json={
                    'message': 'Test message',
                    'conversation_id': 99999,  # Invalid ID
                    'agent_type': 'market'
                }
            )
            
            if response.status_code in [400, 404, 500]:
                self.log_test("Error Handling - Invalid Conversation ID", True, f"Expected error: {response.status_code}")
            else:
                self.log_test("Error Handling - Invalid Conversation ID", False, f"Unexpected status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Error Handling - Invalid Conversation ID", False, str(e))
        
        # Test invalid agent type
        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                headers={
                    'Content-Type': 'application/json',
                    'X-CSRFToken': self.csrf_token
                },
                json={
                    'message': 'Test message',
                    'conversation_id': self.current_conversation_id,
                    'agent_type': 'invalid_agent'
                }
            )
            
            if response.status_code in [400, 404, 500]:
                self.log_test("Error Handling - Invalid Agent Type", True, f"Expected error: {response.status_code}")
            else:
                self.log_test("Error Handling - Invalid Agent Type", False, f"Unexpected status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Error Handling - Invalid Agent Type", False, str(e))
    
    def test_performance(self):
        """Test application performance"""
        print("\n⚡ Testing Performance...")
        
        # Test response time for a simple query
        start_time = time.time()
        
        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                headers={
                    'Content-Type': 'application/json',
                    'X-CSRFToken': self.csrf_token
                },
                json={
                    'message': 'Hello',
                    'conversation_id': self.current_conversation_id,
                    'agent_type': 'market'
                }
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200 and response_time < 10:  # 10 second timeout
                self.log_test("Performance - Response Time", True, f"{response_time:.2f}s")
            else:
                self.log_test("Performance - Response Time", False, f"Slow response: {response_time:.2f}s")
                
        except Exception as e:
            self.log_test("Performance - Response Time", False, str(e))
    
    def test_security(self):
        """Test security features"""
        print("\n🔒 Testing Security...")
        
        # Test CSRF protection
        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                headers={
                    'Content-Type': 'application/json'
                    # Missing CSRF token
                },
                json={
                    'message': 'Test message',
                    'conversation_id': self.current_conversation_id,
                    'agent_type': 'market'
                }
            )
            
            if response.status_code == 400:  # CSRF validation should fail
                self.log_test("Security - CSRF Protection", True, "CSRF validation working")
            else:
                self.log_test("Security - CSRF Protection", False, f"Unexpected status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Security - CSRF Protection", False, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 COMPREHENSIVE TEST SUITE")
        print("=" * 50)
        print(f"Testing application at: {self.base_url}")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Run all test categories
        tests = [
            self.login,
            self.test_conversation_management,
            self.test_market_agent,
            self.test_module_prices_agent,
            self.test_news_agent,
            self.test_agent_switching,
            self.test_error_handling,
            self.test_performance,
            self.test_security
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "=" * 50)
        
        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! Application is ready for deployment!")
        else:
            print("⚠️  Some tests failed. Please review and fix issues before deployment.")
        
        return failed_tests == 0

if __name__ == "__main__":
    test_suite = ComprehensiveTestSuite()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1) 