"""
Module Prices Analysis Agent
============================

A Pydantic AI agent for analyzing solar component prices using PandasAI.
Similar to the market data agent but focused on component pricing data.
"""

import asyncio
import os
import logging
from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass
import pandas as pd
import uuid
from datetime import datetime
import re

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic import BaseModel
from enum import Enum
import pandasai as pai
from pandasai_litellm.litellm import LiteLLM
from dotenv import load_dotenv

# Logfire imports
import logfire

# === Pydantic Output Models ===
class PlotResult(BaseModel):
    """Structured output for plot generation results"""
    plot_type: str
    file_path: str
    url_path: str
    title: str
    description: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

class DataAnalysisResult(BaseModel):
    """Structured output for data analysis results"""
    result_type: Literal["text", "dataframe", "plot"]
    content: str
    dataframe_data: Optional[List[Dict[str, Any]]] = None
    plot_info: Optional[PlotResult] = None

class PlotDataResult(BaseModel):
    """Structured output for frontend plot data (D3/JSON)"""
    plot_type: str
    title: str
    x_axis_label: str
    y_axis_label: str
    unit: str
    data: List[Dict[str, Any]]
    series_info: List[Dict[str, str]] = []
    success: bool = True
    error_message: Optional[str] = None

# === Parameter Schemas (for structured extraction) ===
class PlotType(str, Enum):
    """Allowed plot types for visualization.

    Using an enum ensures the model (and our code) choose only among
    the supported types. This mirrors how we extract typed fields in
    Pydantic-AI docs examples.
    """

    line = "line"
    bar = "bar"
    box = "box"


class PlotTypeRequest(BaseModel):
    """Minimal schema to extract just the plot type.

    This can be expanded later into a full PlotRequest that also
    captures item, region, descriptions, and time bounds, but for now
    we expose a dedicated model so the model can output a typed
    `plot_type` field when asked.
    """

    plot_type: PlotType

class MultiResult(BaseModel):
    """Structured output for multiple results (plots + data)"""
    primary_result_type: Literal["plot", "data", "mixed"]
    summary: str
    plots: List[PlotResult] = []
    data_results: List[DataAnalysisResult] = []
    
    @property
    def has_plots(self) -> bool:
        return len(self.plots) > 0
    
    @property
    def has_data(self) -> bool:
        return len(self.data_results) > 0
    
    @property
    def primary_plot(self) -> Optional[PlotResult]:
        """Return the most relevant plot (usually the last one)"""
        return self.plots[-1] if self.plots else None

# === Configure logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Load environment variables ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

@dataclass
class ModulePricesConfig:
    """Configuration for the module prices agent"""
    model: str = "openai:gpt-4.1"
    llm_model: str = "openai:gpt-4.1"  # Add this for compatibility
    request_limit: int = 10
    total_tokens_limit: int = 20000  # Increased for D3 data processing
    verbose: bool = True

