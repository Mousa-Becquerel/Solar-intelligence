"""
Market Intelligence Agent with Plotting Support
===============================================

Multi-agent workflow for PV market data analysis with code interpreter.
Uses OpenAI Agents SDK with CodeInterpreterTool for data processing and visualization.

Architecture:
1. Classification Agent - Routes queries to data analysis or plotting
2. Market Intelligence Agent - Handles data queries with code interpreter
3. Plotting Agent - Generates D3-compatible JSON for frontend rendering
"""

import os
import logging
import re
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import asyncio
from pydantic import BaseModel

# Import from openai-agents library
from agents import (
    CodeInterpreterTool,
    Agent,
    Runner,
    SQLiteSession,
    ModelSettings,
    RunConfig,
    trace,
    TResponseInputItem,
    AgentOutputSchema
)
from openai.types.shared.reasoning import Reasoning

# Logfire imports
import logfire

# === Configure logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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
    pattern = r'【[^】]*】'
    cleaned = re.sub(pattern, '', text)

    # Also remove any orphaned opening brackets
    cleaned = re.sub(r'【', '', cleaned)

    return cleaned

# === Pydantic Models for Structured Outputs ===

from typing import Literal

class ClassificationAgentSchema(BaseModel):
    """Output schema for classification agent"""
    intent: Literal["data", "plot"]  # Must be exactly "data" or "plot"


class PlottingAgentSchema__FiltersApplied(BaseModel):
    """Filters applied to the data"""
    Scenario: str = None
    Type: str = None
    Connection: str = None
    Territory: str = None  # Optional: specific country/region filter


class PlottingAgentSchema__DataItem(BaseModel):
    """Individual data point for D3.js - supports line, bar, and stacked bar charts"""
    date: str = None  # For line charts
    series: str = None  # For line and bar charts
    category: str = None  # For bar and stacked bar charts (x-axis value, e.g., country name, year)
    stack: str = None  # For stacked bar charts only (stack group name)
    value: float
    formatted_value: str
    share: float = None  # For stacked charts - percentage share
    is_small: bool = None  # Flag for small segments in stacked charts
    show_segment_labels: bool = None  # Control visibility of segment labels in stacked charts


class PlottingAgentSchema__SeriesInfoItem(BaseModel):
    """Series styling information for line charts"""
    name: str
    color: str
    line_style: str = None  # Optional for stacked bars
    marker: str = None  # Optional for stacked bars


class PlottingAgentSchema__StackInfoItem(BaseModel):
    """Stack styling information for stacked bar charts"""
    name: str
    color: str


class PlottingAgentSchema__Metadata(BaseModel):
    """Plot metadata"""
    source: str
    generated_at: str
    notes: str


class PlottingAgentSchema(BaseModel):
    """Complete plotting schema - matches frontend D3.js requirements"""
    plot_type: str  # "line", "bar", or "stacked_bar"
    title: str
    description: str
    x_axis_label: str
    y_axis_label: str
    unit: str
    stack_by: str = None  # For stacked bar charts: "Connection"
    filters_applied: PlottingAgentSchema__FiltersApplied
    data: list[PlottingAgentSchema__DataItem]
    series_info: list[PlottingAgentSchema__SeriesInfoItem] = None  # For line and bar charts
    stack_info: list[PlottingAgentSchema__StackInfoItem] = None  # For stacked bar charts
    metadata: PlottingAgentSchema__Metadata
    success: bool


class EvaluationAgentSchema(BaseModel):
    """Output schema for evaluation agent - assesses response quality"""
    response_quality: Literal["good_answer", "bad_answer"]  # Fixed typo from original


class ResponseAgentSchema(BaseModel):
    """Output schema for response agent - formats final answer"""
    informative_summary: str


class WorkflowInput(BaseModel):
    """Input for the workflow"""
    input_as_text: str


# === Configuration ===
@dataclass
class MarketIntelligenceConfig:
    """Configuration for Market Intelligence Agent"""
    model: str = "gpt-5"
    agent_name: str = "Market Intelligence Agent"
    file_id: str = "file-2C3SRLgo4PVK8PRQhgrjRN"  # Main market data CSV
    plotting_file_id: str = "file-2C3SRLgo4PVK8PRQhgrjRN"  # Plotting data CSV (same file)
    reasoning_effort: str = "low"
    reasoning_summary: str = "auto"


