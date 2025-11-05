"""
Manufacturer Financial Analyst Agent
=====================================

Single-agent workflow for PV manufacturer financial analysis.
Uses OpenAI Agents SDK with code interpreter tool.
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
from agents import Agent, Runner, CodeInterpreterTool, SQLiteSession, ModelSettings, RunConfig, trace, TResponseInputItem
from openai.types.shared.reasoning import Reasoning

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
    Example: 【7:3†Canadian_Solar.csv$Total Revenues】

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
    """Input for the manufacturer financial workflow"""
    input_as_text: str

@dataclass
class ManufacturerFinancialAgentConfig:
    """Configuration for the manufacturer financial agent"""
    model: str = "gpt-5-mini"
    file_ids: list = None
    agent_name: str = "Manufacturer Financial Analyst"
    verbose: bool = True

    def __post_init__(self):
        """Set default file IDs if not provided"""
        if self.file_ids is None:
            self.file_ids = [
                "file-S8Tsm2pfYAGCiFPapLsvtW",  # Canadian Solar
                "file-98xFxNN3m9JTqYdea44Ztm",  # Jinko Solar
                "file-2MoHyYF16wX4zqga2VNRxS",  # LONGi
                "file-6WPBmVCVRjQkfzVic7iz8G",  # Trina Solar
                "file-5HMedi2vcmMGc5kZoKacYJ",  # GCL SI
                "file-X4oRrKNczaNqAprkMmx4AZ",  # Tongwei
                "file-RQzYEDBDv7peW6yep51rcj",  # JA Solar
                "file-PYH6NXAh4UTQd79oaQnjp8"   # Risen Energy
            ]

class ManufacturerFinancialAgent:
    """
    Single-agent manufacturer financial workflow using OpenAI Agents SDK.
    Provides expert analysis on PV manufacturer financial and operational performance.
    """

    MANUFACTURER_FINANCIAL_PROMPT = """System Prompt — PV Financial Analysis Agent (Multi-CSV Version)
You are the PV Financial Analysis Agent, an expert AI system specialized in analyzing, comparing, and interpreting the financial and operational performance of major photovoltaic (PV) manufacturers. You analyze data provided as multiple CSV files, each corresponding to a single company.

📘 Dataset Overview
The dataset is composed of the following 8 CSV files, each containing the same structure of metrics and time periods:

- Canadian_Solar.csv for Canadian Solar
- Jinko_Solar.csv for Jinko Solar
- LONGi.csv for LONGi
- Trina_Solar.csv for Trina Solar
- GCL_SI.csv for GCL SI
- Tongwei.csv for Tongwei
- JA_Solar.csv for JA Solar
- Risen_Energy.csv for Risen Energy

🧾 File Structure
Rows (59 metrics) — identical across all CSVs, representing financial and operational indicators such as: Total Revenues, Sales breakdowns, Costs, Margins, Expenses, Profits, Cash Flow, Manufacturing Capacity, Shipments, and Per-Watt indicators.

Columns represent time periods, formatted like:
Q1 '22, Q2 '22, H1 '22, Q3 '22, Q4 '22, 2022,
Q1 '23, Q2 '23, H1 '23, Q3 '23, Q4 '23, 2023,
Q1 '24, Q2 '24, H1 '24, Q3 '24, Q4 '24, 2024,
Q1 '25, Q2 '25, H1 '25, Q3 '25, Q4 '25, 2025.

"Q" = Quarter, "H" = Half-year, and standalone years are full-year totals.
Values are numeric and expressed in appropriate units (USD million, %, GW, $/W).

**The currency is always in dollars, not anything else.**

📊 Metrics List
Total Revenues, Solar Products Sales, Polysilicon Sales, Wafer Sales, Cell Sales, Module Sales, Service Revenue, Electricity Sales / Power Station Operations, Other Operating Revenue, COGS, Solar Products Costs, Polysilicon Costs, Wafer Costs, Cell Costs, Module Costs, Service Costs, Electricity Costs / Power Station Costs, Other Operating Costs, Gross Margin, Gross Margin Ratio, Gross Margin Ratio Module, Operating Expenses, Taxes And Surcharges, Sales And Marketing Expenses, General And Administrative Expenses, R&D Expenses, Financial Expenses, Other Operating Expenses, Interest Expenses, Interest Income, Other Incomes, Investment Income, From Associates And Joint Ventures, Termination Of Financial Assets, Income From Changes In Fair Value, Subsidy Income, Foreign Exchange, Change in Forex Derivatives, Change in Long-term Investment, Change in Convertible Notes, Credit Impairment Loss, Asset Impairment Loss, Asset Disposal Income, Operating Profit, Operating Margin, Total Profits, EBITDA, EBIT, Cash Balance, Monthly Cash Expenses, Gross Cash Burn Rate, Operating Loss, Net Cash Burn Rate, Manufacturing Capacity, Solar Module Shipment, Revenue per Watt, Cost per Watt, Expenses per Watt.

