# Example: How to enable low_memory_mode for 512MB deployment

from module_prices_agent import ModulePricesAgent, ModulePricesConfig

# Option 1: Create config with low memory optimizations
def create_512mb_agent():
    """Create a module prices agent optimized for 512MB RAM"""
    
    config = ModulePricesConfig(
        # Memory optimizations for 512MB
        low_memory_mode=True,                   # Enable all memory optimizations
        max_conversation_messages=10,           # Limit conversation history
        enable_gc_after_operations=True,        # Force garbage collection
        
        # Performance settings for 512MB
        total_tokens_limit=8000,                # Reduce from default 15000
        request_limit=5,                        # Reduce from default 10
        verbose=False,                          # Reduce logging overhead
        
        # Core settings (usually don't change these)
        model="openai:gpt-4o",
        llm_model="openai:gpt-4o"
    )
    
    agent = ModulePricesAgent(config)
    return agent

# Option 2: Minimal configuration (if you only want to enable low memory mode)
def create_minimal_512mb_agent():
    """Create agent with minimal 512MB configuration"""
    
    config = ModulePricesConfig(low_memory_mode=True)
    agent = ModulePricesAgent(config)
    return agent

# Option 3: For production deployment
def create_production_512mb_agent():
    """Create production-ready agent for 512MB deployment"""
    
    config = ModulePricesConfig(
        # Essential 512MB optimizations
        low_memory_mode=True,
        max_conversation_messages=5,            # Even more aggressive for production
        enable_gc_after_operations=True,
        
        # Production settings
        total_tokens_limit=6000,                # Conservative for 512MB
        request_limit=3,                        # Conservative for 512MB
        verbose=False,                          # Never verbose in production
    )
    
    agent = ModulePricesAgent(config)
    return agent

# Usage examples:
if __name__ == "__main__":
    # For development/testing
    agent = create_512mb_agent()
    
    # For production
    # agent = create_production_512mb_agent()
    
    print("Agent created with 512MB optimizations enabled!")
    print(f"Low memory mode: {agent.config.low_memory_mode}")
    print(f"Max conversation messages: {agent.config.max_conversation_messages}")
    print(f"GC after operations: {agent.config.enable_gc_after_operations}") 