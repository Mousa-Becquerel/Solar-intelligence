#!/usr/bin/env python3
"""
Test script to verify Weaviate connection works
"""

import os
import weaviate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_weaviate_connection():
    """Test basic Weaviate connection"""
    print("🔍 Testing Weaviate Connection...")
    
    try:
        # Connect to Weaviate
        headers = {
            "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
        }
        
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url="aohlqwhyrewcwkuxvurwlg.c0.europe-west3.gcp.weaviate.cloud",
            auth_credentials="THIrblRoMzV6ck9WUmxGRl9ZZktJZ1ZyaDJ4THM5bVFwcDVqWXJ0RXUvay9oa29iYzBlNEo1d3pBcVJVPV92MjAw",
            headers=headers,
        )
        
        print("✅ Weaviate connection successful")
        
        # Test QueryAgent
        from weaviate.agents.query import QueryAgent
        
        qa = QueryAgent(
            client=client,
            collections=["PV_news"]
        )
        
        print("✅ QueryAgent initialized")
        
        # Test a simple query
        response = qa.run("solar energy")
        print(f"✅ Query successful: {response.final_answer[:200]}...")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Weaviate connection failed: {e}")
        return False

if __name__ == "__main__":
    test_weaviate_connection() 