class ModulePricesAgent:
    """
    Enhanced Pydantic-AI agent for analyzing solar module prices.
    """
    
    @property
    def SYSTEM_PROMPT(self):
        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")
        current_year = datetime.now().year
        
        return f"""
You are a solar module price analysis assistant.

**CURRENT CONTEXT:**
- Today's date: {current_date}
- Current year: {current_year}
- When users ask for "current" or "latest" data, actively filter for dates <= {current_date}
- When users ask for "last year", "past year", etc., interpret relative to {current_year}
- IMPORTANT: Always contextualize temporal queries relative to the current date
- Be aware that data may not be available for future dates beyond the current date

**TOOL USAGE:**
- For purely informational or analytical questions, use `analyze_prices_data` and DO NOT call any plotting tools.
- Only when the user explicitly asks to plot/visualize/show/draw a chart, call `get_plot_data_output` for interactive D3 charts. After calling it, reply with: "plot generated successfully".
- Compound queries (multiple plots, data + plots) → use `MultiResult` to return all results
- Greetings → return string directly

**CHART PREFERENCE:**
- Interactive D3 charts provide better user experience with tooltips, zoom, and responsive design
- **CRITICAL:** After `get_plot_data_output`, do not include data details; the UI will render the chart from tool output
- **EFFICIENCY:** Combine all requested series/filters in ONE call (e.g., `descriptions_csv="TOPCon,HJT"`, `min_year=2024`, `max_year=2024`). Do not make multiple plotting tool calls in the same turn.

**CRITICAL RULES:**
- Never compare prices across different units (US$/Wp vs US$/kg vs US$/t)
- **PREFERRED PLOTTING:** Use `get_plot_data_output` for ALL visualization requests and reply with: "plot generated successfully"
- **SINGLE RESULT:** Return PlotDataResult for plots, DataAnalysisResult for single data queries  
- **MULTIPLE RESULTS:** Use MultiResult for compound queries with multiple plots or data+plots
- **NO TEXT SUMMARIES:** Never return plain text when plots or data are generated
- **NEVER use markdown image syntax:** Do not include ![image](path) in responses - use tools instead
- **ALWAYS use tools for plots:** Never describe plots in text - always use plotting tools
- **DATA SOURCE QUERIES:** When users ask about data sources, always check the `source` column in the database
- For multiple regions, use comma-separated format: "China,EU,US"

**DESCRIPTION MATCHING:**
- "PERC ones" or "PERC modules" → use `descriptions=["PERC"]` to match ALL PERC variants
- "TOPCon ones" or "TOPCon modules" → use `descriptions=["TOPCon"]` to match ALL TOPCon variants
- "HJT ones" or "HJT modules" → use `descriptions=["HJT"]` to match ALL HJT variants
- For specific types, use exact names: "p-type mono-Si PERC M10"

**COMPOUND QUERIES:**
- When user asks "what modules prices can you plot for X then plot Y" → FIRST use `analyze_prices_data` to show available data, THEN plot Y
- When user asks "for 2021 and 2022 then plot the PERC ones" → apply the SAME year filter to PERC plot
- Always maintain context from previous parts of the query (years, regions, etc.)
- "What can you plot" or "what data is available" → ALWAYS use `analyze_prices_data` first
- **MANDATORY:** For compound queries, always return MultiResult with both data_results and plots - never plain text

**TEMPORAL QUERY REFORMULATION:**
- "current prices" → "latest prices as of {current_date}"
- "this year" → "prices for {current_year}"
- "last year" → "prices for {current_year - 1}"
- Always clarify temporal context in your responses

**UNITS:** Modules/Cells (US$/Wp), Wafers (US$/pce), Polysilicon (US$/kg), PV Glass (US$/m²), Raw Materials (US$/t)

**REGIONS:** China, EU, US, India, Overseas, Australia

**ITEMS:** Module, Cell, Wafer, Polysilicon, EVA, PV glass, Silver, Copper, Aluminium

**DATA SOURCE:**
- When users ask about data sources or where the data comes from, ALWAYS respond: "All data comes from the DataHub of the Becquerel Institute"
- Never mention other sources or datasets - all price data is exclusively from the Becquerel Institute's DataHub
"""
    
    def __init__(self, config: Optional[ModulePricesConfig] = None):
        self.config = config or ModulePricesConfig()
        self.conversation_memory: Dict[str, List[ModelMessage]] = {}
        self.last_dataframe = None
        self.last_plot_data_result = None  # Track last PlotDataResult for interactive charts
        self._initialize_pandasai()
        self._initialize_agent()

        # Create exports directory for dataframes
        self.EXPORTS_DIR = os.path.join('exports', 'data')
        os.makedirs(self.EXPORTS_DIR, exist_ok=True)

        # Track last generated DataFrame for table rendering
        self.last_dataframe = None
        
    # Note: plotting intent is governed by the system prompt rules; no rule-based detection here.
        
    def _format_dataframe_for_frontend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format DataFrame for frontend display and download"""
        if df is None or df.empty:
            return df
            
        print(f"DEBUG: Starting DataFrame formatting. Shape: {df.shape}")
        print(f"DEBUG: Columns: {list(df.columns)}")
        print(f"DEBUG: Data types: {dict(df.dtypes)}")
        print(f"DEBUG: Sample data:\n{df.head(2)}")
            
        # Create a copy to avoid modifying the original
        formatted_df = df.copy()
        
        # Format timestamp columns to readable dates
        for col in formatted_df.columns:
            print(f"DEBUG: Processing column '{col}', type: {formatted_df[col].dtype}")
            
            # Only process columns that have 'date' in the name
            if 'date' in col.lower():
                print(f"DEBUG: Found date column '{col}'")
                # Check if this column contains timestamp-like values OR pandas datetime objects
                sample_values = formatted_df[col].dropna().head(5)
                if len(sample_values) > 0:
                    sample_val = sample_values.iloc[0]
                    print(f"DEBUG: Sample value from '{col}': {sample_val}, type: {type(sample_val)}")
                    
                    # Handle pandas datetime objects
                    if pd.api.types.is_datetime64_any_dtype(formatted_df[col]):
                        print(f"DEBUG: Converting pandas datetime column '{col}' to string")
                        try:
                            formatted_df[col] = formatted_df[col].dt.strftime('%Y-%m-%d')
                            print(f"DEBUG: Converted pandas datetime to string in column '{col}'")
                            print(f"DEBUG: First few converted dates: {formatted_df[col].head().tolist()}")
                        except Exception as e:
                            print(f"ERROR: Could not convert pandas datetime column {col}: {e}")
                            continue
                    # Handle raw timestamp numbers
                    elif isinstance(sample_val, (int, float)) and sample_val > 1000000000:
                        print(f"DEBUG: Converting timestamps in column '{col}'")
                        try:
                            # Convert timestamps to readable dates
                            if sample_val > 1000000000000:  # Milliseconds
                                formatted_df[col] = pd.to_datetime(formatted_df[col], unit='ms').dt.strftime('%Y-%m-%d')
                                print(f"DEBUG: Converted milliseconds to dates in column '{col}'")
                            else:  # Seconds
                                formatted_df[col] = pd.to_datetime(formatted_df[col], unit='s').dt.strftime('%Y-%m-%d')
                                print(f"DEBUG: Converted seconds to dates in column '{col}'")
                            print(f"DEBUG: First few converted dates: {formatted_df[col].head().tolist()}")
                        except Exception as e:
                            print(f"ERROR: Could not convert column {col} to date: {e}")
                            continue
                    else:
                        print(f"DEBUG: Column '{col}' doesn't contain timestamp-like values or datetime objects")
                else:
                    print(f"DEBUG: Column '{col}' has no valid values")
            
            # Format price columns separately
            if 'price' in col.lower() and formatted_df[col].dtype in ['float64', 'int64']:
                try:
                    # Format prices to 3 decimal places
                    formatted_df[col] = formatted_df[col].round(3)
                    print(f"DEBUG: Formatted price column '{col}'")
                except Exception as e:
                    print(f"ERROR: Could not format price column {col}: {e}")
                    continue
                    
        print(f"DEBUG: Finished formatting DataFrame")
        print(f"DEBUG: Final sample data:\n{formatted_df.head(2)}")
        return formatted_df

    def _initialize_pandasai(self):
        """Initialize PandasAI with LiteLLM"""
        try:
            # Initialize the LLM for PandasAI
            self.llm = LiteLLM(
                model="gpt-4.1-mini",
                api_key=OPENAI_API_KEY,
            )
            
            # Configure PandasAI
            pai.config.set({
                "llm": self.llm,
                "verbose": self.config.verbose,
            })
            
            # Load component prices dataset (like market agent loads Excel file)
            logger.info("Loading component prices dataset...")
            self.component_prices = pai.load("becsight/component-prices")
            logger.info("Component prices dataset loaded successfully")
            
            # No caching during initialization - load data on-demand like market agent
            
        except Exception as e:
            logger.error(f"Failed to initialize PandasAI: {e}")
            raise
    
    def _initialize_agent(self):
        """Initialize the Pydantic AI agent following market agent pattern"""
        try:
            # === Create Main Agent ===
            # We'll add an output function so the model can finish by returning PlotDataResult directly
            # without routing the payload back through the model (saves tokens / avoids 429s).
            # The function is defined a few lines below after the shared builder.
            # A default list of other output types is kept for backward compatibility.
            # We'll set the function in output_type once it's defined.
            self.agent = Agent(
                model=self.config.model,
                output_type=[PlotDataResult, DataAnalysisResult, MultiResult, str],
                system_prompt=self.SYSTEM_PROMPT,
            )

            # Register data analysis as a regular tool (not output type)
            @self.agent.tool(name="analyze_prices_data")
            async def analyze_prices_data_tool(ctx: RunContext[None], query: str):
                """Tool for querying module price data"""
                try:
                    logger.info(f"Executing price data query: {query}")
                    
                    # Prepend dataset schema information to help PandasAI use exact values
                    from datetime import datetime
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    current_year = datetime.now().year
                    
                    dataset_info = f"""
