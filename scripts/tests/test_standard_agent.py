#!/usr/bin/env python3
"""
Test script to verify Logfire works with standard Pydantic AI Agent
"""

import os
import logfire
from pydantic_ai import Agent

# Set OpenAI API key (you'll need to set this)
# os.environ['OPENAI_API_KEY'] = 'your-api-key-here'  # Use environment variable instead

# Configure Logfire
logfire.configure(token='pylf_v1_eu_X1ChXTrsNRcg6rZVy3kVK3DD4m4psCcmYP49KQSfRsm2')
logfire.instrument_pydantic_ai()

def test_standard_agent():
    """Test with standard Pydantic AI Agent"""
    print("🔍 Testing Standard Pydantic AI Agent with Logfire...")
    
    # Create standard agent (this should be instrumented by Logfire)
    agent = Agent('openai:gpt-4o', instructions='Be concise, reply with one sentence.')
    
    # Run the agent
    result = agent.run_sync('What are the current module prices in China?')
    
    print(f"✅ Agent response: {result.output}")
    print("📊 Check Logfire dashboard for detailed LLM traces!")
    
    return result.output

if __name__ == "__main__":
    test_standard_agent() 