#!/usr/bin/env python3
"""
Test script to verify conversation memory is working correctly
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_conversation_memory():
    """Test that conversation memory persists between messages"""
    print("🧪 Testing Conversation Memory")
    print("=" * 50)
    
    try:
        from pydantic_weaviate_agent import get_pydantic_weaviate_agent
        
        # Get the agent
        agent = get_pydantic_weaviate_agent()
        if not agent:
            print("❌ FAILED: Agent not available")
            return False
        
        conversation_id = "test_memory_123"
        
        # First query
        print(f"📝 Query 1: 'What is Germany's solar capacity in 2023?'")
        response1 = agent.process_query("What is Germany's solar capacity in 2023?", conversation_id=conversation_id)
        print(f"✅ Response 1 received ({len(response1)} chars)")
        
        # Check memory info
        memory_info = agent.get_conversation_memory_info()
        print(f"📊 Memory after query 1: {memory_info}")
        
        # Second query that should reference the first
        print(f"\n📝 Query 2: 'How does that compare to France?'")
        response2 = agent.process_query("How does that compare to France?", conversation_id=conversation_id)
        print(f"✅ Response 2 received ({len(response2)} chars)")
        
        # Check memory info again
        memory_info = agent.get_conversation_memory_info()
        print(f"📊 Memory after query 2: {memory_info}")
        
        # Verify conversation is in memory
        if conversation_id in memory_info.get('conversation_ids', []):
            print("✅ PASSED: Conversation memory is working!")
            print(f"   Conversation {conversation_id} has {memory_info['memory_usage'].get(conversation_id, 0)} messages")
            return True
        else:
            print("❌ FAILED: Conversation not found in memory")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error testing conversation memory: {e}")
        return False

def test_memory_cleanup():
    """Test that memory cleanup doesn't clear conversation memory"""
    print("\n🧪 Testing Memory Cleanup")
    print("=" * 50)
    
    try:
        from pydantic_weaviate_agent import get_pydantic_weaviate_agent
        from app import cleanup_memory
        
        # Get the agent
        agent = get_pydantic_weaviate_agent()
        if not agent:
            print("❌ FAILED: Agent not available")
            return False
        
        conversation_id = "test_cleanup_456"
        
        # Add a conversation to memory
        agent.process_query("Test message", conversation_id=conversation_id)
        
        # Check memory before cleanup
        memory_before = agent.get_conversation_memory_info()
        print(f"📊 Memory before cleanup: {memory_before}")
        
        # Run memory cleanup
        print("🧹 Running memory cleanup...")
        cleanup_memory()
        
        # Check memory after cleanup
        memory_after = agent.get_conversation_memory_info()
        print(f"📊 Memory after cleanup: {memory_after}")
        
        # Verify conversation is still in memory
        if conversation_id in memory_after.get('conversation_ids', []):
            print("✅ PASSED: Conversation memory preserved during cleanup!")
            return True
        else:
            print("❌ FAILED: Conversation memory was cleared during cleanup")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error testing memory cleanup: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Conversation Memory Tests")
    print("=" * 60)
    
    # Test 1: Basic conversation memory
    test1_passed = test_conversation_memory()
    
    # Test 2: Memory cleanup preservation
    test2_passed = test_memory_cleanup()
    
    print("\n" + "=" * 60)
    print("📋 Test Results:")
    print(f"   Conversation Memory: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   Memory Cleanup: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Conversation memory is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Check the implementation.")
        sys.exit(1) 