TEMPORAL CONTEXT:
- Current date: {current_date}
- Current year: {current_year}
- For "current" or "latest" queries, use the most recent date available in the dataset that is NOT in the future
- IMPORTANT: Filter out any dates beyond {current_date} when looking for "current" data
- Do not expect data for future dates beyond {current_date}

Available items in the dataset (use exact spelling):
- Aluminium, Cell, Copper, EVA, Module, PV glass, Polysilicon, Silver, Wafer

Available regions in the dataset (use exact names):
- China, EU, US, India, Overseas, Australia

Available columns:
- item, description, date, frequency, base_price, unit, region, source

IMPORTANT SQL GUIDELINES:
- Don't assume data structure - always aggregate when dealing with multiple items/descriptions per region
- Use DuckDB syntax (not MySQL)
- For date filtering: use `date >= '2023-01-01'` instead of `INTERVAL`
- For last 24 months: use `date >= (SELECT MAX(date) - INTERVAL '24 months' FROM component_prices)`
- For year filtering: use `EXTRACT(YEAR FROM date) >= 2023`

QUERY INTERPRETATION RULES:
- PLURAL queries ("module prices", "show prices", "list modules") → Return ALL distinct types/descriptions with their latest prices
  Example: Use a subquery to get the latest date per description, then join to get all latest prices
- SINGULAR queries ("the module price", "latest price", "current price") → Return only ONE result with LIMIT 1
- For plural requests, use this pattern:
  ```sql
  WITH latest_dates AS (
    SELECT description, MAX(date) as max_date
    FROM component_prices
    WHERE item = 'Module' AND region = 'China' AND date <= '{current_date}'
    GROUP BY description
  )
  SELECT cp.description, cp.base_price, cp.unit, cp.date, cp.region
  FROM component_prices cp
  INNER JOIN latest_dates ld ON cp.description = ld.description AND cp.date = ld.max_date
  WHERE cp.item = 'Module' AND cp.region = 'China'
  ORDER BY cp.description
  ```

- Use `AVG(base_price)` for averages, `MIN(base_price)` for minimum, `MAX(base_price)` for maximum
- Group by: `GROUP BY region, description` for detailed analysis, or just `GROUP BY region` for regional summaries
- Order by: `ORDER BY date ASC` (or DESC for latest data)

