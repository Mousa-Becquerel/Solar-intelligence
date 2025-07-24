import psutil
import matplotlib.pyplot as plt
import pandas as pd
import gc
import tracemalloc
from functools import wraps
import time
import asyncio
import os
import sys

# Import the module prices agent directly
from module_prices_agent import ModulePricesAgent, ModulePricesConfig

class MemoryProfiler:
    def __init__(self):
        self.measurements = []
        self.peak_memory = 0
        
    def get_memory_mb(self):
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def get_system_memory(self):
        """Get system memory info"""
        memory = psutil.virtual_memory()
        return {
            'total_mb': memory.total / 1024 / 1024,
            'available_mb': memory.available / 1024 / 1024,
            'used_mb': memory.used / 1024 / 1024,
            'percent': memory.percent
        }
    
    def measure_point(self, label):
        """Record a measurement point"""
        current_mb = self.get_memory_mb()
        system = self.get_system_memory()
        
        measurement = {
            'label': label,
            'process_memory_mb': current_mb,
            'system_available_mb': system['available_mb'],
            'system_used_percent': system['percent'],
            'timestamp': time.time()
        }
        
        self.measurements.append(measurement)
        self.peak_memory = max(self.peak_memory, current_mb)
        
        print(f"{label}: Process={current_mb:.1f}MB, Available={system['available_mb']:.1f}MB, Peak={self.peak_memory:.1f}MB")
        return measurement
    
    def profile_function(self, func):
        """Decorator to profile a function's memory usage"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Start detailed memory tracking
            tracemalloc.start()
            
            self.measure_point(f"Before {func.__name__}")
            gc.collect()
            
            try:
                result = func(*args, **kwargs)
                self.measure_point(f"After {func.__name__}")
                
                # Get detailed tracemalloc info
                current, peak = tracemalloc.get_traced_memory()
                print(f"  Tracemalloc - Current: {current/1024/1024:.1f}MB, Peak: {peak/1024/1024:.1f}MB")
                
                return result
            except Exception as e:
                self.measure_point(f"Error in {func.__name__}")
                raise e
            finally:
                tracemalloc.stop()
                gc.collect()
                
        return wrapper
    
    def profile_async_function(self, func):
        """Decorator to profile an async function's memory usage"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Start detailed memory tracking
            tracemalloc.start()
            
            self.measure_point(f"Before {func.__name__}")
            gc.collect()
            
            try:
                result = await func(*args, **kwargs)
                self.measure_point(f"After {func.__name__}")
                
                # Get detailed tracemalloc info
                current, peak = tracemalloc.get_traced_memory()
                print(f"  Tracemalloc - Current: {current/1024/1024:.1f}MB, Peak: {peak/1024/1024:.1f}MB")
                
                return result
            except Exception as e:
                self.measure_point(f"Error in {func.__name__}")
                raise e
            finally:
                tracemalloc.stop()
                gc.collect()
                
        return wrapper
    
    def get_memory_report(self):
        """Generate memory usage report"""
        if len(self.measurements) < 2:
            return "Not enough measurements"
        
        baseline = self.measurements[0]['process_memory_mb']
        peak = max(m['process_memory_mb'] for m in self.measurements)
        final = self.measurements[-1]['process_memory_mb']
        
        print("\n" + "="*60)
        print("MEMORY USAGE REPORT")
        print("="*60)
        print(f"Baseline memory: {baseline:.1f}MB")
        print(f"Peak memory: {peak:.1f}MB")
        print(f"Final memory: {final:.1f}MB")
        print(f"Memory increase: {peak - baseline:.1f}MB")
        print(f"Memory leaked: {final - baseline:.1f}MB")
        print(f"Recommended minimum RAM: {peak * 1.5:.1f}MB (with 50% safety margin)")
        print("="*60)
        
        return {
            'baseline_mb': baseline,
            'peak_mb': peak,
            'memory_increase_mb': peak - baseline,
            'recommended_ram_mb': peak * 1.5
        }

