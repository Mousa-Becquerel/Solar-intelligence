from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic import BaseModel
from pydantic_ai import ToolOutput
import os, json, uuid
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any, List, Literal
import asyncio
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web apps
import matplotlib.pyplot as plt
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ValidationError
import sys
import gc
import psutil
import pandasai as pai
from pandasai_litellm.litellm import LiteLLM

# === Canonical scenario Enum =================================================
class ScenarioName(str, Enum):
    HISTORICAL = "Historical"
    MOST_PROBABLE = "Most Probable"
    HIGH = "High"
    LOW = "Low"

# Canonical market-segment Enum
class SegmentName(str, Enum):
    TOTAL = "Total"
    DISTRIBUTED = "Distributed"
    CENTRALISED = "Centralised"

# Strict data class for scenario extraction (future use) -----------------------
class ScenarioRequest(BaseModel):
    country: str
    scenarios: Literal["All"] | list[ScenarioName] = "All"
    max_year: int | None = None
    value_type: Literal["cumulative", "annual"] = "cumulative"
    segment: SegmentName = SegmentName.TOTAL

# Helper to convert raw scenario strings to validated Enum list ---------------

def _to_enum_scenario_list(raw: list[str] | None):
    if not raw:
        return "All"

    mapped: list[ScenarioName] = []
    for s in raw:
        norm = _normalize_scenario(s)
        if norm == "All":
            return "All"                      # user explicitly asked for all
        if norm == "Most Probable":
            mapped.append(ScenarioName.MOST_PROBABLE)
        elif norm == "High":
            mapped.append(ScenarioName.HIGH)
        elif norm == "Low":
            mapped.append(ScenarioName.LOW)

    # If **nothing** mapped, treat the whole thing as "All"
    if not mapped:
        return "All"

    # remove duplicates
    return list(dict.fromkeys(mapped))

# === Becquerel Institute Color Palette ===
BI_COLORS = {
    "navy": "#001F5B",
    "gold": "#FDB813",
    "orange": "#F28E2B",
    "sky": "#7FB3D5",
}

# Apply global matplotlib style
plt.rcParams.update({
    "axes.edgecolor": "black",
    "axes.labelcolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "text.color": "black",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "grid.color": "#DDDDDD",
})
import re # Added for segment normalisation

# Default data file for plotting (BI_Market_Data.xlsx located alongside this module or in project root)
DEFAULT_DATA_FILE = os.path.join(os.getcwd(), "BI_Market_Data.xlsx")# Load .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Plotting helper (outside of the class so it can be reused) ===

# ---------------- Scenario filtering helper ---------------------------

def _filter_scenario(df: pd.DataFrame, year_col: str = "Year", scenario: str | None = None) -> pd.DataFrame:
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
        hist_mask = (df["Scenario"] == "Historical") & (df[year_col] <= 2024)
        # For forecast years, match scenario ignoring case and whitespace
        scen_mask = df[year_col] > 2024
        # Find all unique scenario values in the data for forecast years
        forecast_scenarios = df.loc[scen_mask, "Scenario"].dropna().unique()
        # Try to match normalized scenario to one of these
        match = None
        for s in forecast_scenarios:
            if _normalize_scenario(s) == scenario_norm:
                match = s
                break
        if match is None:
            # Fallback: just use scenario_norm as is
            match = scenario_norm
        scen_mask = (df["Scenario"] == match) & (df[year_col] > 2024)
        return df[hist_mask | scen_mask]

    hist_mask = (df["Scenario"] == "Historical") & (df[year_col] <= 2024)
    forecast_mask = (df["Scenario"].isin(["Most Probable", "Most Prob", "MostProb", "Most Prob."])) & (
        df[year_col] > 2024
    )
    return df[hist_mask | forecast_mask]

# ----------------------------------------------------------------------

def plot_market_share_per_segment(
    filepath: str | None,
    sheet: str,
    country: str,
    max_year: int,
    scenario: str | None = None,
    save_path: str | None = None,
    min_year: int | None = None,
):
    """Plots annual market share (Distributed vs Centralised) for a country up to max_year."""
    # Resolve filepath
    if not filepath:
        filepath = DEFAULT_DATA_FILE

    try:
        # Clean country name first (handles e.g. "France's")
        country = _sanitize_country(country)

        # Load data
        df = pd.read_excel(filepath, sheet_name=sheet)
        
        # Check if country exists in dataset
        available_countries = sorted(df['Country'].unique())
        if country not in available_countries:
            # Return error message with available countries
            countries_list = ", ".join(available_countries[:10])  # Show first 10 countries
            if len(available_countries) > 10:
                countries_list += f" and {len(available_countries) - 10} more"
            
            error_msg = (
                f"Sorry, '{country}' is not available in our dataset. "
                f"Our PV market data focuses primarily on European countries. "
                f"Available countries include: {countries_list}. "
                f"Please try one of these countries instead."
            )
            raise ValueError(error_msg)

        # Filter for selected country and appropriate scenario(s)
        df = df[df["Country"] == country]
        df = _filter_scenario(df, scenario=scenario)
        
        # Check if any data exists for this country
        if df.empty:
            raise ValueError(f"No historical data found for {country}")

        # Apply start/end year filters
        df_years = df[df['Year'] <= max_year]
        if min_year is not None:
            df_years = df_years[df_years['Year'] >= min_year]

        # Pivot table for required segments
        pivot_df = (
            df_years[df_years['Market Segment'].isin(['Distributed', 'Centralised'])]
            .pivot_table(index='Year', columns='Market Segment', values='Annual Market', aggfunc='sum')
            .fillna(0)
        )
        
        # Check if pivot table has data
        if pivot_df.empty:
            raise ValueError(f"No market segment data found for {country} up to {max_year}")

        # Calculate shares
        pivot_df['Total'] = pivot_df.sum(axis=1)
        
        # Avoid division by zero
        pivot_df['Distributed Share'] = pivot_df.apply(
            lambda row: (row['Distributed'] / row['Total'] * 100) if row['Total'] > 0 else 0, axis=1
        )
        pivot_df['Centralised Share'] = pivot_df.apply(
            lambda row: (row['Centralised'] / row['Total'] * 100) if row['Total'] > 0 else 0, axis=1
        )

        # Plot
        plt.figure(figsize=(10, 6), dpi=80)
        plt.bar(
            pivot_df.index,
            pivot_df['Distributed Share'],
            label='Distributed',
            color=BI_COLORS["gold"],
        )
        plt.bar(
            pivot_df.index,
            pivot_df['Centralised Share'],
            bottom=pivot_df['Distributed Share'],
            label='Centralised',
            color=BI_COLORS["navy"],
        )
        plt.title(f'Annual Market Share per Segment in {country} (Up to {max_year})')
        plt.ylabel('Market Share (%)')
        plt.xlabel('Year')
        # Add scenario info to legend if forecast years present
        import matplotlib.patches as mpatches
        has_forecast = pivot_df.index.max() > 2024
        if has_forecast:
            # Use actual scenario string from data for legend
            forecast_years = [y for y in pivot_df.index if y > 2024]
            scenario_label = None
            if not pivot_df.empty and forecast_years:
                # Find scenario in the original df for the first forecast year
                forecast_scenarios = df[(df['Year'] == forecast_years[0]) & (df['Country'] == country)]['Scenario'].unique()
                if len(forecast_scenarios) > 0:
                    scenario_label = forecast_scenarios[0]
            if not scenario_label:
                scenario_label = (scenario or 'Most Probable').title()
            dummy = mpatches.Patch(facecolor='none', edgecolor='none', label=f'{scenario_label} Scenario')
            handles, labels = plt.gca().get_legend_handles_labels()
            if dummy.get_label() not in labels:
                handles.append(dummy)
                labels.append(dummy.get_label())
                plt.legend(handles, labels)
        else:
            plt.legend()
        plt.tight_layout()

        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=80, bbox_inches="tight")
            plt.close()
            # Clean up memory after plot generation
            cleanup_plot_memory()
        else:
            plt.show()

        return save_path
        
    except ValueError as ve:
        # Pass through validation errors (like country not found) without wrapping
        plt.close('all')
        cleanup_plot_memory()
        raise ve
    except Exception as e:
        # Close any open matplotlib figures to prevent memory leaks
        plt.close('all')
        cleanup_plot_memory()
        # Re-raise other exceptions with context
        raise Exception(f"Error generating plot: {str(e)}")


