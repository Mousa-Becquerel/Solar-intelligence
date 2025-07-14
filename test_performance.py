#!/usr/bin/env python3
"""
Performance test to check agent initialization and response times
"""
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_agent_initialization():
    """Test how long agent initialization takes"""
    print("🚀 Testing Agent Initialization Performance")
    print("=" * 50)
    
    try:
        start_time = time.time()
        from pydantic_weaviate_agent import get_pydantic_weaviate_agent
        
        # Get the agent
        agent = get_pydantic_weaviate_agent()
        init_time = time.time() - start_time
        
        if not agent:
            print("❌ FAILED: Agent not available")
            return False
        
        print(f"✅ Agent initialized in {init_time:.2f} seconds")
        
        # Test agent info
        start_time = time.time()
        agent_info = agent.get_agent_info()
        info_time = time.time() - start_time
        
        print(f"✅ Agent info retrieved in {info_time:.2f} seconds")
        print(f"📊 Agent status: {agent_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error testing agent initialization: {e}")
        return False

def test_query_performance():
    """Test query response time"""
    print("\n🚀 Testing Query Performance")
    print("=" * 50)
    
    try:
        from pydantic_weaviate_agent import get_pydantic_weaviate_agent
        
        # Get the agent
        agent = get_pydantic_weaviate_agent()
        if not agent:
            print("❌ FAILED: Agent not available")
            return False
        
        conversation_id = "perf_test_123"
        
        # Test simple query
        start_time = time.time()
        response = agent.process_query("Hello", conversation_id=conversation_id)
        query_time = time.time() - start_time
        
        print(f"✅ Simple query completed in {query_time:.2f} seconds")
        print(f"📝 Response length: {len(response)} characters")
        
        # Test data query
        start_time = time.time()
        response = agent.process_query("What is Germany's solar capacity in 2023?", conversation_id=conversation_id)
        data_query_time = time.time() - start_time
        
        print(f"✅ Data query completed in {data_query_time:.2f} seconds")
        print(f"📝 Response length: {len(response)} characters")
        
        # Check memory
        memory_info = agent.get_conversation_memory_info()
        print(f"📊 Memory info: {memory_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error testing query performance: {e}")
        return False

def test_memory_cleanup_performance():
    """Test memory cleanup performance"""
    print("\n🚀 Testing Memory Cleanup Performance")
    print("=" * 50)
    
    try:
        from pydantic_weaviate_agent import get_pydantic_weaviate_agent
        from app import cleanup_memory
        
        # Get the agent
        agent = get_pydantic_weaviate_agent()
        if not agent:
            print("❌ FAILED: Agent not available")
            return False
        
        # Add some conversations to memory
        for i in range(3):
            agent.process_query(f"Test message {i}", conversation_id=f"test_{i}")
        
        # Test cleanup performance
        start_time = time.time()
        cleanup_memory()
        cleanup_time = time.time() - start_time
        
        print(f"✅ Memory cleanup completed in {cleanup_time:.2f} seconds")
        
        # Check memory after cleanup
        memory_info = agent.get_conversation_memory_info()
        print(f"📊 Memory after cleanup: {memory_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error testing memory cleanup performance: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Performance Tests")
    print("=" * 60)
    
    # Test 1: Agent initialization
    test1_passed = test_agent_initialization()
    
    # Test 2: Query performance
    test2_passed = test_query_performance()
    
    # Test 3: Memory cleanup performance
    test3_passed = test_memory_cleanup_performance()
    
    print("\n" + "=" * 60)
    print("📋 Performance Test Results:")
    print(f"   Agent Initialization: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   Query Performance: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print(f"   Memory Cleanup: {'✅ PASSED' if test3_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed and test3_passed:
        print("\n🎉 All performance tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some performance tests failed.")
        sys.exit(1) 