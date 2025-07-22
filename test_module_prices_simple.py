"""
Simple test for Module Prices Agent with India queries
"""

import asyncio
from module_prices_agent import ModulePricesAgent, ModulePricesConfig

async def test_india_queries():
    """Test queries related to India pricing data"""
    
    try:
        # Initialize the agent
        config = ModulePricesConfig(verbose=True)
        agent = ModulePricesAgent(config)
        
        # Test queries that should work with India data
        test_queries = [
            "Show me all solar module prices available for India",
            "What solar module pricing data is available for India?",
            "Retrieve the prices of modules in India",
            "What are the latest module prices for India?",
            "Show price trends for solar modules in India"
        ]
        
        print("=== Testing India Pricing Queries ===\n")
        
        for i, query in enumerate(test_queries, 1):
            print(f"Query {i}: {query}")
            print("-" * 60)
            
            result = await agent.analyze(query)
            
            if result["success"]:
                print(f"✅ SUCCESS")
                print(f"Response: {result['analysis'][:200]}...")
                if result["usage"]:
                    print(f"Usage: {result['usage']}")
            else:
                print(f"❌ ERROR: {result['error']}")
            
            print("\n" + "="*70 + "\n")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_india_queries()) 