def plot_capacity_pie(
    filepath: str | None,
    sheet: str,
    country: str,
    year: int,
    value_type: str,
    scenario: str | None = None,
    save_path: str | None = None,
):
    """Generate a pie chart of capacity share by segment for a single year.

    value_type: 'cumulative' or 'annual'
    scenario: optional scenario for forecast years (None uses default logic)
    """
    if not filepath:
        filepath = DEFAULT_DATA_FILE

    # Clean country name
    country = _sanitize_country(country)

    # Load data
    df = pd.read_excel(filepath, sheet_name=sheet)
    available_countries = sorted(df['Country'].unique())
    if country not in available_countries:
        raise ValueError(
            f"Sorry, '{country}' is not available in our dataset. "
            "Our PV market data focuses primarily on European countries. "
            f"Available examples include: {', '.join(available_countries[:10])}..."
        )

    # Determine column and title
    if value_type is None:
        value_type = "cumulative"
    value_type = value_type.lower()
    if value_type == "cumulative":
        value_column = "Cumulative Market"
        title_prefix = "Cumulative Installed Capacity"
    elif value_type == "annual":
        value_column = "Annual Market"
        title_prefix = "Annual Installed Capacity"
    else:
        raise ValueError("value_type must be either 'cumulative' or 'annual'")

    # Filter dataframe using scenario logic
    df_country = df[df['Country'] == country]
    df_scenario = _filter_scenario(df_country, scenario=scenario)
    df_filtered = df_scenario[
        (df_scenario['Year'] == year)
        & (df_scenario['Market Segment'].isin(['Distributed', 'Centralised']))
    ]

    if df_filtered.empty:
        raise ValueError(f"No {value_type} data found for {country} in {year}.")

    df_agg = df_filtered.groupby('Market Segment')[value_column].sum()

    # Clear any existing plots to prevent state issues
    plt.close('all')

    # Plot
    plt.figure(figsize=(6, 6), dpi=80)
    wedges, texts, autotexts = plt.pie(
        df_agg,
        labels=df_agg.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=[BI_COLORS["gold"], BI_COLORS["orange"]],
    )
    plt.title(
        f"{title_prefix} by Segment in {country} ({year})\nTotal: {df_agg.sum()/1000:.1f} GW"
    )
    # Scenario legend patch if forecast year
    if year > 2024:
        import matplotlib.patches as mpatches
        scenario_label = None
        forecast_scenarios = df_filtered['Scenario'].unique()
        if len(forecast_scenarios) > 0:
            scenario_label = forecast_scenarios[0]
        if not scenario_label:
            scenario_label = (scenario or 'Most Probable').title()
        dummy = mpatches.Patch(facecolor='none', edgecolor='none', label=f'{scenario_label} Scenario')
        plt.legend(handles=[dummy], loc='upper right')
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=80, bbox_inches="tight")
        plt.close()
        # Clean up memory after plot generation
        cleanup_plot_memory()
    else:
        plt.show()

    return save_path

# ------------- NEW HELPER: total market bar chart ----------------