# Test your specific module prices agent
async def test_module_prices_agent_memory():
    """Test memory usage of your module prices agent operations"""
    profiler = MemoryProfiler()
    
    # Test agent initialization
    @profiler.profile_function
    def init_agent():
        profiler.measure_point("Start agent initialization")
        config = ModulePricesConfig(verbose=True)
        agent = ModulePricesAgent(config)
        profiler.measure_point("Agent initialized")
        return agent
    
    # Test data queries
    @profiler.profile_async_function
    async def test_data_query(agent, query):
        profiler.measure_point(f"Start data query: {query}")
        result = await agent.analyze(query, conversation_id="memory_test")
        profiler.measure_point(f"Data query completed")
        return result
    
    # Test plotting operations
    @profiler.profile_async_function  
    async def test_plotting(agent, query):
        profiler.measure_point(f"Start plotting: {query}")
        result = await agent.analyze(query, conversation_id="memory_test")
        profiler.measure_point(f"Plotting completed")
        return result
    
    # Test conversation memory
    @profiler.profile_function
    def test_conversation_memory(agent):
        profiler.measure_point("Check conversation memory")
        memory_info = agent.get_conversation_memory_info()
        print(f"Conversation memory: {memory_info}")
        profiler.measure_point("Memory check completed")
        return memory_info
    
    # Run the tests
    print("Testing memory usage for Module Prices Agent...")
    
    profiler.measure_point("Application start")
    
    # Test 1: Agent initialization
    agent = init_agent()
    
    # Test 2: Simple data query
    await test_data_query(agent, "show me module prices in China")
    
    # Test 3: Data query with table results
    await test_data_query(agent, "list all modules available in EU")
    
    # Test 4: Simple plot
    await test_plotting(agent, "plot module prices in China")
    
    # Test 5: Complex plot (boxplot)
    await test_plotting(agent, "show box plots of different modules in China")
    
    # Test 6: Multiple regions plot
    await test_plotting(agent, "plot module prices in China and EU")
    
    # Test 7: Check conversation memory
    test_conversation_memory(agent)
    
    # Test 8: Clear memory and check again
    agent.clear_conversation_memory()
    test_conversation_memory(agent)
    
    # Generate report
    report = profiler.get_memory_report()
    
    return report, profiler.measurements

# Test different plotting scenarios
async def test_plotting_scenarios():
    """Test different plotting scenarios to identify memory bottlenecks"""
    profiler = MemoryProfiler()
    
    profiler.measure_point("Plotting scenarios start")
    
    # Initialize agent once
    config = ModulePricesConfig(verbose=False)  # Reduce verbosity for cleaner output
    agent = ModulePricesAgent(config)
    
    plotting_scenarios = [
        "plot module prices in China",
        "plot module prices in EU and US", 
        "show box plots of different modules in China",
        "plot average prices by description for modules",
        "plot wafer prices in all regions",
        "show price distribution for cells in India"
    ]
    
    results = {}
    
    for i, scenario in enumerate(plotting_scenarios):
        print(f"\n--- Scenario {i+1}: {scenario} ---")
        
        try:
            profiler.measure_point(f"Start scenario {i+1}")
            result = await agent.analyze(scenario, conversation_id=f"test_{i}")
            profiler.measure_point(f"End scenario {i+1}")
            
            # Check if plot was generated
            if "PLOT_GENERATED" in str(result.get('analysis', '')):
                results[scenario] = "SUCCESS - Plot generated"
            elif "DATAFRAME_RESULT" in str(result.get('analysis', '')):
                results[scenario] = "SUCCESS - Data table generated"
            else:
                results[scenario] = "SUCCESS - Text response"
                
        except Exception as e:
            results[scenario] = f"FAILED: {str(e)}"
            profiler.measure_point(f"Error scenario {i+1}")
            print(f"❌ Scenario failed: {e}")
    
    print(f"\nPlotting scenarios results:")
    for scenario, result in results.items():
        print(f"  {scenario}: {result}")
    
    return results, profiler.measurements

# Quick memory checker for current system
def check_current_memory():
    """Quick check of current memory situation"""
    memory = psutil.virtual_memory()
    process = psutil.Process()
    
    print("CURRENT MEMORY STATUS:")
    print(f"Total system RAM: {memory.total/1024/1024/1024:.1f}GB")
    print(f"Available RAM: {memory.available/1024/1024:.1f}MB")
    print(f"Used RAM: {memory.percent:.1f}%")
    print(f"Current process: {process.memory_info().rss/1024/1024:.1f}MB")
    print(f"Free for plotting: {memory.available/1024/1024:.1f}MB")
    
    if memory.available < 200 * 1024 * 1024:  # Less than 200MB
        print("⚠️  WARNING: Very low available memory!")
    elif memory.available < 500 * 1024 * 1024:  # Less than 500MB  
        print("⚠️  CAUTION: Limited memory available")
    else:
        print("✅ Memory looks sufficient")

