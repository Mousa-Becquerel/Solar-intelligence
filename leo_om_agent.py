"""
Leo - O&M Agent
===============

A Pydantic AI agent specialized in PV Operations & Maintenance (O&M) questions.
This agent provides guidance on solar plant operations, maintenance procedures,
troubleshooting, and best practices.
"""

import asyncio
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import uuid
from datetime import datetime
import json

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic import BaseModel
from dotenv import load_dotenv

# Logfire imports
import logfire

# Load environment variables
load_dotenv()

# === Output Models ===
class OMAnalysisResult(BaseModel):
    """Structured output for O&M analysis results"""
    content: str
    category: str  # e.g., "maintenance", "troubleshooting", "monitoring", "safety"
    confidence: float = 1.0
    success: bool = True
    error_message: Optional[str] = None

# === Agent Configuration ===
@dataclass
class LeoOMConfig:
    """Configuration for Leo O&M Agent"""
    model_name: str = "openai:gpt-4o"
    max_tokens: int = 4000
    temperature: float = 0.7
    conversation_memory_limit: int = 50

# === Memory Management ===
class ConversationMemory:
    """Simple in-memory conversation storage"""
    def __init__(self):
        self.conversations: Dict[str, List[ModelMessage]] = {}

    def get_messages(self, conversation_id: str) -> List[ModelMessage]:
        return self.conversations.get(conversation_id, [])

    def add_messages(self, conversation_id: str, messages: List[ModelMessage]):
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        self.conversations[conversation_id].extend(messages)

        # Limit conversation history to prevent memory growth
        max_messages = 50
        if len(self.conversations[conversation_id]) > max_messages:
            self.conversations[conversation_id] = self.conversations[conversation_id][-max_messages:]

    def clear_conversation(self, conversation_id: str):
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]

# Global memory instance
_conversation_memory = ConversationMemory()

# === Agent Definition ===
def create_leo_om_agent(config: LeoOMConfig) -> Agent:
    """Create the Leo O&M Agent with specialized knowledge"""

    system_prompt = """You are Leo, a specialized AI assistant for PV (Photovoltaic) Operations & Maintenance (O&M) with local knowledge of Trento, Italy.

    **Memory & Context:**
    - You have access to the full conversation history and can refer to previous questions and answers.
    - When users ask "what did I ask before" or similar questions, review the conversation history to answer.
    - Build upon previous context in multi-turn conversations.

    Your expertise covers:

    🔧 **Maintenance Procedures**
    - Preventive maintenance schedules and checklists
    - Corrective maintenance procedures
    - Component replacement guidelines
    - Cleaning and inspection protocols adapted to local climate (snow, dust, alpine conditions)

    ⚡ **Performance Monitoring**
    - Performance ratio analysis
    - Energy yield optimization
    - Fault detection and diagnosis
    - Data analysis and reporting

    🔍 **Troubleshooting**
    - Common PV system issues and solutions
    - Electrical troubleshooting procedures
    - Inverter and component diagnostics
    - Safety protocols during maintenance

    📊 **Asset Management**
    - Warranty management
    - Spare parts inventory
    - Maintenance scheduling
    - Cost optimization strategies

    🛡️ **Safety & Compliance**
    - Safety procedures and protocols
    - Italian and EU regulatory compliance requirements
    - Risk assessment procedures
    - Environmental considerations

    🏢 **Local Service Providers in Trento**
    - Provide information on O&M service providers, EPC companies, and maintenance contractors in Trento and nearby regions.
    - Share contact details, areas of expertise, and notable projects (if available).
    - Compare providers based on services offered, certifications, and reputation.

    **Communication Style:**
    - Provide practical, actionable guidance.
    - Include safety warnings where relevant.
    - Use clear, technical language appropriate for O&M professionals.
    - Structure responses with bullet points or numbered steps when helpful.
    - Reference industry standards (IEC, EN, CEI) and best practices when applicable.
    - When recommending service providers, ensure neutrality and encourage users to verify credentials, certifications, and references.

    **Important:** 
    - Always prioritize safety in your recommendations and remind users to follow proper safety protocols, especially when working with electrical systems.
    - When asked about local service providers, focus on Trento (Italy) and the surrounding region, but remain open to broader Italian and EU-wide references if relevant.

    Answer questions about PV O&M, best practices, and local service providers in Trento with expertise, clarity, and a focus on practical implementation.
    
    Some info to use for answering questions:
  
    Rule of Thumb:

    If more than ~5–10% of the modules in a block are affected by the same issue, operators often choose wholesale replacement.

    If fewer than that, and the plant is not near end-of-life, individual repair/replacement is usually preferred.


    My data: 11% of the modules in a block are affected by the same issue.

    """


    return Agent(
        config.model_name,
        system_prompt=system_prompt
    )