def plot_total_market(
    filepath: str | None,
    sheet: str,
    country: str,
    value_type: str,
    segment: str = "Total",
    max_year: int | None = None,
    scenario: str | None = None,
    save_path: str | None = None,
    min_year: int | None = None,
):
    """Plot annual or cumulative total market size bar chart for a country."""
    if not filepath:
        filepath = DEFAULT_DATA_FILE

    # Clean country name
    country = _sanitize_country(country)

    # Load data
    df = pd.read_excel(filepath, sheet_name=sheet)
    available_countries = sorted(df['Country'].unique())
    if country not in available_countries:
        raise ValueError(
            f"Sorry, '{country}' is not available in our dataset. "
            "Our PV market data focuses primarily on European countries. "
            f"Available examples include: {', '.join(available_countries[:10])}..."
        )

    # Ensure value_type is not None and convert to lowercase
    if value_type is None:
        value_type = "cumulative"  # Default to cumulative if None
    value_type = value_type.lower()
    if value_type == "cumulative":
        value_column = "Cumulative Market"
        title_prefix = "Cumulative"
    elif value_type == "annual":
        value_column = "Annual Market"
        title_prefix = "Annual"
    else:
        raise ValueError("value_type must be either 'annual' or 'cumulative'")

    segment = segment.title()
    if segment not in ["Total", "Distributed", "Centralised"]:
        raise ValueError("segment must be 'Total', 'Distributed', or 'Centralised'")

    # Filter required rows
    df_total = df[
        (df['Country'] == country)
        & (df['Market Segment'] == segment)
    ]
    df_total = _filter_scenario(df_total, scenario=scenario)

    if max_year is not None:
        df_total = df_total[df_total['Year'] <= max_year]
    if min_year is not None:
        df_total = df_total[df_total['Year'] >= min_year]

    if df_total.empty:
        raise ValueError(f"No {value_type} total market data found for {country}.")

    df_total_grouped = df_total.groupby('Year')[value_column].sum().reset_index()

    # Plot
    plt.figure(figsize=(10, 6), dpi=80)
    plt.bar(df_total_grouped['Year'], df_total_grouped[value_column], color=BI_COLORS["gold"], label=segment)
    suffix = f" (Up to {max_year})" if max_year else ""
    plot_label = f"{title_prefix} {'Total' if segment=='Total' else segment} Market in {country}{suffix}"
    plt.title(plot_label)
    plt.ylabel('Market Size (MW)')
    plt.xlabel('Year')
    plt.grid(axis='y')
    # Scenario legend if forecast included
    has_forecast = df_total_grouped['Year'].max() > 2024
    if has_forecast:
        import matplotlib.patches as mpatches
        scenario_label = None
        forecast_years = df_total_grouped[df_total_grouped['Year'] > 2024]['Year']
        if not df_total.empty and not forecast_years.empty:
            # Find scenario in the original df for the first forecast year
            forecast_scenarios = df_total[(df_total['Year'] == forecast_years.iloc[0])]['Scenario'].unique()
            if len(forecast_scenarios) > 0:
                scenario_label = forecast_scenarios[0]
        if not scenario_label:
            scenario_label = (scenario or 'Most Probable').title()
        dummy = mpatches.Patch(facecolor='none', edgecolor='none', label=f'{scenario_label} Scenario')
        handles, labels = plt.gca().get_legend_handles_labels()
        if dummy.get_label() not in labels:
            handles.append(dummy)
            labels.append(dummy.get_label())
        plt.legend(handles, labels)
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=80, bbox_inches="tight")
        plt.close()
        # Clean up memory after plot generation
        cleanup_plot_memory()
    else:
        plt.show()

    return save_path

# ----------------- NEW HELPER: YoY growth line chart --------------

def plot_yoy_growth(
    filepath: str | None,
    sheet: str,
    country: str,
    segment: str = "Total",
    max_year: int | None = None,
    scenario: str | None = None,
    save_path: str | None = None,
    min_year: int | None = None,
):
    """Plot year-on-year growth (%) for a country/segment."""
    if not filepath:
        filepath = DEFAULT_DATA_FILE

    # Clean country name
    country = _sanitize_country(country)

    df = pd.read_excel(filepath, sheet_name=sheet)
    available_countries = sorted(df["Country"].unique())
    if country not in available_countries:
        raise ValueError(
            f"Sorry, '{country}' is not available in our dataset. "
            "Dataset focuses primarily on European countries."
        )

    segment = segment.title()  # normalise
    if segment not in ["Total", "Distributed", "Centralised"]:
        raise ValueError("segment must be 'Total', 'Distributed', or 'Centralised'")

    df_filtered = df[(df["Country"] == country) & (df["Market Segment"] == segment)]
    df_filtered = _filter_scenario(df_filtered, scenario=scenario)
    if max_year is not None:
        df_filtered = df_filtered[df_filtered["Year"] <= max_year]
    if min_year is not None:
        df_filtered = df_filtered[df_filtered["Year"] >= min_year]

    df_grouped = (
        df_filtered.groupby("Year")["Annual Market"].sum().reset_index()
    )
    df_grouped["YoY Growth (%)"] = df_grouped["Annual Market"].pct_change() * 100

    plt.figure(figsize=(10, 6), dpi=80)
    plt.plot(
        df_grouped["Year"],
        df_grouped["YoY Growth (%)"],
        marker="o",
        color=BI_COLORS["navy"],
        linewidth=1.5,
        label='YoY Growth',
    )
    plt.scatter(
        df_grouped["Year"],
        df_grouped["YoY Growth (%)"],
        color=BI_COLORS["gold"],
        zorder=5,
    )
    plt.axhline(0, color="gray", linestyle="--", linewidth=0.8)

    suffix = f" (Up to {max_year})" if max_year else ""
    plt.title(f"Year-on-Year Market Growth in {country} ({segment})" + suffix)
    plt.ylabel("Growth (%)")
    plt.xlabel("Year")
    plt.grid(True, linestyle="--", alpha=0.7)
    has_forecast = df_grouped["Year"].max() > 2024
    if has_forecast:
        import matplotlib.patches as mpatches
        scenario_label = None
        forecast_years = df_grouped[df_grouped['Year'] > 2024]['Year']
        if not df_filtered.empty and not forecast_years.empty:
            forecast_scenarios = df_filtered[(df_filtered['Year'] == forecast_years.iloc[0])]['Scenario'].unique()
            if len(forecast_scenarios) > 0:
                scenario_label = forecast_scenarios[0]
        if not scenario_label:
            scenario_label = (scenario or 'Most Probable').title()
        dummy = mpatches.Patch(facecolor='none', edgecolor='none', label=f'{scenario_label} Scenario')
        handles, labels = plt.gca().get_legend_handles_labels()
        if dummy.get_label() not in labels:
            handles.append(dummy)
            labels.append(dummy.get_label())
        plt.legend(handles, labels)
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=80, bbox_inches="tight")
        plt.close()
        # Clean up memory after plot generation
        cleanup_plot_memory()
    else:
        plt.show()

    return save_path

# ----------------- NEW HELPER: Country installation share donut ----

