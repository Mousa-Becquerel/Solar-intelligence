"""
Digitalization Trends Agent
===========================

Single-agent workflow for digitalization and AI integration in the PV value chain.
Uses OpenAI Agents SDK with file search tool.
"""

import os
import logging
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import asyncio
from pydantic import BaseModel

# Import from openai-agents library
from agents import Agent, Runner, FileSearchTool, SQLiteSession, ModelSettings, RunConfig, trace, TResponseInputItem

# Logfire imports
import logfire

# === Configure logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Utility Functions ===
def clean_citation_markers(text: str) -> str:
    """
    Remove OpenAI citation markers from text.

    Citation format: 【citation_number:citation_index†source_file$content】
    Example: 【7:3†news_articles_pretty.json$'s largest floating PV plant】

    Args:
        text: Text containing citation markers

    Returns:
        Cleaned text without citation markers
    """
    # Pattern to match citation markers: 【...】
    # These markers include special unicode brackets 【】
    pattern = r'【[^】]*】'
    cleaned = re.sub(pattern, '', text)

    # Also remove any orphaned opening brackets
    cleaned = re.sub(r'【', '', cleaned)

    # Clean up any extra spaces or line breaks caused by removal
    cleaned = re.sub(r'\s+\(', ' (', cleaned)  # Fix spacing before parentheses
    cleaned = re.sub(r'\)\s*\n\s*\)', ')', cleaned)  # Remove empty parentheses

    return cleaned

# === Load environment variables ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Set OpenAI API key for agents library
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# === Pydantic Models ===
class WorkflowInput(BaseModel):
    """Input for the digitalization workflow"""
    input_as_text: str

@dataclass
class DigitalizationAgentConfig:
    """Configuration for the digitalization agent"""
    model: str = "gpt-4.1"
    vector_store_ids: list = None  # Changed from single ID to list
    agent_name: str = "Digitalization Expert"
    verbose: bool = True

    def __post_init__(self):
        """Set default vector store IDs if not provided"""
        if self.vector_store_ids is None:
            self.vector_store_ids = [
                "vs_68e5846b1a708191a5b17970b3ac9994",  # Original AI report
                "vs_6904c71afe4c8191a966640cf67c59fc"   # Updated AI report with latest data
            ]

