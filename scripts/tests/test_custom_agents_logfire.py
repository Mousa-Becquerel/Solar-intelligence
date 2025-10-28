#!/usr/bin/env python3
"""
Test script to verify Logfire works with custom agents
"""

import os
import asyncio
import logfire

# Set OpenAI API key
# os.environ['OPENAI_API_KEY'] = 'your-api-key-here'  # Use environment variable instead

# Configure Logfire
logfire.configure(token='pylf_v1_eu_X1ChXTrsNRcg6rZVy3kVK3DD4m4psCcmYP49KQSfRsm2')
logfire.instrument_pydantic_ai()

async def test_custom_agents():
    """Test custom agents with Logfire instrumentation"""
    print("🔍 Testing Custom Agents with Logfire...")
    
    # Test PydanticWeaviateAgent
    print("\n📊 Testing PydanticWeaviateAgent...")
    try:
        from pydantic_weaviate_agent import get_pydantic_weaviate_agent
        
        agent = get_pydantic_weaviate_agent()
        if agent:
            result = agent.process_query("What are the current market trends for solar installations?", conversation_id="test-1")
            print(f"✅ PydanticWeaviateAgent response: {str(result)[:200]}...")
        else:
            print("❌ PydanticWeaviateAgent not available")
    except Exception as e:
        print(f"❌ PydanticWeaviateAgent error: {e}")
    
    # Test ModulePricesAgent
    print("\n💰 Testing ModulePricesAgent...")
    try:
        from module_prices_agent import ModulePricesAgent, ModulePricesConfig
        
        config = ModulePricesConfig()
        agent = ModulePricesAgent(config)
        
        result = await agent.analyze("What are the current module prices in China?", conversation_id="test-2")
        print(f"✅ ModulePricesAgent response: {result.get('analysis', 'No analysis')[:200]}...")
    except Exception as e:
        print(f"❌ ModulePricesAgent error: {e}")
    
    print("\n📊 Check Logfire dashboard for detailed traces!")
    print("You should see:")
    print("  - pydantic_weaviate_agent_call spans")
    print("  - module_prices_agent_call spans")
    print("  - Detailed LLM interaction information")

if __name__ == "__main__":
    asyncio.run(test_custom_agents()) 