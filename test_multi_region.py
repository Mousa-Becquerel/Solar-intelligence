import asyncio
import os
from module_prices_agent import ModulePricesAgent, ModulePricesConfig

async def test_multi_region_extraction():
    """Test if multiple regions are properly extracted and passed to plotting tools"""
    
    print("Testing multi-region parameter extraction...")
    
    # Initialize agent
    config = ModulePricesConfig(verbose=True)
    agent = ModulePricesAgent(config)
    
    test_queries = [
        "plot module prices in China and EU",
        "show module prices in EU and US", 
        "chart wafer prices in China, EU, and US",
        "plot prices in both China and EU",
        "show box plots of modules in EU and US"
    ]
    
    for i, query in enumerate(test_queries):
        print(f"\n=== Test {i+1}: {query} ===")
        
        try:
            result = await agent.analyze(query, conversation_id=f"test_multi_{i}")
            
            # Check if plot was generated
            if "PLOT_GENERATED" in str(result.get('analysis', '')):
                print("✅ SUCCESS - Plot generated")
            else:
                print("❌ FAILED - No plot generated")
                print(f"Response: {result.get('analysis', 'No response')}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    # Handle Windows asyncio event loop issues
    if os.name == 'nt':  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(test_multi_region_extraction()) 