class DigitalizationAgent:
    """
    Single-agent digitalization workflow using OpenAI Agents SDK.
    Provides expert analysis on digitalization and AI integration in PV value chain.
    """

    DIGITALIZATION_EXPERT_PROMPT = """You are an expert in digitalization and AI integration in the different solutions and stages of the PV value chain. You have access to an AI report in the PV industry. You must answer users' queries about digitalization topics by accessing the data from this report.

**Response Formatting Guidelines:**
- Use proper markdown formatting with headers (##), bullet points (-), and numbered lists
- Break content into clear sections with descriptive headers
- Use **bold** for key terms and important numbers
- Add blank lines between sections for readability
- Structure long lists as proper bullet points, not run-on sentences
- Use concise paragraphs (2-3 sentences max)

**Content Guidelines:**
- Search the knowledge base before answering only when the question is about digitalization or about the content of the report
- Provide specific examples and data from the reports when available
- Cite relevant information from the documents
- If information is not in the knowledge base, clearly state that
- Keep responses clear, well-structured, and actionable

**Important Guidelines:**
- Never search the knowledge base for greetings and general conversation."""

    def __init__(self, config: Optional[DigitalizationAgentConfig] = None):
        """
        Initialize the Digitalization Agent

        Args:
            config: Configuration object for the agent
        """
        self.config = config or DigitalizationAgentConfig()
        self.digitalization_expert = None
        self.conversation_sessions: Dict[str, Any] = {}  # conversation_id -> session

        logger.info("Using SQLite for session storage (simple and reliable)")

        # Initialize agent
        self._initialize_agent()

        logger.info(f"✅ Digitalization Agent initialized (Memory: SQLite)")

    def _initialize_agent(self):
        """Create the digitalization expert agent"""
        try:
            # Create file search tool with multiple vector stores
            file_search = FileSearchTool(
                vector_store_ids=self.config.vector_store_ids
            )

            # Create digitalization expert agent with file search
            self.digitalization_expert = Agent(
                name="Digitalization expert",
                instructions=self.DIGITALIZATION_EXPERT_PROMPT,
                model=self.config.model,
                tools=[file_search],
                model_settings=ModelSettings(
                    temperature=1,
                    top_p=1,
                    max_tokens=2048,
                    store=True
                )
            )
            logger.info(f"✅ Created digitalization expert with {len(self.config.vector_store_ids)} vector stores: {', '.join(self.config.vector_store_ids)}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            raise

    async def run_workflow(self, workflow_input: WorkflowInput, conversation_id: str = None):
        """
        Run the digitalization workflow

        Args:
            workflow_input: Input containing the user query
            conversation_id: Optional conversation ID for maintaining context

        Returns:
            Dictionary with output_text containing the response
        """
        with trace("New workflow"):
            # Get or create session for this conversation
            session = None
            if conversation_id:
                if conversation_id not in self.conversation_sessions:
                    session_id = f"digitalization_{conversation_id}"
                    self.conversation_sessions[conversation_id] = SQLiteSession(
                        session_id=session_id
                    )
                    logger.info(f"Created SQLite session for conversation {conversation_id}")

                session = self.conversation_sessions[conversation_id]

            # Prepare conversation history
            workflow = workflow_input.model_dump()
            conversation_history: list[TResponseInputItem] = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": workflow["input_as_text"]
                        }
                    ]
                }
            ]

            # Run digitalization expert
            digitalization_expert_result_temp = await Runner.run(
                self.digitalization_expert,
                input=[*conversation_history],
                session=session,
                run_config=RunConfig(trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_68e9933196dc8190b65301893f6024d10240b55e3f16f91c"
                })
            )

            # Update conversation history
            conversation_history.extend([item.to_input_item() for item in digitalization_expert_result_temp.new_items])

            # Extract final output
            output_text = digitalization_expert_result_temp.final_output_as(str)

            # Clean citation markers
            output_text = clean_citation_markers(output_text)

            digitalization_expert_result = {
                "output_text": output_text
            }

            return digitalization_expert_result

    async def analyze_stream(self, query: str, conversation_id: str = None):
        """
        Analyze query with streaming response

        Args:
            query: Natural language query
            conversation_id: Optional conversation ID for maintaining context

        Yields:
            Text chunks as they are generated
        """
        try:
            logger.info(f"Processing query (streaming): {query}")

            # Get or create session for this conversation
            session = None
            if conversation_id:
                if conversation_id not in self.conversation_sessions:
                    session_id = f"digitalization_{conversation_id}"
                    self.conversation_sessions[conversation_id] = SQLiteSession(
                        session_id=session_id
                    )
                    logger.info(f"Created SQLite session for conversation {conversation_id}")

                session = self.conversation_sessions[conversation_id]

            # Run with streaming
            result = Runner.run_streamed(self.digitalization_expert, query, session=session)

            # Stream text deltas as they arrive
            async for event in result.stream_events():
                if event.type == "raw_response_event":
                    # Check if it's a text delta event
                    from openai.types.responses import ResponseTextDeltaEvent
                    if isinstance(event.data, ResponseTextDeltaEvent):
                        # Clean citation markers before yielding
                        cleaned_delta = clean_citation_markers(event.data.delta)
                        if cleaned_delta:  # Only yield if there's content after cleaning
                            yield cleaned_delta

        except Exception as e:
            error_msg = f"Failed to stream query: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            yield f"\n\n**Error:** {error_msg}"

    async def analyze(self, query: str, conversation_id: str = None) -> Dict[str, Any]:
        """
        Analyze digitalization query

        Args:
            query: Natural language query about digitalization in PV
            conversation_id: Optional conversation ID for maintaining context

        Returns:
            Dictionary with analysis results and metadata
        """
        # Logfire span for digitalization agent
        with logfire.span("digitalization_agent_call") as agent_span:
            agent_span.set_attribute("agent_type", "digitalization")
            agent_span.set_attribute("conversation_id", str(conversation_id))
            agent_span.set_attribute("message_length", len(query))
            agent_span.set_attribute("user_message", query)

            try:
                logger.info(f"Processing digitalization query: {query}")

                # Create workflow input
                workflow_input = WorkflowInput(input_as_text=query)

                # Run workflow
                result = await self.run_workflow(workflow_input, conversation_id)

                # Extract response
                response_text = result.get("output_text", "")

                # Track the response
                agent_span.set_attribute("assistant_response", response_text)
                agent_span.set_attribute("response_length", len(response_text))
                agent_span.set_attribute("success", True)

                logger.info(f"✅ Digitalization agent response: {response_text[:100]}...")

                return {
                    "success": True,
                    "analysis": response_text,
                    "usage": None,  # Usage info not directly available in this architecture
                    "query": query
                }

            except Exception as e:
                error_msg = f"Failed to analyze digitalization query: {str(e)}"
                logger.error(error_msg)
                agent_span.set_attribute("success", False)
                agent_span.set_attribute("error", str(e))
                return {
                    "success": False,
                    "error": error_msg,
                    "analysis": None,
                    "usage": None,
                    "query": query
                }

    def clear_conversation_memory(self, conversation_id: str = None):
        """Clear conversation memory by removing session"""
        if conversation_id:
            if conversation_id in self.conversation_sessions:
                del self.conversation_sessions[conversation_id]
                logger.info(f"Cleared conversation session for {conversation_id}")
        else:
            # Clear all sessions
            self.conversation_sessions.clear()
            logger.info("Cleared all conversation sessions")

    def get_conversation_memory_info(self) -> Dict[str, Any]:
        """Get information about conversation memory usage"""
        return {
            "total_conversations": len(self.conversation_sessions),
            "conversation_ids": list(self.conversation_sessions.keys()),
        }

    def cleanup(self):
        """Cleanup resources"""
        try:
            logger.info("Digitalization agent ready for cleanup if needed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global agent instance
_digitalization_agent = None

def get_digitalization_agent() -> Optional[DigitalizationAgent]:
    """Get or create the global digitalization agent instance"""
    global _digitalization_agent
    if _digitalization_agent is None:
        try:
            config = DigitalizationAgentConfig()
            _digitalization_agent = DigitalizationAgent(config)
            logger.info("✅ Global digitalization agent created")
        except Exception as e:
            logger.error(f"❌ Failed to create digitalization agent: {e}")
            return None
    return _digitalization_agent

def close_digitalization_agent():
    """Close the global digitalization agent"""
    global _digitalization_agent
    if _digitalization_agent:
        _digitalization_agent.cleanup()
        _digitalization_agent = None
        logger.info("✅ Global digitalization agent closed")

# Test function
async def test_digitalization_agent():
    """Test the digitalization agent"""
    try:
        agent = get_digitalization_agent()
        if agent:
            result = await agent.analyze(
                "What are the key digitalization trends in the PV industry?",
                conversation_id="test-1"
            )
            print("Digitalization Agent response received successfully")
            print(f"Response length: {len(result.get('analysis', ''))}")
            print(f"\nResponse:\n{result.get('analysis', '')}")
            return result
        else:
            print("Digitalization Agent not available")
            return None
    except Exception as e:
        print(f"Digitalization Agent error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        close_digitalization_agent()

if __name__ == "__main__":
    asyncio.run(test_digitalization_agent())