def plot_country_installation_share(
    filepath: str | None,
    sheet: str,
    year: int,
    countries: list[str] | None = None,
    scenario: str | None = None,
    save_path: str | None = None,
):
    """Donut chart of annual PV installations per country for a given year."""
    if not filepath:
        filepath = DEFAULT_DATA_FILE

    # Clean country name
    country = _sanitize_country(country)

    df = pd.read_excel(filepath, sheet_name=sheet)

    # Filter dataset
    df_year = df[(df['Market Segment'] == 'Total') & (df['Year'] == year)]
    if df_year.empty:
        raise ValueError(f"No total market data found for year {year}.")

    if countries:
        df_year = df_year[df_year['Country'].isin(countries)]
        df_grouped = df_year.groupby('Country')['Annual Market'].sum().sort_values(ascending=False)
        if df_grouped.empty:
            raise ValueError("Specified countries not found in dataset for this year.")
    else:
        df_grouped_all = df_year.groupby('Country')['Annual Market'].sum().sort_values(ascending=False)
        top_countries = df_grouped_all.head(6)
        rest = df_grouped_all[6:].sum()
        df_grouped = top_countries
        if rest > 0:
            df_grouped['Rest of Europe'] = rest

    total_gw = df_grouped.sum() / 1000  # convert to GW

    palette = [
        BI_COLORS["gold"],
        BI_COLORS["orange"],
        BI_COLORS["sky"],
        BI_COLORS["navy"],
        "#145DA0",
        "#FFB000",
        "#003f88",
    ]
    colors = palette[:len(df_grouped)]

    plt.figure(figsize=(8, 8), dpi=80)
    wedges, texts, autotexts = plt.pie(
        df_grouped,
        labels=df_grouped.index,
        autopct='%1.1f%%',
        startangle=90,
        wedgeprops=dict(width=0.4),
        colors=colors,
        pctdistance=0.85,
    )
    plt.text(0, 0, f"{total_gw:.1f} GW", ha='center', va='center', fontsize=18, fontweight='bold')
    plt.title(f"PV Capacity Installed in {year}", fontsize=14, fontweight='bold')
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=80, bbox_inches="tight")
        plt.close()
        # Clean up memory after plot generation
        cleanup_plot_memory()
    else:
        plt.show()

    return save_path

# ----------------- NEW HELPER: Capacity trend line chart -------------

def plot_capacity_trend(
    filepath: str | None,
    sheet: str,
    country: str,
    value_type: str = "cumulative",
    segment: str | None = None,
    max_year: int | None = None,
    scenario: str | None = None,
    save_path: str | None = None,
    min_year: int | None = None,
):
    """Plot annual or cumulative capacity trend line over years for a country/segment."""
    if not filepath:
        filepath = DEFAULT_DATA_FILE

    # Clean country name
    country = _sanitize_country(country)

    df = pd.read_excel(filepath, sheet_name=sheet)
    segment_norm = _normalize_segment(segment)
    value_type = (value_type or "cumulative").lower()
    if value_type == "cumulative":
        value_column = "Cumulative Market"
        title_prefix = "Cumulative"
    elif value_type == "annual":
        value_column = "Annual Market"
        title_prefix = "Annual"
    else:
        raise ValueError("value_type must be either 'annual' or 'cumulative'")

    df_filt = df[(df["Country"] == country) & (df["Market Segment"] == segment_norm)]
    df_filt = _filter_scenario(df_filt, scenario=scenario)
    if max_year is not None:
        df_filt = df_filt[df_filt["Year"] <= max_year]
    if min_year is not None:
        df_filt = df_filt[df_filt["Year"] >= min_year]

    if df_filt.empty:
        raise ValueError("No data found for given parameters")

    pivot = (
        df_filt.groupby("Year")[value_column]
        .sum()
        .reset_index()
    )

    plt.figure(figsize=(10, 6), dpi=80)
    plt.plot(
        pivot["Year"],
        pivot[value_column],
        marker="o",
        color=BI_COLORS["gold"],
        markerfacecolor="white",
        label=segment_norm,
    )
    plt.title(f"{title_prefix} {segment_norm} Capacity Trend in {country}")
    plt.ylabel("Capacity (MW)")
    plt.xlabel("Year")
    plt.grid(True, linestyle="--", alpha=0.7)
    has_forecast = pivot["Year"].max() > 2024
    if has_forecast:
        import matplotlib.patches as mpatches
        scenario_label = None
        forecast_years = pivot[pivot['Year'] > 2024]['Year']
        if not df_filt.empty and not forecast_years.empty:
            forecast_scenarios = df_filt[(df_filt['Year'] == forecast_years.iloc[0])]['Scenario'].unique()
            if len(forecast_scenarios) > 0:
                scenario_label = forecast_scenarios[0]
        if not scenario_label:
            scenario_label = (scenario or 'Most Probable').title()
        dummy = mpatches.Patch(facecolor='none', edgecolor='none', label=f'{scenario_label} Scenario')
        handles, labels = plt.gca().get_legend_handles_labels()
        if dummy.get_label() not in labels:
            handles.append(dummy)
            labels.append(dummy.get_label())
        plt.legend(handles, labels)
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=80, bbox_inches="tight")
        plt.close()
        # Clean up memory after plot generation
        cleanup_plot_memory()
    else:
        plt.show()

    return save_path

# ----------------- NEW HELPER: Multi-scenario capacity trend line chart -------------

