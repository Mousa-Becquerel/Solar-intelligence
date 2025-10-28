from pydantic_ai import Agent, RunContext, ToolOutput
from pydantic_ai.usage import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ToolReturnPart
from pydantic import BaseModel
import os, json, uuid
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass, replace
import asyncio
import pandas as pd
from enum import Enum
import sys
import pandasai as pai
from pandasai_litellm.litellm import LiteLLM
import time

# Logfire imports
import logfire

# === Memory Management Functions =========================================
def filter_large_tool_returns(messages: List[ModelMessage], max_content_length: int = 500) -> List[ModelMessage]:
    """
    Filter out large tool return content from conversation memory to prevent token bloat.

    This function processes conversation messages and truncates large DataFrame outputs
    from analyze_market_data_tool while preserving the conversation flow and context.

    Args:
        messages: List of ModelMessage objects from conversation history
        max_content_length: Maximum allowed content length before truncation (default: 500 chars)

    Returns:
        Filtered list of ModelMessage objects with truncated tool returns
    """
    filtered = []
    total_original_size = 0
    total_filtered_size = 0
    truncated_count = 0

    for msg in messages:
        if hasattr(msg, 'parts'):
            filtered_parts = []

            for part in msg.parts:
                # Check if this is a ToolReturnPart
                part_class_name = part.__class__.__name__

                if part_class_name == 'ToolReturnPart':
                    tool_name = getattr(part, 'tool_name', '')
                    content = getattr(part, 'content', '')

                    # Skip filtering for DataAnalysisResult objects - they're already optimized
                    if isinstance(content, DataAnalysisResult):
                        print(f"   ✅ Keeping DataAnalysisResult object from {tool_name} (structured data, no filtering needed)")
                        filtered_parts.append(part)
                        # Estimate size of DataAnalysisResult
                        content_size = len(str(getattr(content, 'content', '')))
                        total_original_size += content_size
                        total_filtered_size += content_size
                        continue

                    content_str = str(content)
                    content_length = len(content_str)
                    total_original_size += content_length

                    # Filter analyze_market_data_tool outputs that are too large (only raw strings)
                    if 'analyze' in tool_name.lower() and content_length > max_content_length:
                        # Count rows in the DataFrame output
                        row_count = content_str.count('\n')

                        # Create a short summary - the system prompt already explains the behavior
                        summary = f"[Data table with {row_count} rows shown to user - not stored in memory. Re-run analyze_market_data_tool if you need specific values.]"

                        # Replace the content with summary
                        try:
                            truncated_part = replace(part, content=summary)
                            filtered_parts.append(truncated_part)
                            total_filtered_size += len(summary)
                            truncated_count += 1

                            # Log the truncation
                            print(f"   🔧 Truncated tool output: {tool_name} ({content_length} → {len(summary)} chars, saved {content_length - len(summary)} chars)")
                        except Exception as e:
                            # If replace fails, just use the part as-is
                            print(f"   ⚠️ Failed to truncate tool return: {e}")
                            filtered_parts.append(part)
                            total_filtered_size += content_length
                    else:
                        # Keep small tool returns unchanged
                        filtered_parts.append(part)
                        total_filtered_size += content_length
                else:
                    # Keep non-tool-return parts unchanged
                    filtered_parts.append(part)
                    # Estimate size for other parts
                    if hasattr(part, 'content'):
                        part_size = len(str(getattr(part, 'content', '')))
                        total_original_size += part_size
                        total_filtered_size += part_size

            # Reconstruct message with filtered parts
            try:
                filtered_msg = replace(msg, parts=filtered_parts)
                filtered.append(filtered_msg)
            except Exception as e:
                # If replace fails, keep original message
                print(f"   ⚠️ Failed to filter message: {e}")
                filtered.append(msg)
        else:
            # Keep messages without parts unchanged
            filtered.append(msg)

    # Log summary statistics
    if truncated_count > 0:
        saved_chars = total_original_size - total_filtered_size
        saved_tokens_estimate = saved_chars // 4  # Rough estimate: 4 chars per token
        print(f"   📊 Memory filter stats: Truncated {truncated_count} tool outputs, saved ~{saved_chars:,} chars (~{saved_tokens_estimate:,} tokens)")

    return filtered

# === Plot Parameters Class ===============================================
@dataclass
class PlotParameters:
    """Parameters for plot generation - passed via dependency injection."""
    plot_type: str = "line"
    country: Optional[str] = None
    segment: Optional[str] = None
    value_type: Optional[str] = None
    year: Optional[int] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    scenario: Optional[str] = None
    countries: Optional[str] = None
    scenarios: Optional[str] = None

# === Plot Output Classes =================================================
class MarketPlotDataResult(BaseModel):
    """Structured output for frontend D3 charts (Market agent)."""
    plot_type: str
    title: str
    x_axis_label: str
    y_axis_label: str
    unit: Optional[str] = None
    data: List[Dict[str, Any]]
    series_info: List[Dict[str, Any]] = []
    notes: List[str] = []  # Notes displayed at bottom of chart (optional)
    success: bool = True
    error_message: Optional[str] = None





class PlotType(str, Enum):
    line = "line"
    bar = "bar"
    stacked = "stacked"
    pie = "pie"
    yoy = "yoy"
    multi_scenario = "multi_scenario"
    country_comparison = "country_comparison"
    multi_country = "multi_country"

class SegmentLiteral(str, Enum):
    TOTAL = "Total"
    DISTRIBUTED = "Distributed"
    CENTRALISED = "Centralised"
    RESIDENTIAL = "Residential"
    COMMERCIAL_INDUSTRIAL = "Commercial & Industrial"
    GROUND_MOUNTED = "Ground-mounted"
    AGRIPV = "AgriPV"
    FLOATING_PV = "Floating PV"

class ScenarioLiteral(str, Enum):
    HISTORICAL = "Historical"
    MOST_PROBABLE = "Most Probable"
    HIGH = "High"
    LOW = "Low"

class DurationLiteral(str, Enum):
    FY = "FY"  # Full Year
    Q1 = "Q1"  # Quarter 1
    Q2 = "Q2"  # Quarter 2
    Q3 = "Q3"  # Quarter 3
    Q4 = "Q4"  # Quarter 4
    ALL_QUARTERS = "ALL_QUARTERS"  # All quarterly data (Q1+Q2+Q3+Q4)

class TypeLiteral(str, Enum):
    ANNUAL = "Annual"      # Yearly additions
    CUMULATIVE = "Cumulative"  # Running totals

class MarketPlotParameters(BaseModel):
    """All parameters required; LLM/tool must provide valid values."""
    plot_type: PlotType
    country: str                 # single country (use "" if unused and rely on `countries`)
    segment: SegmentLiteral
    value_type: Literal["annual", "cumulative", "dual"]
    year: int
    min_year: int
    max_year: int
    scenario: Optional[ScenarioLiteral] = None  # Optional when scenarios is provided
    countries: str               # comma-separated list; use "" if single-country
    scenarios: str               # comma-separated list; use "" if single-scenario
    duration: DurationLiteral = DurationLiteral.FY  # Default to Full Year
    type: TypeLiteral = TypeLiteral.ANNUAL  # Default to Annual
    
    def model_post_init(self, __context) -> None:
        """Validate scenario/scenarios logic after initialization."""
        # Convert "dual" to "annual" since we only have annual capacity data
        if self.value_type == "dual":
            self.value_type = "annual"
        
        # If scenarios is provided, scenario should be None
        if self.scenarios and self.scenarios.strip():
            if self.scenario is not None:
                self.scenario = None  # Clear scenario when scenarios is provided
        # If scenario is provided, scenarios should be empty
        elif self.scenario is not None:
            if self.scenarios and self.scenarios.strip():
                self.scenarios = ""  # Clear scenarios when scenario is provided





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

import re # Added for segment normalisation

# Load .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Plotting helper (outside of the class so it can be reused) ===

# ---------------- Scenario filtering helper ---------------------------

def _filter_scenario(df: pd.DataFrame, year_col: str = "year", scenario: str | None = None) -> pd.DataFrame:
    """Return dataframe filtered by scenario logic.

    If *scenario* is provided, keep only rows whose Scenario column equals
    that value (case-insensitive).

    If *scenario* is None, apply the following default logic:
        • Years ≤ 2024  → Scenario == "Historical"
        • Years  > 2024 → Scenario == "Most Probable"  (most-probable forecast)
    This way, mixed-period plots seamlessly stitch historical and forecast
    data without the user needing to specify anything.
    """
    if scenario:
        scenario_norm = _normalize_scenario(scenario)
        print(f"📊 Scenario filtering: input='{scenario}' → normalized='{scenario_norm}'")
        hist_mask = (df["scenario"] == "Historical") & (df[year_col] <= 2024)
        # For forecast years, match scenario ignoring case and whitespace
        scen_mask = df[year_col] > 2024
        # Find all unique scenario values in the data for forecast years
        forecast_scenarios = df.loc[scen_mask, "scenario"].dropna().unique()
        print(f"📊 Available forecast scenarios in data: {list(forecast_scenarios)}")
        # Try to match normalized scenario to one of these
        match = None
        for s in forecast_scenarios:
            s_norm = _normalize_scenario(s)
            print(f"📊 Comparing: '{s}' (norm: '{s_norm}') vs '{scenario_norm}'")
            if s_norm == scenario_norm:
                match = s
                print(f"📊 ✅ Match found: '{match}'")
                break
        if match is None:
            # Fallback: just use scenario_norm as is
            match = scenario_norm
            print(f"📊 ⚠️ No match found, using normalized scenario as-is: '{match}'")
        scen_mask = (df["scenario"] == match) & (df[year_col] > 2024)
        print(f"📊 Filtering by scenario: '{match}' for years > 2024")
        return df[hist_mask | scen_mask]

    hist_mask = (df["scenario"] == "Historical") & (df[year_col] <= 2024)
    forecast_mask = (df["scenario"].isin(["Forecast - Most probable"])) & (
        df[year_col] > 2024
    )
    return df[hist_mask | forecast_mask]


def _normalize_scenario(scenario: str | None) -> str | None:
    """Map user scenario input to canonical scenario names in the dataset."""
    if not scenario:
        return None
    s = scenario.strip().lower()
    # Common cleanup
    s = (
        s.replace('probable', 'prob')
        .replace('growth', '')
        .replace('scenario', '')
        .replace('scenarios', '')
        .replace('.', '')
        .replace('-', ' ')
        .replace('_', ' ')
    )
    s = ' '.join(s.split())  # collapse whitespace

    # Map to canonical names (updated for annual-full-dataset)
    if s in {'most prob', 'most probable', 'mostprob', 'probable', 'prob', 'moderate', 'baseline', 'base', 'current', 'current policy', 'policy', 'average', 'average case', 'forecast', 'forecasted', 'forecast data', 'forecasted data'}:
        return 'Forecast - Most probable'
    if s in {'high', 'high prob', 'high probable', 'highgrowth', 'high growth', 'best case', 'best', 'forecast high'}:
        return 'Forecast - High'
    if s in {'low', 'low prob', 'low probable', 'lowgrowth', 'low growth', 'worst case', 'worst', 'forecast low'}:
        return 'Forecast - Low'
    if s in {'historical', 'hist', 'past', 'actual', 'recorded', 'real'}:
        return 'Historical'
    if s in {'all', 'all the', 'multiple', 'three', 'different', 'compare', 'forecasting for all'}:
        return 'All'
    # If not matched, return title-case version to preserve original
    return scenario.title()

# ----------------------------------------------------------------------------------


class chat_response(BaseModel):
    chat_response: str

