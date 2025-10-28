"""
News Analysis Agent
===================

Multi-agent workflow for news analysis with intent classification and web scraping.
Uses OpenAI Agents SDK with classifier-based routing.
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
from agents import Agent, Runner, FileSearchTool, WebSearchTool, SQLiteSession, ModelSettings

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
class IntentClassificationSchema(BaseModel):
    """Schema for intent classification"""
    query_class: str  # "general_news_query", "more_detailed_news_query", or "general"

class WebSearchFilters(BaseModel):
    """Filters for web search tool"""
    allowed_domains: list[str] = []

    class Config:
        extra = "allow"

@dataclass
class NewsAgentConfig:
    """Configuration for the news agent"""
    model: str = "gpt-4.1"
    intent_model: str = "gpt-4.1"  # Using gpt-4o for intent classification (gpt-5 not widely available yet)
    vector_store_id: str = "vs_68eac39b41248191be25c41a212c58a2"
    agent_name: str = "News Analyst"
    verbose: bool = True

class NewsAgent:
    """
    Multi-agent news analysis workflow using OpenAI Agents SDK.
    Uses intent classification to route queries to appropriate specialized agents.
    """

    INTENT_CLASSIFICATION_PROMPT = """You are an intent classification agent. Your role is to classify user queries into categories:

**"general_news_query"**: Use this when:
- User asks about any news topic (e.g., "What's the latest news about France?", "Show me solar news")
- User asks for news on a specific topic for the first time
- User asks general questions about news, trends, or developments
- User wants to search for articles or news items
- This is the DEFAULT for most news-related queries

**"more_detailed_news_query"**: ONLY use this when:
- A specific news article with a URL was already mentioned in previous messages
- User explicitly asks for MORE details about THAT SPECIFIC article (e.g., "Tell me more about that article", "What are the exact numbers?", "Give me more details")
- User references a previously mentioned article (e.g., "about that", "from the article you mentioned")
- There must be a clear reference to a previous article in the conversation

**"general"**: Use this for:
- Greetings (hello, hi, how are you)
- General conversation unrelated to news
- Off-topic queries

**IMPORTANT**: If in doubt between "general_news_query" and "more_detailed_news_query", choose "general_news_query".

Analyze the conversation history carefully to determine the intent.
"""

    NEWS_AGENT_PROMPT = """You are a news analysis assistant specialized in photovoltaic (PV) and renewable energy news. You have access to a news database through file search.

