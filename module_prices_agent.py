"""
Module Prices Analysis Agent
============================

A Pydantic AI agent for analyzing solar component prices using PandasAI.
Similar to the market data agent but focused on component pricing data.
"""

import asyncio
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import pandas as pd
import uuid
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
import pandasai as pai
from pandasai_litellm.litellm import LiteLLM
from dotenv import load_dotenv

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
    model: str = "openai:gpt-4o"
    request_limit: int = 10
    total_tokens_limit: int = 5000
    verbose: bool = True

class ModulePricesAgent:
    """
    Solar component prices analysis agent using PandasAI
    """
    
    def __init__(self, config: Optional[ModulePricesConfig] = None):
        self.config = config or ModulePricesConfig()
        self.conversation_memory: Dict[str, List[ModelMessage]] = {}
        self._initialize_pandasai()
        self._initialize_agent()

        # Create exports directory for dataframes
        self.EXPORTS_DIR = os.path.join('exports', 'data')
        os.makedirs(self.EXPORTS_DIR, exist_ok=True)
        
        # Create directories for plots/charts
        self.PLOTS_DIR = os.path.join('static', 'plots')
        self.CHARTS_EXPORT_DIR = os.path.join('exports', 'charts')
        os.makedirs(self.PLOTS_DIR, exist_ok=True)
        os.makedirs(self.CHARTS_EXPORT_DIR, exist_ok=True)
        
        # Track last generated DataFrame for table rendering
        self.last_dataframe = None
        
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
    
    def _plot_module_price_trends_to_path(self, df: pd.DataFrame, item: str = None, region: str = None, descriptions: List[str] = None, save_path: str = None, export_path: str = None) -> bool:
        """
        Create a plot showing module price trends over time and save to specific paths
        
        Args:
            df: DataFrame with price data
            item: Component item to filter by (e.g., 'Module', 'Cell', 'Wafer')
            region: Region to filter by (e.g., 'US', 'China', 'Europe') 
            descriptions: List of descriptions to include in the plot
            save_path: Path to save the plot for web serving
            export_path: Path to save the plot for download
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Make a copy to avoid modifying original data
            plot_df = df.copy()
            
            # Ensure date column is datetime
            if 'date' in plot_df.columns:
                if plot_df['date'].dtype == 'object':
                    # Try to parse various date formats
                    plot_df['date'] = pd.to_datetime(plot_df['date'], errors='coerce')
            
            # Apply filters
            if item and 'item' in plot_df.columns:
                plot_df = plot_df[plot_df['item'].str.contains(item, case=False, na=False)]
            
            if region and 'region' in plot_df.columns:
                plot_df = plot_df[plot_df['region'].str.contains(region, case=False, na=False)]
            
            if descriptions and 'description' in plot_df.columns:
                plot_df = plot_df[plot_df['description'].isin(descriptions)]
            
            if plot_df.empty:
                logger.warning("No data available after filtering for the plot")
                return False
            
            # Create the plot
            plt.figure(figsize=(14, 8))
            
            # Group by description if available, otherwise plot all data
            if 'description' in plot_df.columns and len(plot_df['description'].unique()) > 1:
                for desc, group in plot_df.groupby('description'):
                    if 'date' in group.columns and 'base_price' in group.columns:
                        # Group by date and calculate mean price
                        group_avg = group.groupby('date')['base_price'].mean().reset_index()
                        group_avg = group_avg.sort_values('date')
                        plt.plot(group_avg['date'], group_avg['base_price'], 
                                label=desc, marker='o', linewidth=2, markersize=4)
            else:
                # Single line plot
                if 'date' in plot_df.columns and 'base_price' in plot_df.columns:
                    plot_data = plot_df.groupby('date')['base_price'].mean().reset_index()
                    plot_data = plot_data.sort_values('date')
                    label = f"{item or 'Component'} in {region or 'All Regions'}"
                    plt.plot(plot_data['date'], plot_data['base_price'], 
                            label=label, marker='o', linewidth=2, markersize=4)
            
            # Customize the plot
            title_parts = []
            if item:
                title_parts.append(item)
            title_parts.append("Price Trends")
            if region:
                title_parts.append(f"in {region}")
            
            plt.title(' '.join(title_parts), fontsize=16, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Base Price (US$/Wp)', fontsize=12)
            
            # Format x-axis
            plt.xticks(rotation=45)
            
            # Add grid and legend
            plt.grid(True, alpha=0.3)
            if len(plt.gca().get_lines()) > 1:
                plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            plt.tight_layout()
            
            # Save the plot to both paths
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            if export_path:
                plt.savefig(export_path, dpi=300, bbox_inches='tight')
            
            plt.close()  # Important: close the figure to free memory
            
            logger.info(f"Module price plot saved to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating module price plot: {e}")
            plt.close()  # Ensure figure is closed even on error
            return False
    
    def _ensure_list(self, val):
        """Helper method to ensure a value is a list, handling comma-separated strings"""
        if isinstance(val, list):
            return val
        if isinstance(val, str) and ',' in val:
            return [v.strip() for v in val.split(',')]
        return val

    def _plot_price_distribution_boxplot(self, item: str = "all", description: str = "all", region_filter: str = "all", x_axis: str = "region", save_path: str = None) -> bool:
        """
        Create a boxplot showing price distribution with flexible x-axis categories
        
        Args:
            item: Component item to filter by (e.g., 'Module', 'Cell', 'Wafer') or "all" or list of items
            description: Description to filter by (e.g., 'n-type mono-Si HJT') or "all" or list of descriptions
            region_filter: Region filter (e.g., 'US', 'China') or "all" or list of regions
            x_axis: What to plot on x-axis - "region", "item", or "description"
            save_path: Path to save the plot
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load data from the component prices dataset
            df = self.component_prices.copy()
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            filtered_df = df.copy()
            
            # Helper function to handle single values or lists
            def process_filter(value, column_name):
                value = self._ensure_list(value)
                if value == "all":
                    return filtered_df
                elif isinstance(value, list):
                    return filtered_df[filtered_df[column_name].isin(value)]
                else:
                    return filtered_df[filtered_df[column_name] == value]
            
            # Apply filters only if not "all"
            if item != "all":
                filtered_df = process_filter(item, 'item')
                logger.info(f"Filtered by item '{item}': {len(filtered_df)} rows remaining")
            
            if description != "all":
                filtered_df = process_filter(description, 'description')
                logger.info(f"Filtered by description '{description}': {len(filtered_df)} rows remaining")
            
            if region_filter != "all":
                region_val = self._ensure_list(region_filter)
                if isinstance(region_val, list):
                    region_mapping = {
                        'EU': 'EU', 'EUROPE': 'EU', 'EUROPEAN UNION': 'EU',
                        'USA': 'US', 'UNITED STATES': 'US', 'AMERICA': 'US',
                        'CHINA': 'China', 'INDIA': 'India', 'OVERSEAS': 'Overseas', 'AUSTRALIA': 'Australia'
                    }
                    normalized_regions = [region_mapping.get(r.upper(), r) for r in region_val]
                    logger.info(f"Region mapping: {region_val} -> {normalized_regions}")
                    available_regions = filtered_df['region'].unique()
                    logger.info(f"Available regions in dataset: {available_regions}")
                    filtered_df = filtered_df[filtered_df['region'].isin(normalized_regions)]
                    logger.info(f"Filtered by regions {normalized_regions}: {len(filtered_df)} rows remaining")
                else:
                    region_mapping = {
                        'EU': 'EU', 'EUROPE': 'EU', 'EUROPEAN UNION': 'EU',
                        'USA': 'US', 'UNITED STATES': 'US', 'AMERICA': 'US',
                        'CHINA': 'China', 'INDIA': 'India', 'OVERSEAS': 'Overseas', 'AUSTRALIA': 'Australia'
                    }
                    normalized_region = region_mapping.get(region_filter.upper(), region_filter)
                    logger.info(f"Region mapping: '{region_filter}' -> '{normalized_region}'")
                    available_regions = filtered_df['region'].unique()
                    logger.info(f"Available regions in dataset: {available_regions}")
                    filtered_df = filtered_df[filtered_df['region'].str.contains(normalized_region, case=False, na=False)]
                    logger.info(f"Filtered by region '{normalized_region}': {len(filtered_df)} rows remaining")
            
            if filtered_df.empty:
                logger.warning("No data available for boxplot after filtering")
                return False
            
            # Validate x_axis parameter
            valid_x_axes = ["region", "item", "description"]
            if x_axis.lower() not in valid_x_axes:
                logger.error(f"Invalid x_axis '{x_axis}'. Must be one of: {valid_x_axes}")
                return False
            
            # Convert x_axis to lowercase to match column names
            x_axis = x_axis.lower()
            
            # Log what categories are available for the chosen x_axis
            available_categories = filtered_df[x_axis].unique()
            logger.info(f"Available {x_axis}s in filtered data: {available_categories}")
            
            # Create the plot
            plt.figure(figsize=(12, 6))
            sns.boxplot(data=filtered_df, x=x_axis, y='base_price')
            title_parts = [f"Distribution of Prices by {x_axis.title()}"]
            if item != "all":
                title_parts.append(f"Item: {item}")
            if description != "all":
                title_parts.append(f"Description: {description}")
            if region_filter != "all":
                title_parts.append(f"Region: {region_filter}")
            plt.title('\n'.join(title_parts))
            plt.xlabel(x_axis.title())
            plt.ylabel('Base Price (US$/Wp)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                logger.info(f"Boxplot saved to {save_path}")
                return True
            else:
                plt.show()
                return True
        except Exception as e:
            logger.error(f"Error creating price distribution boxplot: {e}")
            plt.close()
            return False

    def _plot_avg_prices_by_description(self, item: str = "all", description_filter: str = "all", region_filter: str = "all", save_path: str = None) -> bool:
        try:
            df = self.component_prices.copy()
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            filtered_df = df.copy()
            def process_filter(value, column_name):
                value = self._ensure_list(value)
                if value == "all":
                    return filtered_df
                elif isinstance(value, list):
                    return filtered_df[filtered_df[column_name].isin(value)]
                else:
                    return filtered_df[filtered_df[column_name] == value]
            if item != "all":
                filtered_df = process_filter(item, 'item')
                logger.info(f"Filtered by item '{item}': {len(filtered_df)} rows remaining")
            if description_filter != "all":
                filtered_df = process_filter(description_filter, 'description')
                logger.info(f"Filtered by description '{description_filter}': {len(filtered_df)} rows remaining")
            if region_filter != "all":
                region_val = self._ensure_list(region_filter)
                if isinstance(region_val, list):
                    region_mapping = {
                        'EU': 'EU', 'EUROPE': 'EU', 'EUROPEAN UNION': 'EU',
                        'USA': 'US', 'UNITED STATES': 'US', 'AMERICA': 'US',
                        'CHINA': 'China', 'INDIA': 'India', 'OVERSEAS': 'Overseas', 'AUSTRALIA': 'Australia'
                    }
                    normalized_regions = [region_mapping.get(r.upper(), r) for r in region_val]
                    logger.info(f"Region mapping: {region_val} -> {normalized_regions}")
                    available_regions = filtered_df['region'].unique()
                    logger.info(f"Available regions in dataset: {available_regions}")
                    filtered_df = filtered_df[filtered_df['region'].isin(normalized_regions)]
                    logger.info(f"Filtered by regions {normalized_regions}: {len(filtered_df)} rows remaining")
                else:
                    region_mapping = {
                        'EU': 'EU', 'EUROPE': 'EU', 'EUROPEAN UNION': 'EU',
                        'USA': 'US', 'UNITED STATES': 'US', 'AMERICA': 'US',
                        'CHINA': 'China', 'INDIA': 'India', 'OVERSEAS': 'Overseas', 'AUSTRALIA': 'Australia'
                    }
                    normalized_region = region_mapping.get(region_filter.upper(), region_filter)
                    logger.info(f"Region mapping: '{region_filter}' -> '{normalized_region}'")
                    available_regions = filtered_df['region'].unique()
                    logger.info(f"Available regions in dataset: {available_regions}")
                    filtered_df = filtered_df[filtered_df['region'].str.contains(normalized_region, case=False, na=False)]
                    logger.info(f"Filtered by region '{normalized_region}': {len(filtered_df)} rows remaining")
            if filtered_df.empty:
                logger.warning("No data available for average price chart after filtering")
                return False
            avg_by_desc = filtered_df.groupby('description')['base_price'].mean().sort_values()
            logger.info(f"Average prices by description: {avg_by_desc.to_dict()}")
            plt.figure(figsize=(12, 6))
            avg_by_desc.plot(kind='barh')
            title_parts = [f"Average Prices by Description"]
            if item != "all":
                title_parts.append(f"Item: {item}")
            if region_filter != "all":
                title_parts.append(f"Region: {region_filter}")
            plt.title('\n'.join(title_parts))
            plt.xlabel('Base Price (US$/Wp)')
            plt.ylabel('Description')
            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                logger.info(f"Average price chart saved to {save_path}")
                return True
            else:
                plt.show()
                return True
        except Exception as e:
            logger.error(f"Error creating average price chart: {e}")
            plt.close()
            return False

    def _plot_module_price_trends_from_dataset(self, item: str = None, region: str = None, descriptions: list = None, save_path: str = None, export_path: str = None) -> bool:
        try:
            logger.info("Loading component prices dataset for plotting...")
            df = self.component_prices.copy()
            logger.info(f"Loaded dataset with shape: {df.shape}")
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')

            # --- Filtering ---
            # Item
            if item and item != "all":
                item_val = self._ensure_list(item)
                if isinstance(item_val, list):
                    df = df[df['item'].isin(item_val)]
                else:
                    df = df[df['item'] == item_val]
                logger.info(f"Filtered by item '{item}': {len(df)} rows remaining")
            # Descriptions
            if descriptions and descriptions != "all":
                desc_val = self._ensure_list(descriptions)
                if isinstance(desc_val, list):
                    df = df[df['description'].isin(desc_val)]
                else:
                    df = df[df['description'] == desc_val]
                logger.info(f"Filtered by descriptions '{descriptions}': {len(df)} rows remaining")
            # Regions
            if region and region != "all":
                region_val = self._ensure_list(region)
                region_mapping = {
                    'EU': 'EU', 'EUROPE': 'EU', 'EUROPEAN UNION': 'EU',
                    'USA': 'US', 'UNITED STATES': 'US', 'AMERICA': 'US',
                    'CHINA': 'China', 'INDIA': 'India', 'OVERSEAS': 'Overseas', 'AUSTRALIA': 'Australia'
                }
                if isinstance(region_val, list):
                    normalized_regions = [region_mapping.get(r.upper(), r) for r in region_val]
                    df = df[df['region'].isin(normalized_regions)]
                else:
                    normalized_region = region_mapping.get(region_val.upper(), region_val)
                    df = df[df['region'] == normalized_region]
                logger.info(f"Filtered by region(s) '{region}': {len(df)} rows remaining")

            if df.empty:
                logger.warning("No data available after filtering for the plot")
                return False

            # --- Plotting ---
            plt.figure(figsize=(14, 6))
            for (desc, region_val), group in df.groupby(['description', 'region']):
                group_avg = group.groupby('date')['base_price'].mean().reset_index()
                label = f"{desc} ({region_val})"
                plt.plot(group_avg['date'], group_avg['base_price'], label=label)

            plt.title('Price Trends Over Time by Description and Region')
            plt.xlabel('Date')
            plt.ylabel('Base Price (US$/Wp)')
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.xticks(rotation=45)
            plt.grid(True)
            plt.tight_layout()
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            if export_path:
                plt.savefig(export_path, dpi=300, bbox_inches='tight')
            plt.close()
            logger.info(f"Module price plot saved to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating module price plot from dataset: {e}")
            plt.close()
            return False

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
        """Initialize the Pydantic AI agent"""
        system_prompt="""You are a data analyst querying solar component prices using PandasAI.
        You are analyzing a dataset of solar component prices. Each row represents the price of a specific solar PV component on a certain date and in a specific region. The dataset includes the following fields:

        Item: The general category of the solar component. Possible values include Aluminium, Cell, Copper, EVA, Module, PV glass, Polysilicon, Silver, and Wafer.

        Description: A more detailed description of the component, such as its technology or subtype (e.g., "n-type mono-Si HJT").

        Date: The date on which the price was recorded. Dates are in the format MM/DD/YYYY.

        Frequency: How often the price is reported (typically "Weekly").

        Base Price: The price of the component, expressed as a floating-point number in USD.

        Unit: The unit in which the price is reported (e.g., US$/Wp, US$/kg).

        Region: The geographical area associated with the price, such as China or Overseas.

        Source: The origin of the price data. Some records may have this field missing.
        
        Available tools:
        1. 'analyze_component_prices' - Use this to query and analyze solar component price data
        2. 'plot_module_price_trends' - Use this to create charts/graphs/plots of price trends over time
        3. 'plot_price_boxplot' - Use this to create boxplots showing price distributions by region, item, or description
        4. 'plot_avg_prices_by_description' - Use this to create horizontal bar charts showing average prices by description
        
        IMPORTANT: When users ask for visualizations, use the appropriate tool:
        - For time series trends: use 'plot_module_price_trends'
        - For boxplots/distributions: use 'plot_price_boxplot'
        - For average price comparisons: use 'plot_avg_prices_by_description'
        
        MULTI-VALUE SUPPORT: All plotting tools support multiple values for items, regions, and descriptions:
        - Use comma-separated values: "Module,Cell,Wafer" or "China,US,EU" or "n-type mono-Si HJT,mono-Si PERC"
        - This allows comparing multiple components, regions, or technologies in a single plot
        
        Examples:
        - "plot the modules prices in india" → plot_module_price_trends(item="Module", region="India")
        - "show me a chart of wafer prices" → plot_module_price_trends(item="Wafer")
        - "create a graph of cell prices in China" → plot_module_price_trends(item="Cell", region="China")
        - "show box plots for modules" → plot_price_boxplot(item="Module")
        - "show average prices by description" → plot_avg_prices_by_description()
        - "boxplot of prices by region" → plot_price_boxplot(x_axis="region")
        - "compare Module and Cell prices in China and US" → plot_module_price_trends(item="Module,Cell", region="China,US")
        - "show boxplots for all regions" → plot_price_boxplot(region_filter="China,US,EU,India,Overseas")
        - "average prices for n-type and p-type technologies" → plot_avg_prices_by_description(description_filter="n-type mono-Si HJT,mono-Si PERC")
        
        The plotting tools will load the data internally, so you don't need to query data first.
        
        CRITICAL: If any plotting tool returns a response starting with "PLOT_GENERATED|", return that response exactly as-is. Do NOT convert it to markdown or add any additional text. Do NOT wrap it in any formatting. Return the raw string exactly as received from the tool.
        """,

        
        self.agent = Agent(
            model=self.config.model,
            system_prompt=system_prompt,
        )
        
        # Create nested plotting agent (like market agent)
        async def price_trend_factory(ctx: RunContext[None], item: str = None, region: str = None, descriptions_csv: str = None) -> str:
            """Factory function for creating price trend plots."""
            try:
                # Parse descriptions if provided
                descriptions = None
                if descriptions_csv:
                    descriptions = [desc.strip() for desc in descriptions_csv.split(',')]
                
                # Parse item if it's a comma-separated list
                item_list = None
                if item and ',' in item:
                    item_list = [item.strip() for item in item.split(',')]
                elif item:
                    item_list = item
                
                # Parse region if it's a comma-separated list
                region_list = None
                if region and ',' in region:
                    region_list = [region.strip() for region in region.split(',')]
                elif region:
                    region_list = region
                
                # Generate unique filename
                filename_parts = ["module_prices"]
                if item_list:
                    if isinstance(item_list, list):
                        filename_parts.append("_".join([i.lower().replace(' ', '_') for i in item_list]))
                    else:
                        filename_parts.append(item_list.lower().replace(' ', '_'))
                if region_list:
                    if isinstance(region_list, list):
                        filename_parts.append("_".join([r.lower().replace(' ', '_') for r in region_list]))
                    else:
                        filename_parts.append(region_list.lower().replace(' ', '_'))
                filename_parts.append(f"{uuid.uuid4().hex[:8]}")
                
                file_name = "_".join(filename_parts) + ".png"
                save_path = os.path.join(self.PLOTS_DIR, file_name)
                url_path = f"/static/plots/{file_name}"
                export_path = os.path.join(self.CHARTS_EXPORT_DIR, file_name)
                
                # Create the plot using the entire dataset (like market agent)
                plot_result = self._plot_module_price_trends_from_dataset(
                    item=item_list,
                    region=region_list,
                    descriptions=descriptions,
                    save_path=save_path,
                    export_path=export_path
                )
                
                if plot_result:
                    return f"PLOT_GENERATED|{url_path}|"
                else:
                    return "Failed to generate plot. Please check if the data contains the requested filters."
                    
            except Exception as e:
                error_msg = f"Error creating plot: {str(e)}"
                logger.error(error_msg)
                return error_msg
        
        # Create nested plotting agent
        async def price_boxplot_factory(ctx: RunContext[None], item: str = "all", description: str = "all", region_filter: str = "all", x_axis: str = "region") -> str:
            try:
                # Parse item if it's a comma-separated list
                item_list = "all"
                if item != "all" and ',' in item:
                    item_list = [item.strip() for item in item.split(',')]
                elif item != "all":
                    item_list = item
                
                # Parse description if it's a comma-separated list
                description_list = "all"
                if description != "all" and ',' in description:
                    description_list = [desc.strip() for desc in description.split(',')]
                elif description != "all":
                    description_list = description
                
                # Parse region if it's a comma-separated list
                region_list = "all"
                if region_filter != "all" and ',' in region_filter:
                    region_list = [region.strip() for region in region_filter.split(',')]
                elif region_filter != "all":
                    region_list = region_filter
                
                # Create descriptive filename
                filename_parts = ["boxplot"]
                if item_list != "all":
                    if isinstance(item_list, list):
                        filename_parts.append("_".join([i.lower().replace(' ', '_') for i in item_list]))
                    else:
                        filename_parts.append(item_list.lower().replace(' ', '_'))
                if description_list != "all":
                    if isinstance(description_list, list):
                        filename_parts.append("_".join([d.lower().replace(' ', '_').replace('-', '_') for d in description_list]))
                    else:
                        filename_parts.append(description_list.lower().replace(' ', '_').replace('-', '_'))
                if region_list != "all":
                    if isinstance(region_list, list):
                        filename_parts.append("_".join([r.lower().replace(' ', '_') for r in region_list]))
                    else:
                        filename_parts.append(region_list.lower().replace(' ', '_'))
                filename_parts.append(f"by_{x_axis}")
                filename_parts.append(f"{uuid.uuid4().hex[:8]}")
                
                filename = "_".join(filename_parts) + ".png"
                save_path = os.path.join(self.PLOTS_DIR, filename)
                url_path = f"/static/plots/{filename}"
                
                result = self._plot_price_distribution_boxplot(item_list, description_list, region_list, x_axis, save_path)
                if result:
                    return f"PLOT_GENERATED|{url_path}|"
                else:
                    return "Failed to generate boxplot. Please check if the data contains the requested filters."
            except Exception as e:
                logger.error(f"Error in boxplot factory: {e}")
                return f"Error creating boxplot: {str(e)}"

        # Create nested plotting agent
        async def avg_price_factory(ctx: RunContext[None], item: str = "all", description_filter: str = "all", region_filter: str = "all") -> str:
            try:
                # Parse item if it's a comma-separated list
                item_list = "all"
                if item != "all" and ',' in item:
                    item_list = [item.strip() for item in item.split(',')]
                elif item != "all":
                    item_list = item
                
                # Parse description if it's a comma-separated list
                description_list = "all"
                if description_filter != "all" and ',' in description_filter:
                    description_list = [desc.strip() for desc in description_filter.split(',')]
                elif description_filter != "all":
                    description_list = description_filter
                
                # Parse region if it's a comma-separated list
                region_list = "all"
                if region_filter != "all" and ',' in region_filter:
                    region_list = [region.strip() for region in region_filter.split(',')]
                elif region_filter != "all":
                    region_list = region_filter
                
                # Create descriptive filename
                filename_parts = ["avg_price"]
                if item_list != "all":
                    if isinstance(item_list, list):
                        filename_parts.append("_".join([i.lower().replace(' ', '_') for i in item_list]))
                    else:
                        filename_parts.append(item_list.lower().replace(' ', '_'))
                if description_list != "all":
                    if isinstance(description_list, list):
                        filename_parts.append("_".join([d.lower().replace(' ', '_').replace('-', '_') for d in description_list]))
                    else:
                        filename_parts.append(description_list.lower().replace(' ', '_').replace('-', '_'))
                if region_list != "all":
                    if isinstance(region_list, list):
                        filename_parts.append("_".join([r.lower().replace(' ', '_') for r in region_list]))
                    else:
                        filename_parts.append(region_list.lower().replace(' ', '_'))
                filename_parts.append(f"{uuid.uuid4().hex[:8]}")
                
                filename = "_".join(filename_parts) + ".png"
                save_path = os.path.join(self.PLOTS_DIR, filename)
                url_path = f"/static/plots/{filename}"
                
                result = self._plot_avg_prices_by_description(item_list, description_list, region_list, save_path)
                if result:
                    return f"PLOT_GENERATED|{url_path}|"
                else:
                    return "Failed to generate average price chart. Please check if the data contains the requested filters."
            except Exception as e:
                logger.error(f"Error in avg price factory: {e}")
                return f"Error creating average price chart: {str(e)}"

        # Create the nested plotting agent
        self.plot_generation_agent = Agent(
            model="openai:gpt-4o",
            output_type=[price_trend_factory, price_boxplot_factory, avg_price_factory],
            system_prompt=(
                "You are a plotting assistant for solar component prices.\n\n"
                "Tool-selection rules:\n"
                "• When users ask for price trends, charts, graphs, or visualizations over time, call `price_trend_factory`.\n"
                "• When users ask for a boxplot, distribution, or comparison of price distributions by region, call `price_boxplot_factory`.\n"
                "• When users ask for average prices, mean prices, or price comparisons by description, call `avg_price_factory`.\n"
                "• Extract item from phrases like 'module prices', 'cell prices', 'wafer prices', 'polysilicon prices'.\n"
                "• Extract region from phrases like 'in India', 'in China', 'in US', 'in Europe'.\n"
                "• Extract descriptions from specific technology mentions like 'n-type mono-Si HJT', 'mono-Si PERC'.\n\n"
                "Parameter extraction:\n"
                "• Extract item from: Module, Cell, Wafer, Polysilicon, EVA, PV glass, Silver, Copper, Aluminium.\n"
                "• Extract region from: US, China, EU, India, Overseas, Australia.\n"
                "• Region mapping: 'EU' → 'EU', 'Europe' → 'EU', 'USA' → 'US', 'United States' → 'US'.\n"
                "• For boxplots, you can use 'all' for any parameter to show all available data:\n"
                "  - 'all' for item: shows all component types\n"
                "  - 'all' for description: shows all technologies/descriptions\n"
                "  - 'all' for region_filter: shows all regions\n"
                "• x_axis parameter controls what's plotted on x-axis:\n"
                "  - 'region': boxes represent different regions (default)\n"
                "  - 'item': boxes represent different component types (Module, Cell, etc.)\n"
                "  - 'description': boxes represent different technologies (n-type mono-Si HJT, etc.)\n"
                "• x_axis values must be lowercase: 'region', 'item', 'description'.\n"
                "• For average price charts, use 'all' for any parameter to show all available data.\n"
                "• If no item is specified, pass 'all' to show all components.\n"
                "• If no region is specified, pass 'all' to show all regions.\n"
                "• If no description is specified, pass 'all' to show all descriptions.\n"
                "• If no x_axis is specified, pass 'region' (default).\n\n"
                "Return ONLY the tool output you receive. Do NOT add extra commentary or markdown."
            ),
        )
        
        # Register the component prices analysis tool
        @self.agent.tool(name="analyze_component_prices")
        async def analyze_component_prices(ctx: RunContext[None], query: str) -> str:
            """
            Analyze solar component prices using PandasAI

            Available item types in the dataset:
            - Aluminium
            - Cell
            - Copper
            - EVA
            - Module
            - PV glass
            - Polysilicon
            - Silver
            - Wafer

            Args:
                query: Natural language query about component prices
                
            Returns:
                Analysis result as string
            """
            try:
                logger.info(f"Executing component prices query: {query}")
                # Prepend exact item names to help LLM use correct spelling
                item_list = (
                    "Available items in the dataset (use exact spelling): "
                    "Aluminium, Cell, Copper, EVA, Module, PV glass, Polysilicon, Silver, Wafer.\n\n"
                )
                enriched_query = item_list + query
                response = self.component_prices.chat(enriched_query)

                print("--- PANDASAI RAW RESPONSE ---")
                print(f"Type: {type(response)}")
                print(f"Content:\n{response}")
                print("-----------------------------")

                # Check if the response is a DataFrame to save it
                df_to_save = None
                if hasattr(response, 'value') and isinstance(response.value, pd.DataFrame):
                    df_to_save = response.value
                    print(f"DEBUG: Found DataFrame in response.value with shape {df_to_save.shape}")
                elif isinstance(response, pd.DataFrame):
                    df_to_save = response
                    print(f"DEBUG: Found DataFrame directly with shape {df_to_save.shape}")

                if df_to_save is not None and not df_to_save.empty:
                    # Store DataFrame for table rendering and potential download
                    self.last_dataframe = df_to_save
                    print(f"DEBUG: DataFrame stored for table rendering and download")
                else:
                    print(f"DEBUG: No DataFrame detected or DataFrame is empty")
                    self.last_dataframe = None
                
                # Handle other response types
                if response is None:
                    return "No data found for your query."
                elif hasattr(response, 'empty') and response.empty:
                    return "No data found for your query."
                elif hasattr(response, 'to_string'):
                    # For DataFrames, limit size to avoid token limits
                    if df_to_save is not None and len(df_to_save) > 10:
                        # Show first 10 rows + summary for large DataFrames
                        display_text = df_to_save.head(10).to_string()
                        total_rows = len(df_to_save)
                        return f"{display_text}\n\n... and {total_rows - 10} more rows. Full data available in table below."
                    else:
                        # For small DataFrames, show all
                        return response.to_string()
                else:
                    # It's a string, number, or other type
                    return str(response)

            except Exception as e:
                error_msg = f"Error analyzing component prices: {str(e)}"
                logger.error(error_msg)
                return error_msg

        # Register the plotting tool (wrapper that delegates to nested agent)
        @self.agent.tool(name="plot_module_price_trends")
        async def plot_module_price_trends(ctx: RunContext[None], item: str = None, region: str = None, descriptions_csv: str = None) -> str:
            """
            Create a plot showing module/component price trends over time
            
            Use this tool when the user asks for a chart, graph, plot, or visualization of price trends.
            
            Args:
                item: Component type (e.g., 'Module', 'Cell', 'Wafer', 'Polysilicon', 'EVA', 'PV glass', 'Silver', 'Copper', 'Aluminium') or comma-separated list
                region: Region filter (e.g., 'US', 'China', 'Europe', 'Overseas') or comma-separated list
                descriptions_csv: Comma-separated list of descriptions to include (e.g., 'n-type mono-Si HJT,mono-Si PERC')
                
            Returns:
                Status message about the plot generation
            """
            try:
                # Parse descriptions if provided
                descriptions = None
                if descriptions_csv:
                    descriptions = [desc.strip() for desc in descriptions_csv.split(',')]
                
                # Parse item if it's a comma-separated list
                item_list = None
                if item and ',' in item:
                    item_list = [item.strip() for item in item.split(',')]
                elif item:
                    item_list = item
                
                # Parse region if it's a comma-separated list
                region_list = None
                if region and ',' in region:
                    region_list = [region.strip() for region in region.split(',')]
                elif region:
                    region_list = region
                
                # Generate unique filename
                filename_parts = ["module_prices"]
                if item_list:
                    if isinstance(item_list, list):
                        filename_parts.append("_".join([i.lower().replace(' ', '_') for i in item_list]))
                    else:
                        filename_parts.append(item_list.lower().replace(' ', '_'))
                if region_list:
                    if isinstance(region_list, list):
                        filename_parts.append("_".join([r.lower().replace(' ', '_') for r in region_list]))
                    else:
                        filename_parts.append(region_list.lower().replace(' ', '_'))
                filename_parts.append(f"{uuid.uuid4().hex[:8]}")
                
                file_name = "_".join(filename_parts) + ".png"
                save_path = os.path.join(self.PLOTS_DIR, file_name)
                url_path = f"/static/plots/{file_name}"
                export_path = os.path.join(self.CHARTS_EXPORT_DIR, file_name)
                
                logger.info(f"PLOT TOOL CALLED: item={item}, region={region}, descriptions={descriptions_csv}")
                
                # Create the plot directly (like market agent)
                plot_result = self._plot_module_price_trends_from_dataset(
                    item=item_list,
                    region=region_list,
                    descriptions=descriptions,
                    save_path=save_path,
                    export_path=export_path
                )
                
                if plot_result:
                    return f"PLOT_GENERATED|{url_path}|"
                else:
                    return "Failed to generate plot. Please check if the data contains the requested filters."
                    
            except Exception as e:
                error_msg = f"Error creating plot: {str(e)}"
                logger.error(error_msg)
                return error_msg

        # Register as a tool on the main agent
        @self.agent.tool(name="plot_price_boxplot")
        async def plot_price_boxplot(ctx: RunContext[None], item: str = "all", description: str = "all", region_filter: str = "all", x_axis: str = "region") -> str:
            try:
                # Parse item if it's a comma-separated list
                item_list = "all"
                if item != "all" and ',' in item:
                    item_list = [item.strip() for item in item.split(',')]
                elif item != "all":
                    item_list = item
                
                # Parse description if it's a comma-separated list
                description_list = "all"
                if description != "all" and ',' in description:
                    description_list = [desc.strip() for desc in description.split(',')]
                elif description != "all":
                    description_list = description
                
                # Parse region if it's a comma-separated list
                region_list = "all"
                if region_filter != "all" and ',' in region_filter:
                    region_list = [region.strip() for region in region_filter.split(',')]
                elif region_filter != "all":
                    region_list = region_filter
                
                # Create descriptive filename
                filename_parts = ["boxplot"]
                if item_list != "all":
                    if isinstance(item_list, list):
                        filename_parts.append("_".join([i.lower().replace(' ', '_') for i in item_list]))
                    else:
                        filename_parts.append(item_list.lower().replace(' ', '_'))
                if description_list != "all":
                    if isinstance(description_list, list):
                        filename_parts.append("_".join([d.lower().replace(' ', '_').replace('-', '_') for d in description_list]))
                    else:
                        filename_parts.append(description_list.lower().replace(' ', '_').replace('-', '_'))
                if region_list != "all":
                    if isinstance(region_list, list):
                        filename_parts.append("_".join([r.lower().replace(' ', '_') for r in region_list]))
                    else:
                        filename_parts.append(region_list.lower().replace(' ', '_'))
                filename_parts.append(f"by_{x_axis}")
                filename_parts.append(f"{uuid.uuid4().hex[:8]}")
                
                filename = "_".join(filename_parts) + ".png"
                save_path = os.path.join(self.PLOTS_DIR, filename)
                url_path = f"/static/plots/{filename}"
                
                result = self._plot_price_distribution_boxplot(item_list, description_list, region_list, x_axis, save_path)
                if result:
                    return f"PLOT_GENERATED|{url_path}|"
                else:
                    return "Failed to generate boxplot. Please check if the data contains the requested filters."
            except Exception as e:
                logger.error(f"Error in boxplot tool: {e}")
                return f"Error creating boxplot: {str(e)}"

        # Register as a tool on the main agent
        @self.agent.tool(name="plot_avg_prices_by_description")
        async def plot_avg_prices_by_description(ctx: RunContext[None], item: str = "all", description_filter: str = "all", region_filter: str = "all") -> str:
            try:
                # Parse item if it's a comma-separated list
                item_list = "all"
                if item != "all" and ',' in item:
                    item_list = [item.strip() for item in item.split(',')]
                elif item != "all":
                    item_list = item
                
                # Parse description if it's a comma-separated list
                description_list = "all"
                if description_filter != "all" and ',' in description_filter:
                    description_list = [desc.strip() for desc in description_filter.split(',')]
                elif description_filter != "all":
                    description_list = description_filter
                
                # Parse region if it's a comma-separated list
                region_list = "all"
                if region_filter != "all" and ',' in region_filter:
                    region_list = [region.strip() for region in region_filter.split(',')]
                elif region_filter != "all":
                    region_list = region_filter
                
                # Create descriptive filename
                filename_parts = ["avg_price"]
                if item_list != "all":
                    if isinstance(item_list, list):
                        filename_parts.append("_".join([i.lower().replace(' ', '_') for i in item_list]))
                    else:
                        filename_parts.append(item_list.lower().replace(' ', '_'))
                if description_list != "all":
                    if isinstance(description_list, list):
                        filename_parts.append("_".join([d.lower().replace(' ', '_').replace('-', '_') for d in description_list]))
                    else:
                        filename_parts.append(description_list.lower().replace(' ', '_').replace('-', '_'))
                if region_list != "all":
                    if isinstance(region_list, list):
                        filename_parts.append("_".join([r.lower().replace(' ', '_') for r in region_list]))
                    else:
                        filename_parts.append(region_list.lower().replace(' ', '_'))
                filename_parts.append(f"{uuid.uuid4().hex[:8]}")
                
                filename = "_".join(filename_parts) + ".png"
                save_path = os.path.join(self.PLOTS_DIR, filename)
                url_path = f"/static/plots/{filename}"
                
                result = self._plot_avg_prices_by_description(item_list, description_list, region_list, save_path)
                if result:
                    return f"PLOT_GENERATED|{url_path}|"
                else:
                    return "Failed to generate average price chart. Please check if the data contains the requested filters."
            except Exception as e:
                logger.error(f"Error in avg price tool: {e}")
                return f"Error creating average price chart: {str(e)}"




    async def analyze(self, query: str, conversation_id: str = None) -> Dict[str, Any]:
        """
        Analyze component prices based on user query
        
        Args:
            query: Natural language query about component prices
            conversation_id: Optional conversation ID for memory tracking
            
        Returns:
            Dictionary with analysis results and metadata
        """
        try:
            usage_limits = UsageLimits(
                request_limit=self.config.request_limit,
                total_tokens_limit=self.config.total_tokens_limit
            )
            
            # Clear last_dataframe at the start of each analyze call
            self.last_dataframe = None

            # Get conversation history if conversation_id is provided
            message_history: List[ModelMessage] = []
            if conversation_id and conversation_id in self.conversation_memory:
                message_history = self.conversation_memory[conversation_id]
                logger.info(f"[MEMORY DEBUG] Using conversation memory for {conversation_id} with {len(message_history)} messages")
            logger.info(f"[MEMORY DEBUG] Conversation ID: {conversation_id}")
            logger.info(f"[MEMORY DEBUG] Message history before agent call: {message_history}")
            
            logger.info(f"Processing query: {query}")
            result = await self.agent.run(query, message_history=message_history, usage_limits=usage_limits)
            
            logger.info(f"[MEMORY DEBUG] New messages from agent: {result.new_messages()}")
            
            # Store the new messages for future conversation context
            if conversation_id:
                # Always replace with the full message history (all_messages), not just new_messages
                self.conversation_memory[conversation_id] = result.all_messages()
                logger.info(f"[MEMORY DEBUG] Updated conversation memory for {conversation_id}: {self.conversation_memory[conversation_id]}")
            
            # Check if a DataFrame was generated and format response accordingly
            analysis_result = result.output
            if self.last_dataframe is not None and not self.last_dataframe.empty:
                print(f"DEBUG: About to format DataFrame with shape {self.last_dataframe.shape}")
                # Format the DataFrame for frontend (dates, prices, etc.)
                formatted_df = self._format_dataframe_for_frontend(self.last_dataframe)
                
                # Create table-ready response with formatted data
                display_df = formatted_df.head(50) if len(formatted_df) > 50 else formatted_df
                table_data = display_df.to_json(orient='records')
                
                # Use the full formatted data for download (not just display subset)
                full_data = formatted_df.to_json(orient='records')
                
                # Format as DATAFRAME_RESULT for frontend detection: text|display_data|full_data
                analysis_result = f"DATAFRAME_RESULT|{result.output}|{table_data}|{full_data}"
                print(f"DEBUG: Created DATAFRAME_RESULT with {len(display_df)} rows for display, {len(formatted_df)} rows for download")
            else:
                print(f"DEBUG: No DataFrame to format - last_dataframe is None or empty")
            
            return {
                "success": True,
                "analysis": analysis_result,
                "usage": result.usage(),
                "query": query
            }
            
        except Exception as e:
            error_msg = f"Failed to analyze query: {str(e)}"
            logger.error(error_msg)
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