Query: """
                    
                    enriched_query = dataset_info + query
                    response = self.component_prices.chat(enriched_query)
                    
                    # Handle different response types
                    df = None
                    if hasattr(response, 'value') and isinstance(response.value, pd.DataFrame):
                        df = response.value
                    elif isinstance(response, pd.DataFrame):
                        df = response
                    
                    if df is not None and not df.empty:
                        # Store for downstream use (plots/table rendering)
                        self.last_dataframe = df
                        
                        # Prepare a table payload for the UI
                        try:
                            formatted_df = self._format_dataframe_for_frontend(df)
                        except Exception:
                            formatted_df = df
                        display_df = formatted_df.head(50) if len(formatted_df) > 50 else formatted_df
                        table_data = display_df.to_dict(orient='records')

                        # Build a concise, useful summary instead of a vague sentence
                        parts = []
                        parts.append(f"{len(df)} records")

                        # Date range
                        if 'date' in df.columns:
                            try:
                                min_date = str(pd.to_datetime(df['date']).min().date())
                                max_date = str(pd.to_datetime(df['date']).max().date())
                                parts.append(f"period: {min_date} → {max_date}")
                            except Exception:
                                pass

                        # Units
                        if 'unit' in df.columns:
                            try:
                                units = list(pd.Series(df['unit']).dropna().unique())
                                if units:
                                    parts.append(f"units: {', '.join(units[:3])}{' (+)' if len(units) > 3 else ''}")
                            except Exception:
                                pass

                        # If exactly two regions, provide a direct comparison
                        comparison_line = None
                        if 'region' in df.columns and 'base_price' in df.columns:
                            try:
                                region_avgs = (
                                    df.groupby('region')['base_price']
                                      .mean()
                                      .round(3)
                                      .sort_index()
                                )
                                if len(region_avgs.index.unique()) == 2:
                                    r1, r2 = list(region_avgs.index)
                                    v1, v2 = float(region_avgs.loc[r1]), float(region_avgs.loc[r2])
                                    delta = round(v1 - v2, 3)
                                    comparison_line = f"avg {r1}: ${v1}/Wp vs {r2}: ${v2}/Wp (Δ ${abs(delta):.3f} {'higher' if delta>0 else 'lower'} in {r1})"
                            except Exception:
                                pass

                        header = "; ".join(parts)
                        if comparison_line:
                            header = f"{header}. {comparison_line}"

                        # Return a structured DataAnalysisResult for the UI and logs
                        return DataAnalysisResult(
                            result_type="dataframe",
                            content=header,
                            dataframe_data=table_data,
                        )
                    else:
                        # For non-DataFrame responses, return natural text
                        if response is None:
                            return "No data found for your query."
                        elif hasattr(response, 'empty') and response.empty:
                            return "No data found for your query."
                        elif hasattr(response, 'to_string'):
                            return response.to_string()
                        else:
                            return str(response)
                        
                except Exception as e:
                    error_msg = f"Error analyzing price data: {str(e)}"
                    logger.error(error_msg)
                    
                    # Provide helpful guidance for common SQL errors
                    if "INTERVAL" in str(e) or "DATE_SUB" in str(e):
                        return "I encountered a SQL syntax error. Let me try a simpler approach to get the module price data for you."
                    elif "No code found" in str(e):
                        return "I'm having trouble generating the right query. Let me try a different approach to analyze the module prices."
                    else:
                        return f"Error analyzing price data: {str(e)}"

            # Shared builder for plot data (used by tool and output function)
            async def _build_plot_data(
                ctx: RunContext[None],
                item: str = None,
                region: str = None,
                descriptions_csv: str = None,
                max_year: int = None,
                min_year: int = None,
                plot_type: str = "line",
                x_axis: str = "description",
            ) -> PlotDataResult:
                """Build PlotDataResult for frontend D3 rendering (no model round-trip)."""
                try:
                    logger.info(f"🔍 _build_plot_data called with: item={item}, region={region}, plot_type={plot_type}")
                    # Normalize plot_type synonyms (model is responsible to choose, we accept common variants)
                    raw_plot_type = plot_type or "line"
                    plot_type_norm = raw_plot_type.strip().lower() if isinstance(raw_plot_type, str) else "line"
                    synonyms = {
                        # box
                        "boxplot": "box",
                        "box_plot": "box",
                        # bar (averages)
                        "barplot": "bar",
                        "bar_plot": "bar",
                        "avg": "bar",
                        "avg_price": "bar",
                        "avg_prices": "bar",
                        "average": "bar",
                        "average_price": "bar",
                        "average_prices": "bar",
                        # line (trends)
                        "trend": "line",
                        "trends": "line",
                    }
                    plot_type = synonyms.get(plot_type_norm, plot_type_norm)
                    if plot_type not in {"line", "bar", "box"}:
                        logger.warning(f"Unsupported plot_type received after normalization: {plot_type_norm} -> {plot_type}")
                        return PlotDataResult(
                            plot_type="line",
                            title="Invalid plot type",
                            x_axis_label="",
                            y_axis_label="",
                            unit="",
                            data=[],
                            series_info=[],
                            success=False,
                            error_message="Unsupported plot type. Use: line, bar, or box."
                        )
                    
                    # Load and filter data
                    df = self.component_prices.copy()
                    logger.info(f"🔍 Loaded dataset with {len(df)} rows")
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'], errors='coerce')
                        df = df.dropna(subset=['date'])
                        logger.info(f"🔍 After date processing: {len(df)} rows")
                    
                    # Apply filters similar to plotting functions
                    if max_year is not None or min_year is not None:
                        df['year'] = df['date'].dt.year
                        logger.info(f"🔍 Year range in data: {df['year'].min()} to {df['year'].max()}")
                        if max_year is not None:
                            df = df[df['year'] <= max_year]
                            logger.info(f"🔍 After max_year filter ({max_year}): {len(df)} rows")
                        if min_year is not None:
                            df = df[df['year'] >= min_year]
                            logger.info(f"🔍 After min_year filter ({min_year}): {len(df)} rows")
                    else:
                        logger.info(f"🔍 No year filters applied - using all available data")
                    
                    # Item filter
                    if item and item != "all":
                        logger.info(f"🔍 Available items in data: {df['item'].unique().tolist()}")
                        item_list = [i.strip() for i in item.split(',')] if ',' in item else [item]
                        df = df[df['item'].isin(item_list)]
                        logger.info(f"🔍 After item filter ({item_list}): {len(df)} rows")
                    
                    # Region filter
                    if region and region != "all":
                        logger.info(f"🔍 Available regions in data: {df['region'].unique().tolist()}")
                        region_list = [r.strip() for r in region.split(',')] if ',' in region else [region]
                        # Apply region mapping
                        region_mapping = {
                            'EU': 'EU', 'EUROPE': 'EU', 'EUROPEAN UNION': 'EU',
                            'USA': 'US', 'UNITED STATES': 'US', 'AMERICA': 'US',
                            'CHINA': 'China', 'INDIA': 'India', 'OVERSEAS': 'Overseas', 'AUSTRALIA': 'Australia'
                        }
                        normalized_regions = [region_mapping.get(r.upper(), r) for r in region_list]
                        logger.info(f"🔍 Normalized regions: {normalized_regions}")
                        df = df[df['region'].isin(normalized_regions)]
                        logger.info(f"🔍 After region filter: {len(df)} rows")
                    
                    # Description filter with partial matching
                    if descriptions_csv:
                        descriptions = [desc.strip() for desc in descriptions_csv.split(',')]
                        filtered_dfs = []
                        for desc in descriptions:
                            if 'PERC' in desc.upper():
                                matched = df[df['description'].str.contains('PERC', case=False, na=False)]
                            elif 'TOPCON' in desc.upper():
                                matched = df[df['description'].str.contains('TOPCon', case=False, na=False)]
                            elif 'HJT' in desc.upper():
                                matched = df[df['description'].str.contains('HJT', case=False, na=False)]
                            else:
                                matched = df[df['description'] == desc]
                            filtered_dfs.append(matched)
                        
                        if filtered_dfs:
                            df = pd.concat(filtered_dfs, ignore_index=True).drop_duplicates()
                    
                    if df.empty:
                        logger.warning(f"🔍 No data found after filtering - returning empty PlotDataResult")
                        return PlotDataResult(
                            plot_type=plot_type,
                            title="No Data Found",
                            x_axis_label="",
                            y_axis_label="Price",
                            unit="",
                            data=[],
                            success=False,
                            error_message="No data available after applying filters"
                        )
                    
                    # Get unit from data
                    unit = "US$/Wp"  # default
                    if 'unit' in df.columns and not df['unit'].dropna().empty:
                        unit = df['unit'].dropna().iloc[0]
                    
                    # Prepare data for D3 (limit data points for performance)
                    plot_data = []
                    series_info = []

                    if plot_type == "line":
                        for (desc, reg, itm), group in df.groupby(['description', 'region', 'item']):
                            if 'date' not in group.columns or 'base_price' not in group.columns:
                                continue
                            series_data = (
                                group.groupby([group['date'].dt.to_period('M')])['base_price']
                                .mean()
                                .reset_index()
                            )
                            series_data['date'] = series_data['date'].dt.to_timestamp()
                            series_data = series_data.sort_values('date')
                            if len(series_data) > 50:
                                series_data = series_data.iloc[::len(series_data)//50]
                            series_name = f"{desc} {itm} ({reg})"
                            series_info.append({"name": series_name, "description": desc, "region": reg, "item": itm})
                            for _, row in series_data.iterrows():
                                plot_data.append({
                                    "date": row['date'].strftime('%Y-%m-%d'),
                                    "series": series_name,
                                    "value": round(float(row['base_price']), 3),
                                    "description": desc,
                                    "region": reg,
                                    "item": itm
                                })
                        title = f"{item or 'Price'} Trends" + (f" in {region}" if region and region != "all" else "") + (f" ({min_year}-{max_year})" if min_year and max_year else "")
                        x_label = ""

                    elif plot_type == "bar":
                        if x_axis.lower() not in ["description", "region", "item"]:
                            x_axis = "description"
                        avg_df = df.groupby(x_axis)['base_price'].mean().reset_index()
                        for _, row in avg_df.iterrows():
                            category = str(row[x_axis])
                            series_info.append({"name": category})
                            plot_data.append({"category": category, "series": category, "value": float(round(row['base_price'], 3))})
                        title = f"Average Prices by {x_axis.title()}"
                        x_label = x_axis.title()

                    elif plot_type == "box":
                        if x_axis.lower() not in ["description", "region", "item"]:
                            x_axis = "description"
                        for category, group in df.groupby(x_axis):
                            prices = group['base_price'].dropna().astype(float)
                            if prices.empty:
                                continue
                            q1 = float(prices.quantile(0.25))
                            q2 = float(prices.quantile(0.5))
                            q3 = float(prices.quantile(0.75))
                            whisk_min = float(prices.min())
                            whisk_max = float(prices.max())
                            category = str(category)
                            series_info.append({"name": category})
                            plot_data.append({"category": category, "series": category, "q1": round(q1,3), "q2": round(q2,3), "q3": round(q3,3), "min": round(whisk_min,3), "max": round(whisk_max,3)})
                        title = f"Price Distribution by {x_axis.title()}"
                        x_label = x_axis.title()

                    else:
                        return PlotDataResult(plot_type=plot_type, title="Unsupported chart", x_axis_label="", y_axis_label="", unit=unit, data=[], success=False, error_message="Unsupported plot_type")

                    result = PlotDataResult(
                        plot_type=plot_type,
                        title=title,
                        x_axis_label=x_label,
                        y_axis_label=f"Price ({unit})",
                        unit=unit,
                        data=plot_data,
                        series_info=series_info,
                        success=True
                    )
                    # Cache only on successful, non-empty results
                    if result.success and result.data:
                        self.last_plot_data_result = result
                    logger.info(f"🔍 Successfully created PlotDataResult with {len(plot_data)} data points, {len(series_info)} series")
                    return result
                    
                except Exception as e:
                    logger.error(f"Error getting plot data: {e}")
                    return PlotDataResult(
                        plot_type=plot_type,
                        title="Error",
                        x_axis_label="",
                        y_axis_label="Price",
                        unit="",
                        data=[],
                        success=False,
                        error_message=str(e)
                    )

            # Tool wrapper removed - using output function only

            # Register as a tool (fallback if output_function API not available)
            @self.agent.tool(name="get_plot_data_output")
            async def get_plot_data_output(
                ctx: RunContext[None],
                item: str = None,
                region: str = None,
                descriptions_csv: str = None,
                max_year: int = None,
                min_year: int = None,
                plot_type: str = "line",
                x_axis: str = "description",
            ) -> str:
                # Build and cache the PlotDataResult, but only return a tiny stub to the model
                try:
                    # Mark that plotting tools were called in this session
                    self._plot_tools_called_in_session = True
                    result = await _build_plot_data(
                        ctx=ctx,
                        item=item,
                        region=region,
                        descriptions_csv=descriptions_csv,
                        max_year=max_year,
                        min_year=min_year,
                        plot_type=plot_type,
                        x_axis=x_axis,
                    )
                    # If no data or failed, signal failure to the model
                    if not result or not result.success or not result.data:
                        return "plot generation failed"
                    # Cache only when successful and non-empty
                    self.last_plot_data_result = result
                    # Return exact phrase the analyzer expects to gate rendering
                    return "plot generated successfully"
                except Exception as e:
                    logger.error(f"get_plot_data_output failed: {e}")
                    return "plot generation failed"

            logger.info("Module prices agent with structured output models setup complete")
        except Exception as e:
            logger.error(f"Failed to setup module prices agent: {e}")
            self.agent = None

    async def analyze(self, query: str, conversation_id: str = None) -> Dict[str, Any]:
        """
        Analyze component prices based on user query using the new tool-based architecture
        
        Args:
            query: Natural language query about component prices
            conversation_id: Optional conversation ID for memory tracking
            
        Returns:
            Dictionary with analysis results and metadata
        """
        # Logfire span for module prices agent
        with logfire.span("module_prices_agent_call") as agent_span:
            agent_span.set_attribute("agent_type", "module_prices")
            agent_span.set_attribute("conversation_id", str(conversation_id))
            agent_span.set_attribute("message_length", len(query))
            agent_span.set_attribute("user_message", query)
            
        try:
            usage_limits = UsageLimits(
                request_limit=self.config.request_limit,
                total_tokens_limit=self.config.total_tokens_limit
            )
            
            # Clear cached results at the start of each analyze call
            self.last_dataframe = None
            self.last_plot_data_result = None

            # Get conversation history if conversation_id is provided
            message_history: List[ModelMessage] = []
            if conversation_id and conversation_id in self.conversation_memory:
                message_history = self.conversation_memory[conversation_id]
                logger.info(f"[MEMORY DEBUG] Using conversation memory for {conversation_id} with {len(message_history)} messages")
                agent_span.set_attribute("memory_messages", len(message_history))
            else:
                agent_span.set_attribute("memory_messages", 0)
            
            logger.info(f"Processing query: {query}")
            if self.agent is None:
                raise RuntimeError("Prices agent failed to initialize; self.agent is None")
            
            # Store query for intent analysis and reset session flags
            self._current_query = query
            self._plot_tools_called_in_session = False
            
            # Rely on the SYSTEM_PROMPT rules exclusively (no heuristic routing)
            result = await self.agent.run(query, message_history=message_history, usage_limits=usage_limits)
            
            # Track the response
            if hasattr(result, 'output'):
                output = result.output
                if isinstance(output, str):
                    agent_span.set_attribute("assistant_response", output)
                    agent_span.set_attribute("response_length", len(output))
                else:
                    agent_span.set_attribute("assistant_response", str(output))
            
            # Store the new messages for future conversation context
            if conversation_id:
                self.conversation_memory[conversation_id] = result.all_messages()
                logger.info(f"[MEMORY DEBUG] Updated conversation memory for {conversation_id}")
            
            # Handle structured output from Pydantic AI
            output = result.output
            # If the model confirms plot generation explicitly, short-circuit to cached plot data
            def _should_return_plot_data() -> bool:
                """
                Generic logic to determine if we should return plot data instead of text.
                Based on actual state rather than text pattern matching.
                """
                # 1. Check if we have valid plot data available
                if self.last_plot_data_result is None:
                    return False
                
                # 2. Check if the plot data is successful and has actual data
                if not self.last_plot_data_result.success or not self.last_plot_data_result.data:
                    return False
                
                # 3. Check if plotting tools were called in this conversation
                # (This indicates the user requested visualization)
                plot_tools_called = getattr(self, '_plot_tools_called_in_session', False)
                
                # 4. Analyze the original query intent for visualization keywords
                original_query = getattr(self, '_current_query', '').lower()
                visualization_keywords = [
                    'plot', 'chart', 'graph', 'visualize', 'show', 'display',
                    'trend', 'compare', 'evolution', 'development', 'analysis'
                ]
                has_viz_intent = any(keyword in original_query for keyword in visualization_keywords)
                
                # 5. Decision logic
                should_return = (plot_tools_called or has_viz_intent) and len(self.last_plot_data_result.data) > 0
                
                # Debug logging
                logger.info(f"🔍 Plot decision logic:")
                logger.info(f"   - Plot data available: {self.last_plot_data_result is not None}")
                logger.info(f"   - Plot data successful: {self.last_plot_data_result.success if self.last_plot_data_result else False}")
                logger.info(f"   - Data points: {len(self.last_plot_data_result.data) if self.last_plot_data_result else 0}")
                logger.info(f"   - Plot tools called: {plot_tools_called}")
                logger.info(f"   - Has viz intent: {has_viz_intent}")
                logger.info(f"   - Original query: '{original_query}'")
                logger.info(f"   - Final decision: {should_return}")
                
                return should_return
            def _is_plot_failure(text: str) -> bool:
                if not isinstance(text, str):
                    return False
                normalized = re.sub(r"\W+", " ", text).strip().lower()
                return normalized == "plot generation failed"

            if _should_return_plot_data():
                if self.last_plot_data_result is not None:
                    agent_span.set_attribute("response_type", "plot_data_from_stub")
                    analysis_result = self.last_plot_data_result
                    # Clear after use to avoid bleed into other turns
                    self.last_plot_data_result = None
                    return {
                        "success": True,
                        "analysis": analysis_result,
                        "usage": result.usage(),
                        "query": query
                    }
            elif _is_plot_failure(output):
                # Explicit tool failure → return a clear error message
                analysis_result = "Plot generation failed (no matching data). Try adjusting item/description/years."
                agent_span.set_attribute("response_type", "error")
                return {
                    "success": False,
                    "analysis": analysis_result,
                    "usage": result.usage(),
                    "query": query
                }
            
            # Check if it's a DataAnalysisResult
            if isinstance(output, DataAnalysisResult):
                analysis_result = output
                agent_span.set_attribute("response_type", "data_analysis")
                agent_span.set_attribute("result_type", output.result_type)
                logger.info(f"📊 DataAnalysisResult: {output.result_type}")
            
            # Check if it's a MultiResult
            elif isinstance(output, MultiResult):
                analysis_result = output
                agent_span.set_attribute("response_type", "multi_result")
                agent_span.set_attribute("plots_count", len(output.plots))
                agent_span.set_attribute("data_count", len(output.data_results))
                logger.info(f"🎯 MultiResult: {len(output.plots)} plots, {len(output.data_results)} data results")
            
            # Check if it's a PlotDataResult (D3/JSON plot data)
            elif isinstance(output, PlotDataResult):
                # Prefer a successful cached result if current output is empty/failed
                if (not output.success or not output.data) and self.last_plot_data_result is not None:
                    analysis_result = self.last_plot_data_result
                    agent_span.set_attribute("response_type", "plot_data_from_cache_after_failure")
                    agent_span.set_attribute("plot_type", analysis_result.plot_type)
                    agent_span.set_attribute("data_points", len(analysis_result.data))
                    logger.info("♻️ Using previous successful PlotDataResult instead of empty/failed result")
                else:
                    analysis_result = output
                    if output.success and output.data:
                        self.last_plot_data_result = output
                    agent_span.set_attribute("response_type", "plot_data")
                    agent_span.set_attribute("plot_type", output.plot_type)
                    agent_span.set_attribute("data_points", len(output.data))
                    logger.info(f"📊 PlotDataResult: {output.plot_type} with {len(output.data)} data points (success={output.success})")
            
            # Check if it's a string and there's DataFrame data available  
            elif isinstance(output, str) and self.last_dataframe is not None and not self.last_dataframe.empty:
                print(f"DEBUG: About to format DataFrame with shape {self.last_dataframe.shape}")
                # Format the DataFrame for frontend (dates, prices, etc.)
                formatted_df = self._format_dataframe_for_frontend(self.last_dataframe)
                
                # Create table-ready response with formatted data
                display_df = formatted_df.head(50) if len(formatted_df) > 50 else formatted_df
                table_data = display_df.to_dict(orient='records')
                full_data = formatted_df.to_dict(orient='records')
                
                # Log summary instead of raw data
                logger.info(f"Formatted DataFrame: {len(formatted_df)} rows, {len(formatted_df.columns)} columns")
                logger.info(f"Display subset: {len(display_df)} rows")
                
                # Create a DataAnalysisResult
                analysis_result = DataAnalysisResult(
                    result_type="dataframe",
                    content=output,
                    dataframe_data=table_data
                )
                agent_span.set_attribute("response_type", "dataframe")
                logger.info(f"Created DataAnalysisResult with {len(display_df)} rows for display, {len(formatted_df)} rows for download")
            
            # Regular string response - but check if we have a successful plot from tool calls
            else:
                logger.info(f"🔍 String response detected: '{output}'")
                logger.info(f"🔍 Last plot data result present: {self.last_plot_data_result is not None}")
                # State-based pattern: return cached plot data based on actual state and intent
                if _should_return_plot_data():
                    analysis_result = self.last_plot_data_result
                    agent_span.set_attribute("response_type", "plot_data_from_cache")
                    logger.info("✅ Returning cached PlotDataResult (stub pattern)")
                elif _is_plot_failure(output):
                    analysis_result = "Plot generation failed (no matching data)."
                    agent_span.set_attribute("response_type", "error")
                else:
                    analysis_result = output
                    agent_span.set_attribute("response_type", "text")
                    logger.info("ℹ️ Returning text response")
            
            agent_span.set_attribute("success", True)
            
            # Return the agent's response
            return {
                "success": True,
                "analysis": analysis_result,
                "usage": result.usage(),
                "query": query
            }
            
        except UsageLimitExceeded as usage_error:
            logger.warning(f"Usage limit exceeded for conversation {conversation_id}: {usage_error}")
            agent_span.set_attribute("usage_limit_exceeded", True)
            agent_span.set_attribute("error", str(usage_error))
            
            # Automatically clear conversation memory when rate limits are exceeded
            self.clear_conversation_memory(conversation_id)
            logger.info(f"Auto-cleared conversation memory for {conversation_id} due to usage limit exceeded")
            
            # Return a helpful message to the user
            return {
                "success": False,
                "error": "⚠️ **Rate limit exceeded!** I've automatically reset our conversation memory to continue. You can now ask your question again with a fresh start.",
                "analysis": None,
                "usage": None,
                "query": query
            }
        except Exception as e:
            error_msg = f"Failed to analyze query: {str(e)}"
            logger.error(error_msg)
            agent_span.set_attribute("success", False)
            agent_span.set_attribute("error", str(e))
            # Fallback: if we have plot data prepared, return it despite validation failure
            if self.last_plot_data_result is not None:
                logger.info("⚠️ Validation failed but PlotDataResult is available; returning interactive chart anyway")
                return {
                    "success": True,
                    "analysis": self.last_plot_data_result,
                    "usage": None,
                    "query": query
                }
            else:
                return {
                    "success": False,
                    "error": error_msg,
                    "analysis": None,
                    "usage": None,
                    "query": query
                }
    
    def clear_conversation_memory(self, conversation_id: str = None):
        """Clear conversation memory for specific conversation or all conversations"""
        if conversation_id:
            if conversation_id in self.conversation_memory:
                del self.conversation_memory[conversation_id]
                logger.info(f"Cleared conversation memory for {conversation_id}")
        else:
            self.conversation_memory.clear()
            logger.info("Cleared all conversation memory")
    
    def get_conversation_memory_info(self) -> Dict[str, Any]:
        """Get information about conversation memory usage"""
        return {
            "total_conversations": len(self.conversation_memory),
            "conversation_ids": list(self.conversation_memory.keys()),
            "total_messages": sum(len(messages) for messages in self.conversation_memory.values()),
            "memory_per_conversation": {
                conv_id: len(messages) for conv_id, messages in self.conversation_memory.items()
            }
        } 