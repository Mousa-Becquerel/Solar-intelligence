from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic import BaseModel
from pydantic_ai import ToolOutput
import weaviate
from weaviate.classes.init import Auth
import os, json, uuid
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.agents.query import QueryAgent
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
        else:
            plt.show()

        return save_path
        
    except ValueError as ve:
        # Pass through validation errors (like country not found) without wrapping
        plt.close('all')
        raise ve
    except Exception as e:
        # Close any open matplotlib figures to prevent memory leaks
        plt.close('all')
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


class WeaviateQueryResult(BaseModel):
    """Model for Weaviate query results"""
    query: str
    response: str
    status: str

class chat_response(BaseModel):
    chat_response: str

# Helper to generate a short unique suffix for filenames
def _unique() -> str:
    return uuid.uuid4().hex[:8]

class PydanticWeaviateAgent:
    """Pydantic-AI based Weaviate agent for PV market analysis with conversation memory"""
    
    def __init__(self):
        self.client = None
        self.query_agent = None
        self.data_analysis_agent = None
        self.conversation_memory = {}  # Store message history per conversation
        self._last_query_context = None  # Store last QueryAgent response for follow-up queries
        self._initialize_weaviate()
        self._setup_pydantic_agent()
    
    def _initialize_weaviate(self):
        """Initialize Weaviate connection"""
        try:
            weaviate_url = os.getenv("WEAVIATE_URL")
            weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
            
            if not weaviate_url or not weaviate_api_key:
                logger.warning("Weaviate credentials not found. Agent will use fallback mode.")
                return
            
            # Optional headers for OpenAI integration
            headers = {}
            if os.getenv("OPENAI_API_KEY"):
                headers["X-OpenAI-Api-Key"] = os.getenv("OPENAI_API_KEY")
            
            # Connect to Weaviate
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=AuthApiKey(weaviate_api_key),
                headers=headers,
            )
            
            # Initialize Query Agent
            self.query_agent = QueryAgent(
                client=self.client,
                collections=["PV_Market_data"]  # Both historical and forecast data
            )
            
            logger.info("Weaviate connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {e}")
            self.client = None
            self.query_agent = None
    
    def _setup_pydantic_agent(self):
        """Setup Pydantic-AI agent with Weaviate integration"""
        try:
            # --- Define a generic chat response tool (for non-PV questions) ---
            async def chat_response(ctx: RunContext[None], chat_response: str) -> str:
                """Simply returns the assistant's free-form reply (no database lookup)."""
                return chat_response

            # --- Secondary agent dedicated to plotting ---
            # Inner agent that ALWAYS returns the tool output (no extra commentary)
            
            # Forward declaration of tool to reference in output_type
            async def _dummy(ctx: RunContext[None]):
                pass

            # We'll define plot_factory first then assign agent


            # Temporary placeholder; will be replaced after plot_factory definition
            
            async def plot_factory(ctx: RunContext[None], country: str, max_year: int, min_year: int | None = None) -> str:
                 """Stacked-bar market-share plot (Distributed vs Centralised).

                 Purpose
                 -------
                 Draw a bar chart showing the **annual market share** split between
                 Distributed and Centralised segments for every year up to
                 `max_year` for `country`.

                 When should the agent call this?
                 --------------------------------
                 • User asks for *market share* over a range of years (e.g. "plot the
                   annual market share for Germany up to 2024").

                 Expected return
                 ----------------
                 A string starting with ``PLOT_GENERATED|`` so the outer system can
                 detect a chart artefact.
                 """
                 try:
                     file_name = f"market_share_{country}_{max_year}_{_unique()}.png"
                     save_path = os.path.join("static", "plots", file_name)  # OS path for saving
                     url_path = f"/static/plots/{file_name}"  # Web-friendly path with forward slashes
                     plot_market_share_per_segment(
                         filepath=DEFAULT_DATA_FILE,
                         sheet="Market Search Data",
                         country=country,
                         max_year=max_year,
                         save_path=save_path,
                         min_year=min_year,
                     )
                     return f"PLOT_GENERATED|{url_path}|"
                 except ValueError as ve:
                     logger.warning(f"Validation error generating plot: {ve}")
                     return str(ve)
                 except Exception as e:
                     logger.error(f"Error generating plot: {e}")
                     return f"Sorry, I encountered an error while generating the plot: {str(e)}"

            async def pie_factory(ctx: RunContext[None], country: str, year: int, value_type: str, scenario: str | None = None) -> str:
                """Capacity pie-chart generator.

                Purpose
                -------
                Create a **pie chart** comparing Distributed vs Centralised
                capacity for a *single* year.

                Parameters
                ----------
                country : str           – country name
                year    : int           – calendar year to visualise
                value_type : {'annual','cumulative'}
                    • annual      → slice sizes = Annual Market (MW) in that year
                    • cumulative → slice sizes = Cumulative Market (MW) in that year
                scenario : str | None   – optional scenario for forecast years

                When should the agent call this?
                --------------------------------
                • User asks for a *pie* or *share* for a single year
                  (e.g. "give me the cumulative capacity pie for Italy 2023").
                """
                try:
                    file_name = f"capacity_pie_{country}_{year}_{value_type}_{_unique()}.png"
                    save_path = os.path.join("static", "plots", file_name)
                    url_path = f"/static/plots/{file_name}"
                    plot_capacity_pie(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        year=year,
                        value_type=value_type,
                        scenario=scenario,
                        save_path=save_path,
                    )
                    return f"PLOT_GENERATED|{url_path}|"
                except ValueError as ve:
                    logger.warning(f"Validation error generating pie: {ve}")
                    return str(ve)
                except Exception as e:
                    logger.error(f"Error generating pie: {e}")
                    return f"Sorry, I encountered an error while generating the pie chart: {str(e)}"

            async def total_market_factory(
                ctx: RunContext[None],
                country: str,
                segment: SegmentName | None = None,
                value_type: str | None = None,
                max_year: int | None = None,
                scenario: str | None = None,
                min_year: int | None = None,
            ) -> str:
                """Total-market bar-chart generator.

                Purpose
                -------
                Produce a bar chart of the **TOTAL PV market size** (segment
                = "Total") for a country.

                value_type
                  • 'annual'     → bars represent Annual Market (MW)
                  • 'cumulative' → bars represent Cumulative Market (MW)

                max_year (optional)
                  • If provided, data are filtered to Year ≤ max_year. Useful
                    for requests like "up to 2025".

                When should the agent call this?
                --------------------------------
                • User asks for *total* market evolution/size (not split by
                  segment), e.g. "plot cumulative total market for Spain up to
                  2030".
                """
                try:
                    segment_norm = _normalize_segment(segment)
                    vt_text = value_type if value_type else "cumulative"
                    file_name_parts = ["total_market", country, segment_norm, vt_text]
                    if max_year is not None:
                        file_name_parts.append(str(max_year))
                    file_name = "total_market_" + "_".join(file_name_parts) + f"_{_unique()}.png"
                    save_path = os.path.join("static", "plots", file_name)
                    url_path = f"/static/plots/{file_name}"
                    plot_total_market(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        segment=segment_norm,
                        value_type=vt_text,  # Use vt_text instead of value_type to ensure it's never None
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year,
                    )
                    return f"PLOT_GENERATED|{url_path}|"
                except ValueError as ve:
                    logger.warning(f"Validation error generating total market chart: {ve}")
                    return str(ve)
                except Exception as e:
                    logger.error(f"Error generating total market chart: {e}")
                    return f"Sorry, I encountered an error while generating the total market chart: {str(e)}"
 
            async def yoy_growth_factory(
                ctx: RunContext[None],
                country: str,
                segment: SegmentName = "Total",
                max_year: int | None = None,
                scenario: str | None = None,
                min_year: int | None = None,
            ) -> str:
                """Year-on-year (YoY) growth line chart generator.

                Call when the user asks for *growth* or *YoY* trends.
                """
                try:
                    seg_clean = segment.title()
                    file_parts = ["yoy_growth", country, seg_clean]
                    if max_year is not None:
                        file_parts.append(str(max_year))
                    file_name = "yoy_growth_" + "_".join(file_parts) + f"_{_unique()}.png"
                    save_path = os.path.join("static", "plots", file_name)
                    url_path = f"/static/plots/{file_name}"
                    plot_yoy_growth(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        segment=seg_clean,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year,
                    )
                    return f"PLOT_GENERATED|{url_path}|"
                except ValueError as ve:
                    logger.warning(f"Validation error generating YoY chart: {ve}")
                    return str(ve)
                except Exception as e:
                    logger.error(f"Error generating YoY chart: {e}")
                    return f"Sorry, I encountered an error while generating the YoY chart: {str(e)}"
 
            async def country_share_factory(
                ctx: RunContext[None],
                year: int,
                countries: list[str] | None = None,
                scenario: str | None = None,
            ) -> str:
                """Donut chart of installation share per country for a given year."""
                try:
                    file_name = "country_share_" + str(year) + ("_custom" if countries else "") + f"_{_unique()}.png"
                    save_path = os.path.join("static", "plots", file_name)
                    url_path = f"/static/plots/{file_name}"
                    plot_country_installation_share(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        year=year,
                        countries=countries,
                        scenario=scenario,
                        save_path=save_path,
                    )
                    return f"PLOT_GENERATED|{url_path}|"
                except ValueError as ve:
                    logger.warning(f"Validation error generating country share donut: {ve}")
                    return str(ve)
                except Exception as e:
                    logger.error(f"Error generating country share donut: {e}")
                    return f"Sorry, I encountered an error while generating the country share chart: {str(e)}"
 
            async def capacity_trend_factory(
                ctx: RunContext[None],
                country: str,
                value_type: str = "cumulative",
                segment: SegmentName | None = None,
                max_year: int | None = None,
                scenario: str | None = None,
                min_year: int | None = None,
            ) -> str:
                """Capacity trend line chart generator."""
                try:
                    segment_norm = _normalize_segment(segment)
                    vt_text = value_type or "cumulative"
                    scenario_slug = "" if scenario is None else f"_{_normalize_scenario(scenario).replace(' ', '')}"
                    file_name = f"capacity_trend_{country}_{segment_norm}_{vt_text}{scenario_slug}_{_unique()}.png"
                    save_path = os.path.join("static", "plots", file_name)
                    url_path = f"/static/plots/{file_name}"
                    plot_capacity_trend(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        value_type=vt_text,
                        segment=segment_norm,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year,
                    )
                    return f"PLOT_GENERATED|{url_path}|"
                except ValueError as ve:
                    logger.warning(f"Validation error generating capacity trend chart: {ve}")
                    return str(ve)
                except Exception as e:
                    logger.error(f"Error generating capacity trend chart: {e}")
                    return f"Sorry, I encountered an error while generating the capacity trend chart: {str(e)}"
 
            async def multi_scenario_capacity_trend_factory(
                ctx: RunContext[None],
                country: str,
                value_type: str = "cumulative",
                segment: SegmentName | None = None,
                max_year: int | None = None,
                scenarios: list[str] | None = None,
                min_year: int | None = None,
            ) -> str:
                """Multi-scenario capacity trend line chart generator.
                
                Call when the user asks for multiple scenarios, comparisons, or 'all scenarios'.
                """
                try:
                    segment_norm = _normalize_segment(segment)
                    vt_text = value_type or "cumulative"
                    scen_slug = "all" if scenarios is None else "_".join([_normalize_scenario(s) for s in scenarios]) if scenarios else "all"
                    file_name = f"multi_scenario_trend_{country}_{segment_norm}_{vt_text}_{scen_slug}_{_unique()}.png"
                    save_path = os.path.join("static", "plots", file_name)
                    url_path = f"/static/plots/{file_name}"
                    plot_multi_scenario_capacity_trend(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country=country,
                        value_type=vt_text,
                        segment=segment_norm,
                        max_year=max_year,
                        scenarios=scenarios,
                        save_path=save_path,
                        min_year=min_year,
                    )
                    return f"PLOT_GENERATED|{url_path}|"
                except ValueError as ve:
                    logger.warning(f"Validation error generating multi-scenario chart: {ve}")
                    return str(ve)
                except Exception as e:
                    logger.error(f"Error generating multi-scenario chart: {e}")
                    return f"Sorry, I encountered an error while generating the multi-scenario chart: {str(e)}"
 
            async def country_comparison_capacity_trend_factory(
                ctx: RunContext[None],
                country_a: str,
                country_b: str,
                value_type: str = "cumulative",
                segment: SegmentName | None = None,
                max_year: int | None = None,
                scenario: str | None = None,
                min_year: int | None = None,
            ) -> str:
                """Country-vs-country capacity trend line chart generator."""
                try:
                    segment_norm = _normalize_segment(segment)
                    vt_text = value_type or "cumulative"
                    file_name = f"country_compare_{country_a}_vs_{country_b}_{segment_norm}_{vt_text}_{_unique()}.png"
                    save_path = os.path.join("static", "plots", file_name)
                    url_path = f"/static/plots/{file_name}"
                    plot_country_comparison_capacity_trend(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        country_a=country_a,
                        country_b=country_b,
                        value_type=vt_text,
                        segment=segment_norm,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year,
                    )
                    return f"PLOT_GENERATED|{url_path}|"
                except ValueError as ve:
                    logger.warning(f"Validation error generating country comparison chart: {ve}")
                    return str(ve)
                except Exception as e:
                    logger.error(f"Error generating country comparison chart: {e}")
                    return f"Sorry, I encountered an error while generating the comparison chart: {str(e)}"

            async def multi_country_capacity_trend_factory(
                ctx: RunContext[None],
                countries: list[str],
                value_type: str = "cumulative",
                segment: SegmentName | None = None,
                max_year: int | None = None,
                scenario: str | None = None,
                min_year: int | None = None,
            ) -> str:
                """Capacity trend comparison for 3+ countries."""
                try:
                    segment_norm = _normalize_segment(segment)
                    vt_text = value_type or "cumulative"
                    slug = "_".join([c.replace(" ", "") for c in countries[:3]])
                    file_name = f"multi_country_trend_{slug}_{segment_norm}_{vt_text}_{_unique()}.png"
                    save_path = os.path.join("static", "plots", file_name)
                    url_path = f"/static/plots/{file_name}"
                    plot_multi_country_capacity_trend(
                        filepath=DEFAULT_DATA_FILE,
                        sheet="Market Search Data",
                        countries=countries,
                        value_type=vt_text,
                        segment=segment_norm,
                        max_year=max_year,
                        scenario=scenario,
                        save_path=save_path,
                        min_year=min_year,
                    )
                    return f"PLOT_GENERATED|{url_path}|"
                except ValueError as ve:
                    logger.warning(f"Validation error generating multi-country chart: {ve}")
                    return str(ve)
                except Exception as e:
                    logger.error(f"Error generating multi-country chart: {e}")
                    return f"Sorry, I encountered an error while generating the multi-country chart: {str(e)}"

            plot_generation_agent = Agent(
                model="openai:gpt-4o",
                output_type=[plot_factory, pie_factory, total_market_factory, yoy_growth_factory, country_share_factory, capacity_trend_factory, multi_scenario_capacity_trend_factory, country_comparison_capacity_trend_factory, multi_country_capacity_trend_factory, chat_response],
                system_prompt=(
                    "You are a plotting assistant.\n\n"
                    "Tool-selection rules:\n"
                    "• If the user asks for *market share* over a period (phrases like 'up to 2024', 'from 2010-2023', 'over the years'), call `plot_factory`.\n"
                    "• If the user asks for *stacked chart*, *stacked bar*, *segments by year*, *breakdown by segment*, or *distributed vs centralised* over time, call `plot_factory`.\n"
                    "  This shows Distributed vs Centralised bars stacked by year.\n"
                    "• If the user asks for a *pie* or uses wording such as 'in 2024', 'for 2024', or clearly references a **single** year, call `pie_factory`.\n"
                    "• If the user asks for *total market* (mentions 'total market', 'overall market size', etc.), call `total_market_factory`.\n"
                    "• If the user asks for *growth*, *YoY*, or *year-on-year* trends, call `yoy_growth_factory`.\n"
                    "• If the user asks to *show capacity trend / line over time*, call `capacity_trend_factory`.\n"
                    "• If the user asks for *country share* of installations for a single year (donut), call `country_share_factory`.\n"
                    "• If the user asks for *multiple scenarios*, *all scenarios*, *all the scenarios*, *compare scenarios*, *different scenarios*, *three scenarios*, or *forecasting for all*, call `multi_scenario_capacity_trend_factory`.\n"
                    "• If the user asks to *compare capacity trends* between two countries, call `country_comparison_capacity_trend_factory`.\n"
                    "• If the user asks to *compare capacity trends* between multiple countries, call `multi_country_capacity_trend_factory`.\n\n"
                    "Parameter extraction:\n"
                    "• Extract max_year from phrases like 'up to 2024', 'from 2020 to 2024', 'until 2025', 'through 2023', 'by 2030'.\n"
                    "• If no max_year is specified but the request is for multiple years, use 2030 as default.\n"
                    "• Extract segment from phrases like 'distributed', 'centralised', 'rooftop', 'utility-scale', 'total market'.\n"
                    "• Extract value_type from phrases like 'cumulative', 'annual', 'yearly installations'.\n"
                    "• If no value_type is specified, use 'cumulative' as default.\n"
                    "• If no segment is specified, use 'Total' as default.\n"
                    "• For multi-scenario requests, extract scenarios list from phrases like 'High and Low', 'all three scenarios', 'High, Low, Most Probable'.\n\n"
                    "Scenario parameter handling:\n"
                    "• If the command mentions a scenario (e.g., 'using the High scenario', 'in the Low scenario', 'Most Probable scenario'), extract the scenario name and pass it to the appropriate factory function.\n"
                    "• Valid scenarios are: 'High', 'Low', 'Most Probable' (or variations like 'Most Probable').\n"
                    "• If no scenario is mentioned, pass None to use default scenario logic.\n"
                    "• For multi-scenario requests, pass a list of scenarios or None for all scenarios.\n\n"
                    "Return ONLY the tool output you receive. Do NOT add extra commentary or markdown."
                ),
            )

            # --- Define the plotting tool WRAPPER used by the main agent ---
            async def plot_market_share_tool(
                ctx: RunContext[None],
                country: str,
                max_year: int,
                min_year: int | None = None,
                scenario: str | None = None,
            ) -> str:
                """Wrapper that delegates plotting to the nested plot_generation_agent."""
                cmd = f"Generate a market share bar chart for {country} from {min_year} to {max_year}."
                if scenario:
                    cmd = cmd.rstrip('.') + f" in the {scenario} scenario."
                print(f"🔧 MARKET-SHARE TOOL CALLED: country={country}, max_year={max_year}, min_year={min_year}, scenario={scenario}")
                print(f"🔧 MARKET-SHARE COMMAND: {cmd}")
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                print(f"🔧 MARKET-SHARE RESPONSE: {response.output}")
                return response.output

            async def plot_capacity_pie_tool(
                ctx: RunContext[None],
                country: str,
                year: int,
                value_type: str,
                scenario: str | None = None,
            ) -> str:
                """Wrapper that delegates pie chart generation to nested agent."""
                cmd = f"Generate a {value_type} capacity pie chart for {country} in {year}"
                if scenario:
                    cmd += f" using the {scenario} scenario"
                cmd += "."
                print(f"🔧 PIE TOOL CALLED: country={country}, year={year}, value_type={value_type}, scenario={scenario}")
                print(f"🔧 PIE COMMAND: {cmd}")
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                print(f"🔧 PIE RESPONSE: {response.output}")
                return response.output

            async def plot_total_market_tool(
                ctx: RunContext[None],
                country: str,
                segment: SegmentName | None = None,
                value_type: str | None = None,
                max_year: int | None = None,
                min_year: int | None = None,
                scenario: str | None = None,
            ) -> str:
                """Wrapper delegating total market bar chart generation."""
                # Build natural language command for nested agent
                segment_norm = _normalize_segment(segment)
                vt_text = value_type if value_type else "cumulative"
                cmd = (
                    f"Generate a {vt_text} total market bar chart for the {segment_norm} segment in {country}"
                    + (f' from {min_year} to {max_year or "2030"}.' if max_year is not None else '.')
                )
                if scenario:
                    cmd = cmd.rstrip('.') + f" in the {scenario} scenario."
                print(f"🔧 TOTAL-MARKET TOOL CALLED: country={country}, segment={segment_norm}, value_type={vt_text}, max_year={max_year}, min_year={min_year}, scenario={scenario}")
                print(f"🔧 TOTAL-MARKET COMMAND: {cmd}")
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                print(f"🔧 TOTAL-MARKET RESPONSE: {response.output}")
                return response.output

            async def plot_yoy_growth_tool(
                ctx: RunContext[None],
                country: str,
                segment: SegmentName = "Total",
                max_year: int | None = None,
                min_year: int | None = None,
                scenario: str | None = None,
            ) -> str:
                """Wrapper delegating YoY growth chart generation."""
                cmd_base = f"Generate a YoY growth chart for {segment} in {country}"
                if min_year is not None and max_year is not None:
                    cmd = f"{cmd_base} from {min_year} to {max_year}."
                elif max_year is not None:
                    cmd = f"{cmd_base} up to {max_year}."
                elif min_year is not None:
                    cmd = f"{cmd_base} starting {min_year}."
                else:
                    cmd = cmd_base + "."
                if scenario:
                    cmd = cmd.rstrip('.') + f" ({scenario} scenario)."
                print(f"🔧 YOY-GROWTH TOOL CALLED: country={country}, segment={segment}, max_year={max_year}, min_year={min_year}, scenario={scenario}")
                print(f"🔧 YOY-GROWTH COMMAND: {cmd}")
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                print(f"🔧 YOY-GROWTH RESPONSE: {response.output}")
                return response.output

            async def plot_country_share_tool(
                ctx: RunContext[None],
                year: int,
                countries: list[str] | None = None,
                scenario: str | None = None,
            ) -> str:
                """Wrapper delegating country share donut chart generation."""
                if countries:
                    country_str = ", ".join(countries)
                    cmd = f"Generate a country share donut chart for year {year} including {country_str}."
                else:
                    cmd = f"Generate a country share donut chart for year {year}."
                if scenario:
                    cmd = cmd.rstrip('.') + f" ({scenario} scenario)."
                print(f"🔧 COUNTRY-SHARE TOOL CALLED: year={year}, countries={countries}, scenario={scenario}")
                print(f"🔧 COUNTRY-SHARE COMMAND: {cmd}")
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                print(f"🔧 COUNTRY-SHARE RESPONSE: {response.output}")
                return response.output

            async def plot_capacity_trend_tool(
                ctx: RunContext[None],
                country: str,
                value_type: str = "cumulative",
                segment: SegmentName | None = None,
                max_year: int | None = None,
                min_year: int | None = None,
                scenario: str | None = None,
            ) -> str:
                """Wrapper that delegates capacity trend generation to nested agent."""
                # Detailed debug information
                print("🔧 SINGLE-SCENARIO TOOL CALLED:")
                print(f"   country   = {country}")
                print(f"   value_type= {value_type}")
                print(f"   segment   = {segment}")
                print(f"   max_year  = {max_year}")
                print(f"   min_year  = {min_year}")
                print(f"   scenario  = {scenario}\n")
                cmd_base = f"Generate a {value_type} capacity trend line for the {segment or 'Total'} segment in {country}"
                if min_year is not None and max_year is not None:
                    cmd = f"{cmd_base} from {min_year} to {max_year}."
                elif max_year is not None:
                    cmd = f"{cmd_base} up to {max_year}."
                elif min_year is not None:
                    cmd = f"{cmd_base} starting {min_year}."
                else:
                    cmd = cmd_base + "."
                if scenario:
                    cmd = cmd.rstrip('.') + f" ({scenario} scenario)."
                print(f"🔧 SINGLE-SCENARIO COMMAND: {cmd}")
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                print(f"🔧 SINGLE-SCENARIO RESPONSE: {response.output}")
                return response.output

            async def plot_multi_scenario_capacity_trend_tool(
                ctx: RunContext[None],
                country: str,
                value_type: str = "cumulative",
                segment: SegmentName | None = None,
                max_year: int | None = None,
                scenarios: list[str] | None = None,
                min_year: int | None = None,
            ) -> str:
                """Wrapper that delegates multi-scenario capacity trend generation to nested agent."""
                print("🔧 MULTI-SCENARIO TOOL CALLED:")
                print(f"   country   = {country}")
                print(f"   value_type= {value_type}")
                print(f"   segment   = {segment}")
                print(f"   max_year  = {max_year}")
                print(f"   min_year  = {min_year}")
                print(f"   raw_scenarios   = {scenarios}")
 
                # Validate / normalise scenarios via Enum mapping
                try:
                    canonical_scenarios = _to_enum_scenario_list(scenarios)
                except ValueError as ve:
                    return str(ve)

                print(f"   canonical_scenarios = {canonical_scenarios}\n")

                # Convert Enum list back to display strings for the nested agent command
                if canonical_scenarios == "All":
                    scenarios_display = None  # let nested agent know it's all
                else:
                    scenarios_display = [sc.value for sc in canonical_scenarios]

                cmd_base = f"Generate a {value_type} capacity trend line for the {segment or 'Total'} segment in {country}"
                if min_year is not None and max_year is not None:
                    cmd = f"{cmd_base} from {min_year} to {max_year}."
                elif max_year is not None:
                    cmd = f"{cmd_base} up to {max_year}."
                elif min_year is not None:
                    cmd = f"{cmd_base} starting {min_year}."
                else:
                    cmd = cmd_base + "."
                if scenarios_display:
                    scenario_str = ", ".join(scenarios_display)
                    cmd = cmd.rstrip('.') + f" for scenarios: {scenario_str}."
                else:
                    cmd = cmd.rstrip('.') + " for all scenarios."
                print(f"🔧 MULTI-SCENARIO COMMAND: {cmd}")
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                print(f"🔧 MULTI-SCENARIO RESPONSE: {response.output}")
                return response.output

            async def plot_country_comparison_capacity_trend_tool(
                ctx: RunContext[None],
                country_a: str,
                country_b: str,
                value_type: str = "cumulative",
                segment: SegmentName | None = None,
                max_year: int | None = None,
                min_year: int | None = None,
                scenario: str | None = None,
            ) -> str:
                """Wrapper delegating country vs country capacity trend generation."""
                cmd_base = f"Generate a {value_type} capacity trend line comparing {country_a} and {country_b}"
                if min_year is not None and max_year is not None:
                    cmd = f"{cmd_base} from {min_year} to {max_year}."
                elif max_year is not None:
                    cmd = f"{cmd_base} up to {max_year}."
                elif min_year is not None:
                    cmd = f"{cmd_base} starting {min_year}."
                else:
                    cmd = cmd_base + "."
                if segment and segment != SegmentName.TOTAL:
                    cmd = cmd.rstrip('.') + f" for the {segment.value} segment."
                if scenario:
                    cmd = cmd.rstrip('.') + f" ({scenario} scenario)."
                print(f"🔧 COUNTRY-COMPARE TOOL CALLED: {country_a} vs {country_b}, segment={segment}, value_type={value_type}, max_year={max_year}, min_year={min_year}, scenario={scenario}")
                print(f"🔧 COUNTRY-COMPARE COMMAND: {cmd}")
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                print(f"🔧 COUNTRY-COMPARE RESPONSE: {response.output}")
                return response.output

            async def plot_multi_country_capacity_trend_tool(
                ctx: RunContext[None],
                countries: list[str],
                value_type: str = "cumulative",
                segment: SegmentName | None = None,
                max_year: int | None = None,
                scenario: str | None = None,
                min_year: int | None = None,
            ) -> str:
                cmd_base = f"Generate a {value_type} capacity trend line comparing {' ,'.join(countries)}"
                if min_year is not None and max_year is not None:
                    cmd = f"{cmd_base} from {min_year} to {max_year}."
                elif max_year is not None:
                    cmd = f"{cmd_base} up to {max_year}."
                elif min_year is not None:
                    cmd = f"{cmd_base} starting {min_year}."
                else:
                    cmd = cmd_base + "."
                if segment and segment != SegmentName.TOTAL:
                    cmd = cmd.rstrip('.') + f" for the {segment.value} segment."
                if scenario:
                    cmd = cmd.rstrip('.') + f" ({scenario} scenario)."
                print(f"🔧 MULTI-COUNTRY TOOL CALLED: countries={countries}, segment={segment}, value_type={value_type}, max_year={max_year}, min_year={min_year}, scenario={scenario}")
                print(f"🔧 MULTI-COUNTRY COMMAND: {cmd}")
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                print(f"🔧 MULTI-COUNTRY RESPONSE: {response.output}")
                return response.output

            # --- Define the Weaviate query tool (used directly as output_type) ---
            async def weaviate_query_tool(ctx: RunContext[None], query: str) -> str:
                """Forwards the user's query verbatim to Weaviate and returns the answer."""
                print("\n🔧 TOOL CALLED: weaviate_query_tool")
                print(f"📝 Original Query Parameter: '{query}'")

                # --- Normalise segment synonyms -------------------------
                synonym_map = {
                    r"\brooftop\b|\bresidential\b|\bcommercial\b|\bsmall[- ]scale\b": "Distributed",
                    r"\butility\b|\butility[- ]scale\b|\blarge[- ]scale\b|\bground[- ]mounted\b|\bcentralized\b|\bcentralised\b": "Centralised",
                }
                normalised_query = query
                for pattern, replacement in synonym_map.items():
                    normalised_query = re.sub(pattern, replacement, normalised_query, flags=re.IGNORECASE)

                if normalised_query != query:
                    print(f"🔄 Normalised Query: '{normalised_query}'")
                    logger.info(f"Query normalised from '{query}' to '{normalised_query}'")
                else:
                    logger.info("No synonym replacement needed for query")

                query_to_use = normalised_query
                # --------------------------------------------------------

                if not self.query_agent:
                    print("❌ ERROR: Weaviate connection not available")
                    return "Weaviate connection not available. Please check your configuration."

                try:
                    print(f" Executing Weaviate QueryAgent with: '{query_to_use}'")
                    # If we have a previous QueryAgentResponse, pass it as context for follow-up
                    response = self.query_agent.run(
                        query_to_use,
                        context=self._last_query_context  # May be None on first run
                    )

                    # Basic debug output (trimmed for brevity)
                    print("✅ Weaviate QueryAgent Response received")
                    print(f"   📊 Response length: {len(response.final_answer)} characters")

                    print(response.display)
                    # Store context for potential follow-up
                    self._last_query_context = response
                    return response.final_answer
                except Exception as e:
                    logger.error(f"Error in Weaviate query: {e}")
                    return f"Error processing query: {str(e)}"

            # --- Create the Pydantic-AI agent that can route between DB queries and normal chat ---
            self.data_analysis_agent = Agent(
                model="openai:gpt-4o",
                output_type=[weaviate_query_tool, chat_response, plot_market_share_tool, plot_capacity_pie_tool, plot_total_market_tool, plot_yoy_growth_tool, plot_country_share_tool, plot_capacity_trend_tool, plot_multi_scenario_capacity_trend_tool, plot_country_comparison_capacity_trend_tool, plot_multi_country_capacity_trend_tool],
                system_prompt=(
                    "You are a smart router for solar/PV market analysis.\n\n"
                    "**For solar/PV market DATA queries** (mentions capacity, MW, installed, year, market segment, etc.), "
                    "call `weaviate_query_tool` with the user's query EXACTLY as given.\n\n"
                    "**CRITICAL ROUTING RULE: DO NOT generate a plot unless the user explicitly asks for a visual** (words such as 'plot', 'chart', 'graph', 'visualise', 'display', 'show', 'create').\n"
                    "\n"
                    "**PLOTTING TOOL SELECTION - FOLLOW THIS EXACT ORDER:**\n"
                    "\n"
                    "**STEP 1: CHECK FOR MULTI-SCENARIO REQUESTS FIRST (HIGHEST PRIORITY)**\n"
                    "If the user's query contains ANY of these exact phrases:\n"
                    "- 'all scenarios' OR 'all the scenarios'\n"
                    "- 'multiple scenarios' OR 'three scenarios'\n"
                    "- 'compare scenarios' OR 'different scenarios'\n"
                    "- 'forecasting for all' OR 'forecasting for all the scenarios'\n"
                    "- 'show all scenarios' OR 'plot all scenarios'\n"
                    "→ ALWAYS use `plot_multi_scenario_capacity_trend_tool`\n"
                    "→ Parameters: country, value_type ('cumulative' or 'annual'), segment (optional), max_year (optional), scenarios (optional list)\n"
                    "→ DO NOT use any other plotting tool for these requests\n"
                    "\n"
                    "**STEP 2: IF NOT MULTI-SCENARIO, CHECK OTHER CHART TYPES:**\n"
                    "• `plot_market_share_tool` — stacked bar chart of Distributed vs Centralised shares over time.\n"
                    "  Use for: 'stacked chart', 'stacked bar', 'market share', 'segments by year', 'breakdown by segment', 'distributed vs centralised over time', OR queries with 'vs' comparing **segments** (e.g. 'rooftop vs utility').\n"
                    "• `plot_country_comparison_capacity_trend_tool` — line chart comparing capacity trend of **two different countries**.\n"
                    "  Trigger when the query contains 'vs', 'vs.', or 'versus' between two country names (e.g. 'Italy vs Germany PV capacity').\n"
                    "• `plot_capacity_pie_tool` — pie chart of Distributed vs Centralised capacity for a single year.\n"
                    "  Parameters: country, year, value_type ('cumulative' or 'annual') — value_type is REQUIRED, scenario (optional).\n"
                    "• `plot_total_market_tool` — bar chart of market size (annual or cumulative) for a given segment.\n"
                    "  Parameters: country, value_type ('cumulative' or 'annual'), segment ('Total'/'Distributed'/'Centralised') **REQUIRED**, max_year (optional), scenario (optional).\n"
                    "• `plot_yoy_growth_tool` — line chart of Year-on-Year growth %.\n"
                    "  Parameters: country, segment ('Total'/'Distributed'/'Centralised'), max_year (optional), scenario (optional).\n"
                    "• `plot_country_share_tool` — donut chart of annual PV installations per country for a single year.\n"
                    "  Parameters: year, countries (optional list of countries), scenario (optional).\n"
                    "• `plot_capacity_trend_tool` — line chart of annual or cumulative capacity trend over years for a country/segment (SINGLE SCENARIO ONLY).\n"
                    "  Parameters: country, value_type ('cumulative' or 'annual'), segment (optional), max_year (optional), scenario (optional).\n"
                    "  ⚠️ WARNING: Do NOT use this tool if the request mentions multiple scenarios!\n"
                    "\n"
                    "**IMPORTANT NOTES:**\n"
                    "• Our dataset focuses primarily on European countries. For countries outside Europe, the plot tools will explain this limitation.\n"
                    "• If you're unsure between single-scenario and multi-scenario, choose multi-scenario to be safe.\n"
                    "• Multi-scenario requests should ALWAYS go to `plot_multi_scenario_capacity_trend_tool`, never to `plot_capacity_trend_tool`.\n\n"
                    "**Parameter extraction guidelines:**\n"
                    "• Extract max_year from phrases like 'up to 2024', 'from 2020 to 2024', 'until 2025', 'through 2023', 'by 2030'.\n"
                    "• If no max_year is specified but the request is for multiple years, use 2030 as default.\n"
                    "• Extract min_year (start year) from phrases like 'from 2010 to 2024', 'between 2015 and 2024', 'starting 2019', 'since 2018'. When both min_year and max_year are supplied, pass both.\n"
                    "• Extract segment from phrases like 'distributed', 'centralised', 'rooftop', 'utility-scale', 'total market'.\n"
                    "• Extract value_type from phrases like 'cumulative', 'annual', 'yearly installations'.\n"
                    "• If no value_type is specified, use 'cumulative' as default.\n"
                    "• If no segment is specified, use 'Total' as default.\n"
                    "• For multi-scenario requests, extract scenarios list from phrases like 'High and Low scenarios', 'all three scenarios', 'compare High, Low, Most Probable', 'different scenarios'.\n"
                    "\n"
                    "**For greetings, small talk, or general questions** NOT about PV market data, call `chat_response` to reply normally.\n\n"
                    "Always return units in MW when presenting solar data. Do NOT alter the user's wording when forwarding queries to tools."
                    "When users refer to segment synonyms, translate them as follows when passing parameters:\n"
                    "  • 'rooftop', 'residential', 'commercial', 'small-scale' → 'Distributed'\n"
                    "  • 'utility-scale', 'large-scale', 'ground-mounted', 'centralized' → 'Centralised'\n"
                    "Pass the proper user query to the tool; allowable segment values are exactly 'Total', 'Distributed', 'Centralised'."
                ),
            )
 
            logger.info("Pydantic-AI agent with Weaviate integration and conversation memory setup complete")
            
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
            message_history = None
            if conversation_id and conversation_id in self.conversation_memory:
                message_history = self.conversation_memory[conversation_id]
                print(f"🧠 Using conversation memory: {len(message_history)} previous messages")
                logger.info(f"Using conversation memory for {conversation_id} with {len(message_history)} previous messages")
            else:
                print(f"🆕 Starting fresh conversation (no memory)")
            
            print(f"🤖 Executing Pydantic-AI agent...")
            
            try:
                # Execute the agent with usage limits and conversation memory
                print(f"   🔄 Starting agent.run_sync call...")
                result = self.data_analysis_agent.run_sync(
                    user_message,
                    message_history=message_history,
                    usage_limits=UsageLimits(request_limit=5, total_tokens_limit=5000),  # Increased for conversation context
                )
                print(f"   ✅ Agent.run_sync completed successfully")
                
            except Exception as agent_error:
                print(f"   ❌ Agent execution failed: {str(agent_error)}")
                logger.error(f"Agent execution error: {agent_error}")
                return f"Agent execution failed: {str(agent_error)}"
            
            print(f"✅ Agent execution completed")
            print(f"📤 Agent response length: {len(str(result.output))} characters")
            print(f"📝 Agent response preview: {str(result.output)[:200]}...")
            
            # Store the new messages for future conversation context
            if conversation_id:
                if conversation_id not in self.conversation_memory:
                    self.conversation_memory[conversation_id] = []
                self.conversation_memory[conversation_id] = result.new_messages()
                print(f"💾 Updated conversation memory: {len(self.conversation_memory[conversation_id])} messages")
                logger.info(f"Updated conversation memory for {conversation_id} with {len(self.conversation_memory[conversation_id])} messages")
            
            # Return the agent's response (already formatted by the agent)
            final_response = str(result.output)
            print(f"🏁 Final response ready to return")
            logger.info(f"Query processing completed successfully")
            return final_response
                
        except Exception as e:
            print(f"❌ ERROR in process_query: {str(e)}")
            logger.error(f"Error processing query: {e}")
            error_response = f"Error processing your request: {str(e)}"
            print(f"🔄 Returning error response: {error_response}")
            return error_response
    
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
            "agent_type": "pydantic_weaviate",
            "weaviate_connected": self.client is not None,
            "query_agent_available": self.query_agent is not None,
            "pydantic_agent_available": self.data_analysis_agent is not None,
            "conversation_memory_enabled": True,
            "active_conversations": memory_info["active_conversations"],
            "status": "ready" if self.data_analysis_agent else "error"
        }
    
    def close(self):
        """Close Weaviate connection and clear memory"""
        if self.client:
            try:
                self.client.close()
                logger.info("Weaviate connection closed")
            except Exception as e:
                logger.error(f"Error closing Weaviate connection: {e}")
        
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