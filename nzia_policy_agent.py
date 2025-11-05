"""
NZIA Policy Agent
=================

Single-agent workflow for NZIA policy analysis (Italy's FERX framework).
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
    Example: 【7:3†FERX_1.pdf$Article 15】

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
    """Input for the NZIA policy workflow"""
    input_as_text: str

@dataclass
class NZIAPolicyAgentConfig:
    """Configuration for the NZIA policy agent"""
    model: str = "gpt-4.1"
    vector_store_ids: list = None
    agent_name: str = "NZIA Policy Agent"
    verbose: bool = True

    def __post_init__(self):
        """Set default vector store IDs if not provided"""
        if self.vector_store_ids is None:
            self.vector_store_ids = [
                "vs_690a1f1d49f081918d551c4e4b5a9472"  # FERX framework documents
            ]

class NZIAPolicyAgent:
    """
    Single-agent NZIA policy workflow using OpenAI Agents SDK.
    Provides expert analysis on Italy's FERX framework and NZIA compliance.
    """

    NZIA_POLICY_PROMPT = """You are NZIA Policy Agent, an expert AI assistant specialized in retrieving, analyzing, and summarizing content from Italy's FERX framework, including the following sources:
- FERX_1.pdf – Ministerial Decree establishing capacity targets and approval of FERX rules
- FERX_2.pdf – Regole Operative defining eligibility, bidding, payments, and compliance
- FERX_3.pdf – Bando Pubblico launching the first PV ("Fotovoltaico NZIA") auction

Your primary objectives:
- Retrieve precise data (articles, clauses, dates, MW/€ values, deadlines)
- Summarize procedures, eligibility, guarantees, and timelines
- Compare and explain relationships between decree ↔ rules ↔ tender
- Generate concise policy or market insights relevant to the Net-Zero Industry Act (NZIA) context