# Stress test with multiple consecutive operations
async def stress_test_operations():
    """Test memory usage with multiple consecutive operations"""
    profiler = MemoryProfiler()
    
    profiler.measure_point("Stress test start")
    
    config = ModulePricesConfig(verbose=False)
    agent = ModulePricesAgent(config)
    
    # Simulate heavy usage
    operations = [
        "show me module prices in China",
        "plot module prices in China", 
        "list all modules in EU",
        "plot module prices in EU",
        "show box plots of modules in US",
        "plot average prices for wafers",
        "show me cell prices in India",
        "plot cell prices in India and China",
        "show price distribution for all components",
        "plot module prices trends over time"
    ]
    
    results = {}
    
    for i, operation in enumerate(operations):
        print(f"\n--- Operation {i+1}: {operation} ---")
        
        try:
            profiler.measure_point(f"Start operation {i+1}")
            result = await agent.analyze(operation, conversation_id="stress_test")
            profiler.measure_point(f"End operation {i+1}")
            
            results[f"op_{i+1}"] = "SUCCESS"
            
            # Force garbage collection between operations
            gc.collect()
            
        except Exception as e:
            results[f"op_{i+1}"] = f"FAILED: {str(e)}"
            print(f"❌ Operation failed: {e}")
            break
    
    # Check final memory state
    memory_info = agent.get_conversation_memory_info()
    print(f"\nFinal conversation memory: {memory_info}")
    
    report = profiler.get_memory_report()
    
    return results, report, profiler.measurements

async def main():
    """Main test runner"""
    print("="*60)
    print("MODULE PRICES AGENT MEMORY PROFILING")
    print("="*60)
    
    # Step 1: Check current memory
    check_current_memory()
    
    print("\n" + "="*60)
    print("TEST 1: BASIC AGENT OPERATIONS")
    print("="*60)
    
    # Step 2: Test basic operations
    try:
        report1, measurements1 = await test_module_prices_agent_memory()
    except Exception as e:
        print(f"❌ Basic operations test failed: {e}")
        return
    
    print("\n" + "="*60)
    print("TEST 2: PLOTTING SCENARIOS")
    print("="*60)
    
    # Step 3: Test plotting scenarios
    try:
        results2, measurements2 = await test_plotting_scenarios()
    except Exception as e:
        print(f"❌ Plotting scenarios test failed: {e}")
    
    print("\n" + "="*60)
    print("TEST 3: STRESS TEST")
    print("="*60)
    
    # Step 4: Stress test
    try:
        results3, report3, measurements3 = await stress_test_operations()
    except Exception as e:
        print(f"❌ Stress test failed: {e}")
    
    # Final recommendations
    print("\n" + "="*60)
    print("FINAL RECOMMENDATIONS")
    print("="*60)
    
    peak_memory = max(
        report1.get('peak_mb', 0),
        report3.get('peak_mb', 0) if 'report3' in locals() else 0
    )
    
    print(f"Peak memory usage: {peak_memory:.1f}MB")
    
    if peak_memory <= 256:
        print("✅ 512MB RAM should be sufficient (Free tier)")
    elif peak_memory <= 1024:
        print("✅ 1GB RAM recommended (Basic tier)")
    elif peak_memory <= 2048:
        print("✅ 2GB RAM recommended (Standard tier)")
    else:
        print(f"⚠️  {peak_memory/1024:.1f}GB+ RAM needed (Pro tier)")
    
    print("\n🎯 OPTIMIZATION SUGGESTIONS:")
    print("1. Use plt.close() after each plot (already implemented)")
    print("2. Clear conversation memory periodically for long sessions")
    print("3. Monitor memory usage in production")
    print("4. Consider data pagination for very large datasets")

if __name__ == "__main__":
    # Handle Windows asyncio event loop issues
    if os.name == 'nt':  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main()) 