def plot_multi_scenario_capacity_trend(
    filepath: str | None,
    sheet: str,
    country: str,
    value_type: str = "cumulative",
    segment: str | None = None,
    max_year: int | None = None,
    scenarios: list[str] | None = None,
    save_path: str | None = None,
    min_year: int | None = None,
):
    """Plot annual or cumulative capacity trend lines for multiple scenarios."""
    if not filepath:
        filepath = DEFAULT_DATA_FILE

    # Clean country name
    country = _sanitize_country(country)

    df = pd.read_excel(filepath, sheet_name=sheet)
    segment_norm = _normalize_segment(segment)
    value_type = (value_type or "cumulative").lower()
    if value_type == "cumulative":
        value_column = "Cumulative Market"
        title_prefix = "Cumulative"
    elif value_type == "annual":
        value_column = "Annual Market"
        title_prefix = "Annual"
    else:
        raise ValueError("value_type must be either 'annual' or 'cumulative'")

    df_filt = df[(df["Country"] == country) & (df["Market Segment"] == segment_norm)]
    df_filt = _filter_multiple_scenarios(df_filt, scenarios=scenarios)
    if max_year is not None:
        df_filt = df_filt[df_filt["Year"] <= max_year]
    if min_year is not None:
        df_filt = df_filt[df_filt["Year"] >= min_year]

    if df_filt.empty:
        raise ValueError("No data found for given parameters")

    # Group by Year and Scenario
    pivot = df_filt.groupby(["Year", "Scenario"])[value_column].sum().reset_index()
    
    # Define colors for different scenarios
    scenario_colors = {
        "Historical": BI_COLORS["navy"],
        "Most Probable": BI_COLORS["gold"],
        "High": BI_COLORS["orange"],
        "Low": BI_COLORS["sky"]
    }
    
    # Define line styles for different scenarios
    scenario_styles = {
        "Historical": "-",
        "Most Probable": "-",
        "High": "--",
        "Low": "-."
    }

    plt.figure(figsize=(12, 8), dpi=80)
    
    # Plot each scenario
    for scenario in pivot["Scenario"].unique():
        scenario_data = pivot[pivot["Scenario"] == scenario]
        color = scenario_colors.get(scenario, BI_COLORS["navy"])
        style = scenario_styles.get(scenario, "-")
        
        plt.plot(
            scenario_data["Year"],
            scenario_data[value_column],
            marker="o",
            color=color,
            linestyle=style,
            linewidth=2,
            markersize=6,
            label=scenario,
            markerfacecolor="white",
            markeredgecolor=color,
            markeredgewidth=2
        )

    plt.title(f"{title_prefix} {segment_norm} Capacity Projections in {country}\n(Multiple Scenarios)")
    plt.ylabel("Capacity (MW)")
    plt.xlabel("Year")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend(loc='upper left')
    
    # Add a vertical line at 2024 to separate historical from forecast
    if pivot["Year"].min() <= 2024 and pivot["Year"].max() > 2024:
        plt.axvline(x=2024.5, color='gray', linestyle=':', alpha=0.7, label='Historical/Forecast')
    
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=80, bbox_inches='tight')
        plt.close()
        # Clean up memory after plot generation
        cleanup_plot_memory()
    else:
        plt.show()

    return save_path

# ---------------- END HELPER -------------------------------------

# Utility to normalise segment synonyms -------------------------------------------------

def _normalize_segment(segment: str | None = None) -> str:
    """Convert common synonyms to official segment names."""
    if segment is None:
        return "Total"
    seg = segment.strip().lower()
    if seg in {"rooftop", "residential", "commercial", "small-scale", "small scale"}:
        return "Distributed"
    if seg in {"utility", "utility-scale", "utility scale", "large-scale", "large scale", "ground-mounted", "centralized", "centralised"}:
        return "Centralised"
    return segment.title()

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

    # Map to canonical names
    if s in {'most prob', 'most probable', 'mostprob', 'probable', 'prob', 'moderate', 'baseline', 'base', 'current', 'current policy', 'policy', 'average', 'average case'}:
        return 'Most Probable'
    if s in {'high', 'high prob', 'high probable', 'highgrowth', 'high growth', 'best case', 'best'}:
        return 'High'
    if s in {'low', 'low prob', 'low probable', 'lowgrowth', 'low growth', 'worst case', 'worst'}:
        return 'Low'
    if s in {'all', 'all the', 'multiple', 'three', 'different', 'compare', 'forecasting for all'}:
        return 'All'
    # If not matched, return title-case version to preserve original
    return scenario.title()

def _filter_multiple_scenarios(df: pd.DataFrame, year_col: str = "Year", scenarios: list[str] | None = None) -> pd.DataFrame:
    """Return dataframe filtered for multiple scenarios.
    
    If scenarios is None or contains 'All', return all forecast scenarios.
    Otherwise, filter for the specified scenarios.
    """
    if not scenarios or 'All' in scenarios:
        # Return all scenarios: Historical for ≤2024, all forecast scenarios for >2024
        hist_mask = (df["Scenario"] == "Historical") & (df[year_col] <= 2024)
        forecast_mask = (df["Scenario"].isin(["Most Probable", "High", "Low"])) & (df[year_col] > 2024)
        return df[hist_mask | forecast_mask]
    else:
        # Filter for specific scenarios
        hist_mask = (df["Scenario"] == "Historical") & (df[year_col] <= 2024)
        forecast_scenarios = []
        for scenario in scenarios:
            norm_scenario = _normalize_scenario(scenario)
            if norm_scenario and norm_scenario != 'All':
                forecast_scenarios.append(norm_scenario)
        
        if forecast_scenarios:
            forecast_mask = (df["Scenario"].isin(forecast_scenarios)) & (df[year_col] > 2024)
            return df[hist_mask | forecast_mask]
        else:
            return df[hist_mask]
# -------------------------------------------------------------------------------------

# Utility to clean country names ---------------------------------------------------

def _sanitize_country(country: str) -> str:
    """Return a cleaned version of the country string.

    Removes possessive apostrophes (e.g. "France's" → "France"), extra
    whitespace, and standardises capitalisation so the value matches the
    dataset exactly.
    """
    if country is None:
        return country
    # Trim whitespace first
    country_clean = country.strip()
    # Handles "France's"  as well as "Netherlands'"
    country_clean = re.sub(r"[']s?$", "", country_clean, flags=re.IGNORECASE)
    # Collapse interior whitespace
    country_clean = " ".join(country_clean.split())
    return country_clean

# ----------------------------------------------------------------------------------


class chat_response(BaseModel):
    chat_response: str

# Helper to generate a short unique suffix for filenames
def _unique() -> str:
    return uuid.uuid4().hex[:8]

