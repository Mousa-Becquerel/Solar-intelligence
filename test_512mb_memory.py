import asyncio
import os
import gc
import psutil
from module_prices_agent import ModulePricesAgent, ModulePricesConfig

def get_memory_mb():
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

async def test_512mb_memory_constraints():
    """Test if the agent can work within 512MB memory constraints"""
    
    print("="*60)
    print("TESTING 512MB MEMORY CONSTRAINTS")
    print("="*60)
    
    # Initialize agent with memory optimizations
    config = ModulePricesConfig(
        verbose=False,  # Reduce log overhead
        low_memory_mode=True,  # Enable memory optimizations
        max_conversation_messages=10,  # Limit conversation history
        enable_gc_after_operations=True,  # Force garbage collection
        total_tokens_limit=8000  # Reduce token limit
    )
    
    print(f"Starting memory: {get_memory_mb():.1f}MB")
    
    agent = ModulePricesAgent(config)
    print(f"After agent init: {get_memory_mb():.1f}MB")
    
    # Test operations with memory monitoring
    test_operations = [
        "show me module prices in China",
        "plot module prices in China",
        "list modules in EU",
        "plot modules in EU and US",
        "show box plots of modules in China"
    ]
    
    max_memory = 0
    
    for i, operation in enumerate(test_operations):
        print(f"\n--- Operation {i+1}: {operation} ---")
        
        memory_before = get_memory_mb()
        print(f"Memory before: {memory_before:.1f}MB")
        
        try:
            # Use a new conversation ID each time to avoid memory buildup
            result = await agent.analyze(operation, conversation_id=f"test_512_{i}")
            
            memory_after = get_memory_mb()
            max_memory = max(max_memory, memory_after)
            
            print(f"Memory after: {memory_after:.1f}MB")
            print(f"Memory delta: +{memory_after - memory_before:.1f}MB")
            
            # Check if operation was successful
            if "PLOT_GENERATED" in str(result.get('analysis', '')):
                print("✅ Plot generated successfully")
            elif "DATAFRAME_RESULT" in str(result.get('analysis', '')):
                print("✅ Data table generated successfully")
            else:
                print("✅ Text response generated successfully")
            
            # Force cleanup between operations
            gc.collect()
            
            # Check if we're approaching 512MB limit
            if memory_after > 400:
                print(f"⚠️  WARNING: Approaching 512MB limit!")
            
        except Exception as e:
            print(f"❌ FAILED: {e}")
            break
    
    print(f"\n" + "="*60)
    print("MEMORY TEST RESULTS")
    print("="*60)
    print(f"Peak memory usage: {max_memory:.1f}MB")
    print(f"Final memory usage: {get_memory_mb():.1f}MB")
    
    if max_memory <= 400:
        print("✅ SAFE for 512MB deployment")
    elif max_memory <= 450:
        print("⚠️  RISKY but might work on 512MB")
    else:
        print("❌ TOO HIGH for 512MB deployment")
    
    # Test conversation memory cleanup
    print(f"\nConversation memory: {agent.get_conversation_memory_info()}")
    
    # Clear all memory
    agent.clear_conversation_memory()
    gc.collect()
    
    final_memory = get_memory_mb()
    print(f"After cleanup: {final_memory:.1f}MB")
    
    return max_memory

async def stress_test_512mb():
    """Stress test with aggressive memory constraints"""
    print("\n" + "="*60)
    print("STRESS TEST FOR 512MB")
    print("="*60)
    
    config = ModulePricesConfig(
        verbose=False,
        low_memory_mode=True,
        max_conversation_messages=5,  # Very limited history
        enable_gc_after_operations=True,
        total_tokens_limit=5000,  # Lower token limit
        request_limit=5  # Fewer requests
    )
    
    agent = ModulePricesAgent(config)
    
    # Run many operations to test memory stability
    operations = [
        "plot module prices in China",
        "plot module prices in EU", 
        "plot module prices in US",
        "show modules in China",
        "show modules in EU",
        "plot wafer prices in China",
        "plot cell prices in China"
    ]
    
    memories = []
    conversation_id = "stress_test"
    
    for i, op in enumerate(operations):
        try:
            memory_before = get_memory_mb()
            
            # Use same conversation ID to test memory buildup
            result = await agent.analyze(op, conversation_id=conversation_id)
            
            memory_after = get_memory_mb()
            memories.append(memory_after)
            
            print(f"Op {i+1}: {memory_after:.1f}MB (+{memory_after-memory_before:.1f}MB)")
            
            # Check for memory leaks
            if i > 2 and memory_after > memories[0] + 100:
                print(f"⚠️  Potential memory leak detected!")
                break
                
        except Exception as e:
            print(f"❌ Failed at operation {i+1}: {e}")
            break
    
    peak_stress = max(memories) if memories else 0
    print(f"\nStress test peak: {peak_stress:.1f}MB")
    
    return peak_stress

async def main():
    """Run 512MB memory tests"""
    
    # Check system memory first
    system_memory = psutil.virtual_memory()
    print(f"System total RAM: {system_memory.total/1024/1024/1024:.1f}GB")
    print(f"Available RAM: {system_memory.available/1024/1024:.1f}MB")
    
    # Run basic test
    peak_basic = await test_512mb_memory_constraints()
    
    # Run stress test
    peak_stress = await stress_test_512mb()
    
    # Final recommendation
    print("\n" + "="*60)
    print("FINAL 512MB RECOMMENDATION")
    print("="*60)
    
    overall_peak = max(peak_basic, peak_stress)
    print(f"Overall peak memory: {overall_peak:.1f}MB")
    
    if overall_peak <= 380:
        print("✅ RECOMMENDED: Should work well on 512MB")
        print("   - Use low_memory_mode=True")
        print("   - Monitor memory in production")
    elif overall_peak <= 420:
        print("⚠️  POSSIBLE: Might work on 512MB with risks")
        print("   - MUST use low_memory_mode=True")
        print("   - Enable enable_gc_after_operations=True")
        print("   - Limit max_conversation_messages=5")
        print("   - Monitor closely and be ready to upgrade")
    else:
        print("❌ NOT RECOMMENDED: Too risky for 512MB")
        print("   - Upgrade to 1GB minimum")
        print("   - Or implement more aggressive optimizations")

if __name__ == "__main__":
    if os.name == 'nt':  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main()) 