# === Market Intelligence Agent Class ===
class MarketIntelligenceAgent:
    """
    Multi-agent workflow for market intelligence with plotting support.
    """

    # Schema description for the market database
    MARKET_DATABASE_SCHEMA = """You are a Market Intelligence Agent with access to PV market data. Your role is to analyze data and extract insights.

**Your Focus:**
- Extract accurate data from the database
- Perform calculations and comparisons
- Identify trends and patterns
- Provide clear, factual insights
- Keep responses concise and focused on the data

**Response Style:**
- Focus on facts and numbers, not formatting
- Use simple, clear language
- State findings directly (e.g., "Italy installed 1,234.5 MW in 2024, up 20% from 2023")
- List key data points without elaborate formatting
- Avoid markdown headers, tables, or emojis - a Response Agent will handle formatting later

**Example Response:**
"Based on the data, Italy's total solar capacity in 2024 was 1,234.5 MW. This represents a 20% increase from 2023 when capacity was 1,028 MW. Germany leads the region with 1,560 MW installed. The growth rate across these markets averaged 15.2% year-over-year."

This is the schema of the data:

dataset:
  name: Market_Database_FY_Final
  version: 2.0.0
  description: Simplified PV market database with annual and cumulative capacity data by territory
  source: Market_Database_FY_Final.csv
  encoding: utf-8
schema:
  fields:
  - name: Territory
    type: string
    description: Country or region name (full name, not code)
    example: Albania, Italy, Germany
    constraints:
      required: true
  - name: Year
    type: integer
    description: Calendar year
    example: 2023, 2024
    constraints:
      min: 1992
      max: 2030
  - name: Scenario
    type: string
    description: Data scenario (Historical or Forecast)
    constraints:
      enum:
      - Historical Primary
      - Forecast - High
      - Forecast - Low
      - Forecast - Most probable
  - name: Connection
    type: string
    description: Connection type for the installation
    constraints:
      enum:
      - Total
      - Centralised
      - Distributed
      - Off-grid
  - name: Type
    type: string
    description: Whether the capacity value represents annual additions or cumulative total
    constraints:
      enum:
      - Annual
      - Cumulative
  - name: Capacity(MW)
    type: float
    description: Power capacity in megawatts (MW), DC values
  - name: AC/DC
    type: string
    description: Whether capacity is measured in AC or DC
    example: DC, AC
    constraints:
      enum:
      - DC
      - AC
  - name: Estimated/Confirmed
    type: string
    description: Data reliability indicator
    constraints:
      enum:
      - Estimated
      - Confirmed
  - name: Installed/Decomissioned
    type: string
    description: Whether capacity was installed or decommissioned
    constraints:
      enum:
      - Installed
      - Decomissioned

profiling:
  row_count: ~18000
  column_count: 9

**Field Descriptions:**

**Connection:**
- "Total": Sum of Centralised + Distributed + Off-grid (always accurate, no double counting)
- "Centralised": Utility-scale centralized installations
- "Distributed": Distributed/rooftop installations
- "Off-grid": Off-grid installations

**Type:**
- "Annual": New capacity added in that year
- "Cumulative": Total installed capacity up to and including that year

**Default Behavior:**
Use Connection = "Total" for general queries unless the user specifically asks for a breakdown by connection type.

**Data Cleaning for Plots:**
When generating plots showing trends over time:
- Filter out leading zero values at the beginning of time series
- Only include years where the capacity value is greater than zero
- This avoids showing long flat lines at zero before actual data begins
- Example: If Italy has zeros from 1992-2005, start the plot from 2006 when actual capacity begins

Never give any link to the user to download anything.
"""

    def __init__(self, config: Optional[MarketIntelligenceConfig] = None):
        """Initialize the Market Intelligence Agent with multi-agent workflow"""
        self.config = config or MarketIntelligenceConfig()
        self.conversation_sessions: Dict[str, Any] = {}

        # Initialize agents
        self._initialize_agents()

        logger.info("✅ Market Intelligence Agent initialized (Memory: SQLite)")

    def _initialize_agents(self):
        """Initialize all agents in the workflow"""
        try:
            # Code interpreter for main market intelligence agent
            self.code_interpreter_main = CodeInterpreterTool(tool_config={
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "file_ids": [self.config.file_id]
                }
            })

            # Code interpreter for plotting agent
            self.code_interpreter_plotting = CodeInterpreterTool(tool_config={
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "file_ids": [self.config.plotting_file_id]
                }
            })

            # 1. Classification Agent - Routes between data vs plot intent
            self.classification_agent = Agent(
                name="Classification Agent",
                instructions="""You are a classification agent. Your job is to determine the user's intent based on their current query and conversation history.

Return EXACTLY one of these two values:
- "data" - if the user wants to analyze data, get insights, or ask questions about the data
- "plot" - if the user wants to generate a chart, graph, or visualization

IMPORTANT: Consider conversation context for follow-up queries:
- If the previous response was a plot and user says "now do it for Italy", classify as "plot"
- If the previous query was about plotting and user says "what about Germany?", classify as "plot"
- Look at the conversation history to understand what "it" or "that" refers to

Examples:
- "How much PV did Italy install?" -> "data"
- "Generate a plot of Italy PV" -> "plot"
- "Show me a chart of installations" -> "plot"
- "What were the top countries?" -> "data"
- After a plot: "now do it for Italy" -> "plot" (context: user wants same plot for different country)
- After a plot: "what about Germany?" -> "plot" (context: continuing plot requests)
""",
                model="gpt-4.1",  # Fast, lightweight model for simple classification (no reasoning support)
                output_type=ClassificationAgentSchema,
                model_settings=ModelSettings(
                    store=True
                    # Note: gpt-4.1 does not support reasoning, so no Reasoning config
                )
            )

            # 2. Market Intelligence Agent - Handles data queries
            self.market_intelligence_agent = Agent(
                name=self.config.agent_name,
                instructions=self.MARKET_DATABASE_SCHEMA,
                model=self.config.model,
                tools=[self.code_interpreter_main],
                model_settings=ModelSettings(
                    store=True,
                    reasoning=Reasoning(
                        effort=self.config.reasoning_effort,
                        summary=self.config.reasoning_summary
                    )
                )
            )

            # 3. Plotting Agent - Generates D3-compatible JSON
            self.plotting_agent = Agent(
                name="Plotting Agent",
                instructions="""
You are a plotting agent. Your role is to extract the parameters for generating a plot from the user query, and then provide the response in the specified JSON format so it can be rendered in the frontend.

**IMPORTANT: Brand Color Palette**

Always use these specific colors in this exact order for series_info and stack_info:

1. **#EB8F47** (Persian orange) - Primary color, use for first series/stack
2. **#000A55** (Federal blue) - Use for second series/stack
3. **#949CFF** (Vista Blue) - Use for third series/stack
4. **#C5C5C5** (Silver) - Use for fourth series/stack
5. **#E5A342** (Hunyadi yellow) - Use for fifth series/stack

For stacked bar charts specifically:
- Centralised → #000A55 (Federal blue)
- Distributed → #EB8F47 (Persian orange)
- Off-grid → #949CFF (Vista Blue)

You can generate three types of plots:

## 1. LINE CHART
Use for showing trends over time for different countries, regions, or series.

Example schema:
{
  "plot_type": "line",
  "title": "PV Installations Over Time",
  "description": "Line chart showing the evolution of photovoltaic capacity over time for selected countries, regions, or segments.",

  "x_axis_label": "Year",
  "y_axis_label": "Installed Capacity (MW)",
  "unit": "MW",

  "filters_applied": {
    "Scenario": "Historical Primary",
    "Type": "Cumulative",
    "Connection": "Total"
  },

  "data": [
    {
      "date": "2020-01-01",
      "series": "Italy",
      "value": 21000.0,
      "formatted_value": "21.0 GW"
    },
    {
      "date": "2021-01-01",
      "series": "Italy",
      "value": 24200.0,
      "formatted_value": "24.2 GW"
    }
  ],

  "series_info": [
    {
      "name": "Italy",
      "color": "#EB8F47",
      "line_style": "solid",
      "marker": "circle"
    }
  ],

  "metadata": {
    "source": "Market_Database_Final.csv",
    "generated_at": "2025-10-22T00:00:00Z",
    "notes": "Data filtered to avoid double counting; only total values used unless detailed view requested."
  },

  "success": true
}

## 2. BAR CHART
Use for comparing values across different categories (e.g., countries, regions) for a specific time period or single year.

**IMPORTANT**: Bar charts should use ONLY ONE SCENARIO at a time. For multi-scenario comparisons, use LINE CHART instead.

Example schema:
{
  "plot_type": "bar",
  "title": "PV Capacity by Country in 2024",
  "description": "Bar chart comparing total installed PV capacity across different countries in 2024.",

  "x_axis_label": "",
  "y_axis_label": "Installed Capacity (MW)",
  "unit": "MW",

  "filters_applied": {
    "Scenario": "Historical Primary",
    "Type": "Cumulative",
    "Connection": "Total",
    "Territory": "Multiple"
  },

  "data": [
    {
      "category": "Italy",
      "series": "Total Capacity",
      "value": 28450.0,
      "formatted_value": "28.5 GW"
    },
    {
      "category": "Germany",
      "series": "Total Capacity",
      "value": 65200.0,
      "formatted_value": "65.2 GW"
    },
    {
      "category": "Spain",
      "series": "Total Capacity",
      "value": 19800.0,
      "formatted_value": "19.8 GW"
    }
  ],

  "series_info": [
    {
      "name": "Total Capacity",
      "color": "#EB8F47",
      "line_style": "solid",
      "marker": "square"
    }
  ],

  "metadata": {
    "source": "Market_Database_Final.csv",
    "generated_at": "2025-10-22T00:00:00Z",
    "notes": "Bar chart showing comparative values for a specific time period."
  },

  "success": true
}

## 3. STACKED BAR CHART
Use for showing composition/breakdown of capacity by Connection type over time.

**IMPORTANT RULES for Stacked Bar Charts:**
- When stacking by "Connection": Only include "Centralised", "Distributed", and "Off-grid" - NEVER include "Total"
- The "Total" values are the sum of all connection types and should NOT be included as a separate stack
- Include "share" (percentage as decimal), "is_small" (true for segments < 5% of total), and "show_segment_labels" (true to show value labels on bars)
- Set "show_segment_labels" to false if there are many years/categories to prevent label clutter

Example schema for stacked bar chart:
{
  "plot_type": "stacked_bar",
  "title": "PV Installations by Connection Type - Italy",
  "description": "Stacked bar chart showing the distribution of capacity across Centralised, Distributed, and Off-grid connections over time.",

  "x_axis_label": "Year",
  "y_axis_label": "Installed Capacity (MW)",
  "unit": "MW",
  "stack_by": "Connection",

  "filters_applied": {
    "Scenario": "Historical Primary",
    "Type": "Annual",
    "Territory": "Italy"
  },

  "data": [
    {
      "category": "2020",
      "stack": "Centralised",
      "value": 15000.0,
      "formatted_value": "15.0 GW",
      "share": 0.638,
      "is_small": false,
      "show_segment_labels": true
    },
    {
      "category": "2020",
      "stack": "Distributed",
      "value": 8000.0,
      "formatted_value": "8.0 GW",
      "share": 0.340,
      "is_small": false,
      "show_segment_labels": true
    },
    {
      "category": "2020",
      "stack": "Off-grid",
      "value": 500.0,
      "formatted_value": "0.5 GW",
      "share": 0.021,
      "is_small": true,
      "show_segment_labels": true
    },
    {
      "category": "2021",
      "stack": "Centralised",
      "value": 18000.0,
      "formatted_value": "18.0 GW",
      "share": 0.629,
      "is_small": false,
      "show_segment_labels": true
    },
    {
      "category": "2021",
      "stack": "Distributed",
      "value": 10000.0,
      "formatted_value": "10.0 GW",
      "share": 0.350,
      "is_small": false,
      "show_segment_labels": true
    },
    {
      "category": "2021",
      "stack": "Off-grid",
      "value": 600.0,
      "formatted_value": "0.6 GW",
      "share": 0.021,
      "is_small": true,
      "show_segment_labels": true
    }
  ],

  "stack_info": [
    {
      "name": "Centralised",
      "color": "#000A55"
    },
    {
      "name": "Distributed",
      "color": "#EB8F47"
    },
    {
      "name": "Off-grid",
      "color": "#949CFF"
    }
  ],

  "metadata": {
    "source": "Market_Database_Final.csv",
    "generated_at": "2025-10-22T00:00:00Z",
    "notes": "Stacked bars show individual connection types. Total values excluded to avoid double counting."
  },

  "success": true
}

**DECISION LOGIC:**
- If user asks for "breakdown", "distribution", "composition", or "split by Connection" → use STACKED BAR CHART
- If user asks for "trend", "over time", "evolution", or compares data across multiple time periods → use LINE CHART
- If user asks to "compare scenarios", "show all forecasts", or wants to see multiple scenarios → use LINE CHART (each scenario as a separate line)
- If user asks for "compare countries", "top countries", or wants to compare values for a SINGLE YEAR/TIME PERIOD with ONE SCENARIO → use BAR CHART

**CRITICAL RULES:**
1. BAR CHARTS: Always use ONLY ONE scenario (e.g., only "Historical Primary" OR only "Forecast - High")
2. STACKED BAR CHARTS: Always use ONLY ONE scenario, stack by Connection type only
3. MULTI-SCENARIO COMPARISONS: Always use LINE CHART with each scenario as a separate series/line

Examples:
- "Show me PV capacity trends in Italy from 2015-2024" → LINE CHART (multi-year trend)
- "Compare PV capacity across European countries in 2024" → BAR CHART (single year, single scenario comparison)
- "Show Italy's installations broken down by connection type" → STACKED BAR CHART (composition, single scenario)
- "Top 5 countries by capacity in 2023" → BAR CHART (single year ranking, single scenario)
- "Germany and France capacity evolution" → LINE CHART (multi-year comparison)
- "Show Germany's forecast for 2025-2030 with all scenarios" → LINE CHART (each scenario as a separate line)
- "Compare low, most probable, and high forecasts for Italy" → LINE CHART (three lines, one per scenario)
- "Plot Germany's utility-scale additions 2025-2030" → LINE CHART if multiple scenarios, BAR CHART if user specifies one scenario only

**CRITICAL: Data Cleaning and Sampling for Clean Visualizations**

When extracting data for plots, apply these rules to ensure clean, readable visualizations:

**1. Filter out leading zeros (LINE CHARTS only):**
- For LINE CHARTS showing trends over time, filter out leading zero values
- Find the first year where capacity > 0 for each series and start from there
- This avoids long flat lines at zero before actual data begins

**2. Smart Sampling for BAR and STACKED BAR CHARTS:**

BAR CHARTS and STACKED BAR CHARTS get cluttered when showing too many years. Apply intelligent sampling:

- **If time range > 15 years**: Sample data intelligently to show ~10-15 bars maximum
- **Sampling strategies**:
  - For 20-30 years: Show every 2nd or 3rd year (e.g., 2000, 2003, 2006, 2009...)
  - For 30+ years: Show every 5th year (e.g., 1995, 2000, 2005, 2010...)
  - **Always include most recent year** (e.g., 2024) for current context
  - For historical + forecast: Show last 5 historical years + all forecast years

**3. Alternative Approach - Focus on Recent Data:**
- If user doesn't specify time range, default to **last 10 years** for BAR/STACKED BAR charts
- Example: For a query about Netherlands installations, show 2015-2024 instead of 1994-2024
- This keeps visualizations clean and focuses on recent, relevant trends

**Python code examples:**

```python
# Example 1: Sample every N years for long time series
years = sorted(df['Year'].unique())
if len(years) > 15:
    # Keep every 3rd year, but always include the most recent year
    sampled_years = years[::3]  # Every 3rd year
    if years[-1] not in sampled_years:
        sampled_years = list(sampled_years) + [years[-1]]
    df = df[df['Year'].isin(sampled_years)]

# Example 2: Focus on recent years (recommended for most cases)
recent_years = 10  # Last 10 years
max_year = df['Year'].max()
df = df[df['Year'] >= (max_year - recent_years)]

# Example 3: Historical + Forecast split
# Show last 5 historical years + all forecast years
historical = df[df['Scenario'] == 'Historical Primary']
forecast = df[df['Scenario'].str.contains('Forecast')]
max_historical_year = historical['Year'].max()
historical_recent = historical[historical['Year'] >= (max_historical_year - 5)]
df_combined = pd.concat([historical_recent, forecast])
```
Once you understand the plot to be generated, extract the required data from the dataset you have access to, applying the data cleaning and sampling rules above.

""",
                model=self.config.model,  # gpt-5 with reasoning for high-quality plots
                tools=[self.code_interpreter_plotting],
                output_type=PlottingAgentSchema,
                model_settings=ModelSettings(
                    store=True,
                    reasoning=Reasoning(
                        effort=self.config.reasoning_effort,
                        summary=self.config.reasoning_summary
                    )
                )
            )

            # 4. Evaluation Agent - Assesses response quality (good vs bad answer)
            self.evaluation_agent = Agent(
                name="Evaluation Agent",
                instructions="""You evaluate Market Intelligence Agent responses about PV (solar photovoltaic) market data. Classify as "good_answer" or "bad_answer" based on whether the agent found relevant data.

**Classification Criteria:**

- **"good_answer"**: The agent provides relevant PV market data that answers the user's query, even if partial or limited.
- **"bad_answer"**: The agent explicitly states that NO relevant data exists in the database for the query.

**Important Distinctions:**

✅ **"good_answer"** includes:
- Complete data answering the full query
- Partial data (e.g., data for 2023-2024 when user asked for 2020-2024)
- Data for similar regions/technologies if exact match not available
- Any insights derived from available PV market data

❌ **"bad_answer"** ONLY when:
- Agent says "no data available" or "data does not exist" for the query
- Agent cannot find ANY relevant information in the database
- Agent explicitly states the requested information is not in the dataset

**Output Format:**

Respond ONLY with this JSON (no explanations):

{
  "response_quality": "good_answer"
}

or

{
  "response_quality": "bad_answer"
}

**Examples:**

**Example 1 - good_answer**
- User Query: "What was Italy's solar capacity in 2024?"
- Agent Response: "Italy's total solar capacity in 2024 was 28,450 MW, representing a 12% increase from 2023."
- Output: {"response_quality": "good_answer"}

**Example 2 - bad_answer**
- User Query: "What is Tesla's solar panel manufacturing capacity?"
- Agent Response: "I don't have data on Tesla's solar panel manufacturing capacity. Our database contains PV market installation data by country and region, not individual company manufacturing details."
- Output: {"response_quality": "bad_answer"}

**Example 3 - good_answer (partial data)**
- User Query: "Show me Germany's solar installations from 2010 to 2024"
- Agent Response: "I have data for Germany from 2015 to 2024. In 2015, Germany had 39,700 MW installed, growing to 82,150 MW by 2024."
- Output: {"response_quality": "good_answer"}

**Example 4 - bad_answer**
- User Query: "What are the labor costs for solar installation in Spain?"
- Agent Response: "Our database doesn't include labor cost data. We only have PV installation capacity data by territory, connection type, and technology."
- Output: {"response_quality": "bad_answer"}

**Example 5 - good_answer (alternative data)**
- User Query: "What's the solar capacity in Scandinavia?"
- Agent Response: "While we don't have a 'Scandinavia' category, I can provide data for the Nordic countries. Norway had 450 MW, Sweden had 2,100 MW, and Denmark had 1,800 MW in 2024."
- Output: {"response_quality": "good_answer"}

**Rules:**
- Only output the JSON with "response_quality" field
- Do NOT add reasoning, explanations, or extra fields
- When in doubt, if ANY relevant PV market data was provided, classify as "good_answer"
""",
                model="gpt-4.1",  # Fast classification model
                output_type=EvaluationAgentSchema,
                model_settings=ModelSettings(
                    store=True
                )
            )

            # 5. Response Agent - Formats and presents good answers beautifully
            self.response_agent = Agent(
                name="Response Agent",
                instructions="""You are a Response Agent that transforms raw market intelligence data into beautifully formatted, user-friendly responses.

**Your Role:**
- Take the factual response from the Market Intelligence Agent
- Transform it into a professional, well-structured format
- Apply consistent styling and formatting guidelines
- Make the data easy to scan and understand
- Highlight key insights and findings

**Formatting Guidelines (CRITICAL - Apply these consistently):**
- Use proper markdown formatting with headers (##, ###), bullet points (-), and numbered lists
- Break content into clear sections with descriptive headers
- Use **bold** for key terms, important numbers, and metrics
- Use tables for comparative data (e.g., country comparisons, year-over-year data)
- Add blank lines between sections for readability
- Structure long lists as proper bullet points, not run-on sentences
- Use concise paragraphs (2-3 sentences max)
- Highlight trends with visual indicators when appropriate (📈 for growth, 📉 for decline)
- Format large numbers with thousand separators (e.g., 1,234.5 MW instead of 1234.5)

**Example Transformation:**

Input from Market Intelligence Agent:
"Italy's total solar capacity in 2024 was 1,234.5 MW. This represents a 20% increase from 2023 when capacity was 1,028 MW. Germany leads with 1,560 MW installed. Growth rate averaged 15.2% year-over-year."

Your Output:
## Market Overview
Based on the latest data, here's the solar capacity analysis you requested:

### Key Findings 📊
- **Italy 2024**: 1,234.5 MW total installed capacity
- **Growth Rate**: +20% year-over-year 📈
- **Regional Leader**: Germany with 1,560 MW

### Detailed Breakdown
| Country | 2023 | 2024 | Growth |
|---------|------|------|--------|
| Germany | 1,300 MW | 1,560 MW | +20.0% |
| Italy | 1,028 MW | 1,234.5 MW | +20.1% |

### Market Insights
The regional solar market showed strong growth with an average increase of **15.2% year-over-year**. Germany maintains its position as the market leader, while Italy demonstrated impressive expansion.

**Important Rules:**
- Do NOT add facts or numbers that weren't in the Market Intelligence Agent's response
- Do NOT make assumptions or estimates
- Do NOT change the meaning of the data
- ONLY reformat, structure, and present the existing information beautifully
- If the Market Intelligence Agent mentions data unavailability, present it clearly but don't apologize excessively""",
                model="gpt-4.1",
                output_type=ResponseAgentSchema,
                model_settings=ModelSettings(
                    store=True
                )
            )

            # 6. Follow-up Agent - Handles bad answers by offering expert contact
            self.follow_up_agent = Agent(
                name="Follow-up Agent",
                instructions="""You are an agent which requires to summarize the response coming from the Market Intelligence Agent, and to ask the user whether he would like to reach experts to answer his query since the information is not present.

First summarize what comes from the Market Intelligence Agent regarding the info the user asks for, then offer the user to reach an expert to get a proper answer to his query.

Example format:
"Based on the available data, [summary of what was found/not found].

Unfortunately, we don't have complete information on [specific missing data]. Would you like me to connect you with one of our market experts who can provide more detailed insights on this topic? They can offer personalized analysis based on the latest industry research."
""",
                model="gpt-4.1-mini",  # Lighter model for simple follow-up
                model_settings=ModelSettings(
                    store=True
                )
            )

            logger.info(f"✅ Created market intelligence agent with file: {self.config.file_id}")
            logger.info(f"✅ Created evaluation, response, and follow-up agents")

        except Exception as e:
            logger.error(f"❌ Failed to initialize agents: {e}")
            raise

    async def run_workflow(self, workflow_input: WorkflowInput, conversation_id: str = None):
        """
        Run the multi-agent workflow

        Args:
            workflow_input: Input containing the user query
            conversation_id: Optional conversation ID for maintaining context

        Returns:
            Dictionary with output from the appropriate agent
        """
        with trace("New workflow"):
            # Get or create session for this conversation
            session = None
            if conversation_id:
                if conversation_id not in self.conversation_sessions:
                    session_id = f"market_intel_{conversation_id}"
                    self.conversation_sessions[conversation_id] = SQLiteSession(
                        session_id=session_id
                    )
                    logger.info(f"Created SQLite session for conversation {conversation_id}")

                session = self.conversation_sessions[conversation_id]

            # Get user query as string (required when using session)
            workflow = workflow_input.model_dump()
            user_query = workflow["input_as_text"]

            # Step 1: Classification - Determine intent (data vs plot)
            # IMPORTANT: Don't pass session to classification agent to avoid duplicate messages
            classification_result_temp = await Runner.run(
                self.classification_agent,
                input=user_query,
                session=None,
                run_config=RunConfig(trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "market_intelligence_workflow"
                })
            )

            classification_result = {
                "output_text": classification_result_temp.final_output.json(),
                "output_parsed": classification_result_temp.final_output.model_dump()
            }

            intent = classification_result["output_parsed"]["intent"]
            logger.info(f"Classified intent: {intent}")

            # Step 2: Route to appropriate agent based on intent
            if intent == "plot":
                # Step 2a: Use plotting agent to generate D3-compatible JSON
                # IMPORTANT: Don't pass session here either, as plotting agent doesn't need conversation context
                logger.info("Routing to plotting agent")
                plotting_result_temp = await Runner.run(
                    self.plotting_agent,
                    input=user_query,
                    session=None,
                    run_config=RunConfig(trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "market_intelligence_workflow"
                    })
                )

                # Return plot JSON directly (no commentary)
                return {
                    "output_text": plotting_result_temp.final_output.json(),
                    "output_parsed": plotting_result_temp.final_output.model_dump(),
                    "response_type": "plot"  # Flag for app.py to handle differently
                }

            else:
                # Step 2b: Use market intelligence agent for data analysis
                logger.info("Routing to market intelligence agent")
                market_result_temp = await Runner.run(
                    self.market_intelligence_agent,
                    input=user_query,
                    session=session,
                    run_config=RunConfig(trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "market_intelligence_workflow"
                    })
                )

                market_intelligence_response = market_result_temp.final_output_as(str)
                logger.info("Market intelligence agent completed")

                # Step 3: Evaluation - Assess response quality
                # IMPORTANT: Don't pass session to evaluation agent
                logger.info("Evaluating response quality")
                evaluation_result_temp = await Runner.run(
                    self.evaluation_agent,
                    input=user_query,  # Evaluation agent will see conversation history including market agent's response
                    session=None,
                    run_config=RunConfig(trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "market_intelligence_workflow"
                    })
                )

                evaluation_result = evaluation_result_temp.final_output.model_dump()
                response_quality = evaluation_result["response_quality"]
                logger.info(f"Response quality: {response_quality}")

                # Step 4: Route based on evaluation
                if response_quality == "bad_answer":
                    # Step 4a: Follow-up agent offers expert contact
                    logger.info("Bad answer detected - routing to follow-up agent")
                    follow_up_result_temp = await Runner.run(
                        self.follow_up_agent,
                        input=user_query,
                        session=session,  # Follow-up agent should have context
                        run_config=RunConfig(trace_metadata={
                            "__trace_source__": "agent-builder",
                            "workflow_id": "market_intelligence_workflow"
                        })
                    )

                    follow_up_response = follow_up_result_temp.final_output_as(str)
                    return {
                        "output_text": follow_up_response,
                        "response_type": "text",
                        "quality": "bad_answer",
                        "offers_expert_contact": True
                    }

                else:  # good_answer
                    # Step 4b: Response agent formats and summarizes
                    logger.info("Good answer - routing to response agent")
                    response_result_temp = await Runner.run(
                        self.response_agent,
                        input=user_query,
                        session=session,  # Response agent needs full context
                        run_config=RunConfig(trace_metadata={
                            "__trace_source__": "agent-builder",
                            "workflow_id": "market_intelligence_workflow"
                        })
                    )

                    final_response = response_result_temp.final_output.informative_summary
                    return {
                        "output_text": final_response,
                        "response_type": "text",
                        "quality": "good_answer"
                    }

    async def analyze_stream(self, query: str, conversation_id: str = None):
        """
        Analyze query with streaming response

        Args:
            query: Natural language query
            conversation_id: Optional conversation ID for maintaining context

        Yields:
            Text chunks or plot JSON as they are generated
        """
        try:
            logger.info(f"Processing query (streaming): {query}")

            # Get or create session for this conversation
            session = None
            if conversation_id:
                if conversation_id not in self.conversation_sessions:
                    session_id = f"market_intel_{conversation_id}"
                    self.conversation_sessions[conversation_id] = SQLiteSession(
                        session_id=session_id
                    )
                    logger.info(f"Created SQLite session for conversation {conversation_id}")

                session = self.conversation_sessions[conversation_id]

            # Step 1: Classification - Determine intent (data vs plot)
            # IMPORTANT: Pass session so classification can understand context (e.g., "now do it for Italy")
            classification_result = await Runner.run(
                self.classification_agent,
                input=query,
                session=session,  # Changed from None to session for context-aware classification
                run_config=RunConfig(trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": "market_intelligence_workflow"
                })
            )

            intent = classification_result.final_output.intent if hasattr(classification_result.final_output, 'intent') else "data"
            logger.info(f"Classified intent: {intent}")

            # Step 2: Route to appropriate agent with streaming
            if intent == "plot":
                # Step 2a: Use plotting agent - plots return complete JSON (no streaming)
                # IMPORTANT: Pass session so plot queries are added to conversation history
                logger.info("Routing to plotting agent")

                plotting_result = await Runner.run(
                    self.plotting_agent,
                    input=query,
                    session=session,  # Changed from None to session to maintain conversation history
                    run_config=RunConfig(trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "market_intelligence_workflow"
                    })
                )

                # Yield the plot JSON
                plot_json = plotting_result.final_output.model_dump()
                yield json.dumps({"type": "plot", "content": plot_json})

            else:
                # Step 2b: Use market intelligence agent for data analysis
                # NOTE: For streaming, we collect the full response first, then evaluate
                logger.info("Routing to market intelligence agent")

                # Send status update - analyzing data
                yield json.dumps({"type": "status", "message": "Analyzing data..."})

                # Run market intelligence agent (non-streaming for evaluation)
                market_result_temp = await Runner.run(
                    self.market_intelligence_agent,
                    input=query,
                    session=session,
                    run_config=RunConfig(trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "market_intelligence_workflow"
                    })
                )

                market_intelligence_response = market_result_temp.final_output_as(str)
                logger.info("Market intelligence agent completed")

                # Send status update - evaluating quality
                yield json.dumps({"type": "status", "message": "Evaluating response quality..."})

                # Step 3: Evaluation - Assess response quality
                logger.info("Evaluating response quality")
                evaluation_result_temp = await Runner.run(
                    self.evaluation_agent,
                    input=query,
                    session=None,
                    run_config=RunConfig(trace_metadata={
                        "__trace_source__": "agent-builder",
                        "workflow_id": "market_intelligence_workflow"
                    })
                )

                evaluation_result = evaluation_result_temp.final_output.model_dump()
                response_quality = evaluation_result["response_quality"]
                logger.info(f"Response quality: {response_quality}")

                # Step 4: Route based on evaluation
                if response_quality == "bad_answer":
                    # Follow-up agent offers expert contact
                    logger.info("Bad answer detected - routing to follow-up agent")

                    # Send status update
                    yield json.dumps({"type": "status", "message": "Preparing alternative response..."})

                    follow_up_result_temp = await Runner.run(
                        self.follow_up_agent,
                        input=query,
                        session=session,
                        run_config=RunConfig(trace_metadata={
                            "__trace_source__": "agent-builder",
                            "workflow_id": "market_intelligence_workflow"
                        })
                    )

                    follow_up_response = follow_up_result_temp.final_output_as(str)
                    # Yield approval request - frontend will show Yes/No buttons
                    yield json.dumps({
                        "type": "approval_request",
                        "message": follow_up_response,
                        "approval_question": "Would you like to proceed and reach the expert?",
                        "conversation_id": conversation_id,
                        "context": "expert_contact"
                    })

                else:  # good_answer
                    # Response agent formats and summarizes
                    logger.info("Good answer - routing to response agent")

                    # Send status update
                    yield json.dumps({"type": "status", "message": "Formatting response..."})

                    response_result_temp = await Runner.run(
                        self.response_agent,
                        input=query,
                        session=session,
                        run_config=RunConfig(trace_metadata={
                            "__trace_source__": "agent-builder",
                            "workflow_id": "market_intelligence_workflow"
                        })
                    )

                    final_response = response_result_temp.final_output.informative_summary
                    # Clean citation markers
                    cleaned_response = clean_citation_markers(final_response)
                    # Yield formatted response
                    yield json.dumps({
                        "type": "text",
                        "content": cleaned_response,
                        "quality": "good_answer"
                    })

        except Exception as e:
            error_msg = f"Failed to stream query: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            yield f"\n\n**Error:** {error_msg}"

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
        self.clear_conversation_memory()
        logger.info("Market Intelligence Agent cleanup complete")


# === Global Instance Management ===
_global_market_intelligence_agent: Optional[MarketIntelligenceAgent] = None


def get_market_intelligence_agent(config: Optional[MarketIntelligenceConfig] = None) -> MarketIntelligenceAgent:
    """
    Get or create the global Market Intelligence agent instance (singleton pattern).

    Args:
        config: Optional configuration for the agent

    Returns:
        MarketIntelligenceAgent: Global agent instance
    """
    global _global_market_intelligence_agent

    if _global_market_intelligence_agent is None:
        _global_market_intelligence_agent = MarketIntelligenceAgent(config)
        logger.info("✅ Global market intelligence agent created")

    return _global_market_intelligence_agent


def close_market_intelligence_agent():
    """Close and cleanup the global Market Intelligence agent"""
    global _global_market_intelligence_agent

    if _global_market_intelligence_agent is not None:
        _global_market_intelligence_agent.cleanup()
        _global_market_intelligence_agent = None
        logger.info("✅ Global market intelligence agent closed")