class PydanticWeaviateAgent:
    """Pydantic-AI based agent for PV market analysis with conversation memory (now using PandasAI)"""
    
    def __init__(self):
        self.data_analysis_agent = None
        self.conversation_memory: Dict[str, List[ModelMessage]] = {}
        self.last_dataframe = None
        self._initialize_pandasai()
        self._setup_pydantic_agent()

    def _initialize_pandasai(self):
        self.llm = LiteLLM(
            model="gpt-4.1-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        pai.config.set({
            "llm": self.llm,
            "verbose": True,
        })
        self.market_data = pai.load("becsight/market-search-data")

    def _setup_pydantic_agent(self):
        try:
            # Create the agent first
            system_prompt = """
You are a data analyst for PV market analysis using PandasAI. For any market data query, use the 'analyze_market_data' tool. For plotting, use the appropriate plotting tool. Return results as clearly as possible.

For plotting requests, use these tools:
- plot_market_share_tool: For market share analysis by segment
- plot_capacity_pie_tool: For capacity pie charts
- plot_total_market_tool: For total market analysis
- plot_yoy_growth_tool: For year-over-year growth analysis
- plot_country_installation_share_tool: For country installation share
- plot_capacity_trend_tool: For capacity trends over time
- plot_multi_scenario_capacity_trend_tool: For multi-scenario capacity trends
- plot_country_comparison_capacity_trend_tool: For comparing two countries
- plot_multi_country_capacity_trend_tool: For multi-country capacity trends

When plotting, ensure to:
- Use appropriate scenarios (Historical, Most Probable, High, Low)
- Specify correct segments (Total, Distributed, Centralised)
- Use proper value types (cumulative, annual)
- Return plot results in the format: PLOT_GENERATED|{url_path}|
"""
            self.data_analysis_agent = Agent(
                model="openai:gpt-4o",
                system_prompt=system_prompt,
            )
            
            # Now register all tools
            async def chat_response(ctx: RunContext[None], chat_response: str) -> str:
                return chat_response

            @self.data_analysis_agent.tool(name="analyze_market_data")
            async def analyze_market_data(ctx: RunContext[None], query: str) -> str:
                try:
                    logger.info(f"Executing market data query: {query}")
                    response = self.market_data.chat(query)
                    df = None
                    if hasattr(response, 'value') and isinstance(response.value, pd.DataFrame):
                        df = response.value
                    elif isinstance(response, pd.DataFrame):
                        df = response
                    if df is not None and not df.empty:
                        self.last_dataframe = df
                        if len(df) > 10:
                            display_text = df.head(10).to_string()
                            total_rows = len(df)
                            return f"{display_text}\n\n... and {total_rows - 10} more rows. Full data available in table below."
                        else:
                            return df.to_string()
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

            @self.data_analysis_agent.tool(name="plot_market_share_tool")
            async def plot_market_share_tool(ctx: RunContext[None], country: str, max_year: int, scenario: str = None, min_year: int = None) -> str:
                try:
                    save_path = f"static/plots/market_share_{_unique()}.png"
                    plot_market_share_per_segment(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year
                    )
                    return f"PLOT_GENERATED|{save_path}|"
                except Exception as e:
                    return f"Error generating market share plot: {str(e)}"

            @self.data_analysis_agent.tool(name="plot_capacity_pie_tool")
            async def plot_capacity_pie_tool(ctx: RunContext[None], country: str, year: int, value_type: str, scenario: str = None) -> str:
                try:
                    save_path = f"static/plots/capacity_pie_{_unique()}.png"
                    plot_capacity_pie(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        year=year,
                        value_type=value_type,
                        scenario=scenario,
                        save_path=save_path
                    )
                    return f"PLOT_GENERATED|{save_path}|"
                except Exception as e:
                    return f"Error generating capacity pie plot: {str(e)}"

            @self.data_analysis_agent.tool(name="plot_total_market_tool")
            async def plot_total_market_tool(ctx: RunContext[None], country: str, value_type: str, segment: str = "Total", max_year: int = None, scenario: str = None, min_year: int = None) -> str:
                try:
                    save_path = f"static/plots/total_market_{_unique()}.png"
                    plot_total_market(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        value_type=value_type,
                        segment=segment,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year
                    )
                    return f"PLOT_GENERATED|{save_path}|"
                except Exception as e:
                    return f"Error generating total market plot: {str(e)}"

            @self.data_analysis_agent.tool(name="plot_yoy_growth_tool")
            async def plot_yoy_growth_tool(ctx: RunContext[None], country: str, segment: str = "Total", max_year: int = None, scenario: str = None, min_year: int = None) -> str:
                try:
                    save_path = f"static/plots/yoy_growth_{_unique()}.png"
                    plot_yoy_growth(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        segment=segment,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year
                    )
                    return f"PLOT_GENERATED|{save_path}|"
                except Exception as e:
                    return f"Error generating YoY growth plot: {str(e)}"

            @self.data_analysis_agent.tool(name="plot_country_installation_share_tool")
            async def plot_country_installation_share_tool(ctx: RunContext[None], year: int, countries: str = None, scenario: str = None) -> str:
                try:
                    save_path = f"static/plots/installation_share_{_unique()}.png"
                    country_list = [c.strip() for c in countries.split(",")] if countries else None
                    plot_country_installation_share(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        year=year,
                        countries=country_list,
                        scenario=scenario,
                        save_path=save_path
                    )
                    return f"PLOT_GENERATED|{save_path}|"
                except Exception as e:
                    return f"Error generating installation share plot: {str(e)}"

            @self.data_analysis_agent.tool(name="plot_capacity_trend_tool")
            async def plot_capacity_trend_tool(ctx: RunContext[None], country: str, value_type: str = "cumulative", segment: str = None, max_year: int = None, scenario: str = None, min_year: int = None) -> str:
                try:
                    save_path = f"static/plots/capacity_trend_{_unique()}.png"
                    plot_capacity_trend(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        value_type=value_type,
                        segment=segment,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year
                    )
                    return f"PLOT_GENERATED|{save_path}|"
                except Exception as e:
                    return f"Error generating capacity trend plot: {str(e)}"

            @self.data_analysis_agent.tool(name="plot_multi_scenario_capacity_trend_tool")
            async def plot_multi_scenario_capacity_trend_tool(ctx: RunContext[None], country: str, value_type: str = "cumulative", segment: str = None, max_year: int = None, scenarios: str = None, min_year: int = None) -> str:
                try:
                    save_path = f"static/plots/multi_scenario_trend_{_unique()}.png"
                    scenario_list = [s.strip() for s in scenarios.split(",")] if scenarios else None
                    plot_multi_scenario_capacity_trend(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        value_type=value_type,
                        segment=segment,
                        max_year=max_year,
                        scenarios=scenario_list,
                        save_path=save_path,
                        min_year=min_year
                    )
                    return f"PLOT_GENERATED|{save_path}|"
                except Exception as e:
                    return f"Error generating multi-scenario trend plot: {str(e)}"

            @self.data_analysis_agent.tool(name="plot_country_comparison_capacity_trend_tool")
            async def plot_country_comparison_capacity_trend_tool(ctx: RunContext[None], country_a: str, country_b: str, value_type: str = "cumulative", segment: str = None, max_year: int = None, scenario: str = None, min_year: int = None) -> str:
                try:
                    save_path = f"static/plots/country_comparison_{_unique()}.png"
                    plot_country_comparison_capacity_trend(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country_a=country_a,
                        country_b=country_b,
                        value_type=value_type,
                        segment=segment,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year
                    )
                    return f"PLOT_GENERATED|{save_path}|"
                except Exception as e:
                    return f"Error generating country comparison plot: {str(e)}"

            @self.data_analysis_agent.tool(name="plot_multi_country_capacity_trend_tool")
            async def plot_multi_country_capacity_trend_tool(ctx: RunContext[None], countries: str, value_type: str = "cumulative", segment: str = None, max_year: int = None, scenario: str = None, min_year: int = None) -> str:
                try:
                    save_path = f"static/plots/multi_country_trend_{_unique()}.png"
                    country_list = [c.strip() for c in countries.split(",")]
                    plot_multi_country_capacity_trend(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        countries=country_list,
                        value_type=value_type,
                        segment=segment,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year
                    )
                    return f"PLOT_GENERATED|{save_path}|"
                except Exception as e:
                    return f"Error generating multi-country trend plot: {str(e)}"

            # Register chat_response tool as well
            self.data_analysis_agent.tool(chat_response)
            logger.info("Pydantic-AI agent with PandasAI integration and conversation memory setup complete")
        except Exception as e:
            logger.error(f"Failed to setup Pydantic-AI agent: {e}")
            self.data_analysis_agent = None
    
    def process_query(self, user_message: str, conversation_id: str = None) -> str:
        """Process user query through the Pydantic-AI agent with conversation memory"""
        try:
            print(f"\n🎯 USER QUERY RECEIVED: '{user_message}'")
            print(f"💬 Conversation ID: {conversation_id}")
            logger.info(f"Processing user query: {user_message} (conversation_id: {conversation_id})")
            
            if not self.data_analysis_agent:
                print(f"❌ ERROR: Agent not properly initialized")
                return "Agent not properly initialized. Please check your configuration."
            
            # Get conversation history if conversation_id is provided
            message_history: List[ModelMessage] = []
            if conversation_id and conversation_id in self.conversation_memory:
                message_history = self.conversation_memory[conversation_id]
                print(f"🧠 Using conversation memory: {len(message_history)} previous messages")
                logger.info(f"Using conversation memory for {conversation_id} with {len(message_history)} previous messages")
            else:
                print(f"🆕 Starting fresh conversation (no memory)")
            
            print(f"🤖 Executing Pydantic-AI agent...")
            
            # Use proper asyncio event loop management like module prices agent
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                print(f"   🔄 Starting agent.run with new event loop...")
                
                async def run_agent():
                    return await self.data_analysis_agent.run(
                        user_message,
                        message_history=message_history,
                        usage_limits=UsageLimits(request_limit=5, total_tokens_limit=5000),
                    )
                
                result = loop.run_until_complete(run_agent())
                print(f"   ✅ Agent.run completed successfully")
                
            except Exception as agent_error:
                print(f"   ❌ Agent execution failed: {str(agent_error)}")
                logger.error(f"Agent execution error: {agent_error}")
                return f"Agent execution failed: {str(agent_error)}"
            finally:
                loop.close()
            
            print(f"✅ Agent execution completed")
            print(f"📤 Agent response length: {len(str(result.output))} characters")
            print(f"📝 Agent response preview: {str(result.output)[:200]}...")
            
            # Store the new messages for future conversation context
            if conversation_id:
                if conversation_id not in self.conversation_memory:
                    self.conversation_memory[conversation_id] = []
                
                # Add the new messages from this interaction to the conversation history
                self.conversation_memory[conversation_id].extend(result.new_messages())
                print(f"💾 Updated conversation memory: {len(self.conversation_memory[conversation_id])} messages")
                logger.info(f"Updated conversation memory for {conversation_id} with {len(self.conversation_memory[conversation_id])} messages")
            
            # Return the agent's response
            return str(result.output)
            
        except Exception as e:
            print(f"❌ ERROR in process_query: {str(e)}")
            logger.error(f"Error in process_query: {e}")
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

