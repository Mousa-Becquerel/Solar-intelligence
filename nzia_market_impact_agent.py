"""
NZIA Market Impact Agent
========================

Single-agent workflow for NZIA market impact analysis on European PV industry.
Uses OpenAI Agents SDK with file search tool for the Becquerel Institute report.
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
    Example: 【7:3†NZIA_Report.pdf$Chapter 5】

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
    """Input for the NZIA market impact workflow"""
    input_as_text: str

@dataclass
class NZIAMarketImpactAgentConfig:
    """Configuration for the NZIA market impact agent"""
    model: str = "gpt-4.1"
    vector_store_ids: list = None
    agent_name: str = "NZIA Market Impact Agent"
    verbose: bool = True

    def __post_init__(self):
        """Set default vector store IDs if not provided"""
        if self.vector_store_ids is None:
            self.vector_store_ids = [
                "vs_690b636df880819196c9c9d62deaf221"  # Becquerel Institute NZIA Market Impact report
            ]

class NZIAMarketImpactAgent:
    """
    Single-agent NZIA market impact workflow using OpenAI Agents SDK.
    Provides expert analysis on EU NZIA effects on European PV industry.
    """

    NZIA_MARKET_IMPACT_PROMPT = """You are NZIA Market Impact Agent, an expert AI assistant specialized in retrieving, analyzing, and contextualizing data from the Becquerel Institute report on how the EU Net-Zero Industry Act (NZIA) affects the European photovoltaic (PV) industry.

📘 **Knowledge Base Description**

The Becquerel database contains comprehensive information about:
- **NZIA Regulation Goals**: 40% EU manufacturing by 2030, 15% of global production by 2040
- **Implementation Timeline**: Key milestones from 2024–2026
- **Compliance Criteria**: Resilience, sustainability, innovation, and social factors for public procurement, auctions, and incentive schemes
- **Market Impact Analysis**: Quantitative analysis for PV segments (utility-scale, C&I, residential)
- **Country-Level Forecasts**: Detailed projections for Germany, Italy, Spain, France, and other EU countries
- **Strategic Recommendations**: Actionable insights for developers, EPCs, manufacturers, and public authorities

**Your Primary Objectives:**
- Retrieve precise data (manufacturing targets, MW/€ values, percentages, deadlines, country forecasts)
- Analyze market impact across different PV segments and countries
- Explain compliance criteria and their implications
- Provide strategic recommendations based on the report
- Compare country-level implementations and market responses
- Generate concise market insights relevant to NZIA context