⚙️ Agent Capabilities
You can:
- Load and interpret data from any of the company CSVs
- Perform time-series and cross-company analyses
- Compute YoY growth, CAGR, margins, cost ratios, and shipment efficiency
- Identify outliers or anomalies (e.g., margin drops, cost surges)
- Generate summaries, rankings, or comparisons based on any metric

**Response Formatting Guidelines:**
- **Always start with an executive summary** using a ## header followed by 2-3 sentence overview
- **Use hierarchical headers** (## for main sections, ### for subsections) to create clear document structure
- **Present data in tables** when comparing multiple companies or time periods - use markdown table syntax
- **Use bullet points** for listing insights, findings, or recommendations
- **Use numbered lists** for sequential steps, rankings, or prioritized items
- **Bold key financial figures** and percentages (e.g., **$1.2B revenue**, **15.3% margin**)
- **Add blank lines** between all sections and paragraphs for visual breathing room
- **Keep paragraphs concise** (2-3 sentences maximum) - break longer explanations into multiple paragraphs
- **Use descriptive section headers** that tell the story (e.g., "## Revenue Growth Comparison" not just "## Data")
- **Include clear trend indicators** using arrows or descriptive language (↑ increasing, ↓ decreasing, → stable)
- **End with key takeaways** when appropriate - summarize the most important findings
- **Never use run-on sentences** in lists - each bullet should be a complete, focused thought
- **Format large numbers clearly** with proper units (M for millions, B for billions, GW for capacity)

**Citation Guidelines - CRITICAL:**
- ALWAYS cite information as coming from the "Becquerel database"
- NEVER mention the actual filename or file extension (e.g., never say "according to Canadian_Solar.csv" or "as stated in the CSV")
- Use phrases like: "According to the Becquerel database..."
- Example: "The Becquerel database indicates that..."
- When referencing specific data, say: "Based on the Becquerel database..." or "The database shows..."

**Important Guidelines:**
- **Do NOT generate charts, plots, or visualizations** - you are not equipped with visualization capabilities
- **Do NOT offer to create graphs or export data** - focus on textual analysis and markdown tables only
- Never offer charts and exporting of data
- Never mention the name of the files; you can always mention that the reference is Becquerel database only
- Never mention anything like: "You've uploaded the full dataset for all key companies," or anything about the dataset files
- Never search the knowledge base for greetings and general conversation
- Remain factual, structured, and concise—do not speculate or introduce external interpretations"""

    def __init__(self, config: Optional[ManufacturerFinancialAgentConfig] = None):
        """
        Initialize the Manufacturer Financial Agent

        Args:
            config: Configuration object for the agent
        """
        self.config = config or ManufacturerFinancialAgentConfig()
        self.manufacturer_financial_expert = None
        self.conversation_sessions: Dict[str, Any] = {}  # conversation_id -> session

        logger.info("Using SQLite for session storage (simple and reliable)")

        # Initialize agent
        self._initialize_agent()

        logger.info(f"✅ Manufacturer Financial Agent initialized (Memory: SQLite)")

    def _initialize_agent(self):
        """Create the manufacturer financial expert agent"""
        try:
            # Create code interpreter tool with file IDs
            code_interpreter = CodeInterpreterTool(tool_config={
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "file_ids": self.config.file_ids
                }
            })

            # Create manufacturer financial expert agent with code interpreter
            self.manufacturer_financial_expert = Agent(
                name="PV Manufacturer Financial Analyst",
                instructions=self.MANUFACTURER_FINANCIAL_PROMPT,
                model=self.config.model,
                tools=[code_interpreter],
                model_settings=ModelSettings(
                    store=True,
                    reasoning=Reasoning(
                        effort="low",
                        summary="auto"
                    )
                )
            )
            logger.info(f"✅ Created manufacturer financial expert with {len(self.config.file_ids)} data files")

        except Exception as e:
            logger.error(f"❌ Failed to initialize agent: {e}")
            raise

    async def run_workflow(self, workflow_input: WorkflowInput, conversation_id: str = None):
        """
        Run the manufacturer financial workflow

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
                    session_id = f"manufacturer_financial_{conversation_id}"
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

            # Run manufacturer financial expert
            manufacturer_financial_result_temp = await Runner.run(
                self.manufacturer_financial_expert,
                input=[*conversation_history],
                session=session,
                run_config=RunConfig(trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "wf_690a7d7c09fc81909fe33448d112fed801155fa138e020ec"
                })
            )

            # Update conversation history
            conversation_history.extend([item.to_input_item() for item in manufacturer_financial_result_temp.new_items])

            # Extract final output
            output_text = manufacturer_financial_result_temp.final_output_as(str)

            # Clean citation markers
            output_text = clean_citation_markers(output_text)

            manufacturer_financial_result = {
                "output_text": output_text
            }

            return manufacturer_financial_result

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
                    session_id = f"manufacturer_financial_{conversation_id}"
                    self.conversation_sessions[conversation_id] = SQLiteSession(
                        session_id=session_id
                    )
                    logger.info(f"Created SQLite session for conversation {conversation_id}")

                session = self.conversation_sessions[conversation_id]

            # Run with streaming
            result = Runner.run_streamed(self.manufacturer_financial_expert, query, session=session)

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
        Analyze manufacturer financial query

        Args:
            query: Natural language query about manufacturer financials
            conversation_id: Optional conversation ID for maintaining context

        Returns:
            Dictionary with analysis results and metadata
        """
        # Logfire span for manufacturer financial agent
        with logfire.span("manufacturer_financial_agent_call") as agent_span:
            agent_span.set_attribute("agent_type", "manufacturer_financial")
            agent_span.set_attribute("conversation_id", str(conversation_id))
            agent_span.set_attribute("message_length", len(query))
            agent_span.set_attribute("user_message", query)

            try:
                logger.info(f"Processing manufacturer financial query: {query}")

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

                logger.info(f"✅ Manufacturer financial agent response: {response_text[:100]}...")

                return {
                    "success": True,
                    "analysis": response_text,
                    "usage": None,  # Usage info not directly available in this architecture
                    "query": query
                }

            except Exception as e:
                error_msg = f"Failed to analyze manufacturer financial query: {str(e)}"
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
            logger.info("Manufacturer financial agent ready for cleanup if needed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global agent instance
_manufacturer_financial_agent = None

def get_manufacturer_financial_agent() -> Optional[ManufacturerFinancialAgent]:
    """Get or create the global manufacturer financial agent instance"""
    global _manufacturer_financial_agent
    if _manufacturer_financial_agent is None:
        try:
            config = ManufacturerFinancialAgentConfig()
            _manufacturer_financial_agent = ManufacturerFinancialAgent(config)
            logger.info("✅ Global manufacturer financial agent created")
        except Exception as e:
            logger.error(f"❌ Failed to create manufacturer financial agent: {e}")
            return None
    return _manufacturer_financial_agent

def close_manufacturer_financial_agent():
    """Close the global manufacturer financial agent"""
    global _manufacturer_financial_agent
    if _manufacturer_financial_agent:
        _manufacturer_financial_agent.cleanup()
        _manufacturer_financial_agent = None
        logger.info("✅ Global manufacturer financial agent closed")

# Test function
async def test_manufacturer_financial_agent():
    """Test the manufacturer financial agent"""
    try:
        agent = get_manufacturer_financial_agent()
        if agent:
            result = await agent.analyze(
                "Compare the revenue per watt for Canadian Solar and Jinko Solar in 2024",
                conversation_id="test-1"
            )
            print("Manufacturer Financial Agent response received successfully")
            print(f"Response length: {len(result.get('analysis', ''))}")
            print(f"\nResponse:\n{result.get('analysis', '')}")
            return result
        else:
            print("Manufacturer Financial Agent not available")
            return None
    except Exception as e:
        print(f"Manufacturer Financial Agent error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        close_manufacturer_financial_agent()

if __name__ == "__main__":
    asyncio.run(test_manufacturer_financial_agent())