**Response Formatting Guidelines:**
- Use proper markdown formatting with headers (##), bullet points (-), and numbered lists
- Break content into clear sections with descriptive headers
- Use **bold** for key terms and important numbers
- Add blank lines between sections for readability
- Structure long lists as proper bullet points, not run-on sentences
- Use concise paragraphs (2-3 sentences max)

**Content Guidelines:**
- Search the knowledge base before answering questions about FERX/NZIA policy
- Provide specific examples and data from the documents when available
- Cite relevant information from the documents
- If information is not in the knowledge base, clearly state that
- Keep responses clear, well-structured, and actionable

**Critical Language Rule:**
- You MUST ALWAYS respond in English, regardless of the language used in the user's query
- Even if the user writes in Italian or any other language, your response must be in English only

**Citation Guidelines - CRITICAL:**
- ALWAYS refer to information as coming from the "Becquerel database"
- NEVER mention the actual filename or file extension (e.g., never say "according to FERX_1.pdf" or "as stated in the PDF")
- Use phrases like: "According to the Becquerel database..."
- Example: "The Becquerel database indicates that..."
- When referencing specific data, say: "Based on the Becquerel database..." or "The database shows..."

**Italian Regulatory Terms:**
- Use Italian regulatory terms (e.g., Prezzo di Esercizio, Manifestazione di Interesse, Graduatoria)
- When helpful, briefly gloss them in English (but keep all text in the query language)

**Important Guidelines:**
- Never search the knowledge base for greetings and general conversation
- Output must always be fully and precisely in the language of the user's query—including headings, tables, glosses, and any explanatory notes
- Remain factual, structured, and concise—do not speculate or introduce external interpretations"""

    def __init__(self, config: Optional[NZIAPolicyAgentConfig] = None):
        """
        Initialize the NZIA Policy Agent

        Args:
            config: Configuration object for the agent
        """
        self.config = config or NZIAPolicyAgentConfig()
        self.nzia_policy_expert = None
        self.conversation_sessions: Dict[str, Any] = {}  # conversation_id -> session

        logger.info("Using SQLite for session storage (simple and reliable)")

        # Initialize agent
        self._initialize_agent()

        logger.info(f"✅ NZIA Policy Agent initialized (Memory: SQLite)")

    def _initialize_agent(self):
        """Create the NZIA policy expert agent"""
        try:
            # Create file search tool with vector stores
            file_search = FileSearchTool(
                vector_store_ids=self.config.vector_store_ids
            )

            # Create NZIA policy expert agent with file search
            self.nzia_policy_expert = Agent(
                name="NZIA Policy Agent",
                instructions=self.NZIA_POLICY_PROMPT,
                model=self.config.model,
                tools=[file_search],
                model_settings=ModelSettings(
                    temperature=1,
                    top_p=1,
                    max_tokens=2048,
                    store=True
                )
            )
            logger.info(f"✅ Created NZIA policy expert with {len(self.config.vector_store_ids)} vector stores: {', '.join(self.config.vector_store_ids)}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            raise

    async def run_workflow(self, workflow_input: WorkflowInput, conversation_id: str = None):
        """
        Run the NZIA policy workflow

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
                    session_id = f"nzia_policy_{conversation_id}"
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

            # Run NZIA policy expert
            nzia_policy_result_temp = await Runner.run(
                self.nzia_policy_expert,
                input=[*conversation_history],
                session=session,
                run_config=RunConfig(trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_690a1dd23554819086449af2969f3816069e73514b61ce9e"
                })
            )

            # Update conversation history
            conversation_history.extend([item.to_input_item() for item in nzia_policy_result_temp.new_items])

            # Extract final output
            output_text = nzia_policy_result_temp.final_output_as(str)

            # Clean citation markers
            output_text = clean_citation_markers(output_text)

            nzia_policy_result = {
                "output_text": output_text
            }

            return nzia_policy_result

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
                    session_id = f"nzia_policy_{conversation_id}"
                    self.conversation_sessions[conversation_id] = SQLiteSession(
                        session_id=session_id
                    )
                    logger.info(f"Created SQLite session for conversation {conversation_id}")

                session = self.conversation_sessions[conversation_id]

            # Run with streaming
            result = Runner.run_streamed(self.nzia_policy_expert, query, session=session)

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
        Analyze NZIA policy query

        Args:
            query: Natural language query about NZIA/FERX policy
            conversation_id: Optional conversation ID for maintaining context

        Returns:
            Dictionary with analysis results and metadata
        """
        # Logfire span for NZIA policy agent
        with logfire.span("nzia_policy_agent_call") as agent_span:
            agent_span.set_attribute("agent_type", "nzia_policy")
            agent_span.set_attribute("conversation_id", str(conversation_id))
            agent_span.set_attribute("message_length", len(query))
            agent_span.set_attribute("user_message", query)

            try:
                logger.info(f"Processing NZIA policy query: {query}")

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

                logger.info(f"✅ NZIA policy agent response: {response_text[:100]}...")

                return {
                    "success": True,
                    "analysis": response_text,
                    "usage": None,  # Usage info not directly available in this architecture
                    "query": query
                }

            except Exception as e:
                error_msg = f"Failed to analyze NZIA policy query: {str(e)}"
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
            logger.info("NZIA policy agent ready for cleanup if needed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global agent instance
_nzia_policy_agent = None

def get_nzia_policy_agent() -> Optional[NZIAPolicyAgent]:
    """Get or create the global NZIA policy agent instance"""
    global _nzia_policy_agent
    if _nzia_policy_agent is None:
        try:
            config = NZIAPolicyAgentConfig()
            _nzia_policy_agent = NZIAPolicyAgent(config)
            logger.info("✅ Global NZIA policy agent created")
        except Exception as e:
            logger.error(f"❌ Failed to create NZIA policy agent: {e}")
            return None
    return _nzia_policy_agent

def close_nzia_policy_agent():
    """Close the global NZIA policy agent"""
    global _nzia_policy_agent
    if _nzia_policy_agent:
        _nzia_policy_agent.cleanup()
        _nzia_policy_agent = None
        logger.info("✅ Global NZIA policy agent closed")

# Test function
async def test_nzia_policy_agent():
    """Test the NZIA policy agent"""
    try:
        agent = get_nzia_policy_agent()
        if agent:
            result = await agent.analyze(
                "What are the main eligibility requirements for FERX PV auctions?",
                conversation_id="test-1"
            )
            print("NZIA Policy Agent response received successfully")
            print(f"Response length: {len(result.get('analysis', ''))}")
            print(f"\nResponse:\n{result.get('analysis', '')}")
            return result
        else:
            print("NZIA Policy Agent not available")
            return None
    except Exception as e:
        print(f"NZIA Policy Agent error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        close_nzia_policy_agent()

if __name__ == "__main__":
    asyncio.run(test_nzia_policy_agent())