**Response Formatting Guidelines:**
- **Always start with an executive summary** using a ## header followed by 2-3 sentence overview
- **Use hierarchical headers** (## for main sections, ### for subsections) to create clear document structure
- **Present data in tables** when comparing countries, segments, or time periods - use markdown table syntax
- **Use bullet points** for listing insights, impacts, or recommendations
- **Use numbered lists** for sequential steps, timelines, or prioritized recommendations
- **Bold key figures and targets** (e.g., **40% EU manufacturing**, **2030 target**, **€500M investment**)
- **Add blank lines** between all sections and paragraphs for visual breathing room
- **Keep paragraphs concise** (2-3 sentences maximum) - break longer explanations into multiple paragraphs
- **Use descriptive section headers** that tell the story (e.g., "## Germany's Manufacturing Response" not just "## Germany")
- **Include clear trend indicators** using arrows or descriptive language (↑ increasing, ↓ decreasing, → stable)
- **End with key takeaways** when appropriate - summarize the most important strategic implications
- **Never use run-on sentences** in lists - each bullet should be a complete, focused thought
- **Format large numbers clearly** with proper units (M for millions, B for billions, GW for capacity)

**Content Guidelines:**
- Search the knowledge base before answering questions about NZIA market impact
- Provide specific examples and data from the Becquerel report when available
- Cite relevant information from the report
- If information is not in the knowledge base, clearly state that
- Keep responses clear, well-structured, and actionable

**Critical Language Rule:**
- You MUST ALWAYS respond in English, regardless of the language used in the user's query
- Even if the user writes in Italian, German, French, Spanish or any other language, your response must be in English only

**Citation Guidelines - CRITICAL:**
- ALWAYS refer to information as coming from the "Becquerel database"
- NEVER mention the actual filename or file extension (e.g., never say "according to NZIA_Report.pdf" or "as stated in the PDF")
- Use phrases like: "According to the Becquerel database..."
- Example: "The Becquerel database indicates that..."
- When referencing specific data, say: "Based on the Becquerel database..." or "The database shows..."

**Important Guidelines:**
- **Do NOT generate charts, plots, or visualizations** - you are not equipped with visualization capabilities
- **Do NOT offer to create graphs or export data** - focus on textual analysis and markdown tables only
- Never offer charts and exporting of data
- Never mention the name of the files; you can always mention that the reference is Becquerel database only
- Never mention anything like: "You've uploaded the report," or anything about report files
- Never search the knowledge base for greetings and general conversation
- Remain factual, structured, and concise—do not speculate or introduce external interpretations"""

    def __init__(self, config: Optional[NZIAMarketImpactAgentConfig] = None):
        """
        Initialize the NZIA Market Impact Agent

        Args:
            config: Configuration object for the agent
        """
        self.config = config or NZIAMarketImpactAgentConfig()
        self.nzia_market_impact_expert = None
        self.conversation_sessions: Dict[str, Any] = {}  # conversation_id -> session

        logger.info("Using SQLite for session storage (simple and reliable)")

        # Initialize agent
        self._initialize_agent()

        logger.info(f"✅ NZIA Market Impact Agent initialized (Memory: SQLite)")

    def _initialize_agent(self):
        """Create the NZIA market impact expert agent"""
        try:
            # Create file search tool with vector stores
            file_search = FileSearchTool(
                vector_store_ids=self.config.vector_store_ids
            )

            # Create NZIA market impact expert agent with file search
            self.nzia_market_impact_expert = Agent(
                name="NZIA Market Impact Agent",
                instructions=self.NZIA_MARKET_IMPACT_PROMPT,
                model=self.config.model,
                tools=[file_search],
                model_settings=ModelSettings(
                    temperature=1,
                    top_p=1,
                    max_tokens=2048,
                    store=True
                )
            )
            logger.info(f"✅ Created NZIA market impact expert with {len(self.config.vector_store_ids)} vector stores: {', '.join(self.config.vector_store_ids)}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            raise

    async def run_workflow(self, workflow_input: WorkflowInput, conversation_id: str = None):
        """
        Run the NZIA market impact workflow

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
                    session_id = f"nzia_market_impact_{conversation_id}"
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

            # Run NZIA market impact expert
            nzia_market_impact_result_temp = await Runner.run(
                self.nzia_market_impact_expert,
                input=[*conversation_history],
                session=session,
                run_config=RunConfig(trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_nzia_market_impact"
                })
            )

            # Update conversation history
            conversation_history.extend([item.to_input_item() for item in nzia_market_impact_result_temp.new_items])

            # Extract final output
            output_text = nzia_market_impact_result_temp.final_output_as(str)

            # Clean citation markers
            output_text = clean_citation_markers(output_text)

            nzia_market_impact_result = {
                "output_text": output_text
            }

            return nzia_market_impact_result

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
                    session_id = f"nzia_market_impact_{conversation_id}"
                    self.conversation_sessions[conversation_id] = SQLiteSession(
                        session_id=session_id
                    )
                    logger.info(f"Created SQLite session for conversation {conversation_id}")

                session = self.conversation_sessions[conversation_id]

            # Run with streaming
            result = Runner.run_streamed(self.nzia_market_impact_expert, query, session=session)

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
        Analyze NZIA market impact query

        Args:
            query: Natural language query about NZIA market impact
            conversation_id: Optional conversation ID for maintaining context

        Returns:
            Dictionary with analysis results and metadata
        """
        # Logfire span for NZIA market impact agent
        with logfire.span("nzia_market_impact_agent_call") as agent_span:
            agent_span.set_attribute("agent_type", "nzia_market_impact")
            agent_span.set_attribute("conversation_id", str(conversation_id))
            agent_span.set_attribute("message_length", len(query))
            agent_span.set_attribute("user_message", query)

            try:
                logger.info(f"Processing NZIA market impact query: {query}")

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

                logger.info(f"✅ NZIA market impact agent response: {response_text[:100]}...")

                return {
                    "success": True,
                    "analysis": response_text,
                    "usage": None,  # Usage info not directly available in this architecture
                    "query": query
                }

            except Exception as e:
                error_msg = f"Failed to analyze NZIA market impact query: {str(e)}"
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
            logger.info("NZIA market impact agent ready for cleanup if needed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global agent instance
_nzia_market_impact_agent = None

def get_nzia_market_impact_agent() -> Optional[NZIAMarketImpactAgent]:
    """Get or create the global NZIA market impact agent instance"""
    global _nzia_market_impact_agent
    if _nzia_market_impact_agent is None:
        try:
            config = NZIAMarketImpactAgentConfig()
            _nzia_market_impact_agent = NZIAMarketImpactAgent(config)
            logger.info("✅ Global NZIA market impact agent created")
        except Exception as e:
            logger.error(f"❌ Failed to create NZIA market impact agent: {e}")
            return None
    return _nzia_market_impact_agent

def close_nzia_market_impact_agent():
    """Close the global NZIA market impact agent"""
    global _nzia_market_impact_agent
    if _nzia_market_impact_agent:
        _nzia_market_impact_agent.cleanup()
        _nzia_market_impact_agent = None
        logger.info("✅ Global NZIA market impact agent closed")

# Test function
async def test_nzia_market_impact_agent():
    """Test the NZIA market impact agent"""
    try:
        agent = get_nzia_market_impact_agent()
        if agent:
            result = await agent.analyze(
                "What are the EU NZIA manufacturing targets for 2030 and 2040?",
                conversation_id="test-1"
            )
            print("NZIA Market Impact Agent response received successfully")
            print(f"Response length: {len(result.get('analysis', ''))}")
            print(f"\nResponse:\n{result.get('analysis', '')}")
            return result
        else:
            print("NZIA Market Impact Agent not available")
            return None
    except Exception as e:
        print(f"NZIA Market Impact Agent error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        close_nzia_market_impact_agent()

if __name__ == "__main__":
    asyncio.run(test_nzia_market_impact_agent())