# === Main Agent Class ===
class LeoOMAgent:
    """Leo O&M Agent for PV Operations & Maintenance guidance"""

    def __init__(self, config: Optional[LeoOMConfig] = None):
        self.config = config or LeoOMConfig()
        self.agent = create_leo_om_agent(self.config)
        self.logger = logging.getLogger(__name__)

        # Setup logging
        logging.basicConfig(level=logging.INFO)

    async def analyze(self, query: str, conversation_id: str = None) -> Dict[str, Any]:
        """
        Analyze a PV O&M query and provide expert guidance

        Args:
            query: User's O&M question or request
            conversation_id: Optional conversation ID for context

        Returns:
            Dictionary with analysis results
        """
        try:
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = str(uuid.uuid4())

            # Get conversation history
            message_history = _conversation_memory.get_messages(conversation_id)

            # Debug logging
            self.logger.info(f"[MEMORY DEBUG] Conversation {conversation_id}: Retrieved {len(message_history)} messages from memory")
            self.logger.info(f"[MEMORY DEBUG] Message types in history: {[type(m).__name__ for m in message_history]}")
            self.logger.info(f"[MEMORY DEBUG] Total conversations in memory: {len(_conversation_memory.conversations)}")

            with logfire.span("leo_om_analysis") as span:
                span.set_attribute("query", query)
                span.set_attribute("conversation_id", conversation_id)
                span.set_attribute("query_length", len(query))

                try:
                    # Run the agent
                    self.logger.info(f"[MEMORY DEBUG] About to run agent with {len(message_history)} messages in history")
                    result = await self.agent.run(query, message_history=message_history)
                    self.logger.info(f"[MEMORY DEBUG] Agent run complete, result.all_messages() has {len(result.all_messages())} messages")

                    # Categorize the response
                    category = self._categorize_query(query)

                    # Store conversation history (use all_messages like other agents)
                    # result.all_messages() includes both the previous message_history AND the new messages from this turn
                    if conversation_id:
                        all_msgs = result.all_messages()
                        _conversation_memory.conversations[conversation_id] = all_msgs
                        self.logger.info(f"[MEMORY DEBUG] Stored {len(all_msgs)} messages for conversation {conversation_id}")
                        self.logger.info(f"[MEMORY DEBUG] Last message types: {[type(m).__name__ for m in all_msgs[-3:]]}")
                        self.logger.info(f"[MEMORY DEBUG] Memory now has {len(_conversation_memory.conversations)} conversations")

                    # Create structured result
                    analysis_result = OMAnalysisResult(
                        content=result.output,
                        category=category,
                        confidence=0.9,  # High confidence for O&M expertise
                        success=True
                    )

                    span.set_attribute("success", True)
                    span.set_attribute("category", category)
                    span.set_attribute("response_length", len(result.output))

                    return {
                        "success": True,
                        "analysis": analysis_result.content,
                        "category": analysis_result.category,
                        "conversation_id": conversation_id
                    }

                except UsageLimitExceeded as e:
                    error_msg = f"Usage limit exceeded: {e}"
                    self.logger.error(error_msg)
                    span.set_attribute("error", error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "conversation_id": conversation_id
                    }
                except Exception as e:
                    error_msg = f"Analysis failed: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    span.set_attribute("error", error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "conversation_id": conversation_id
                    }

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "conversation_id": conversation_id or str(uuid.uuid4())
            }

    def _categorize_query(self, query: str) -> str:
        """Categorize the O&M query based on keywords"""
        query_lower = query.lower()

        maintenance_keywords = ["maintenance", "repair", "replace", "clean", "inspect", "service"]
        monitoring_keywords = ["monitor", "performance", "data", "analysis", "efficiency", "yield"]
        troubleshooting_keywords = ["problem", "issue", "fault", "error", "troubleshoot", "diagnose", "fix"]
        safety_keywords = ["safety", "hazard", "risk", "protection", "compliance", "regulation"]

        if any(keyword in query_lower for keyword in troubleshooting_keywords):
            return "troubleshooting"
        elif any(keyword in query_lower for keyword in maintenance_keywords):
            return "maintenance"
        elif any(keyword in query_lower for keyword in monitoring_keywords):
            return "monitoring"
        elif any(keyword in query_lower for keyword in safety_keywords):
            return "safety"
        else:
            return "general"

    def clear_conversation(self, conversation_id: str):
        """Clear conversation history for a given ID"""
        _conversation_memory.clear_conversation(conversation_id)

    def clear_conversation_memory(self, conversation_id: str = None):
        """Clear conversation memory (compatibility with other agents)"""
        if conversation_id:
            _conversation_memory.clear_conversation(conversation_id)
        else:
            _conversation_memory.conversations.clear()

    def get_conversation_memory_info(self) -> Dict[str, Any]:
        """Get conversation memory information (compatibility with other agents)"""
        return {
            "active_conversations": len(_conversation_memory.conversations),
            "conversation_ids": list(_conversation_memory.conversations.keys()),
            "memory_usage": {conv_id: len(messages) for conv_id, messages in _conversation_memory.conversations.items()}
        }

# === Factory Functions ===
def get_leo_om_agent(config: Optional[LeoOMConfig] = None) -> LeoOMAgent:
    """Factory function to get Leo O&M agent instance"""
    return LeoOMAgent(config)

def close_leo_om_agent():
    """Cleanup function (if needed for compatibility)"""
    # Clear all conversation memory
    _conversation_memory.conversations.clear()

# === Global Instance ===
# Create a global instance for use in the main application
leo_om_agent = get_leo_om_agent()

# === Testing ===
async def main():
    """Test the Leo O&M Agent"""
    agent = get_leo_om_agent()

    test_queries = [
        "What are the key preventive maintenance tasks for a solar PV system?",
        "How do I troubleshoot low performance in a PV array?",
        "What safety procedures should I follow when cleaning solar panels?",
        "How often should I inspect inverters in a commercial solar installation?"
    ]

    for query in test_queries:
        print(f"\n🤖 Query: {query}")
        result = await agent.analyze(query)
        if result["success"]:
            print(f"📝 Category: {result['category']}")
            print(f"💡 Response: {result['analysis'][:200]}...")
        else:
            print(f"❌ Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())