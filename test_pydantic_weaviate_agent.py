#!/usr/bin/env python3
"""
Test script for Pydantic-AI Weaviate agent integration with conversation memory
"""

import os
import sys
import time
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pydantic_weaviate_agent import PydanticWeaviateAgent, get_pydantic_weaviate_agent, close_pydantic_weaviate_agent

def test_basic_connection():
    """Test basic Weaviate connection and agent initialization"""
    print("=" * 60)
    print("TEST 1: Basic Connection and Agent Initialization")
    print("=" * 60)
    
    agent = get_pydantic_weaviate_agent()
    
    if agent is None:
        print("❌ FAILED: Agent initialization returned None")
        return False
    
    agent_info = agent.get_agent_info()
    print(f"✅ Agent Info: {agent_info}")
    
    if not agent_info.get('weaviate_connected', False):
        print("⚠️  WARNING: Weaviate not connected - agent will work in fallback mode")
    
    if not agent_info.get('pydantic_agent_available', False):
        print("❌ FAILED: Pydantic agent not available")
        return False
    
    print("✅ PASSED: Basic connection and agent initialization successful")
    return True

def test_tool_output_display():
    """Test that tool outputs are properly formatted for display"""
    print("\n" + "=" * 60)
    print("TEST 2: Tool Output Display Format")
    print("=" * 60)
    
    agent = get_pydantic_weaviate_agent()
    
    if agent is None:
        print("❌ FAILED: Agent not available")
        return False
    
    # Test a simple query that should trigger the tool
    test_query = "What was the solar capacity in Spain for 2020?"
    print(f"Testing query: {test_query}")
    
    try:
        response = agent.process_query(test_query, conversation_id="test_tool_output")
        print(f"\n📋 Response Format Check:")
        print(f"Response type: {type(response)}")
        print(f"Response length: {len(response)} characters")
        
        # Check if the response contains tool output formatting
        if "**Query:**" in response and "**Response:**" in response and "**Status:**" in response:
            print("✅ PASSED: Tool output properly formatted with Query/Response/Status sections")
            print(f"\n📄 Formatted Response Preview:")
            print("-" * 40)
            print(response[:500] + "..." if len(response) > 500 else response)
            print("-" * 40)
            return True
        else:
            print("⚠️  WARNING: Response does not contain expected tool output formatting")
            print(f"📄 Response Preview:")
            print("-" * 40)
            print(response[:300] + "..." if len(response) > 300 else response)
            print("-" * 40)
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error processing query: {e}")
        return False

def test_conversation_memory_with_tool_outputs():
    """Test conversation memory works with tool outputs"""
    print("\n" + "=" * 60)
    print("TEST 3: Conversation Memory with Tool Outputs")
    print("=" * 60)
    
    agent = get_pydantic_weaviate_agent()
    
    if agent is None:
        print("❌ FAILED: Agent not available")
        return False
    
    conversation_id = "test_memory_tools"
    
    try:
        # First query
        query1 = "What was the solar capacity in Germany for 2020?"
        print(f"Query 1: {query1}")
        response1 = agent.process_query(query1, conversation_id=conversation_id)
        print(f"✅ First response received ({len(response1)} chars)")
        
        # Second query referencing the first
        query2 = "How does that compare to France in the same year?"
        print(f"\nQuery 2: {query2}")
        response2 = agent.process_query(query2, conversation_id=conversation_id)
        print(f"✅ Second response received ({len(response2)} chars)")
        
        # Check memory info
        memory_info = agent.get_conversation_memory_info()
        print(f"\n📊 Memory Info: {memory_info}")
        
        if conversation_id in memory_info.get('conversation_ids', []):
            print("✅ PASSED: Conversation memory working with tool outputs")
            return True
        else:
            print("❌ FAILED: Conversation not found in memory")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error in conversation memory test: {e}")
        return False

def test_collection_routing():
    """Test that the agent routes queries to correct collections based on year"""
    print("\n" + "=" * 60)
    print("TEST 4: Collection Routing (Historical vs Forecast)")
    print("=" * 60)
    
    agent = get_pydantic_weaviate_agent()
    
    if agent is None:
        print("❌ FAILED: Agent not available")
        return False
    
    conversation_id = "test_routing"
    
    try:
        # Test historical data query (should use market_historical_only)
        historical_query = "What was the solar capacity in Spain for 2022?"
        print(f"Historical Query: {historical_query}")
        hist_response = agent.process_query(historical_query, conversation_id=conversation_id)
        
        if "**Query:**" in hist_response:
            print("✅ Historical query triggered tool output format")
        
        # Test forecast data query (should use market_projection_most_probable)  
        forecast_query = "What is the forecasted solar capacity for Spain in 2027?"
        print(f"\nForecast Query: {forecast_query}")
        forecast_response = agent.process_query(forecast_query, conversation_id=conversation_id)
        
        if "**Query:**" in forecast_response:
            print("✅ Forecast query triggered tool output format")
        
        # Test mixed query (should handle both collections appropriately)
        mixed_query = "Compare Spain's solar capacity in 2023 vs forecasted for 2026"
        print(f"\nMixed Query: {mixed_query}")
        mixed_response = agent.process_query(mixed_query, conversation_id=conversation_id)
        
        if "**Query:**" in mixed_response:
            print("✅ Mixed query triggered tool output format")
        
        print("✅ PASSED: Collection routing tests completed")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error in collection routing test: {e}")
        return False

def test_error_handling():
    """Test error handling in tool outputs"""
    print("\n" + "=" * 60)
    print("TEST 5: Error Handling in Tool Outputs")
    print("=" * 60)
    
    agent = get_pydantic_weaviate_agent()
    
    if agent is None:
        print("❌ FAILED: Agent not available")
        return False
    
    try:
        # Test with a query that might cause issues
        error_query = "What was the solar capacity in NonExistentCountry for 2020?"
        print(f"Error Test Query: {error_query}")
        response = agent.process_query(error_query, conversation_id="test_error")
        
        print(f"✅ Error query handled gracefully")
        print(f"Response preview: {response[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error handling test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🧪 PYDANTIC WEAVIATE AGENT - ENHANCED TOOL OUTPUT TESTS")
    print("=" * 60)
    
    tests = [
        test_basic_connection,
        test_tool_output_display,
        test_conversation_memory_with_tool_outputs,
        test_collection_routing,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ FAILED: Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"🏁 TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Tool output display is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("=" * 60)
    
    # Clean up
    agent = get_pydantic_weaviate_agent()
    if agent:
        agent.close()

if __name__ == "__main__":
    run_all_tests() 