# ----------------- NEW HELPER: Country vs country capacity trend -------------

def plot_country_comparison_capacity_trend(
    filepath: str | None,
    sheet: str,
    country_a: str,
    country_b: str,
    value_type: str = "cumulative",
    segment: str | None = None,
    max_year: int | None = None,
    scenario: str | None = None,
    save_path: str | None = None,
    min_year: int | None = None,
):
    """Plot capacity trend lines for two countries on the same chart."""
    if not filepath:
        filepath = DEFAULT_DATA_FILE

    # Clean country names
    country_a = _sanitize_country(country_a)
    country_b = _sanitize_country(country_b)

    df = pd.read_excel(filepath, sheet_name=sheet)

    segment_norm = _normalize_segment(segment)
    value_type = (value_type or "cumulative").lower()
    if value_type == "cumulative":
        value_column = "Cumulative Market"
        title_prefix = "Cumulative"
    elif value_type == "annual":
        value_column = "Annual Market"
        title_prefix = "Annual"
    else:
        raise ValueError("value_type must be either 'annual' or 'cumulative'")

    def filter_country(c: str):
        d = df[(df["Country"] == c) & (df["Market Segment"] == segment_norm)]
        return _filter_scenario(d, scenario=scenario)

    df_a = filter_country(country_a)
    df_b = filter_country(country_b)

    if max_year is not None:
        df_a = df_a[df_a["Year"] <= max_year]
        df_b = df_b[df_b["Year"] <= max_year]
    if min_year is not None:
        df_a = df_a[df_a["Year"] >= min_year]
        df_b = df_b[df_b["Year"] >= min_year]

    if df_a.empty or df_b.empty:
        raise ValueError("No data found for given parameters")

    pivot_a = df_a.groupby("Year")[value_column].sum().reset_index()
    pivot_b = df_b.groupby("Year")[value_column].sum().reset_index()

    plt.figure(figsize=(10, 6), dpi=80)
    plt.plot(pivot_a["Year"], pivot_a[value_column], marker="o", color=BI_COLORS["navy"], label=country_a)
    plt.plot(pivot_b["Year"], pivot_b[value_column], marker="o", color=BI_COLORS["gold"], label=country_b)
    plt.title(f"{title_prefix} {segment_norm} Capacity: {country_a} vs {country_b}")
    plt.ylabel("Capacity (MW)")
    plt.xlabel("Year")
    plt.grid(True, linestyle="--", alpha=0.7)
    # Append scenario information to legend when forecast data (>2024) is plotted
    has_forecast = max(pivot_a["Year"].max(), pivot_b["Year"].max()) > 2024
    if has_forecast:
        import matplotlib.patches as mpatches
        scenario_label = None
        # Identify the first forecast year present across either country
        future_years = [y for y in sorted(set(pivot_a["Year"]).union(pivot_b["Year"])) if y > 2024]
        if future_years:
            first_fy = future_years[0]
            scen_vals = df_a[df_a["Year"] == first_fy]["Scenario"].unique()
            if len(scen_vals) > 0:
                scenario_label = scen_vals[0]
            else:
                scen_vals = df_b[df_b["Year"] == first_fy]["Scenario"].unique()
                if len(scen_vals) > 0:
                    scenario_label = scen_vals[0]
        if not scenario_label:
            scenario_label = (scenario or "Most Probable").title()
        dummy = mpatches.Patch(facecolor='none', edgecolor='none', label=f"{scenario_label} Scenario")
        handles, labels = plt.gca().get_legend_handles_labels()
        if dummy.get_label() not in labels:
            handles.append(dummy)
            labels.append(dummy.get_label())
        plt.legend(handles, labels)
    else:
        plt.legend()
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=80, bbox_inches="tight")
        plt.close()
        # Clean up memory after plot generation
        cleanup_plot_memory()
    else:
        plt.show()

    return save_path