class PydanticWeaviateAgent:
    """Pydantic-AI based agent for PV market analysis with conversation memory (now using PandasAI)"""
    
    def __init__(self):
        self.data_analysis_agent = None
        self.conversation_memory: Dict[str, List[ModelMessage]] = {}
        self.memory_lock = asyncio.Lock()  # Thread-safe conversation memory access
        self.last_dataframe = None
        self.last_market_plot_data_result: Optional[MarketPlotDataResult] = None
        self._initialize_pandasai()
        self._setup_pydantic_agent()

    def _initialize_pandasai(self):
        self.llm = LiteLLM(
            model="gpt-4.1",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        pai.config.set({
            "llm": self.llm,
            "verbose": True,
        })
        self.market_data = pai.load("becsight/annual-full-dataset")

    # === Helper Methods for Plot Generation ===

    @staticmethod
    def _format_capacity_value(value: float) -> str:
        """Format capacity values for better readability (e.g., 2.4k instead of 2400)"""
        if value == 0 or value == 0.0:
            return "0"
        elif value >= 1000000:
            return f"{value/1000000:.1f}GW"
        elif value >= 10000:
            formatted = value/1000
            if formatted == int(formatted):
                return f"{int(formatted)}k"
            else:
                return f"{formatted:.1f}k"
        elif value >= 1000:
            return f"{value/1000:.1f}k"
        elif value >= 100:
            return f"{value:.0f}"
        elif value >= 1:
            if value == int(value):
                return f"{int(value)}"
            else:
                return f"{value:.1f}"
        else:
            return f"{value:.2f}"

    @staticmethod
    def _normalize_segment_param(s: str | None) -> str:
        """Normalize segment parameter to match dataset values"""
        if not s: return "Total"
        s = s.strip()

        # 🛠️ FIX: Handle comma-separated segments (from LLM context extraction errors)
        # If multiple segments are provided, default to "Total" for aggregate view
        if "," in s:
            print(f"⚠️ Multiple segments detected in parameter: '{s}', defaulting to 'Total'")
            return "Total"

        s = s.lower()
        if s.startswith("dist"): return "Distributed"
        if s.startswith("cent"): return "Centralised"
        if s == "total": return "Total"
        # Handle stacking dimension requests
        if s in ["applications", "application", "segments", "segment", "connections", "connection"]: return "Total"
        # Handle specific segments
        if s in ["agripv", "agri pv", "agrivoltaics", "agricultural"]: return "AgriPV"
        if s in ["floating", "floating pv", "floating solar"]: return "Floating PV"
        if s in ["residential"]: return "Residential"
        if s in ["commercial", "industrial", "commercial & industrial", "c&i"]: return "Commercial & Industrial"
        if s in ["ground mounted", "ground-mounted"]: return "Ground-mounted"
        return s.title()

    def _generate_yoy_plot(
        self,
        df: pd.DataFrame,
        country: str | None,
        segment: str,
        value_type: str | None,
        scenario: str | None,
        min_year: int | None,
        max_year: int | None
    ) -> MarketPlotDataResult:
        """Generate year-over-year growth plot."""
        print(f"📊 Processing YOY plot...")
        # Year-over-year growth for a country/segment
        c = (country or "China").title()
        seg = self._normalize_segment_param(segment)
        vt = (value_type or "annual").lower()
        value_column = "capacity"  # New dataset only has capacity column

        # Filter by segment type correctly
        if seg == "Total":
            d = df[(df["country"] == c) & (df["connection"] == "Total") & (df["segment"] == "Total") & (df["applications"] == "Total")]
        elif seg in ["Distributed", "Centralised"]:
            # For connection types, filter by connection
            d = df[(df["country"] == c) & (df["connection"] == seg) & (df["segment"] == "Total") & (df["applications"] == "Total")]
        else:
            # For specific segment types (Ground-mounted, Residential, AgriPV, Floating PV, etc.), filter by segment
            d = df[(df["country"] == c) & (df["segment"] == seg) & (df["applications"] == "Total")]
        # Apply proper scenario filtering using global function
        d = _filter_scenario(d, year_col="year", scenario=scenario)
        print(f"📊 After scenario filter: {len(d)} rows")

        if max_year is not None and max_year > 0:
            d = d[d["year"] <= max_year]
        if min_year is not None and min_year > 0:
            d = d[d["year"] >= min_year]
        if d.empty:
            return MarketPlotDataResult(
                plot_type="bar",
                title="No Data Found",
                x_axis_label="",
                y_axis_label="YoY (%)",
                unit="%",
                data=[],
                success=False,
                error_message="No data"
            )
        pivot = d.groupby("year")[value_column].sum().sort_index().reset_index()
        pivot["yoy"] = pivot[value_column].pct_change() * 100.0
        pivot = pivot.dropna(subset=["yoy"])  # first year has NaN
        data = [
            {"category": int(row["year"]), "series": f"{c} {seg}", "value": float(row["yoy"]), "formatted_value": f"{row['yoy']:.1f}%"}
            for _, row in pivot.iterrows()
        ]
        return MarketPlotDataResult(
            plot_type="bar",
            title=f"YoY Growth ({seg}) in {c}",
            x_axis_label="",
            y_axis_label="YoY (%)",
            unit="%",
            data=data,
            series_info=[{"name": f"{c} {seg}"}],
        )

    def _generate_multi_scenario_plot(
        self,
        df: pd.DataFrame,
        country: str | None,
        segment: str,
        value_type: str | None,
        scenarios: str | None,
        min_year: int | None,
        max_year: int | None
    ) -> MarketPlotDataResult:
        """Generate multi-scenario comparison plot."""
        print(f"📊 Processing MULTI_SCENARIO plot...")
        # Multiple scenarios for one country+segment
        c = (country or "China").title()
        seg = self._normalize_segment_param(segment)
        vt = (value_type or "cumulative").lower()
        # New dataset only has capacity (annual capacity)
        value_column = "capacity"
        scenario_list = [s.strip().title() for s in (scenarios.split(",") if scenarios else ["Most Probable", "High", "Low"])]
        series_info = []
        data = []
        for scen in scenario_list:
            # Map scenario names to match dataset format
            if scen in ["Most Probable", "Most probable"]:
                dataset_scenario = "Forecast - Most probable"
            elif scen == "High":
                dataset_scenario = "Forecast - High"
            elif scen == "Low":
                dataset_scenario = "Forecast - Low"
            else:
                dataset_scenario = scen  # Fallback for other scenarios

            # Filter by segment type correctly
            if seg == "Total":
                d = df[(df["country"] == c) & (df["connection"] == "Total") & (df["segment"] == "Total") & (df["applications"] == "Total") & (df["scenario"] == dataset_scenario)]
            elif seg in ["Distributed", "Centralised"]:
                # For connection types, filter by connection
                d = df[(df["country"] == c) & (df["connection"] == seg) & (df["segment"] == "Total") & (df["applications"] == "Total") & (df["scenario"] == dataset_scenario)]
            else:
                # For specific segment types (Ground-mounted, Residential, AgriPV, Floating PV, etc.), filter by segment
                d = df[(df["country"] == c) & (df["segment"] == seg) & (df["applications"] == "Total") & (df["scenario"] == dataset_scenario)]
            if max_year is not None and max_year > 0:
                d = d[d["year"] <= max_year]
            if min_year is not None and min_year > 0:
                d = d[d["year"] >= min_year]
            if d.empty:
                continue
            pivot = d.groupby("year")[value_column].sum().reset_index()

            # Apply smart year filtering for better visual appearance
            all_years = sorted(pivot["year"].unique())
            if len(all_years) > 15:  # Too many years, filter smartly
                recent_threshold = max(all_years) - 5
                filtered_years = []
                for i, year in enumerate(all_years):
                    if year >= recent_threshold:
                        filtered_years.append(year)
                    elif i % 2 == 0:
                        filtered_years.append(year)
                pivot = pivot[pivot["year"].isin(filtered_years)]

            for _, row in pivot.iterrows():
                data.append({
                    "date": f"{int(row['year'])}-01-01",
                    "series": f"{scen}",
                    "value": float(row[value_column]),
                    "formatted_value": self._format_capacity_value(float(row[value_column]))
                })
            series_info.append({"name": scen, "country": c, "segment": seg, "value_type": vt})
        if not data:
            return MarketPlotDataResult(
                plot_type="line",
                title="No Data Found",
                x_axis_label="",
                y_axis_label="Capacity (MW)",
                unit="MW",
                data=[],
                success=False,
                error_message="No data"
            )
        return MarketPlotDataResult(
            plot_type="line",
            title=f"{vt.title()} {seg} Capacity in {c} (Scenarios)",
            x_axis_label="",
            y_axis_label="Capacity (MW)",
            unit="MW",
            data=data,
            series_info=series_info,
        )

    def _generate_country_comparison_plot(
        self,
        df: pd.DataFrame,
        country: str | None,
        countries: str | None,
        segment: str,
        value_type: str | None,
        scenario: str | None,
        min_year: int | None,
        max_year: int | None
    ) -> MarketPlotDataResult:
        """Generate country comparison plot."""
        print(f"📊 Processing MULTI_COUNTRY plot...")
        # Multi-country line series
        # Determine country list
        country_list = []
        if countries:
            country_list = [cc.strip().title() for cc in countries.split(",") if cc.strip()]
        if country and not country_list:
            country_list = [c.strip().title() for c in country.split(",")]
        if len(country_list) < 2:
            return MarketPlotDataResult(
                plot_type="line",
                title="Invalid parameters",
                x_axis_label="",
                y_axis_label="Capacity (MW)",
                unit="MW",
                data=[],
                success=False,
                error_message="Provide at least two countries"
            )
        if not country_list:
            country_list = ["China", "India", "US"]
        seg = self._normalize_segment_param(segment)
        vt = (value_type or "cumulative").lower()
        # New dataset only has capacity (annual capacity)
        value_column = "capacity"

        data = []
        series_info = []
        for ctry in country_list:
            # Filter by segment type correctly
            if seg == "Total":
                d = df[(df["country"] == ctry) & (df["connection"] == "Total") & (df["segment"] == "Total") & (df["applications"] == "Total")]
            elif seg in ["Distributed", "Centralised"]:
                # For connection types, filter by connection
                d = df[(df["country"] == ctry) & (df["connection"] == seg) & (df["segment"] == "Total") & (df["applications"] == "Total")]
            else:
                # For specific segment types (Ground-mounted, Residential, AgriPV, Floating PV, etc.), filter by segment
                d = df[(df["country"] == ctry) & (df["segment"] == seg) & (df["applications"] == "Total")]
            # Apply proper scenario filtering using global function
            d = _filter_scenario(d, year_col="year", scenario=scenario)
            if max_year is not None and max_year > 0:
                d = d[d["year"] <= max_year]
            if min_year is not None and min_year > 0:
                d = d[d["year"] >= min_year]
            if d.empty:
                continue
            pivot = d.groupby("year")[value_column].sum().reset_index()

            # Apply smart year filtering for better visual appearance
            all_years = sorted(pivot["year"].unique())
            if len(all_years) > 15:  # Too many years, filter smartly
                recent_threshold = max(all_years) - 5
                filtered_years = []
                for i, year in enumerate(all_years):
                    if year >= recent_threshold:
                        filtered_years.append(year)
                    elif i % 2 == 0:
                        filtered_years.append(year)
                pivot = pivot[pivot["year"].isin(filtered_years)]

            for _, row in pivot.iterrows():
                data.append({
                    "date": f"{int(row['year'])}-01-01",
                    "series": ctry,
                    "value": float(row[value_column]),
                    "formatted_value": self._format_capacity_value(float(row[value_column]))
                })
            series_info.append({"name": ctry, "segment": seg, "value_type": vt})
        if not data:
            return MarketPlotDataResult(
                plot_type="line",
                title="No Data Found",
                x_axis_label="",
                y_axis_label="Capacity (MW)",
                unit="MW",
                data=[],
                success=False,
                error_message="No data"
            )
        title_suffix = " vs ".join(country_list[:2]) if len(country_list) == 2 else ", ".join(country_list)
        return MarketPlotDataResult(
            plot_type="line",
            title=f"{vt.title()} {seg} Capacity: {title_suffix}",
            x_axis_label="",
            y_axis_label="Capacity (MW)",
            unit="MW",
            data=data,
            series_info=series_info,
        )

    def _generate_pie_plot(
        self,
        df: pd.DataFrame,
        country: str | None,
        segment: str,
        year: int | None,
        max_year: int | None,
        scenario: str | None,
        user_query: str = ""
    ) -> MarketPlotDataResult:
        """Generate pie plot data for market share distribution."""
        print(f"📊 Processing PIE plot...")
        # Installation share by connection/segment/application for a country in a year
        yr = year or (max_year or 2024)
        d = df[df["year"] == yr]

        # Apply scenario filtering using global function
        d = _filter_scenario(d, year_col="year", scenario=scenario)
        print(f"📊 After scenario filter: {len(d)} rows")

        if country:
            d = d[d["country"].str.lower() == country.strip().lower()]
        if d.empty:
            return MarketPlotDataResult(
                plot_type="pie",
                title="No Data Found",
                x_axis_label="",
                y_axis_label="Share",
                unit="ratio",
                data=[],
                success=False,
                error_message="No data available"
            )

        # Determine the best pie dimension based on user intent and data availability
        def determine_pie_dimension(data, segment_param, user_query=""):
            # Analyze what dimensions have meaningful diversity for pie slicing
            connection_diversity = len([c for c in data['connection'].unique() if c != 'Total'])
            segment_diversity = len([s for s in data['segment'].unique() if s != 'Total'])
            app_diversity = len([a for a in data['applications'].unique() if a != 'Total'])

            print(f"📊 Pie data diversity - Connections: {connection_diversity}, Segments: {segment_diversity}, Applications: {app_diversity}")

            # Explicit user intent detection
            query_lower = user_query.lower()
            explicitly_wants_segments = any(phrase in query_lower for phrase in ['by segment', 'with segment', 'segment breakdown', 'segments', 'showing the segments'])
            explicitly_wants_connections = any(phrase in query_lower for phrase in ['by connection', 'connection type', 'distributed vs centralised'])
            explicitly_wants_applications = any(phrase in query_lower for phrase in ['by application', 'application breakdown', 'applications'])

            # PRIORITY 1: Honor explicit user requests
            if explicitly_wants_segments and segment_diversity >= 2:
                return 'segment'
            elif explicitly_wants_applications and app_diversity >= 2:
                return 'applications'
            elif explicitly_wants_connections and connection_diversity >= 2:
                return 'connection'

            # PRIORITY 2: Default logic based on data diversity
            if connection_diversity >= 2:
                return 'connection'
            elif segment_diversity >= 2:
                return 'segment'
            elif app_diversity >= 2:
                return 'applications'
            else:
                return 'connection'  # Fallback

        seg = self._normalize_segment_param(segment)
        pie_dimension = determine_pie_dimension(d, seg, user_query)
        print(f"📊 Determined pie dimension: {pie_dimension}")

        # Filter and group based on determined dimension
        if pie_dimension == 'connection':
            by_seg = (
                d[(d["connection"].isin(["Distributed", "Centralised"])) &
                  (d["segment"] == "Total") &
                  (d["applications"] == "Total")]
                .groupby("connection")["capacity"].sum().reset_index()
            )
            group_by_col = "connection"
            title_dimension = "Connection Type"
        elif pie_dimension == 'segment':
            # Use segment-connection combination approach
            available_connections = d['connection'].unique()
            non_total_connections = [conn for conn in available_connections if conn != 'Total']
            available_segments = d['segment'].unique()
            non_total_segments = [seg for seg in available_segments if seg != 'Total']

            segment_connection_data = []
            for connection in non_total_connections:
                # Get total capacity for this connection
                conn_total_data = d[(d["connection"] == connection) & (d["segment"] == "Total") & (d["applications"] == "Total")]
                if len(conn_total_data) > 0:
                    total_capacity = float(conn_total_data["capacity"].iloc[0])

                    # Add individual segments for this connection
                    specific_segments_sum = 0
                    for segment in non_total_segments:
                        seg_data = d[(d["connection"] == connection) & (d["segment"] == segment) & (d["applications"] != "Total")]
                        if len(seg_data) > 0:
                            segment_capacity = float(seg_data["capacity"].sum())
                            if segment_capacity > 0:
                                segment_connection_data.append({
                                    "segment_connection": f"{connection} {segment}",
                                    "capacity": segment_capacity,
                                    "connection": connection,
                                    "segment": segment
                                })
                                specific_segments_sum += segment_capacity

                    # Calculate "Other" for this connection
                    other_capacity = total_capacity - specific_segments_sum
                    if other_capacity > 0.01:
                        segment_connection_data.append({
                            "segment_connection": f"{connection} Other",
                            "capacity": other_capacity,
                            "connection": connection,
                            "segment": "Other"
                        })

            if segment_connection_data:
                by_seg = pd.DataFrame(segment_connection_data)
                group_by_col = "segment_connection"
                title_dimension = "Segment by Connection"
            else:
                # Fallback to connection if no segment data
                by_seg = (
                    d[(d["connection"].isin(["Distributed", "Centralised"])) &
                      (d["segment"] == "Total") &
                      (d["applications"] == "Total")]
                    .groupby("connection")["capacity"].sum().reset_index()
                )
                group_by_col = "connection"
                title_dimension = "Connection Type"
        elif pie_dimension == 'applications':
            # Use application-connection combination approach
            available_connections = d['connection'].unique()
            non_total_connections = [conn for conn in available_connections if conn != 'Total']
            available_applications = d['applications'].unique()
            non_total_applications = [app for app in available_applications if app != 'Total']

            application_connection_data = []
            for connection in non_total_connections:
                # Get total capacity for this connection
                conn_total_data = d[(d["connection"] == connection) & (d["segment"] == "Total") & (d["applications"] == "Total")]
                if len(conn_total_data) > 0:
                    total_capacity = float(conn_total_data["capacity"].iloc[0])

                    # Add individual applications for this connection
                    specific_applications_sum = 0
                    for application in non_total_applications:
                        app_data = d[(d["connection"] == connection) & (d["applications"] == application) & (d["segment"] != "Total")]
                        if len(app_data) > 0:
                            application_capacity = float(app_data["capacity"].sum())
                            if application_capacity > 0:
                                application_connection_data.append({
                                    "application_connection": f"{connection} {application}",
                                    "capacity": application_capacity,
                                    "connection": connection,
                                    "application": application
                                })
                                specific_applications_sum += application_capacity

                    # Calculate "Other" for this connection
                    other_capacity = total_capacity - specific_applications_sum
                    if other_capacity > 0.01:
                        application_connection_data.append({
                            "application_connection": f"{connection} Other",
                            "capacity": other_capacity,
                            "connection": connection,
                            "application": "Other"
                        })

            if application_connection_data:
                by_seg = pd.DataFrame(application_connection_data)
                group_by_col = "application_connection"
                title_dimension = "Application by Connection"
            else:
                # Fallback to connection if no application data
                by_seg = (
                    d[(d["connection"].isin(["Distributed", "Centralised"])) &
                      (d["segment"] == "Total") &
                      (d["applications"] == "Total")]
                    .groupby("connection")["capacity"].sum().reset_index()
                )
                group_by_col = "connection"
                title_dimension = "Connection Type"

        if by_seg.empty:
            return MarketPlotDataResult(
                plot_type="pie",
                title="No Data Found",
                x_axis_label="",
                y_axis_label="Share",
                unit="ratio",
                data=[],
                success=False,
                error_message="No segment data"
            )

        # Filter out zero-value categories from pie chart
        by_seg = by_seg[by_seg["capacity"] > 0]
        print(f"📊 Excluding zero-value categories from pie chart")

        if by_seg.empty:
            return MarketPlotDataResult(
                plot_type="pie",
                title="No Data Found",
                x_axis_label="",
                y_axis_label="Share",
                unit="ratio",
                data=[],
                success=False,
                error_message="No non-zero data"
            )

        total_mw = float(by_seg["capacity"].sum())
        total = total_mw if total_mw > 0 else 1.0
        data = []
        for _, row in by_seg.iterrows():
            seg_name = row[group_by_col]
            mw_val = float(row["capacity"]) if row["capacity"] is not None else 0.0
            share = (mw_val / total) if total > 0 else 0.0
            data.append({
                "category": seg_name,
                "series": "Share",
                "value": share,
                "mw": mw_val,
            })
        # Also include an explicit 'Total' entry for frontend convenience
        data.append({
            "category": "Total",
            "series": "Total",
            "value": 1.0,
            "mw": total_mw,
        })

        title_country = country or ""
        return MarketPlotDataResult(
            plot_type="pie",
            title=f"{title_dimension} in {yr} {title_country}".strip(),
            x_axis_label="",
            y_axis_label="",
            unit="ratio",
            data=data,
            series_info=[{"name": "Share", "year": yr, "country": title_country, "total_mw": total_mw}],
        )

    def _generate_stacked_plot(
        self,
        df: pd.DataFrame,
        country: str | None,
        segment: str,
        value_type: str | None,
        scenarios: str | None,
        scenario: str | None,
        min_year: int | None,
        max_year: int | None,
        duration: str | None,
        user_query: str = ""
    ) -> MarketPlotDataResult:
        """Generate stacked plot data for breakdown analysis."""
        print(f"📊 Processing STACKED plot...")
        # Market share per segment stacked by year for a country
        c = (country or "China").title()
        seg = self._normalize_segment_param(segment)
        vt = (value_type or "annual").lower()
        value_column = "capacity"  # New dataset only has capacity column

        # ✅ FIX: Handle multiple scenarios if provided
        d = df[df["country"] == c]

        # For stacked charts, only use ONE scenario at a time
        # If multiple scenarios are requested, use the last one mentioned
        selected_scenario_name = None
        if scenarios and "," in scenarios:
            scenario_list = [s.strip() for s in scenarios.split(",")]
            # Use the last scenario mentioned (most recent request)
            selected_scenario_name = scenario_list[-1]
            print(f"📊 Multiple scenarios requested: {scenarios}, using latest: {selected_scenario_name}")
            d = _filter_scenario(d, year_col="year", scenario=selected_scenario_name)
            print(f"📊 After scenario filter ({selected_scenario_name}): {len(d)} rows")
        else:
            # Single scenario or default behavior
            selected_scenario_name = scenario
            d = _filter_scenario(d, year_col="year", scenario=scenario)
            print(f"📊 After single scenario filter: {len(d)} rows")

        # ✅ FIX: Extend year range automatically for forecast scenarios
        is_forecast_scenario = selected_scenario_name and selected_scenario_name.lower() in ['high', 'low', 'most probable', 'most_probable']
        if is_forecast_scenario and max_year is not None and max_year <= 2024:
            print(f"📊 🔮 Forecast scenario detected ({selected_scenario_name}), extending max_year from {max_year} to 2030")
            max_year = 2030  # Extend to include forecast years

        if max_year is not None and max_year > 0:
            d = d[d["year"] <= max_year]
            print(f"📊 After max_year filter ({max_year}): {len(d)} rows")
        if min_year is not None and min_year > 0:
            d = d[d["year"] >= min_year]
            print(f"📊 After min_year filter ({min_year}): {len(d)} rows")
        if d.empty:
            return MarketPlotDataResult(
                plot_type="bar",
                title="No Data Found",
                x_axis_label="",
                y_axis_label="Share",
                unit="ratio",
                data=[],
                success=False,
                error_message="No data available"
            )
        # Compute per-year shares for Distributed and Centralised (or Total fallback)
        print(f"📊 Available segments in data: {sorted(d['segment'].unique())}")

        # Smart stacking logic - determine what dimension to stack by based on data availability
        def determine_stack_dimension(data, segment_param, user_query=""):
            """Determine the best stacking dimension based on user intent and data availability"""

            # Analyze what dimensions have meaningful diversity for stacking
            connection_diversity = len([c for c in data['connection'].unique() if c != 'Total'])
            segment_diversity = len([s for s in data['segment'].unique() if s != 'Total']) 
            app_diversity = len([a for a in data['applications'].unique() if a != 'Total'])

            print(f"📊 Data diversity - Connections: {connection_diversity}, Segments: {segment_diversity}, Applications: {app_diversity}")

            # Explicit user intent detection (stronger than before)
            query_lower = user_query.lower()
            explicitly_wants_segments = any(phrase in query_lower for phrase in ['by segment', 'with segment', 'segment breakdown', 'segments'])
            explicitly_wants_connections = any(phrase in query_lower for phrase in ['by connection', 'connection type', 'distributed vs centralised'])
            explicitly_wants_applications = any(phrase in query_lower for phrase in ['by application', 'application breakdown', 'applications'])

            # PRIORITY 1: Honor explicit user requests even if data has limited diversity
            if explicitly_wants_applications:
                if app_diversity >= 1:  # Even 1 application type can be shown
                    return 'applications'
            else:
                print(f"📊 User wants applications but no application data available, falling back")
            if explicitly_wants_segments:
                if segment_diversity >= 1:
                    return 'segment'
                else:
                    print(f"📊 User wants segments but no segment data available, falling back")
            elif explicitly_wants_connections:
                if connection_diversity >= 1:
                    return 'connection'
                else:
                    print(f"📊 User wants connections but no connection data available, falling back")

            # PRIORITY 2: If user specified a specific connection, stack by segments within it
            if segment_param in ["Distributed", "Centralised", "Off-grid"]:
                if segment_diversity >= 2:
                    return 'segment'
                elif app_diversity >= 2:
                    return 'applications'
                else:
                    return 'connection'

            # PRIORITY 3: If user specified a specific segment, stack by applications within it
            elif segment_param in ["Residential", "Commercial & Industrial", "Ground-mounted", "AgriPV", "Floating PV"]:
                if app_diversity >= 2:
                    return 'applications'
                elif connection_diversity >= 2:
                    return 'connection'
                else:
                    return 'segment'

            # PRIORITY 4: Default logic based on data diversity
            else:
                # Use data diversity priority: connection > segment > applications
                if connection_diversity >= 2:
                    return 'connection'
                elif segment_diversity >= 2:
                    return 'segment'
                elif app_diversity >= 2:
                    return 'applications'
                else:
                    # Fallback to connection even if no diversity (will show as single series)
                    return 'connection'

        # Get user query from request context (async) or self (sync fallback)
        from request_context import get_user_query
        user_query = get_user_query() or getattr(self, 'last_user_query', '')
        stack_by = determine_stack_dimension(d, seg, user_query)
        print(f"📊 Determined stacking dimension: {stack_by}")

        if stack_by == 'connection':
            # Stack by connection type (Distributed vs Centralised vs Off-grid)
            available_connections = d['connection'].unique()
            print(f"📊 Available connections: {sorted(available_connections)}")

            # Use non-Total connections for stacking, with Total segments/applications to avoid double counting
            non_total_connections = [conn for conn in available_connections if conn != 'Total']
            if len(non_total_connections) >= 2:
                d = d[(d["connection"].isin(non_total_connections)) & (d["segment"] == "Total") & (d["applications"] == "Total")]
                group_by_col = "connection"
                print(f"📊 Stacking by connection: {non_total_connections} ({len(d)} rows)")
            else:
                # Fallback to total if insufficient connections
                d = d[(d["connection"] == "Total") & (d["segment"] == "Total") & (d["applications"] == "Total")]
                group_by_col = "connection"
                print(f"📊 Insufficient connections for stacking, using Total")

        elif stack_by == 'segment':
            # Stack by segment-connection combinations for complete breakdown
            available_segments = d['segment'].unique()
            available_connections = d['connection'].unique()
            print(f"📊 Available segments: {sorted(available_segments)}")
            print(f"📊 Available connections: {sorted(available_connections)}")

            # Create comprehensive segment-connection breakdown
            segment_connection_data = []
            non_total_segments = [seg for seg in available_segments if seg != 'Total']

            # Process each connection to build segment breakdown
            for conn in available_connections:
                if conn != 'Total':
                    # Get the total capacity for this connection
                    conn_total_data = d[(d["connection"] == conn) & (d["segment"] == "Total") & (d["applications"] == "Total")]

                    if not conn_total_data.empty:
                        # For each year, break down this connection's capacity
                        for _, total_row in conn_total_data.iterrows():
                            year = total_row["year"]
                            total_capacity = total_row["capacity"]

                            if total_capacity > 0:  # Only process non-zero connections
                                specific_segments_sum = 0

                                # Add specific segments for this connection-year
                                for segment in non_total_segments:
                                    # Try with Total applications first, then without filter if empty
                                    seg_data = d[(d["connection"] == conn) & (d["segment"] == segment) & 
                                               (d["applications"] == "Total") & (d["year"] == year)]

                                    # If no Total applications data, aggregate across all applications
                                    if seg_data.empty:
                                        seg_data = d[(d["connection"] == conn) & (d["segment"] == segment) & 
                                                   (d["year"] == year) & (d["applications"] != "Total")]

                                    if not seg_data.empty:
                                        segment_capacity = seg_data["capacity"].sum()
                                        if segment_capacity > 0:
                                            segment_connection_data.append({
                                                "year": year,
                                                "segment_connection": f"{conn} {segment}",
                                                "capacity": segment_capacity,
                                                "connection": conn,
                                                "segment": segment
                                            })
                                            specific_segments_sum += segment_capacity

                                # Add "Other" for this connection-year if there's unaccounted capacity
                                other_capacity = total_capacity - specific_segments_sum
                                if other_capacity > 0:  # Add any remainder as "Other"
                                    segment_connection_data.append({
                                        "year": year,
                                        "segment_connection": f"{conn} Other",
                                        "capacity": other_capacity,
                                        "connection": conn,
                                        "segment": "Other"
                                    })

            # Check if we successfully created segment-connection data
            if segment_connection_data:
                seg_conn_df = pd.DataFrame(segment_connection_data)
                print(f"📊 Debug: seg_conn_df columns: {list(seg_conn_df.columns)}")
                print(f"📊 Debug: seg_conn_df shape: {seg_conn_df.shape}")

                yearly = seg_conn_df[["year", "segment_connection", "capacity"]].copy()
                yearly.columns = ["year", "segment_connection", value_column]
                group_by_col = "segment_connection"
                print(f"📊 ✅ Successfully created segment-connection breakdown with {len(yearly)} data points")
            else:
                # Fallback to connection stacking if no segment data could be created
                print(f"📊 ❌ No segment-connection data found, falling back to connection stacking")
                d = d[(d["connection"].isin(["Distributed", "Centralised", "Off-grid"])) & (d["segment"] == "Total") & (d["applications"] == "Total")]
                yearly = d.groupby(["year", "connection"])[value_column].sum().reset_index()
                group_by_col = "connection"

        else:  # stack_by == 'applications'
            # Stack by application-connection combinations for complete breakdown
            available_applications = d['applications'].unique()
            available_connections = d['connection'].unique()
            print(f"📊 Available applications: {sorted(available_applications)}")
            print(f"📊 Available connections: {sorted(available_connections)}")

            # Create comprehensive application-connection breakdown
            application_connection_data = []
            non_total_applications = [app for app in available_applications if app != 'Total']

            # Process each connection to build application breakdown
            for conn in available_connections:
                if conn != 'Total':
                    # Get the total capacity for this connection
                    conn_total_data = d[(d["connection"] == conn) & (d["segment"] == "Total") & (d["applications"] == "Total")]

                    if not conn_total_data.empty:
                        # For each year, break down this connection's capacity by applications
                        for _, total_row in conn_total_data.iterrows():
                            year = total_row["year"]
                            total_capacity = total_row["capacity"]

                            if total_capacity > 0:  # Only process non-zero connections
                                specific_applications_sum = 0

                                # Add specific applications for this connection-year
                                for application in non_total_applications:
                                    # Aggregate across all segments for this connection-application
                                    app_data = d[(d["connection"] == conn) & (d["applications"] == application) & 
                                                (d["year"] == year) & (d["segment"] != "Total")]

                                    if not app_data.empty:
                                        application_capacity = app_data["capacity"].sum()
                                        if application_capacity > 0:
                                            application_connection_data.append({
                                                "year": year,
                                                "application_connection": f"{conn} {application}",
                                                "capacity": application_capacity,
                                                "connection": conn,
                                                "application": application
                                            })
                                            specific_applications_sum += application_capacity

                                # Add "Other" for this connection-year if there's unaccounted capacity
                                other_capacity = total_capacity - specific_applications_sum
                                if other_capacity > 0:  # Add any remainder as "Other"
                                    application_connection_data.append({
                                        "year": year,
                                        "application_connection": f"{conn} Other",
                                        "capacity": other_capacity,
                                        "connection": conn,
                                        "application": "Other"
                                    })

            # Check if we successfully created application-connection data
            if application_connection_data:
                app_conn_df = pd.DataFrame(application_connection_data)
                print(f"📊 Debug: app_conn_df columns: {list(app_conn_df.columns)}")
                print(f"📊 Debug: app_conn_df shape: {app_conn_df.shape}")

                yearly = app_conn_df[["year", "application_connection", "capacity"]].copy()
                yearly.columns = ["year", "application_connection", value_column]
                group_by_col = "application_connection"
                print(f"📊 ✅ Successfully created application-connection breakdown with {len(yearly)} data points")
            else:
                # Fallback to connection stacking if no application data could be created
                print(f"📊 ❌ No application-connection data found, falling back to connection stacking")
                d = d[(d["connection"].isin(["Distributed", "Centralised", "Off-grid"])) & (d["segment"] == "Total") & (d["applications"] == "Total")]
                yearly = d.groupby(["year", "connection"])[value_column].sum().reset_index()
                group_by_col = "connection"


        # Group by the determined dimension (skip for segment and applications which are handled above)
        if stack_by not in ['segment', 'applications']:
            yearly = d.groupby(["year", group_by_col])[value_column].sum().reset_index()
        # Note: For segment and applications stacking, yearly is already created in the combination logic above

        totals = yearly.groupby("year")[value_column].sum().rename("_total").reset_index()
        merged = yearly.merge(totals, on="year")
        merged["share"] = merged[value_column] / merged["_total"].replace(0, 1.0)

        # Smart year filtering for better visual appearance
        all_years = sorted(merged["year"].unique())
        if len(all_years) > 15:  # Too many years, filter smartly
            # Keep every 2nd year for better spacing, but always include recent years
            recent_threshold = max(all_years) - 5  # Last 5 years always shown
            filtered_years = []
            for i, year in enumerate(all_years):
                if year >= recent_threshold:  # Always include recent years
                    filtered_years.append(year)
                elif i % 2 == 0:  # Every 2nd year for older data
                    filtered_years.append(year)
            merged = merged[merged["year"].isin(filtered_years)]
            print(f"📊 Filtered years for better display: {len(filtered_years)} years instead of {len(all_years)}")

        # Check if we have multiple categories for stacking
        unique_categories = merged[group_by_col].unique()
        print(f"📊 Unique {group_by_col} categories after processing: {unique_categories}")

        if len(unique_categories) > 1:
            # Check for very small categories that might not be visible
            category_totals = merged.groupby(group_by_col)[value_column].sum().sort_values(ascending=False)
            max_total = category_totals.max()
            small_categories = []
            tiny_categories = []

            for cat, total in category_totals.items():
                if total < max_total * 0.001:  # Less than 0.1% of the largest category
                    tiny_categories.append(cat)
                elif total < max_total * 0.01:  # Less than 1% of the largest category
                    small_categories.append(cat)

            # Keep all categories - no filtering based on size
            if tiny_categories:
                print(f"📊 Tiny categories detected but keeping them: {tiny_categories} (< 0.1% of largest category)")

            if small_categories:
                print(f"📊 Warning: Small categories detected: {small_categories} (may be hard to see in chart)")

            # Smart labeling logic - determine if we should show segment labels or rely on x-axis
            unique_years = len(merged["year"].unique())
            label_threshold = 6  # Show segment labels only if <= 6 bars
            show_segment_labels = unique_years <= label_threshold

            print(f"📊 Chart has {unique_years} bars. Segment labels: {'ON' if show_segment_labels else 'OFF (rely on x-axis)'}")

            # Filter out categories with zero total capacity across all years
            category_totals = merged.groupby(group_by_col)[value_column].sum()
            categories_with_data = category_totals[category_totals > 0].index.tolist()

            if len(categories_with_data) < len(unique_categories):
                zero_categories = [cat for cat in unique_categories if cat not in categories_with_data]
                print(f"📊 Excluding zero-value categories from legend: {zero_categories}")
                merged = merged[merged[group_by_col].isin(categories_with_data)]

            # Multiple categories - create stacked chart with smart formatting
            data = [
                {
                    "category": int(row["year"]), 
                    "series": row[group_by_col], 
                    "value": float(row[value_column]),  # Use MW values for display
                    "share": float(row["share"]),  # Keep share for stacking logic
                    "formatted_value": self._format_capacity_value(float(row[value_column])),  # Smart formatting
                    "is_small": row[group_by_col] in small_categories,  # Flag for frontend styling
                    "show_segment_labels": show_segment_labels  # Control segment label visibility
                }
                for _, row in merged.iterrows()
            ]
            series_info = [{"name": s} for s in sorted(merged[group_by_col].unique())]

            # Create appropriate title based on stacking dimension
            if group_by_col == "connection":
                title_suffix = "by Connection Type"
            elif group_by_col == "segment":
                title_suffix = "by Segment"
            elif group_by_col == "applications":
                title_suffix = "by Application"
            else:
                title_suffix = f"by {group_by_col.title()}"

            # Add note about small/filtered categories and labeling if present
            chart_title = f"{vt.title()} Market {title_suffix} in {c}"
            notes = []
            # Note: No longer filtering out any categories
            if small_categories:
                notes.append(f"{', '.join(small_categories)} values are very small")
            if not show_segment_labels:
                notes.append(f"refer to legend for segment identification")

            # Add explanation if user requested different stacking but we had to fallback
            # Get user query from request context (async) or self (sync fallback)
            user_query_text = user_query or getattr(self, 'last_user_query', '')
            query_lower = user_query_text.lower()
            if stack_by != 'applications' and 'application' in query_lower:
                available_apps = d['applications'].unique()
                non_total_apps = [a for a in available_apps if a != 'Total']
                if len(non_total_apps) <= 1:
                    notes.append(f"only {len(non_total_apps)} application type available, showing by {group_by_col} instead")
            elif stack_by != 'segment' and any(word in query_lower for word in ['segment', 'segments']):
                available_segs = d['segment'].unique()
                non_total_segs = [s for s in available_segs if s != 'Total']
                if len(non_total_segs) <= 1:
                    notes.append(f"only {len(non_total_segs)} segment type available, showing by {group_by_col} instead")

            # Keep title clean - notes will be displayed separately at bottom
            result = MarketPlotDataResult(
                plot_type="stacked",
                title=chart_title,
                x_axis_label="",
                y_axis_label="Capacity (MW)",
                unit="MW",
                data=data,
                series_info=series_info,
                notes=notes,  # Pass notes separately for bottom display
            )
        else:
            # Single category - create regular bar chart
            print(f"📊 Single {group_by_col} category detected, creating bar chart instead of stacked")
            data = [
                {
                    "category": int(row["year"]), 
                    "series": f"{c} {row[group_by_col]}", 
                    "value": float(row[value_column]),
                    "formatted_value": self._format_capacity_value(float(row[value_column]))
                }
                for _, row in merged.iterrows()
            ]
            # Safety check for empty categories
            if len(unique_categories) == 0:
                print("📊 ❌ ERROR: No data categories found after filtering")
                return MarketPlotDataResult(
                    plot_type="bar",
                    title="No Data Found",
                    x_axis_label="",
                    y_axis_label="Capacity (MW)",
                    unit="MW",
                    data=[],
                    success=False,
                    error_message="No data categories found"
                )

            series_info = [{"name": f"{c} {unique_categories[0]}"}]
            result = MarketPlotDataResult(
                plot_type="bar",
                title=f"{vt.title()} {unique_categories[0]} Market in {c}",
                x_axis_label="",
                y_axis_label="Capacity (MW)",
                unit="MW",
                data=data,
                series_info=series_info,
            )

        return result

    def _setup_pydantic_agent(self):
        try:


            # Legacy nested plot generation agent removed

            plot_parameter_agent = Agent(
                model="openai:gpt-4.1",
                output_type=MarketPlotParameters,
                system_prompt=(
                    "Return ONLY a valid MarketPlotParameters object for plotting.\n\n"
                    "Dataset schema (must match exactly):\n"
                    "- Countries: 82 global countries (including China, USA, India, Brazil, European countries)\n"
                    "- Connection ∈ {Total, Distributed, Centralised, Off-grid}\n"
                    "- Segment ∈ {Total, Residential, Commercial & Industrial, Ground-mounted, AgriPV, Floating PV}\n"
                    "- Applications ∈ {Total, BAPV, BIPV, Commercial BAPV, Industrial BAPV, Residential BAPV}\n"
                    "- Scenario ∈ {Historical, Forecast - Most probable, Forecast - High, Forecast - Low}\n"
                    "- Year ∈ [1992, 2030] (Historical: 1992-2024, Forecasts: 2025-2030)\n"
                    "- Duration ∈ {FY, Q1, Q2, Q3, Q4, ALL_QUARTERS} (Full Year, Specific Quarter, or All Quarters)\n"
                    "- Type ∈ {Annual, Cumulative} (Yearly additions or Running totals)\n"
                    "- Value column: capacity (PV capacity in MW)\n"
                    "- Quality: estimation_status ∈ {Confirmed, Estimated}, install_action ∈ {Installed}\n\n"
                    "**CONNECTION & SEGMENT MAPPING RULES:**\n"
                    "- **Connection Types**: Total (overall), Distributed (rooftop/small-scale), Centralised (utility-scale), Off-grid (standalone)\n"
                    "- **Segment Types**: Total, Residential, Commercial & Industrial, Ground-mounted, AgriPV, Floating PV\n"
                    "- **Application Types**: Total, BAPV (Building-attached), BIPV (Building-integrated), Commercial/Industrial/Residential BAPV\n"
                    "- **IMPORTANT**: Use 'Total' for segment parameter when user asks for breakdowns 'by segment', 'by connection', or 'by application'\n"
                    "- **Use 'Total' for connection/segment/applications** when user asks for overall market or doesn't specify\n"
                    "\n"
                    "**CRITICAL: Utility-scale vs Ground-mounted:**\n"
                    "- **'utility-scale', 'utility scale' (alone)** → segment='Centralised' (this is a CONNECTION TYPE, representing ALL utility-scale installations)\n"
                    "- **'ground-mounted', 'ground mounted', 'utility scale ground mounted'** → segment='Ground-mounted' (this is a SEGMENT TYPE, a subset of Centralised)\n"
                    "\n"
                    "**For specific segments**: \n"
                    "  - 'agripv', 'agri pv', 'agrivoltaics', 'agricultural' → segment='AgriPV' (always Centralised)\n"
                    "  - 'floating', 'floating pv', 'floating solar' → segment='Floating PV' (always Centralised)\n"
                    "  - 'residential', 'rooftop residential' → segment='Residential' (usually Distributed)\n"
                    "  - 'commercial', 'industrial', 'c&i' → segment='Commercial & Industrial' (usually Distributed)\n"
                    "- **For building integration**: Use BAPV/BIPV applications when discussing building-mounted solar\n\n"
                    "**DURATION PARAMETER RULES:**\n"
                    "- **Default**: duration='FY' (Full Year) - use for most queries\n"
                    "- **ALL QUARTERLY DATA**: When user wants to see quarterly breakdown or multiple quarters:\n"
                    "  - 'quarterly data', 'quarterly breakdown', 'show quarterly', 'by quarters' → duration='ALL_QUARTERS'\n"
                    "  - 'plot quarterly', 'quarterly trend', 'quarter by quarter' → duration='ALL_QUARTERS'\n"
                    "- **SPECIFIC QUARTER**: When user wants one specific quarter:\n"
                    "  - 'Q1', 'first quarter', 'Q1 2024' → duration='Q1'\n"
                    "  - 'Q2', 'second quarter', 'Q2 data' → duration='Q2'\n"
                    "  - 'Q3', 'third quarter', 'Q3 results' → duration='Q3'\n"
                    "  - 'Q4', 'fourth quarter', 'Q4 numbers' → duration='Q4'\n"
                    "- **CRITICAL**: 'quarterly data' means ALL quarters (Q1+Q2+Q3+Q4), not just one quarter!\n"
                    "- **Examples**: \n"
                    "  - 'plot quarterly data for Italy' → duration='ALL_QUARTERS'\n"
                    "  - 'Q1 2024 capacity' → duration='Q1'\n"
                    "  - 'full year capacity' → duration='FY'\n\n"
                    "**TYPE PARAMETER RULES:**\n"
                    "- **Cumulative requests**: type='Cumulative' for running totals\n"
                    "  - 'cumulative', 'total installed', 'total capacity', 'cumulative capacity', 'installed capacity to date'\n"
                    "- **Annual requests**: type='Annual' for yearly additions\n"
                    "  - 'annual', 'yearly', 'new capacity', 'additions', 'installed in [year]', 'capacity added'\n"
                    "- **Default**: type='Annual' when user intent is unclear (most common)\n"
                    "- **Examples**: 'cumulative capacity of China' → type='Cumulative', 'annual capacity in 2024' → type='Annual'\n\n"
                    "**PLOT TYPE RULES (Valid values: 'line', 'bar', 'stacked', 'pie', 'multi_scenario'):**\n"
                    "- **MULTI-YEAR + ANY COUNTRY**: Use plot_type='line' for time trends (e.g., 'since 2019', '2015-2024', 'over time', country comparisons over time)\n"
                    "- **MULTI-SCENARIO + SINGLE COUNTRY**: Use plot_type='multi_scenario' when user wants multiple scenarios (e.g., 'show all scenarios', 'compare scenarios', 'other scenarios too')\n"
                    "- **SINGLE YEAR + MULTI COUNTRY**: Use plot_type='bar' for country comparison (only when explicitly single year)\n"
                    "- **SINGLE YEAR + SINGLE COUNTRY**: Use plot_type='pie' to show segment distribution\n"
                    "- **STACKED PLOTS** (Use plot_type='stacked' for breakdowns over time):\n"
                    "  - When user says 'with segments', 'by segment', 'segment breakdown' → plot_type='stacked' (the backend will auto-detect best stacking)\n"
                    "  - When user says 'by connection', 'connection type' → plot_type='stacked' (the backend will auto-detect best stacking)\n"
                    "  - When user says 'by application', 'application breakdown' → plot_type='stacked' (the backend will auto-detect best stacking)\n"
                    "  - 'stacked bars', 'stacked chart', 'breakdown over time' → plot_type='stacked'\n"
                    "  - **KEY**: Always use plot_type='stacked' for any breakdown request, let backend choose the dimension\n"
                    "- **EXPLICIT REQUESTS**: \n"
                    "  - 'line chart' → plot_type='line'\n"
                    "  - 'bar chart' → plot_type='bar'\n"
                    "  - 'stacked bar chart' → plot_type='stacked'\n"
                    "  - 'pie chart' → plot_type='pie'\n\n"
                    "**PLOT TYPE EXAMPLES:**\n"
                    "- 'Plot annual values since 2019' → plot_type='line' (multi-year trend)\n"
                    "- 'Capacity evolution 2015-2030' → plot_type='line' (multi-year trend)\n"
                    "- 'Compare Germany and France over time' → plot_type='line' (multi-year country comparison)\n"
                    "- 'Plot these data' (with historical context) → plot_type='line' (time series)\n"
                    "- 'Compare countries in 2024 only' → plot_type='bar' (explicitly single-year)\n"
                    "- 'Top 5 countries in 2024' → plot_type='bar' (single-year comparison)\n"
                    "- 'Show all scenarios for Belgium' → plot_type='multi_scenario' (scenario comparison)\n"
                    "- 'Other scenarios too' → plot_type='multi_scenario' (scenario comparison)\n\n"
                    "**VALUE TYPE RULES:**\n"
                    "- **annual**: Use when user asks for 'annual installations', 'yearly capacity', 'new capacity', 'installations in 2024'\n"
                    "- **cumulative**: Use when user asks for 'total capacity', 'cumulative installations', 'overall market size'\n"
                    "- **dual**: Use when user asks for general 'market', 'capacity', 'evolution', 'development' without specifying annual/cumulative AND it's multi-year\n"
                    "- **single-year multi-country**: For single year + multiple countries, prefer 'annual' for cleaner comparison\n"
                    "- **default**: Use 'annual' for single-year requests, 'dual' for multi-year requests\n\n"
                    "Scenario rules (strict):\n"
                    "- If requested period is ONLY ≤ 2024 (e.g., year<=2024 or max_year<=2024), set scenario='Historical'.\n"
                    "- If ANY requested year > 2024, scenario MUST be one of: 'Most Probable', 'High', 'Low'. "
                    "If user provided 'Historical' or unknown, coerce to 'Most Probable'.\n"
                    "- If user says 'all scenarios', set scenarios='Most Probable, High, Low' and set scenario=None.\n"
                    "- For single scenario requests, set scenario to the specific scenario and leave scenarios=''.\n\n"
                    "Year handling:\n"
                    "- If min_year and max_year are both set and min_year>max_year, swap them.\n"
                    "- If user says 'last N years' without numbers, leave years unset.\n\n"
                    "**COUNTRY HANDLING RULES:**\n"
                    "- **Single country**: Set 'country' field, leave 'countries' empty\n"
                    "- **Multiple countries**: Set 'countries' as comma-separated string (e.g., 'Germany, Spain, Italy'), leave 'country' empty\n"
                    "- **From data analysis**: If previous context shows top countries list, include ALL countries in 'countries' field\n"
                    "- **Example**: For 'plot top 5 countries' → countries='Germany, Spain, Italy, France, Netherlands'\n\n"
                    "Output rules:\n"
                    "- Do not title-case acronyms (e.g., keep 'US' if user wrote 'US').\n"
                ),
            )
            
            async def extract_plot_parameters(ctx: RunContext[None], user_query: str) -> MarketPlotParameters:
                """Extract structured plotting parameters from a natural language request."""
                try:
                    sub = await plot_parameter_agent.run(user_query)
                    params = sub.output
                except UsageLimitExceeded as usage_error:
                    print(f"⚠️ Usage limit exceeded in plot parameter extraction: {usage_error}")
                    # This is a nested function, so we'll propagate the exception to the outer handler
                    raise usage_error
                except Exception as e:
                    print(f"❌ Plot parameter extraction failed: {e}")
                    print(f"❌ User query: {user_query}")
                    # Return a default set of parameters for debugging
                    return MarketPlotParameters(
                        plot_type=PlotType.line,
                        country="Spain",
                        segment=SegmentLiteral.TOTAL,
                        value_type="cumulative",
                        year=2024,
                        min_year=2015,
                        max_year=2030,
                        scenario=None,
                        countries="",
                        scenarios="Most Probable, High, Low"
                    )
                try:
                    logger.info(
                        "Extracted params: plot_type=%s, country=%s, segment=%s, value_type=%s, year=%s, min_year=%s, max_year=%s, scenario=%s, countries=%s, scenarios=%s, duration=%s, type=%s",
                        getattr(params, 'plot_type', None),
                        getattr(params, 'country', None),
                        getattr(params, 'segment', None),
                        getattr(params, 'value_type', None),
                        getattr(params, 'year', None),
                        getattr(params, 'min_year', None),
                        getattr(params, 'max_year', None),
                        getattr(params, 'scenario', None),
                        getattr(params, 'countries', None),
                        getattr(params, 'scenarios', None),
                        getattr(params, 'duration', None),
                        getattr(params, 'type', None),
                    )
                    print(
                        f"🧩 Extracted params → plot_type={getattr(params, 'plot_type', None)}, "
                        f"country={getattr(params, 'country', None)}, segment={getattr(params, 'segment', None)}, "
                        f"value_type={getattr(params, 'value_type', None)}, year={getattr(params, 'year', None)}, "
                        f"min_year={getattr(params, 'min_year', None)}, max_year={getattr(params, 'max_year', None)}, "
                        f"scenario={getattr(params, 'scenario', None)}, countries={getattr(params, 'countries', None)}, "
                        f"scenarios={getattr(params, 'scenarios', None)}, duration={getattr(params, 'duration', None)}, "
                        f"type={getattr(params, 'type', None)}"
                    )
                except Exception:
                    pass
                return params

            # === Tool Wrappers for Main Agent (Hybrid Approach) ===
            async def get_market_plot_data_output(
                ctx: RunContext[None],
                plot_type: str,
                country: str | None = None,
                segment: str | None = None,
                value_type: str | None = None,
                year: int | None = None,
                min_year: int | None = None,
                max_year: int | None = None,
                scenario: str | None = None,
                countries: str | None = None,
                scenarios: str | None = None,
                duration: str | None = None,
                type: str | None = None
            ) -> str:
                """Build JSON data for D3 and cache it. Returns a small stub to the model."""
                # Import request context for thread-safe state management
                from request_context import get_current_context, set_plot_result, set_user_query, get_user_query

                try:
                    print(f"📊 Tool called: plot_type='{plot_type}', country='{country}'")
                    print(f"📊 Parameters: segment={segment}, scenario={scenario}, year_range={min_year}-{max_year}")
                    print(f"📊 New schema params: duration={duration}, type={type}")
                    
                    # Trust parameter extraction tool to provide canonical plot_type
                    pt = plot_type

                    # ✅ ENHANCEMENT: Handle single year requests intelligently
                    is_single_year = (
                        (year is not None and min_year is None and max_year is None) or
                        (min_year is not None and max_year is not None and min_year == max_year)
                    )
                    # Only force pie chart for single year if it's NOT a multi-country comparison AND user didn't explicitly request a different chart type
                    is_multi_country = countries and len([c.strip() for c in countries.split(",") if c.strip()]) > 1
                    user_explicitly_requested_chart_type = pt in ["stacked", "line", "bar"]
                    
                    if is_single_year and pt not in ["pie", "donut"] and not is_multi_country and not user_explicitly_requested_chart_type:
                        print(f"📊 🥧 Single year detected ({year or min_year}), suggesting pie chart for segment distribution")
                        pt = "pie"
                    elif is_single_year and is_multi_country:
                        print(f"📊 📊 Single year multi-country comparison detected, keeping {pt} chart for country comparison")
                    elif is_single_year and user_explicitly_requested_chart_type:
                        print(f"📊 📊 User explicitly requested {pt} chart for single year, expanding to multi-year range")
                        # If user requested stacked/line/bar for single year, expand to last 5 years
                        current_year = year or min_year or 2024
                        min_year = current_year - 4
                        max_year = current_year
                        print(f"📊 📊 Expanded year range to {min_year}-{max_year} for {pt} chart")
                    
                    # Load data via pandas from the annual-full-dataset parquet file
                    df = pd.read_parquet("datasets/becsight/annual-full-dataset/data.parquet")
                    print(f"📊 Loaded {len(df)} rows from annual-full-dataset parquet")
                    
                    # Apply critical filtering for new schema columns
                    original_count = len(df)
                    
                    # Filter for installed capacity only (exclude decommissioned)
                    if 'install_action' in df.columns:
                        df = df[df['install_action'] == 'Installed']
                        print(f"📊 Filtered to {len(df)} rows after install_action=Installed")
                    
                    # Filter by duration parameter (extracted from user query)
                    if 'duration' in df.columns:
                        filter_duration = duration or 'FY'  # Default to Full Year if not specified
                        
                        if filter_duration == 'ALL_QUARTERS':
                            # Include all quarterly data (Q1, Q2, Q3, Q4)
                            df = df[df['duration'].isin(['Q1', 'Q2', 'Q3', 'Q4'])]
                            print(f"📊 Filtered to {len(df)} rows after duration=ALL_QUARTERS (Q1+Q2+Q3+Q4)")
                        else:
                            # Filter for specific duration (FY, Q1, Q2, Q3, or Q4)
                            df = df[df['duration'] == filter_duration]
                            print(f"📊 Filtered to {len(df)} rows after duration={filter_duration}")
                    
                    # Filter by type parameter (extracted from user query)  
                    if 'type' in df.columns:
                        filter_type = type or 'Annual'  # Default to Annual if not specified
                        df = df[df['type'] == filter_type]
                        print(f"📊 Filtered to {len(df)} rows after type={filter_type}")
                    
                    print(f"📊 Final filtered dataset: {len(df)} rows (filtered out {original_count - len(df)} rows)")

                    seg = self._normalize_segment_param(segment)
                    print(f"📊 Normalized segment: {seg}")



                    # Build different JSON shapes per plot_type
                    result: Optional[MarketPlotDataResult] = None

                    if pt == "line":
                        print(f"📊 Processing LINE plot...")
                        # capacity trend style line (country + optional segment/value_type)
                        
                        # ✅ FIX: Handle multi-country requests
                        if countries and countries.strip():
                            # Multi-country request (keep original case for special cases like UK, USA)
                            country_list = [c.strip() for c in countries.split(",") if c.strip()]
                            print(f"📊 Multi-country request: {country_list}")
                            is_multi_country = True
                        else:
                            # Single country request (keep original case)
                            c = (country or "China")
                            print(f"📊 Single country: {c}")
                            is_multi_country = False

                        vt = (value_type or "annual").lower()  # Default to "annual" instead of "dual"
                        # New dataset only has capacity (annual capacity) - no cumulative available
                        show_dual = False  # Simplified since we only have annual capacity
                        value_column = "capacity"
                        print(f"📊 Value type: {vt}, Column: {value_column}")
                        
                        # Initial filter by country and segment - FIXED TO PROPERLY HANDLE SEGMENTS VS CONNECTIONS
                        if is_multi_country:
                            if seg == "Total":
                                # For Total segment, get actual Total data (not breakdown)
                                d = df[(df["country"].isin(country_list)) & (df["connection"] == "Total") & (df["segment"] == "Total") & (df["applications"] == "Total")]
                                print(f"📊 After multi-country+Total segment filter: {len(d)} rows")
                            elif seg in ["Distributed", "Centralised"]:
                                # For connection types, filter by connection and get Total segments/applications
                                d = df[(df["country"].isin(country_list)) & (df["connection"] == seg) & (df["segment"] == "Total") & (df["applications"] == "Total")]
                                print(f"📊 After multi-country+connection filter: {len(d)} rows")
                            else:
                                # For specific segment types (AgriPV, Floating PV, etc.), filter by segment
                                d = df[(df["country"].isin(country_list)) & (df["segment"] == seg) & (df["applications"] == "Total")]
                                print(f"📊 After multi-country+segment filter ({seg}): {len(d)} rows")
                        else:
                            if seg == "Total":
                                # For Total segment, get actual Total data (not breakdown)
                                d = df[(df["country"] == c) & (df["connection"] == "Total") & (df["segment"] == "Total") & (df["applications"] == "Total")]
                                print(f"📊 After country+Total segment filter: {len(d)} rows")
                            elif seg in ["Distributed", "Centralised"]:
                                # For connection types, filter by connection and get Total segments/applications
                                d = df[(df["country"] == c) & (df["connection"] == seg) & (df["segment"] == "Total") & (df["applications"] == "Total")]
                                print(f"📊 After country+connection filter: {len(d)} rows")
                            else:
                                # For specific segment types (AgriPV, Floating PV, etc.), filter by segment
                                # Note: AgriPV/Floating PV are always Centralised, but we don't want to restrict connection
                                d = df[(df["country"] == c) & (df["segment"] == seg) & (df["applications"] == "Total")]
                                print(f"📊 After country+segment filter ({seg}): {len(d)} rows")
                        
                        if len(d) > 0:
                            print(f"📊 Available years: {sorted(d['year'].unique())}")
                            print(f"📊 Available scenarios: {d['scenario'].unique()}")
                        else:
                            print(f"📊 ❌ No data found for {c} + {seg}")
                            available_countries = sorted(df['country'].unique())
                            print(f"📊 Available countries: {available_countries}")
                        
                        # ✅ FIX: Apply proper scenario filtering using the helper function
                        d = _filter_scenario(d, year_col="year", scenario=scenario)
                        print(f"📊 After scenario filter: {len(d)} rows")
                        
                        # ✅ FIX: Calculate year range for "last X years" if not specified
                        if min_year is None and max_year is None:
                            # For "last 5 years", calculate from available data
                            current_year = 2024
                            available_years = sorted(d['year'].unique()) if len(d) > 0 else []
                            if available_years:
                                latest_year = max(available_years)
                                reference_year = min(latest_year, current_year)
                                min_year = reference_year - 4  # Last 5 years
                                max_year = reference_year
                                print(f"📊 Calculated year range: {min_year} to {max_year}")
                            else:
                                print(f"📊 No years available to calculate range from")
                        
                        # Apply year filtering (treat 0 as "not set")
                        if max_year is not None and max_year > 0:
                            d = d[d["year"] <= max_year]
                            print(f"📊 After max_year filter ({max_year}): {len(d)} rows")
                        if min_year is not None and min_year > 0:
                            d = d[d["year"] >= min_year]
                            print(f"📊 After min_year filter ({min_year}): {len(d)} rows")

                        if d.empty:
                            print(f"📊 ❌ NO DATA FOUND after all filters")
                            # Create detailed error message
                            # Handle both single and multi-country cases
                            if is_multi_country:
                                country_str = ", ".join(country_list)
                                available_data = df[df["country"].isin(country_list)]
                            else:
                                country_str = c
                                available_data = df[df["country"] == c]

                            if len(available_data) > 0:
                                available_years = sorted(available_data['year'].unique())
                                year_range_str = f"{min_year}-{max_year}" if (min_year and min_year > 0) or (max_year and max_year > 0) else "all years"
                                error_msg = f"No data for {country_str} {seg} in range {year_range_str}. Available years: {available_years}"
                            else:
                                available_countries = sorted(df['country'].unique())
                                error_msg = f"No data for {country_str}. Available countries: {available_countries}"

                            error_result = MarketPlotDataResult(
                                plot_type="line",
                                title="No Data Found",
                                x_axis_label="",
                                y_axis_label="Capacity (MW)",
                                unit=None,
                                data=[],
                                success=False,
                                error_message=error_msg
                            )
                            set_plot_result(error_result)
                            self.last_market_plot_data_result = error_result  # Also cache in instance for fallback
                            return "plot generation failed"
                        
                        print(f"📊 Final data: {len(d)} rows")
                        if len(d) > 0:
                            print(f"📊 Final years: {sorted(d['year'].unique())}")
                            print(f"📊 Final scenarios: {d['scenario'].unique()}")
                        
                        if show_dual:
                            # Dual value type - show both annual and cumulative
                            if is_multi_country:
                                # Multi-country dual processing
                                data = []
                                # New dataset only has capacity (annual), so we simulate cumulative by aggregating 
                                for value_type_name, column_name in [("Annual", "capacity")]:
                                    # ✅ FIX: Handle quarterly data in multi-country dual processing
                                    if duration == 'ALL_QUARTERS' and 'duration' in d.columns:
                                        # For quarterly data, group by year, duration, and country
                                        pivot = d.groupby(["year", "duration", "country"])[column_name].sum().reset_index()
                                        quarter_months = {"Q1": "01", "Q2": "04", "Q3": "07", "Q4": "10"}
                                        for _, row in pivot.iterrows():
                                            month = quarter_months.get(row['duration'], "01")
                                        data.append({
                                                "date": f"{int(row['year'])}-{month}-01", 
                                                "series": f"{row['country']} {value_type_name}", 
                                                "value": float(row[column_name])
                                            })
                                    else:
                                        # For annual data, group by year and country
                                        pivot = d.groupby(["year", "country"])[column_name].sum().reset_index()
                                        for _, row in pivot.iterrows():
                                            data.append({
                                                "date": f"{int(row['year'])}-01-01", 
                                                "series": f"{row['country']} {value_type_name}", 
                                            "value": float(row[column_name])
                                        })
                                print(f"📊 Multi-country dual pivot result: {len(data)} data points")
                            else:
                                # Single country dual processing
                                data = []
                                # New dataset only has capacity (annual), so we simulate cumulative by aggregating 
                                for value_type_name, column_name in [("Annual", "capacity")]:
                                    # ✅ FIX: Handle quarterly data in dual processing
                                    if duration == 'ALL_QUARTERS' and 'duration' in d.columns:
                                        # For quarterly data, group by year and duration
                                        pivot = d.groupby(["year", "duration"])[column_name].sum().reset_index()
                                        quarter_months = {"Q1": "01", "Q2": "04", "Q3": "07", "Q4": "10"}
                                        for _, row in pivot.iterrows():
                                            month = quarter_months.get(row['duration'], "01")
                                        data.append({
                                                "date": f"{int(row['year'])}-{month}-01", 
                                                "series": f"{c} {value_type_name}", 
                                                "value": float(row[column_name])
                                            })
                                    else:
                                        # For annual data, group by year only
                                        pivot = d.groupby("year")[column_name].sum().reset_index()
                                        for _, row in pivot.iterrows():
                                            data.append({
                                                "date": f"{int(row['year'])}-01-01", 
                                            "series": f"{c} {value_type_name}", 
                                            "value": float(row[column_name])
                                        })
                                print(f"📊 Single country dual pivot result: {len(data)} data points")
                        else:
                            # Single value type processing
                            if is_multi_country:
                                # Multi-country processing
                                # ✅ FIX: Handle quarterly data in multi-country processing
                                if duration == 'ALL_QUARTERS' and 'duration' in d.columns:
                                    # For quarterly data, group by year, duration, and country
                                    pivot = d.groupby(["year", "duration", "country"])[value_column].sum().reset_index()
                                    print(f"📊 Multi-country quarterly pivot result: {len(pivot)} rows")
                                    
                                    quarter_months = {"Q1": "01", "Q2": "04", "Q3": "07", "Q4": "10"}
                                    data = []
                                    for _, row in pivot.iterrows():
                                        month = quarter_months.get(row['duration'], "01")
                                        data.append({
                                            "date": f"{int(row['year'])}-{month}-01", 
                                            "series": f"{row['country']} {seg}", 
                                            "value": float(row[value_column])
                                        })
                                else:
                                    # For annual data, group by year and country
                                    pivot = d.groupby(["year", "country"])[value_column].sum().reset_index()
                                print(f"📊 Multi-country pivot result: {len(pivot)} rows")
                                
                                data = []
                                for _, row in pivot.iterrows():
                                    data.append({
                                            "date": f"{int(row['year'])}-01-01", 
                                            "series": f"{row['country']} {seg}", 
                                        "value": float(row[value_column])
                                    })
                            else:
                                # Single country processing
                                # ✅ FIX: Handle quarterly data by grouping by year+duration
                                if duration == 'ALL_QUARTERS' and 'duration' in d.columns:
                                    # For quarterly data, group by year and duration to preserve quarterly breakdown
                                    pivot = d.groupby(["year", "duration"])[value_column].sum().reset_index()
                                    print(f"📊 Quarterly pivot result: {len(pivot)} rows")
                                    
                                    # Create quarterly date labels (Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct)
                                    quarter_months = {"Q1": "01", "Q2": "04", "Q3": "07", "Q4": "10"}
                                    data = []
                                    for _, row in pivot.iterrows():
                                        month = quarter_months.get(row['duration'], "01")
                                        data.append({
                                            "date": f"{int(row['year'])}-{month}-01", 
                                            "series": f"{c} {seg}", 
                                            "value": float(row[value_column])
                                        })
                                else:
                                    # For annual data, group by year only
                                    pivot = d.groupby("year")[value_column].sum().reset_index()
                                print(f"📊 Pivot result: {len(pivot)} rows")
                                
                                data = [
                                        {"date": f"{int(row['year'])}-01-01", "series": f"{c} {seg}", "value": float(row[value_column])}
                                    for _, row in pivot.iterrows()
                                ]
                        
                        if show_dual:
                            # Dual value type series info and title
                            if is_multi_country:
                                series_info = []
                                for country_name in country_list:
                                    for value_type_name in ["Annual", "Cumulative"]:
                                        series_info.append({
                                            "name": f"{country_name} {value_type_name}", 
                                            "country": country_name, 
                                            "segment": seg, 
                                            "value_type": value_type_name.lower()
                                        })
                                title = f"Annual & Cumulative {seg} Capacity Development - Top {len(country_list)} Countries"
                            else:
                                series_info = []
                                for value_type_name in ["Annual", "Cumulative"]:
                                    series_info.append({
                                        "name": f"{c} {value_type_name}", 
                                        "country": c, 
                                        "segment": seg, 
                                        "value_type": value_type_name.lower()
                                    })
                                title = f"Annual & Cumulative {seg} Capacity Development in {c}"
                        else:
                            # Single value type series info and title
                            if is_multi_country:
                                series_info = []
                                for country_name in country_list:
                                    series_info.append({
                                        "name": f"{country_name} {seg}", 
                                        "country": country_name, 
                                        "segment": seg, 
                                        "value_type": vt
                                    })
                                title = f"{vt.title()} {seg} Capacity Trend - Top {len(country_list)} Countries"
                            else:
                                # Single country series info and title
                                series_info = [{"name": f"{c} {seg}", "country": c, "segment": seg, "value_type": vt}]
                                title = f"{vt.title()} {seg} Capacity Trend in {c}"
                        
                        result = MarketPlotDataResult(
                            plot_type="line",
                            title=title,
                            x_axis_label="",
                            y_axis_label="Capacity (MW)",
                            unit="MW",
                            data=data,
                            series_info=series_info,
                            success=True,
                        )
                        print(f"📊 ✅ SUCCESS: Created result with {len(data)} data points")

                    elif pt == "bar":
                        print(f"📊 Processing BAR plot...")
                        # total market bar per description (e.g., per year for one country)
                        
                        # ✅ FIX: Handle multi-country requests
                        if countries and countries.strip():
                            # Multi-country request (keep original case for special cases like UK, USA)
                            country_list = [c.strip() for c in countries.split(",") if c.strip()]
                            print(f"📊 Multi-country request: {country_list}")
                            is_multi_country = True
                        else:
                            # Single country request (keep original case)
                            c = (country or "China")
                            print(f"📊 Single country: {c}")
                            is_multi_country = False
                        
                        vt = (value_type or "annual").lower()  # Default to "annual" instead of "dual"
                        
                        # Override dual to annual for single-year multi-country comparisons
                        is_single_year = (
                            (year is not None and min_year is None and max_year is None) or
                            (min_year is not None and max_year is not None and min_year == max_year)
                        )
                        if vt == "dual" and is_single_year and is_multi_country:
                            print(f"📊 Override: Single-year multi-country comparison, using annual instead of dual")
                            vt = "annual"
                        
                        if vt == "dual":
                            print(f"📊 Value type: dual - showing both annual and cumulative")
                            show_dual = True
                        else:
                            show_dual = False
                            # New dataset only has capacity (annual capacity)
                            value_column = "capacity"
                            print(f"📊 Value type: {vt}, Column: {value_column}")
                        
                        # Initial filter by country and segment
                        if is_multi_country:
                            if seg == "Total":
                                # For Total segment, get actual Total data (not breakdown)
                                d = df[(df["country"].isin(country_list)) & (df["connection"] == "Total")]
                                print(f"📊 After multi-country+Total segment filter: {len(d)} rows")
                            elif seg in ["Distributed", "Centralised"]:
                                # For connection types, filter by connection and get Total segments/applications
                                d = df[(df["country"].isin(country_list)) & (df["connection"] == seg) & (df["segment"] == "Total") & (df["applications"] == "Total")]
                                print(f"📊 After multi-country+connection filter: {len(d)} rows")
                            else:
                                # For specific segment types (Ground-mounted, Residential, AgriPV, Floating PV, etc.), filter by segment
                                d = df[(df["country"].isin(country_list)) & (df["segment"] == seg) & (df["applications"] == "Total")]
                                print(f"📊 After multi-country+segment filter ({seg}): {len(d)} rows")
                        else:
                            if seg == "Total":
                                # For Total segment, get actual Total data (not breakdown)
                                d = df[(df["country"] == c) & (df["connection"] == "Total")]
                                print(f"📊 After country+Total segment filter: {len(d)} rows")
                            elif seg in ["Distributed", "Centralised"]:
                                # For connection types, filter by connection and get Total segments/applications
                                d = df[(df["country"] == c) & (df["connection"] == seg) & (df["segment"] == "Total") & (df["applications"] == "Total")]
                                print(f"📊 After country+connection filter: {len(d)} rows")
                            else:
                                # For specific segment types (Ground-mounted, Residential, AgriPV, Floating PV, etc.), filter by segment
                                d = df[(df["country"] == c) & (df["segment"] == seg) & (df["applications"] == "Total")]
                                print(f"📊 After country+segment filter ({seg}): {len(d)} rows")
                        
                        # ✅ FIX: Apply proper scenario filtering
                        d = _filter_scenario(d, year_col="year", scenario=scenario)
                        print(f"📊 After scenario filter: {len(d)} rows")
                        
                        if max_year is not None and max_year > 0:
                            d = d[d["year"] <= max_year]
                            print(f"📊 After max_year filter: {len(d)} rows")
                        if min_year is not None and min_year > 0:
                            d = d[d["year"] >= min_year]
                            print(f"📊 After min_year filter: {len(d)} rows")
                            
                        if d.empty:
                            error_result = MarketPlotDataResult(
                                plot_type="bar", title="No Data Found", x_axis_label="", y_axis_label="Capacity (MW)", unit=None, data=[], success=False, error_message="No data available"
                            )
                            set_plot_result(error_result)
                            self.last_market_plot_data_result = error_result  # Also cache in instance for fallback
                            return "plot generation failed"
                            
                        if show_dual:
                            # Dual value type - show both annual and cumulative
                            if is_multi_country:
                                # Check if it's a single year (country comparison) or multi-year (time series)
                                years_in_data = sorted(d['year'].unique())
                                is_single_year_comparison = len(years_in_data) == 1
                                
                                data = []
                                # New dataset only has capacity (annual), so we simulate cumulative by aggregating 
                                for value_type_name, column_name in [("Annual", "capacity")]:
                                    pivot = d.groupby(["year", "country"])[column_name].sum().reset_index()
                                    for _, row in pivot.iterrows():
                                        if is_single_year_comparison:
                                            # Single year: countries as categories (bars)
                                            data.append({
                                                "category": f"{row['country']}", 
                                                "series": f"{row['country']} {value_type_name}", 
                                                "value": float(row[column_name])
                                            })
                                        else:
                                            # Multi-year: years as categories, countries as series
                                            data.append({
                                                "category": int(row["year"]), 
                                                "series": f"{row['country']} {value_type_name}", 
                                                "value": float(row[column_name])
                                            })
                                print(f"📊 Multi-country dual pivot result: {len(data)} data points")
                            else:
                                # Single country dual processing
                                data = []
                                # New dataset only has capacity (annual), so we simulate cumulative by aggregating 
                                for value_type_name, column_name in [("Annual", "capacity")]:
                                    pivot = d.groupby("year")[column_name].sum().reset_index()
                                    country_name = c if not is_multi_country else country_list[0] if country_list else "Unknown"
                                    for _, row in pivot.iterrows():
                                        data.append({
                                            "category": int(row["year"]), 
                                            "series": f"{country_name} {value_type_name}", 
                                            "value": float(row[column_name])
                                        })
                                print(f"📊 Single country dual pivot result: {len(data)} data points")
                        else:
                            # Single value type processing
                            if is_multi_country:
                                # Check if it's a single year (country comparison) or multi-year (time series)
                                years_in_data = sorted(d['year'].unique())
                                is_single_year_comparison = len(years_in_data) == 1
                                
                                if is_single_year_comparison:
                                    # Single year multi-country: countries as categories (bars)
                                    pivot = d.groupby("country")[value_column].sum().reset_index()
                                    data = []
                                    for _, row in pivot.iterrows():
                                        data.append({
                                            "category": f"{row['country']}", 
                                            "series": f"{row['country']} {seg}", 
                                            "value": float(row[value_column])
                                        })
                                else:
                                    # Multi-year multi-country: years as categories, countries as series
                                    pivot = d.groupby(["year", "country"])[value_column].sum().reset_index()
                                    data = []
                                    for _, row in pivot.iterrows():
                                        data.append({
                                            "category": int(row["year"]), 
                                            "series": f"{row['country']} {seg}", 
                                            "value": float(row[value_column])
                                        })
                            else:
                                # Single country processing
                                pivot = d.groupby("year")[value_column].sum().reset_index()
                                # Use the single country name (c should be defined in single country path)
                                country_name = c if not is_multi_country else country_list[0] if country_list else "Unknown"
                                data = [
                                    {"category": int(row["year"]), "series": f"{country_name} {seg}", "value": float(row[value_column])}
                                    for _, row in pivot.iterrows()
                                ]
                        if show_dual:
                            # Dual value type series info and title
                            if is_multi_country:
                                series_info = []
                                for country_name in country_list:
                                    for value_type_name in ["Annual", "Cumulative"]:
                                        series_info.append({
                                            "name": f"{country_name} {value_type_name}", 
                                            "country": country_name, 
                                            "segment": seg, 
                                            "value_type": value_type_name.lower()
                                        })
                                title = f"Annual & Cumulative {seg} Market - Top {len(country_list)} Countries"
                            else:
                                series_info = []
                                for value_type_name in ["Annual", "Cumulative"]:
                                    series_info.append({
                                        "name": f"{c} {value_type_name}", 
                                        "country": c, 
                                        "segment": seg, 
                                        "value_type": value_type_name.lower()
                                    })
                                title = f"Annual & Cumulative {seg} Market in {c}"
                        else:
                            # Single value type series info and title
                            if is_multi_country:
                                series_info = []
                                for country_name in country_list:
                                    series_info.append({
                                        "name": f"{country_name} {seg}", 
                                        "country": country_name, 
                                        "segment": seg, 
                                        "value_type": vt
                                    })
                                title = f"{vt.title()} {seg} Market - Top {len(country_list)} Countries"
                            else:
                                # Single country series info and title
                                series_info = [{"name": f"{c} {seg}", "country": c, "segment": seg, "value_type": vt}]
                                title = f"{vt.title()} {seg} Market in {c}"
                        
                        # Set appropriate x-axis label based on chart type
                        if is_multi_country:
                            # Check if single year comparison or multi-year trend
                            years_in_data = sorted(d['year'].unique()) if len(d) > 0 else []
                            is_single_year_comparison = len(years_in_data) == 1
                            x_axis_label = "country" if is_single_year_comparison else ""
                        else:
                            x_axis_label = ""
                        
                        result = MarketPlotDataResult(
                            plot_type="bar",
                            title=title,
                            x_axis_label=x_axis_label,
                            y_axis_label="Capacity (MW)",
                            unit="MW",
                            data=data,
                            series_info=series_info,
                        )

                    elif pt == "pie":
                        # Get user query from request context (async) or self (sync fallback)
                        user_query_for_pie = get_user_query() or getattr(self, "last_user_query", "")
                        result = self._generate_pie_plot(
                            df=df,
                            country=country,
                            segment=segment,
                            year=year,
                            max_year=max_year,
                            scenario=scenario,
                            user_query=user_query_for_pie
                        )

                    elif pt == "stacked":
                        # Get user query from request context (async) or self (sync fallback)
                        user_query_for_stacked = get_user_query() or getattr(self, "last_user_query", "")
                        result = self._generate_stacked_plot(
                            df=df,
                            country=country,
                            segment=segment,
                            value_type=value_type,
                            scenarios=scenarios,
                            scenario=scenario,
                            min_year=min_year,
                            max_year=max_year,
                            duration=duration,
                            user_query=user_query_for_stacked
                        )

                    elif pt == "yoy":
                        result = self._generate_yoy_plot(
                            df=df,
                            country=country,
                            segment=segment,
                            value_type=value_type,
                            scenario=scenario,
                            min_year=min_year,
                            max_year=max_year
                        )

                    elif pt == "multi_scenario":
                        result = self._generate_multi_scenario_plot(
                            df=df,
                            country=country,
                            segment=segment,
                            value_type=value_type,
                            scenarios=scenarios,
                            min_year=min_year,
                            max_year=max_year
                        )

                    elif pt == "country_comparison" or pt == "multi_country":
                        result = self._generate_country_comparison_plot(
                            df=df,
                            country=country,
                            countries=countries,
                            segment=segment,
                            value_type=value_type,
                            scenario=scenario,
                            min_year=min_year,
                            max_year=max_year
                        )

                    # If nothing matched or result stayed None
                    if result is None:
                        print(f"📊 ❌ No matching plot type: {pt}")
                        error_result = MarketPlotDataResult(
                            plot_type="bar",
                            title="Invalid Plot Type",
                            x_axis_label="",
                            y_axis_label="",
                            unit=None,
                            data=[],
                            success=False,
                            error_message=f"Unsupported plot type: {pt}"
                        )
                        set_plot_result(error_result)
                        self.last_market_plot_data_result = error_result  # Also cache in instance for fallback
                        return "plot generation failed"

                    # Cache and return stub (using request context AND instance variable)
                    set_plot_result(result)
                    self.last_market_plot_data_result = result  # Also cache in instance for fallback
                    print(f"📊 ✅ Success! Cached {result.plot_type} plot with {len(result.data) if result.data else 0} data points")
                    return "plot generated successfully"
                    
                except Exception as e:
                    print(f"📊 ❌ ERROR: {e}")
                    logger.error(f"get_market_plot_data_output failed: {e}")
                    import traceback
                    print(f"📊 ❌ TRACEBACK: {traceback.format_exc()}")
                    error_result = MarketPlotDataResult(
                        plot_type="bar",
                        title="Error",
                        x_axis_label="",
                        y_axis_label="",
                        unit=None,
                        data=[],
                        success=False,
                        error_message=f"Plot generation error: {str(e)}"
                    )
                    set_plot_result(error_result)
                    self.last_market_plot_data_result = error_result  # Also cache in instance for fallback
                    return "plot generation failed"

            # Define analyze_market_data tool before creating the agent
            async def analyze_market_data_tool(ctx: RunContext[None], query: str):
                # Import request context for thread-safe state management
                from request_context import set_dataframe

                try:
                    logger.info(f"Executing market data query: {query}")
                    
                    # Enhanced query with SQL best practices guidance and temporal context
                    from datetime import datetime
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    current_year = datetime.now().year

                    enhanced_query = f"""
🚨 CRITICAL INSTRUCTION: DO NOT SUM, AGGREGATE, OR TOTAL ANY VALUES! 🚨
- Return the raw DataFrame as-is, without any calculations
- Do NOT use .sum(), .total(), .aggregate(), or mathematical operations
- The user will analyze the returned data themselves
- NEVER calculate totals even if the user asks for "total capacity"

⚠️ DATA STRUCTURE WARNING:
This dataset contains hierarchical breakdowns. For Canada 2024:
- Row 1: connection=Total, segment=Total, applications=Total (THIS IS THE ACTUAL TOTAL: 321 MW)
- Other rows: breakdowns by connection/segment/application (150, 0, 150, etc.)
- Summing all rows creates DOUBLE COUNTING: 321+150+0+150+... = WRONG!

✅ CORRECT BEHAVIOR:
- Return ALL matching rows without modification
- Let the user identify which row represents the total
- Do NOT perform any arithmetic operations

📅 TEMPORAL CONTEXT:
- Current date: {current_date}
- Current year: {current_year}
- DEFAULT YEAR: If user doesn't specify a year, default to 2024 (most recent complete year)
- For "current" or "latest" queries without year: use year = 2024
- For "recent" data without year: use year = 2024
- For historical trends: use multiple years as appropriate
- IMPORTANT: When no year is mentioned, assume user wants 2024 data

DATASET COLUMN VALUES (use these exact values in your queries):
- country: Algeria, Australia, Austria, Belgium, Bulgaria, Canada, China, Denmark, Egypt, France, Germany, India, Italy, Japan, Morocco, Netherlands, Poland, South Africa, Spain, Sudan, Sweden, Tunisia, UK, USA, etc.
- year: 1992, 1993, ..., 2024 (Historical), 2025, 2026, 2027, 2028, 2029, 2030 (Forecasts)
- scenario: "Historical", "Forecast - Most probable", "Forecast - High", "Forecast - Low"
- duration: "FY" (full year), "Q1", "Q2", "Q3", "Q4" (quarters)
- connection: "Total", "Distributed", "Centralised", "Off-grid"
- segment: "Total", "Residential", "Commercial & Industrial", "Ground-mounted", "AgriPV", "Floating PV"
- applications: "Total", "BAPV", "BIPV", "Commercial BAPV", "Industrial BAPV", "Residential BAPV"
- type: "Annual" (yearly additions), "Cumulative" (running totals)
- capacity: Numerical values in MW (megawatts)
- estimation_status: "Confirmed", "Estimated"
- install_action: "Installed"
- source: Data source references (e.g., "Snapshot", "IRENA", "OLD DB")
- comments: Free-text annotations and notes

CRITICAL FILTERING REQUIREMENTS:
🔹 ALWAYS include: duration = 'FY' AND install_action = 'Installed' (unless user specifically asks for quarterly or decommissioned data)
🔹 For annual additions: type = 'Annual'  
🔹 For cumulative totals: type = 'Cumulative'
🔹 Default to most recent data: Use Historical for past years, Most probable for future

QUERY EXAMPLES:
- For country data (no year specified): WHERE country = 'Canada' AND year = 2024 AND scenario = 'Historical' AND duration = 'FY' AND type = 'Annual' AND install_action = 'Installed'
- For "latest" or "current" data: WHERE country = 'Germany' AND year = 2024 AND scenario = 'Historical' AND duration = 'FY' AND type = 'Annual' AND install_action = 'Installed'
- For cumulative capacity: WHERE country = 'Germany' AND year = 2024 AND scenario = 'Historical' AND duration = 'FY' AND type = 'Cumulative' AND install_action = 'Installed'
- For forecasts: WHERE year >= 2025 AND scenario = 'Forecast - Most probable' AND duration = 'FY' AND type = 'Annual' AND install_action = 'Installed'
- For quarterly data: WHERE year = 2024 AND duration = 'Q1' AND type = 'Annual' AND install_action = 'Installed'
- For confirmed data only: Add AND estimation_status = 'Confirmed'
- DEFAULT when no year mentioned: Always include year = 2024 in the WHERE clause

USER QUERY: {query}"""
                    
                    response = self.market_data.chat(enhanced_query)
                    print(response)
                    df = None
                    if hasattr(response, 'value') and isinstance(response.value, pd.DataFrame):
                        df = response.value
                    elif isinstance(response, pd.DataFrame):
                        df = response
                    
                    if df is not None and not df.empty:
                        # Cache for both sync and async modes
                        set_dataframe(df)  # For async mode (request context)
                        self.last_dataframe = df  # For sync mode (instance variable)

                        # Reorder columns for better display (most important first)
                        preferred_order = ['country', 'year', 'scenario', 'duration', 'connection', 'segment', 'applications', 'type', 'capacity', 'estimation_status', 'install_action', 'source', 'comments']
                        # Only use columns that exist in the DataFrame
                        display_columns = [col for col in preferred_order if col in df.columns]
                        # Add any remaining columns not in the preferred list
                        remaining_columns = [col for col in df.columns if col not in display_columns]
                        final_column_order = display_columns + remaining_columns

                        # Reorder and prepare table data for the UI (limit to 50 rows for display)
                        df_reordered = df[final_column_order]
                        display_df = df_reordered.head(50) if len(df_reordered) > 50 else df_reordered
                        table_data = display_df.to_dict(orient='records')

                        # Build detailed summary for agent with first 5 rows and column statistics
                        summary_parts = []

                        # Header with record count
                        summary_parts.append(f"Found {len(df)} records.\n")

                        # First 5 rows as a preview table (for agent to see, but not displayed in UI)
                        summary_parts.append("PREVIEW (first 5 rows):")
                        preview_df = df.head(5)
                        summary_parts.append(preview_df.to_string(index=False))
                        summary_parts.append("")  # Empty line

                        # Column statistics
                        summary_parts.append("COLUMN SUMMARY:")

                        for col in df.columns:
                            if col == 'capacity':
                                # For capacity: show min, max (no total due to hierarchical data structure)
                                try:
                                    min_cap = df[col].min()
                                    max_cap = df[col].max()
                                    if max_cap > 1000:
                                        summary_parts.append(f"  - {col}: ranges from {min_cap:.1f} MW to {max_cap/1000:.1f} GW (hierarchical data - contains totals and breakdowns)")
                                    else:
                                        summary_parts.append(f"  - {col}: ranges from {min_cap:.1f} MW to {max_cap:.1f} MW (hierarchical data - contains totals and breakdowns)")
                                except Exception:
                                    summary_parts.append(f"  - {col}: [numeric data]")
                            else:
                                # For other columns: show unique values
                                try:
                                    unique_vals = df[col].dropna().unique()
                                    if len(unique_vals) <= 5:
                                        # Show all values if 5 or fewer
                                        summary_parts.append(f"  - {col}: {', '.join(map(str, unique_vals))}")
                                    else:
                                        # Show count if more than 5
                                        summary_parts.append(f"  - {col}: {len(unique_vals)} unique values ({', '.join(map(str, unique_vals[:3]))}...)")
                                except Exception:
                                    summary_parts.append(f"  - {col}: [data available]")

                        summary_text = "\n".join(summary_parts)

                        # Return detailed summary - the fallback will create DataAnalysisResult from cached df
                        return summary_text
                        
                    elif response is None:
                        return "No data found for your query."
                    elif hasattr(response, 'empty') and response.empty:
                        return "No data found for your query."
                    elif hasattr(response, 'to_string'):
                        return response.to_string()
                    else:
                        return str(response)
                except Exception as e:
                    error_msg = f"Error analyzing market data: {str(e)}"
                    logger.error(error_msg)
                    return error_msg

            # === Create Main Agent ===
            self.data_analysis_agent = Agent(
                model="openai:gpt-4.1",
                output_type=[MarketPlotDataResult, str],
                tools=[extract_plot_parameters, get_market_plot_data_output, analyze_market_data_tool],
                system_prompt=(
                    "You are a helpful PV (photovoltaic) market analysis assistant.\n\n"
                    "**IMPORTANT:** When `analyze_market_data_tool` returns large datasets, the user sees the FULL TABLE but only a SUMMARY is stored in your memory. When answering follow-up questions about that data, you MUST re-run `analyze_market_data_tool` to get accurate values - NEVER answer based on the summary alone.\n\n"
                    "**TOOL USAGE DECISION:**\n"
                    "- **DATA ANALYSIS REQUESTS:** Use `analyze_market_data_tool` for questions like 'top 5 countries', 'which country has the highest', 'compare countries', 'what are the trends', 'show me the data for'\n"
                    "  - The tool returns a DataAnalysisResult object with table data\n"
                    "- **VISUALIZATION REQUESTS:** Use plotting tools for requests like 'create a chart', 'plot this data', 'show me a graph', 'visualize', 'bar chart', 'line chart', 'pie chart'\n"
                    "- **PLOTTING WORKFLOW:** For visualization requests:\n"
                    "  1. First call `extract_plot_parameters` to get structured parameters\n"
                    "  2. Then call `get_market_plot_data_output` using ALL extracted parameters (including duration and type)\n"
                    "  3. Reply with EXACTLY: \"plot generated successfully\"\n"
                    "- **PARAMETER MAPPING:** When calling `get_market_plot_data_output`, use extracted parameters:\n"
                    "  - duration: Use extracted duration value (FY, Q1, Q2, Q3, Q4)\n"
                    "  - type: Use extracted type value (Annual, Cumulative)\n"
                    "  - All other parameters: plot_type, country, segment, value_type, etc.\n"
                    "- **EXAMPLES:** If extract_plot_parameters returns duration='FY' and type='Cumulative', then call:\n"
                    "  get_market_plot_data_output(plot_type='line', country='Belgium', duration='FY', type='Cumulative', ...)\n"
                    "- **MULTI-COUNTRY PLOTTING:** For multiple countries, call `get_market_plot_data_output` ONCE with countries='Germany, Spain, Italy, France, Netherlands' - DO NOT make 5 separate calls\n"
                    "- **GREETINGS:** Return string directly for greetings\n\n"
                    "**CRITICAL RULES:**\n"
                    "- **DATA ANALYSIS FIRST:** If user asks for data insights, rankings, comparisons, or trends, use `analyze_market_data_tool`\n"
                    "- **RETURN DATA OBJECTS:** When `analyze_market_data_tool` returns a DataAnalysisResult object, DIRECTLY RETURN it - the frontend will render it as an interactive table\n"
                    "- **PLOTTING SECOND:** Only use plotting tools when user explicitly requests charts/graphs/visualizations\n"
                    "- **NO TEXT SUMMARIES:** Never return plain text when plots are generated\n"
                    "- **SINGLE PLOT CALL:** Use ONE `get_market_plot_data_output` call per request, even for multiple countries\n\n"
                    "**DATA SOURCE:**\n"
                    "- When users ask about data sources or where the data comes from, ALWAYS respond: \"All data comes from the DataHub of the Becquerel Institute\"\n"
                    "- Never mention other sources or datasets - all market data is exclusively from the Becquerel Institute's DataHub\n"
                ),
            )

            # Tools are now registered via the tools parameter above

            logger.info("Pydantic-AI agent with nested plot generation and conversation memory setup complete")
        except Exception as e:
            logger.error(f"Failed to setup Pydantic-AI agent: {e}")
            self.data_analysis_agent = None
    
    def process_query(self, user_message: str, conversation_id: str = None):
        """
        Synchronous wrapper for process_query_async.

        ✅ IMPROVED: Uses asyncio.run() properly instead of creating manual event loops.
        This is the recommended approach for sync-to-async bridges in Python 3.7+.

        For async callers (like async Flask routes), use process_query_async() directly instead.

        Args:
            user_message: User's query
            conversation_id: Optional conversation ID for memory

        Returns:
            Pydantic AI result object with response
        """
        print(f"🔄 Sync wrapper called - delegating to async implementation")

        try:
            # ✅ Use asyncio.run() - the proper way to run async from sync code
            # This creates and cleans up the event loop automatically
            return asyncio.run(self.process_query_async(user_message, conversation_id))
        except Exception as e:
            print(f"❌ ERROR in sync wrapper: {str(e)}")
            logger.error(f"Error in sync wrapper: {e}")
            return f"An error occurred while processing your query: {str(e)}"

    async def process_query_async(self, user_message: str, conversation_id: str = None):
        """
        🚀 Async version of process_query - Non-blocking, supports concurrent users

        This is the NEW async implementation that eliminates blocking behavior.
        Uses request-scoped context to prevent race conditions.

        Args:
            user_message: User's query
            conversation_id: Optional conversation ID for memory

        Returns:
            Pydantic AI result object with response
        """
        # Import request context
        from request_context import RequestContext, set_current_context, clear_current_context

        # Logfire span for async agent call
        with logfire.span("pydantic_weaviate_agent_async_call") as agent_span:
            agent_span.set_attribute("agent_type", "pydantic_weaviate_async")
            agent_span.set_attribute("conversation_id", str(conversation_id))
            agent_span.set_attribute("message_length", len(user_message))
            agent_span.set_attribute("user_message", user_message)

        try:
            print(f"\n🚀 ASYNC USER QUERY RECEIVED: '{user_message}'")
            print(f"💬 Conversation ID: {conversation_id}")
            print(f"🔍 ASYNC AGENT INSTANCE: {id(self)} | Total conversations: {len(self.conversation_memory)}")
            logger.info(f"Processing async query: {user_message} (conversation_id: {conversation_id})")

            # Create isolated request context for this request
            ctx = RequestContext(
                conversation_id=conversation_id or "default",
                user_query=user_message
            )
            set_current_context(ctx)

            if not self.data_analysis_agent:
                print(f"❌ ERROR: Agent not properly initialized")
                agent_span.set_attribute("success", False)
                agent_span.set_attribute("error", "Agent not properly initialized")
                clear_current_context()
                return "Agent not properly initialized. Please check your configuration."

            # Get conversation history (thread-safe read)
            message_history: List[ModelMessage] = []
            if conversation_id:
                async with self.memory_lock:
                    if conversation_id in self.conversation_memory:
                        # Found in worker's memory cache
                        message_history = self.conversation_memory[conversation_id].copy()
                        print(f"🧠 Using cached conversation memory: {len(message_history)} previous messages")
                        logger.info(f"Using cached conversation memory for {conversation_id} with {len(message_history)} previous messages")
                        agent_span.set_attribute("memory_messages", len(message_history))
                        agent_span.set_attribute("memory_source", "cache")
                    else:
                        # Not in cache - different worker handling request
                        # Note: Database stores simple message history for UI display, but LLM context
                        # cannot be easily reconstructed from DB (contains tool calls, function results, etc.)
                        print(f"ℹ️  Conversation not in this worker's cache - starting with fresh LLM context")
                        print(f"   (User's conversation history from database is still shown in the UI)")
                        logger.info(f"Conversation {conversation_id} not cached in worker {id(self)} - fresh LLM context")
                        agent_span.set_attribute("memory_messages", 0)
                        agent_span.set_attribute("memory_source", "fresh_worker")

            if not message_history and not conversation_id:
                # Only print if no conversation_id was provided (truly fresh)
                print(f"🆕 Starting fresh conversation (no memory)")
                agent_span.set_attribute("memory_messages", 0)
                agent_span.set_attribute("memory_source", "none")

            print(f"🤖 Executing Pydantic-AI agent (async)...")

            # ✅ Direct await - No blocking! Thread is released while waiting for LLM
            try:
                print(f"   🔄 Starting async agent.run...")

                # Retry logic with exponential backoff for rate limits
                max_retries = 3
                retry_count = 0
                result = None

                while retry_count <= max_retries:
                    try:
                        # ✅ Await directly - non-blocking
                        result = await self.data_analysis_agent.run(
                            user_message,
                            message_history=message_history,
                            usage_limits=UsageLimits(request_limit=10, total_tokens_limit=20000),
                        )
                        print(f"   ✅ Async agent.run completed successfully")
                        break  # Success, exit retry loop

                    except Exception as e:
                        error_str = str(e)
                        # Check if it's a rate limit error (429)
                        if "rate_limit" in error_str.lower() or "429" in error_str:
                            retry_count += 1
                            if retry_count <= max_retries:
                                # Exponential backoff: 2^retry * 1 second
                                wait_time = (2 ** retry_count) * 1
                                print(f"   ⚠️ Rate limit hit (attempt {retry_count}/{max_retries}). Retrying in {wait_time}s...")
                                logger.warning(f"Rate limit error, retrying in {wait_time}s (attempt {retry_count}/{max_retries})")
                                await asyncio.sleep(wait_time)  # ✅ Async sleep
                            else:
                                print(f"   ❌ Max retries reached. Rate limit persists.")
                                raise  # Re-raise after max retries
                        else:
                            # Not a rate limit error, raise immediately
                            raise

            except UsageLimitExceeded as usage_error:
                print(f"   ⚠️ Usage limit exceeded: {str(usage_error)}")
                logger.warning(f"Usage limit exceeded for conversation {conversation_id}: {usage_error}")
                agent_span.set_attribute("usage_limit_exceeded", True)

                # Return user-friendly message about usage limits
                return (
                    "I've reached my processing capacity for this conversation. "
                    "This helps ensure fair usage across all users. "
                    "Your conversation memory has been preserved, but please start a new conversation to continue."
                )

            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    print(f"   🔄 Rate limit error detected - clearing memory and suggesting retry")
                    # Clear memory for this conversation (thread-safe)
                    if conversation_id:
                        async with self.memory_lock:
                            if conversation_id in self.conversation_memory:
                                del self.conversation_memory[conversation_id]

                    clear_current_context()
                    return (
                        "I'm experiencing high demand right now. "
                        "Please try your request again in a moment. "
                        "Your conversation has been reset to free up capacity."
                    )
                else:
                    print(f"   ❌ Agent execution failed: {str(e)}")
                    logger.error(f"Agent execution error: {e}")
                    agent_span.set_attribute("success", False)
                    agent_span.set_attribute("error", str(e))
                    clear_current_context()
                    raise

            if not result:
                print(f"❌ ERROR: No result from agent")
                agent_span.set_attribute("success", False)
                clear_current_context()
                return "An error occurred - no result from agent."

            print(f"   ✅ Agent returned result: {type(result)}")

            # Process the result using request context
            if isinstance(getattr(result, 'output', None), str):
                # Check for plot responses first
                if "plot generated successfully" in result.output.lower() and ctx.plot_result:
                    # Replace text response with cached plot data from context
                    print(f"🔄 Replacing text response with cached plot data from context")
                    result.output = ctx.plot_result
                elif "plot generation failed" in result.output.lower():
                    result.output = "Error: interactive plot generation failed (no matching data). Please adjust parameters."
                # Check for DataFrame responses - fallback if tool returned data but agent wrote text
                elif ctx.dataframe is not None and not ctx.dataframe.empty:
                    print(f"🔄 Agent returned string but DataFrame is cached in context - creating DataAnalysisResult")

                    # Reorder columns for better display (same as in tool)
                    preferred_order = ['country', 'year', 'scenario', 'duration', 'connection', 'segment', 'applications', 'type', 'capacity', 'estimation_status', 'install_action', 'source', 'comments']
                    display_columns = [col for col in preferred_order if col in ctx.dataframe.columns]
                    remaining_columns = [col for col in ctx.dataframe.columns if col not in display_columns]
                    final_column_order = display_columns + remaining_columns

                    df_reordered = ctx.dataframe[final_column_order]
                    display_df = df_reordered.head(50) if len(df_reordered) > 50 else df_reordered
                    table_data = display_df.to_dict(orient='records')

                    # Strip out PREVIEW section from UI display (keep for agent memory)
                    user_facing_content = result.output
                    if "PREVIEW (first 5 rows):" in user_facing_content:
                        # Extract parts before and after preview
                        parts = user_facing_content.split("PREVIEW (first 5 rows):")
                        if len(parts) == 2:
                            before_preview = parts[0].strip()
                            after_preview_parts = parts[1].split("COLUMN SUMMARY:")
                            if len(after_preview_parts) >= 2:
                                # Reconstruct without the preview table
                                user_facing_content = before_preview + "\n\nCOLUMN SUMMARY:" + after_preview_parts[1]

                    # Use agent's text as the content/summary (preview stripped for UI)
                    result.output = DataAnalysisResult(
                        result_type="dataframe",
                        content=user_facing_content,
                        dataframe_data=table_data
                    )

            # Store the new messages for future conversation context (thread-safe write)
            if conversation_id:
                # Get all messages from the result
                all_messages = result.all_messages()

                # Apply memory filter to reduce token usage
                print(f"🧹 Filtering conversation memory for {conversation_id}...")
                filtered_messages = filter_large_tool_returns(all_messages, max_content_length=500)

                # Store filtered messages (thread-safe)
                async with self.memory_lock:
                    self.conversation_memory[conversation_id] = filtered_messages
                    logger.info(f"Updated async conversation memory for {conversation_id} (original: {len(all_messages)} msgs, filtered: {len(filtered_messages)} msgs)")

                # Dump memory to file for inspection
                self._dump_memory_to_file(conversation_id, filtered_messages)

            # Clear request context
            clear_current_context()

            # Return the structured result object
            return result

        except Exception as e:
            print(f"❌ ERROR in async process_query: {str(e)}")
            logger.error(f"Error in async process_query: {e}")
            agent_span.set_attribute("success", False)
            agent_span.set_attribute("error", str(e))
            clear_current_context()
            return f"An error occurred while processing your query: {str(e)}"

    def clear_conversation_memory(self, conversation_id: str = None):
        """Clear conversation memory for a specific conversation or all conversations"""
        if conversation_id:
            if conversation_id in self.conversation_memory:
                del self.conversation_memory[conversation_id]
                logger.info(f"Cleared conversation memory for {conversation_id}")
        else:
            self.conversation_memory.clear()
            logger.info("Cleared all conversation memory")

        # Reset last query context as well
        self._last_query_context = None

    def _dump_memory_to_file(self, conversation_id: str, messages: List[ModelMessage]):
        """Dump conversation memory to a text file for inspection"""
        try:
            from datetime import datetime
            import os

            # Create memory_dumps directory if it doesn't exist
            dump_dir = "memory_dumps"
            os.makedirs(dump_dir, exist_ok=True)

            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{dump_dir}/memory_{conversation_id}_{timestamp}.txt"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"=" * 80 + "\n")
                f.write(f"CONVERSATION MEMORY DUMP\n")
                f.write(f"Conversation ID: {conversation_id}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Total Messages: {len(messages)}\n")
                f.write(f"=" * 80 + "\n\n")

                # Analyze memory usage
                total_chars = 0
                message_types = {}

                for idx, msg in enumerate(messages, 1):
                    msg_type = type(msg).__name__
                    message_types[msg_type] = message_types.get(msg_type, 0) + 1

                    f.write(f"\n{'=' * 80}\n")
                    f.write(f"MESSAGE #{idx}\n")
                    f.write(f"Type: {msg_type}\n")
                    f.write(f"{'-' * 80}\n")

                    # Process message parts
                    if hasattr(msg, 'parts'):
                        for part_idx, part in enumerate(msg.parts, 1):
                            part_type = part.__class__.__name__
                            f.write(f"\n  Part {part_idx}: {part_type}\n")
                            f.write(f"  {'-' * 76}\n")

                            # Extract content based on part type
                            if hasattr(part, 'content'):
                                content = str(getattr(part, 'content', ''))
                                content_length = len(content)
                                total_chars += content_length

                                # Show first 500 chars and last 100 chars for long content
                                if content_length > 600:
                                    preview = content[:500] + f"\n\n  ... [{content_length - 600} chars omitted] ...\n\n" + content[-100:]
                                else:
                                    preview = content

                                f.write(f"  Content ({content_length} chars, ~{content_length // 4} tokens):\n")
                                f.write(f"  {preview}\n")

                            # Show tool name for tool-related parts
                            if hasattr(part, 'tool_name'):
                                f.write(f"  Tool: {getattr(part, 'tool_name', 'N/A')}\n")

                            # Show args for tool calls
                            if hasattr(part, 'args'):
                                args = getattr(part, 'args', {})
                                f.write(f"  Args: {args}\n")

                    else:
                        # Messages without parts
                        f.write(f"  (No parts available)\n")
                        f.write(f"  Raw: {str(msg)[:500]}\n")

                # Write summary
                f.write(f"\n\n{'=' * 80}\n")
                f.write(f"SUMMARY\n")
                f.write(f"{'=' * 80}\n")
                f.write(f"Total Messages: {len(messages)}\n")
                f.write(f"Total Characters: {total_chars:,}\n")
                f.write(f"Estimated Tokens: ~{total_chars // 4:,}\n\n")
                f.write(f"Message Type Distribution:\n")
                for msg_type, count in message_types.items():
                    f.write(f"  - {msg_type}: {count}\n")

            print(f"   💾 Memory dump saved to: {filename}")
            logger.info(f"Conversation memory dumped to {filename}")

        except Exception as e:
            print(f"   ⚠️ Failed to dump memory to file: {e}")
            logger.error(f"Failed to dump memory: {e}")

    def get_conversation_memory_info(self) -> Dict[str, Any]:
        """Get information about conversation memory usage"""
        return {
            "active_conversations": len(self.conversation_memory),
            "conversation_ids": list(self.conversation_memory.keys()),
            "memory_usage": {conv_id: len(messages) for conv_id, messages in self.conversation_memory.items()}
        }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent status"""
        memory_info = self.get_conversation_memory_info()
        return {
            "agent_type": "pydantic_market",
            "pandasai_connected": self.market_data is not None,
            "pydantic_agent_available": self.data_analysis_agent is not None,
            "conversation_memory_enabled": True,
            "active_conversations": memory_info["active_conversations"],
            "status": "ready" if self.data_analysis_agent else "error"
        }
    
    def close(self):
        """Close connections and clear memory"""
        # Clear conversation memory
        self.clear_conversation_memory()
        
        # Clean up any pending asyncio tasks
        try:
            loop = asyncio.get_event_loop()
            if loop and not loop.is_closed():
                pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
                if pending_tasks:
                    for task in pending_tasks:
                        task.cancel()
                    logger.info(f"Cancelled {len(pending_tasks)} pending asyncio tasks")
        except Exception as e:
            logger.debug(f"Asyncio cleanup note: {e}")

# Global instance
pydantic_weaviate_agent_instance = None

def get_pydantic_weaviate_agent() -> Optional[PydanticWeaviateAgent]:
    """Get or create the global Pydantic Weaviate agent instance"""
    global pydantic_weaviate_agent_instance
    if pydantic_weaviate_agent_instance is None:
        pydantic_weaviate_agent_instance = PydanticWeaviateAgent()
    return pydantic_weaviate_agent_instance

def close_pydantic_weaviate_agent():
    """Close the global Pydantic Weaviate agent instance"""
    global pydantic_weaviate_agent_instance
    if pydantic_weaviate_agent_instance: 
        pydantic_weaviate_agent_instance.close()
        pydantic_weaviate_agent_instance = None 

"""Legacy helpers removed: timeout-runner and matplotlib cleanup."""