**Response Formatting Guidelines:**
- Use proper markdown formatting with headers (##), bullet points (-), and numbered lists
- Break content into clear sections with descriptive headers
- Use **bold** for key terms and important numbers
- Add blank lines between sections for readability
- Structure long lists as proper bullet points, not run-on sentences
- Use concise paragraphs (2-3 sentences max)

**Content Guidelines:**
- Search the knowledge base before answering news-related questions
- Provide specific examples and data from the news articles when available
- Always include article URLs when referencing news sources
- If information is not in the knowledge base, clearly state that
- Keep responses clear, well-structured, and actionable
- Focus on recent developments and trends in the PV/renewable energy sector

**Date Context:**
- When users ask about "this year" or "recently", interpret based on current date context
- If users don't specify a time period, provide the most recent information available
"""

    SCRAPING_AGENT_PROMPT = """You are a scraping agent that extracts detailed information from news article links.

**Your Task:**
1. First, look through the conversation history to find a pv-magazine.com URL that was mentioned
2. If you find a URL, use the web search tool to extract detailed content from that specific article
3. Provide comprehensive details including:
   - Full article content and context
   - Specific numbers, dates, financial figures, and facts
   - Key quotes and insights
   - Additional information not in the summary

**If NO URL is found in the conversation:**
- Politely inform the user that you need them to first ask for news articles
- Suggest they ask for general news first, then you can provide more details
- Example: "I couldn't find a specific article URL in our conversation. Please first ask me to search for news (e.g., 'What's the latest news about X?'), and then I can provide more details about a specific article."

**Important:**
- Always reference the specific article URL you're analyzing
- Present findings in a clear, well-structured markdown format
- Use **bold** for key numbers and facts
"""

    def __init__(self, config: Optional[NewsAgentConfig] = None):
        """
        Initialize the News Agent with multi-agent workflow

        Args:
            config: Configuration object for the agent
        """
        self.config = config or NewsAgentConfig()
        self.intent_agent = None
        self.news_agent = None
        self.scraping_agent = None
        self.conversation_sessions: Dict[str, Any] = {}  # conversation_id -> session

        logger.info("Using SQLite for session storage (simple and reliable)")

        # Initialize agents
        self._initialize_agents()

        logger.info(f"✅ News Agent workflow initialized (Memory: SQLite)")

    def _initialize_agents(self):
        """Create all agents in the workflow"""
        try:
            # 1. Create intent classification agent
            self.intent_agent = Agent(
                name="Intent Classifier",
                instructions=self.INTENT_CLASSIFICATION_PROMPT,
                model=self.config.intent_model,
                output_type=IntentClassificationSchema,
                model_settings=ModelSettings(
                    temperature=0.3,  # Lower temperature for consistent classification
                    top_p=1,
                    max_tokens=100,
                    store=True
                )
            )
            logger.info("✅ Created intent classification agent")

            # 2. Create file search tool for news agent
            file_search = FileSearchTool(
                max_num_results=8,
                vector_store_ids=[self.config.vector_store_id],
                include_search_results=True,
            )

            # 3. Create news agent with file search
            self.news_agent = Agent(
                name="News Analyst",
                instructions=self.NEWS_AGENT_PROMPT,
                model=self.config.model,
                tools=[file_search],
                model_settings=ModelSettings(
                    temperature=0.7,
                    top_p=1,
                    max_tokens=4096,  # Increased from 2048 to allow for complete responses with citations
                    store=True
                )
            )
            logger.info(f"✅ Created news agent with vector store: {self.config.vector_store_id}")

            # 4. Create web search tool for scraping agent (matching new_agent_new.py)
            web_search = WebSearchTool(
                user_location={
                    "type": "approximate",
                    "country": None,
                    "region": None,
                    "city": None,
                    "timezone": None
                },
                search_context_size="medium",
                filters=WebSearchFilters(
                    allowed_domains=["www.pv-magazine.com"]
                )
            )

            # 5. Create scraping agent with web search
            self.scraping_agent = Agent(
                name="Scraping Agent",
                instructions=self.SCRAPING_AGENT_PROMPT,
                model=self.config.model,
                tools=[web_search],
                model_settings=ModelSettings(
                    temperature=0.7,
                    top_p=1,
                    max_tokens=4096,  # Increased from 2048 to allow for detailed article content
                    store=True
                )
            )
            logger.info("✅ Created scraping agent with web search")

        except Exception as e:
            logger.error(f"❌ Failed to initialize agents: {e}")
            raise

    async def analyze_stream(self, query: str, conversation_id: str = None):
        """
        Analyze query with streaming response using multi-agent workflow

        Args:
            query: Natural language query about news
            conversation_id: Optional conversation ID for maintaining context

        Yields:
            Text chunks as they are generated
        """
        try:
            logger.info(f"Processing news query (streaming): {query}")

            # Get or create session for this conversation
            session = None
            if conversation_id:
                if conversation_id not in self.conversation_sessions:
                    session_id = f"news_{conversation_id}"
                    self.conversation_sessions[conversation_id] = SQLiteSession(
                        session_id=session_id
                    )
                    logger.info(f"Created SQLite session for conversation {conversation_id}")

                session = self.conversation_sessions[conversation_id]

            # Step 1: Classify the intent (non-streaming)
            # IMPORTANT: Don't pass session to intent classifier to avoid duplicate messages in history
            classify_result = await Runner.run(self.intent_agent, query, session=None)
            classification = classify_result.final_output.query_class if hasattr(classify_result.final_output, 'query_class') else "general"

            logger.info(f"Intent classified as: {classification}")

            # Step 2: Route to appropriate agent with streaming
            if classification == "general_news_query":
                # Use news agent with file search
                result = Runner.run_streamed(self.news_agent, query, session=session)
            elif classification == "more_detailed_news_query":
                # Use scraping agent for detailed information
                result = Runner.run_streamed(self.scraping_agent, query, session=session)
            else:
                # Default to news agent for general queries
                result = Runner.run_streamed(self.news_agent, query, session=session)

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
            error_msg = f"Failed to stream news query: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            yield f"\n\n**Error:** {error_msg}"

    async def analyze(self, query: str, conversation_id: str = None) -> Dict[str, Any]:
        """
        Analyze news query using multi-agent workflow

        Args:
            query: Natural language query about news
            conversation_id: Optional conversation ID for maintaining context

        Returns:
            Dictionary with analysis results and metadata
        """
        # Logfire span for news agent
        with logfire.span("news_agent_call") as agent_span:
            agent_span.set_attribute("agent_type", "news")
            agent_span.set_attribute("conversation_id", str(conversation_id))
            agent_span.set_attribute("message_length", len(query))
            agent_span.set_attribute("user_message", query)

            try:
                logger.info(f"Processing news query: {query}")

                # Get or create session for this conversation
                session = None
                if conversation_id:
                    if conversation_id not in self.conversation_sessions:
                        session_id = f"news_{conversation_id}"

                        # Use SQLite for session storage (simple and reliable)
                        self.conversation_sessions[conversation_id] = SQLiteSession(
                            session_id=session_id
                        )
                        logger.info(f"Created SQLite session for conversation {conversation_id}")

                    session = self.conversation_sessions[conversation_id]

                # Step 1: Classify the intent
                # IMPORTANT: Don't pass session to intent classifier to avoid duplicate messages in history
                classify_result = await Runner.run(self.intent_agent, query, session=None)
                classification = classify_result.final_output.query_class if hasattr(classify_result.final_output, 'query_class') else "general"

                logger.info(f"Intent classified as: {classification}")
                agent_span.set_attribute("classification", classification)

                # Step 2: Route to appropriate agent
                if classification == "general_news_query":
                    # Use news agent with file search
                    result = await Runner.run(self.news_agent, query, session=session)
                elif classification == "more_detailed_news_query":
                    # Use scraping agent for detailed information
                    result = await Runner.run(self.scraping_agent, query, session=session)
                else:
                    # Default to news agent for general queries
                    result = await Runner.run(self.news_agent, query, session=session)

                # Extract the final response
                response_text = result.final_output if hasattr(result, 'final_output') else str(result)

                # Clean citation markers from the response
                response_text = clean_citation_markers(response_text)

                # Track the response
                agent_span.set_attribute("assistant_response", response_text)
                agent_span.set_attribute("response_length", len(response_text))
                agent_span.set_attribute("success", True)

                logger.info(f"✅ News agent response: {response_text[:100]}...")

                # Get usage info if available
                usage_info = None
                if hasattr(result, 'usage') and result.usage:
                    usage_info = {
                        "total_tokens": getattr(result.usage, 'total_tokens', None),
                        "prompt_tokens": getattr(result.usage, 'prompt_tokens', None),
                        "completion_tokens": getattr(result.usage, 'completion_tokens', None)
                    }

                return {
                    "success": True,
                    "analysis": response_text,
                    "usage": usage_info,
                    "query": query
                }

            except Exception as e:
                error_msg = f"Failed to analyze news query: {str(e)}"
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
            logger.info("News agent ready for cleanup if needed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global agent instance
_news_agent = None

def get_news_agent() -> Optional[NewsAgent]:
    """Get or create the global news agent instance"""
    global _news_agent
    if _news_agent is None:
        try:
            config = NewsAgentConfig()
            _news_agent = NewsAgent(config)
            logger.info("✅ Global news agent created")
        except Exception as e:
            logger.error(f"❌ Failed to create news agent: {e}")
            return None
    return _news_agent

def close_news_agent():
    """Close the global news agent"""
    global _news_agent
    if _news_agent:
        _news_agent.cleanup()
        _news_agent = None
        logger.info("✅ Global news agent closed")

# Test function
async def test_news_agent():
    """Test the news agent"""
    try:
        agent = get_news_agent()
        if agent:
            result = await agent.analyze(
                "What are the latest developments in solar panel technology?",
                conversation_id="test-1"
            )
            print("News Agent response received successfully")
            print(f"Response length: {len(result.get('analysis', ''))}")
            return result
        else:
            print("News Agent not available")
            return None
    except Exception as e:
        print(f"News Agent error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        close_news_agent()

if __name__ == "__main__":
    asyncio.run(test_news_agent())