# ----------------- NEW HELPER: Multi-country capacity trend -------------------

def plot_multi_country_capacity_trend(
    filepath: str | None,
    sheet: str,
    countries: list[str],
    value_type: str = "cumulative",
    segment: str | None = None,
    max_year: int | None = None,
    scenario: str | None = None,
    save_path: str | None = None,
    min_year: int | None = None,
):
    """Plot capacity trend lines for an arbitrary list of countries."""
    if not filepath:
        filepath = DEFAULT_DATA_FILE

    if len(countries) < 2:
        raise ValueError("Please provide at least two countries for comparison.")

    df = pd.read_excel(filepath, sheet_name=sheet)

    segment_norm = _normalize_segment(segment)
    value_type = (value_type or "cumulative").lower()
    if value_type == "cumulative":
        value_column = "Cumulative Market"
        title_prefix = "Cumulative"
    elif value_type == "annual":
        value_column = "Annual Market"
        title_prefix = "Annual"
    else:
        raise ValueError("value_type must be either 'annual' or 'cumulative'")

    # Build a colour cycle
    colour_cycle = [BI_COLORS["navy"], BI_COLORS["gold"], BI_COLORS["orange"], BI_COLORS["sky"], "#145DA0", "#FFB000", "#003f88"]
    plt.figure(figsize=(12, 7), dpi=80)

    for idx, c in enumerate(countries):
        c_clean = _sanitize_country(c)
        df_c = df[(df["Country"] == c_clean) & (df["Market Segment"] == segment_norm)]
        df_c = _filter_scenario(df_c, scenario=scenario)
        if max_year is not None:
            df_c = df_c[df_c["Year"] <= max_year]
        if min_year is not None:
            df_c = df_c[df_c["Year"] >= min_year]
        if df_c.empty:
            continue
        pivot = df_c.groupby("Year")[value_column].sum().reset_index()
        colour = colour_cycle[idx % len(colour_cycle)]
        plt.plot(pivot["Year"], pivot[value_column], marker="o", label=c_clean, color=colour)

    if len(plt.gca().lines) == 0:
        raise ValueError("No data found for the requested countries/parameters.")

    plt.title(f"{title_prefix} {segment_norm} Capacity Trend: {' vs '.join(countries)}")
    plt.ylabel("Capacity (MW)")
    plt.xlabel("Year")
    plt.grid(True, linestyle="--", alpha=0.5)
    # Add scenario legend when chart contains forecast years (>2024)
    max_year_plotted = max([line.get_xdata().max() for line in plt.gca().lines])
    has_forecast = max_year_plotted > 2024
    if has_forecast:
        import matplotlib.patches as mpatches
        scenario_label = (scenario or "Most Probable").title()
        dummy = mpatches.Patch(facecolor='none', edgecolor='none', label=f"{scenario_label} Scenario")
        handles, labels = plt.gca().get_legend_handles_labels()
        if dummy.get_label() not in labels:
            handles.append(dummy)
            labels.append(dummy.get_label())
        plt.legend(handles, labels)
    else:
        plt.legend()
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=80, bbox_inches="tight")
        plt.close()
        # Clean up memory after plot generation
        cleanup_plot_memory()
    else:
        plt.show()

    return save_path

PLOT_TIMEOUT = 20  # seconds; hard limit for any single plot generation

# Helper to execute a plotting command on the nested agent with a timeout
async def _run_plot_with_timeout(agent, cmd: str, ctx: RunContext[None]):
    """Run *cmd* on *agent* but give up after PLOT_TIMEOUT seconds."""
    try:
        return await asyncio.wait_for(agent.run(cmd, usage=ctx.usage), timeout=PLOT_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning(f"Plot command timed out after {PLOT_TIMEOUT}s: {cmd[:120]}")
        class Dummy:
            output = f"Sorry, plot generation exceeded {PLOT_TIMEOUT} seconds. Please refine your request and try again."
        return Dummy()

# Memory cleanup function
def cleanup_plot_memory():
    """Aggressive memory cleanup after plot generation"""
    try:
        # Verify we're using the Agg backend
        current_backend = matplotlib.get_backend()
        if current_backend != 'Agg':
            logger.warning(f"Matplotlib backend is {current_backend}, not Agg. This may cause memory issues.")
            # Force Agg backend
            matplotlib.use('Agg', force=True)
            logger.info("Forced matplotlib to use Agg backend")
        
        # Close all matplotlib figures
        plt.close('all')
        
        # Clear matplotlib cache
        plt.clf()
        plt.cla()
        
        # Clear matplotlib's internal caches
        try:
            import matplotlib.cbook as cbook
            cbook._lock_held = False
        except:
            pass
        
        # Clear any remaining matplotlib objects
        try:
            import matplotlib._pylab_helpers as pylab_helpers
            pylab_helpers.Gcf.destroy_all()
        except:
            pass
        
        # Force garbage collection multiple times
        collected = 0
        for _ in range(3):
            collected += gc.collect()
        
        logger.info(f"Memory cleanup: {collected} objects collected")
        
        # Get current memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"Current memory usage: {memory_mb:.1f}MB")
        
        return memory_mb
    except Exception as e:
        logger.error(f"Error during memory cleanup: {e}")
        return None