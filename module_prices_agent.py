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
    llm_model: str = "openai:gpt-4o"  # Add this for compatibility
    request_limit: int = 10
    total_tokens_limit: int = 15000  # Increased from 5000
    verbose: bool = True
    # Memory optimization settings
    low_memory_mode: bool = False  # Enable for 512MB deployments
    max_conversation_messages: int = 20  # Limit conversation history
    enable_gc_after_operations: bool = False  # Force garbage collection

class ModulePricesAgent:
    """
    Enhanced Pydantic-AI agent for analyzing solar module prices.
    """
    
    SYSTEM_PROMPT = """
You are a solar module price analysis assistant specialized in photovoltaic component pricing.

**CRITICAL TOOL USAGE RULES:**

**For greetings and general conversation:** Use `chat_response_tool`

**For data queries (finding, listing, showing data):** Use `analyze_prices_data` tool ONLY:
- "What modules available in India" → analyze_prices_data
- "Show me prices for X" → analyze_prices_data  
- "List components in region Y" → analyze_prices_data
- "Find prices between dates" → analyze_prices_data
→ Process the summary and provide helpful analysis

**For visualization requests (creating charts/plots):** Use plotting tools with CORRECT parameters:

**SINGLE REGION/ITEM EXAMPLES:**
- "Plot modules prices in China" → plot_price_trends_tool(item="Module", region="China")
- "Chart wafer prices in EU" → plot_price_trends_tool(item="Wafer", region="EU")
- "Show cell prices" → plot_price_trends_tool(item="Cell")
- "Plot prices in India" → plot_price_trends_tool(region="India")

**MULTIPLE REGIONS EXAMPLES (CRITICAL - Use comma-separated values):**
- "Plot modules in China and EU" → plot_price_trends_tool(item="Module", region="China,EU")
- "Chart prices in EU and US" → plot_price_trends_tool(region="EU,US")
- "Show wafers in China, EU, and US" → plot_price_trends_tool(item="Wafer", region="China,EU,US")
- "Plot in both China and EU" → plot_price_trends_tool(region="China,EU")

**BOXPLOT EXAMPLES:**
- "Show box plots of different modules in China" → plot_boxplot_tool(item="Module", region_filter="China", x_axis="description")
- "Box plots by region for modules" → plot_boxplot_tool(item="Module", x_axis="region")
- "Price distribution of modules in EU and US" → plot_boxplot_tool(item="Module", region_filter="EU,US", x_axis="description")

**NEVER use both data and plotting tools in the same response.**

**IMPORTANT DATA HANDLING:**
- Use EXACT region names from the data (China, EU, US, India, Overseas, Australia)
- Report exactly what the data shows without assumptions
- When describing findings, stick to the actual data values

**PARAMETER EXTRACTION FOR PLOTTING:**
- Extract item: Module, Cell, Wafer, Polysilicon, EVA, PV glass, Silver, Copper, Aluminium
- Extract region: China, EU, US, India, Overseas, Australia
- **FOR MULTIPLE REGIONS: Combine with commas (NO SPACES after commas)**
  - "China and EU" → "China,EU"
  - "EU, US, and China" → "EU,US,China"
  - "both India and China" → "India,China"

**Data Context:**
- Prices are in US$/Wp
- Data includes various module types (mono-Si, multi-Si, etc.)
- Regions: China, EU, US, India, Overseas, Australia (use exact names)
- Always specify currency and units in responses

Remember: Extract and pass exact parameters to plotting tools for accurate filtering. For multiple regions, use comma-separated format without spaces.
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
        """Initialize the Pydantic AI agent following market agent pattern"""
        try:
            # === Factory Functions for Plot Generation ===
            async def price_trend_factory(
                ctx: RunContext[None],
                item: str = None,
                region: str = None,
                descriptions_csv: str = None,
            ) -> str:
                """Price trend chart generator."""
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
                    
                    # Create the plot using the entire dataset
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

            async def boxplot_factory(
                ctx: RunContext[None],
                item: str = "all",
                description: str = "all",
                region_filter: str = "all",
                x_axis: str = "region"
            ) -> str:
                """Boxplot chart generator."""
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

            async def avg_price_factory(
                ctx: RunContext[None],
                item: str = "all",
                description_filter: str = "all",
                region_filter: str = "all"
            ) -> str:
                """Average price chart generator."""
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

            # === Create Plot Generation Agent ===
            plot_generation_agent = Agent(
                model="openai:gpt-4o",
                output_type=[price_trend_factory, boxplot_factory, avg_price_factory],
                system_prompt=(
                    "You are a plotting assistant for solar component prices.\n\n"
                    "When users ask for price trends/charts, call `price_trend_factory`.\n"
                    "When users ask for boxplots/distributions, call `boxplot_factory`.\n"
                    "When users ask for average prices, call `avg_price_factory`.\n\n"
                    "Extract parameters from the command:\n"
                    "• item: Module, Cell, Wafer, etc. (if mentioned)\n"
                    "• region: China, EU, US, India, etc. (if mentioned)\n"
                    "• descriptions_csv: specific tech types (if mentioned)\n\n"
                    "For boxplots, x_axis must be one of: 'region', 'item', 'description'\n"
                    "• 'different modules' or 'module types' → x_axis='description'\n"
                    "• 'by region' or 'across regions' → x_axis='region'\n"
                    "• 'by item' or 'different items' → x_axis='item'\n"
                    "• Default: x_axis='region'\n\n"
                    "For multiple regions: 'EU,China' format\n\n"
                    "Return ONLY the tool output."
                ),
            )

            # === Tool Wrappers for Main Agent ===
            async def plot_price_trends_tool(
                ctx: RunContext[None],
                item: str = None,
                region: str = None,
                descriptions_csv: str = None,
            ) -> str:
                """Wrapper that delegates price trend plotting to nested agent."""
                cmd = f"Generate a price trend chart"
                if item:
                    cmd += f" for {item}"
                if region:
                    cmd += f" in {region}"
                if descriptions_csv:
                    cmd += f" for descriptions: {descriptions_csv}"
                cmd += "."
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                return response.output

            async def plot_boxplot_tool(
                ctx: RunContext[None],
                item: str = "all",
                description: str = "all",
                region_filter: str = "all",
                x_axis: str = "region"
            ) -> str:
                """Wrapper that delegates boxplot generation to nested agent."""
                cmd = f"Generate a boxplot showing price distribution by {x_axis}"
                if item != "all":
                    cmd += f" for item {item}"
                if description != "all":
                    cmd += f" for description {description}"
                if region_filter != "all":
                    cmd += f" for region {region_filter}"
                cmd += "."
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                return response.output

            async def plot_avg_prices_tool(
                ctx: RunContext[None],
                item: str = "all",
                description_filter: str = "all",
                region_filter: str = "all"
            ) -> str:
                """Wrapper that delegates average price chart generation to nested agent."""
                cmd = f"Generate an average price chart by description"
                if item != "all":
                    cmd += f" for item {item}"
                if description_filter != "all":
                    cmd += f" for description {description_filter}"
                if region_filter != "all":
                    cmd += f" for region {region_filter}"
                cmd += "."
                response = await plot_generation_agent.run(cmd, usage=ctx.usage)
                return response.output

            async def chat_response_tool(ctx: RunContext[None], chat_response: str) -> str:
                """Handle greetings, general questions, and casual conversation"""
                return chat_response

            # === Create Main Agent ===
            self.agent = Agent(
                model=self.config.model,
                output_type=[chat_response_tool, plot_price_trends_tool, plot_boxplot_tool, plot_avg_prices_tool],
                system_prompt=self.SYSTEM_PROMPT,
            )

            # Register data analysis as a regular tool (not output type)
            @self.agent.tool(name="analyze_prices_data")
            async def analyze_prices_data_tool(ctx: RunContext[None], query: str) -> str:
                """Tool for querying module price data"""
                try:
                    logger.info(f"Executing price data query: {query}")
                    
                    # Prepend dataset schema information to help PandasAI use exact values
                    dataset_info = """
Available items in the dataset (use exact spelling):
- Aluminium, Cell, Copper, EVA, Module, PV glass, Polysilicon, Silver, Wafer

Available regions in the dataset (use exact names):
- China, EU, US, India, Overseas, Australia

Available columns:
- item, description, date, frequency, base_price, unit, region, source

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
                        # Store the DataFrame for potential plotting and table rendering
                        self.last_dataframe = df
                        
                        # Return a summary to the main agent (not the full data to avoid token limits)
                        if 'description' in df.columns:
                            unique_descriptions = df['description'].unique()
                            if len(unique_descriptions) <= 5:
                                desc_list = ', '.join(unique_descriptions)
                                summary = f"Found {len(df)} price records with the following descriptions: {desc_list}"
                            else:
                                desc_list = ', '.join(unique_descriptions[:5])
                                summary = f"Found {len(df)} price records with {len(unique_descriptions)} different descriptions including: {desc_list} and {len(unique_descriptions)-5} others"
                        elif 'region' in df.columns:
                            unique_regions = df['region'].unique()
                            if len(unique_regions) <= 10:
                                region_list = ', '.join(unique_regions)
                                summary = f"Found {len(df)} records for the following regions: {region_list}"
                            else:
                                region_list = ', '.join(unique_regions[:10])
                                summary = f"Found {len(df)} records for {len(unique_regions)} regions including: {region_list}"
                        elif 'item' in df.columns:
                            unique_items = df['item'].unique()
                            if len(unique_items) <= 10:
                                item_list = ', '.join(unique_items)
                                summary = f"Found {len(df)} records for the following items: {item_list}"
                            else:
                                item_list = ', '.join(unique_items[:10])
                                summary = f"Found {len(df)} records for {len(unique_items)} items including: {item_list}"
                        else:
                            summary = f"Found {len(df)} price records in the dataset"
                        
                        # Add date range info if available
                        if 'date' in df.columns:
                            try:
                                min_date = df['date'].min()
                                max_date = df['date'].max()
                                summary += f" from {min_date} to {max_date}"
                            except:
                                pass
                        
                        # Add price range info if available
                        if 'base_price' in df.columns:
                            try:
                                min_price = df['base_price'].min()
                                max_price = df['base_price'].max()
                                avg_price = df['base_price'].mean()
                                summary += f". Prices range from ${min_price:.3f} to ${max_price:.3f} (avg: ${avg_price:.3f})"
                            except:
                                pass
                        
                        return summary
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
                    return error_msg

            logger.info("Module prices agent with nested plot generation setup complete")
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
                
                # Memory optimization: Limit conversation history length
                if self.config.low_memory_mode and len(message_history) > self.config.max_conversation_messages:
                    # Keep only the most recent messages
                    message_history = message_history[-self.config.max_conversation_messages:]
                    logger.info(f"[MEMORY OPTIMIZATION] Trimmed conversation history to {len(message_history)} messages")
            
            logger.info(f"Processing query: {query}")
            result = await self.agent.run(query, message_history=message_history, usage_limits=usage_limits)
            
            # Store the new messages for future conversation context
            if conversation_id:
                new_messages = result.all_messages()
                
                # Memory optimization: Limit stored conversation history
                if self.config.low_memory_mode and len(new_messages) > self.config.max_conversation_messages:
                    new_messages = new_messages[-self.config.max_conversation_messages:]
                    logger.info(f"[MEMORY OPTIMIZATION] Limited stored messages to {len(new_messages)}")
                
                self.conversation_memory[conversation_id] = new_messages
                logger.info(f"[MEMORY DEBUG] Updated conversation memory for {conversation_id}")
            
            # Memory optimization: Force garbage collection after operations
            if self.config.enable_gc_after_operations:
                import gc
                gc.collect()
                logger.info("[MEMORY OPTIMIZATION] Forced garbage collection")
            
            # Check if a DataFrame was generated and format response accordingly
            analysis_result = result.output
            if self.last_dataframe is not None and not self.last_dataframe.empty:
                print(f"DEBUG: About to format DataFrame with shape {self.last_dataframe.shape}")
                # Format the DataFrame for frontend (dates, prices, etc.)
                formatted_df = self._format_dataframe_for_frontend(self.last_dataframe)
                
                # Memory optimization: Limit display rows for low memory mode
                max_display_rows = 25 if self.config.low_memory_mode else 50
                display_df = formatted_df.head(max_display_rows) if len(formatted_df) > max_display_rows else formatted_df
                table_data = display_df.to_json(orient='records')
                
                # Use the full formatted data for download (not just display subset)
                full_data = formatted_df.to_json(orient='records')
                
                # Format as DATAFRAME_RESULT for frontend detection: text|display_data|full_data
                analysis_result = f"DATAFRAME_RESULT|{result.output}|{table_data}|{full_data}"
                print(f"DEBUG: Created DATAFRAME_RESULT with {len(display_df)} rows for display, {len(formatted_df)} rows for download")
                
                # Memory optimization: Clear large DataFrame after use in low memory mode
                if self.config.low_memory_mode:
                    self.last_dataframe = None
                    logger.info("[MEMORY OPTIMIZATION] Cleared last_dataframe to free memory")
            else:
                print(f"DEBUG: No DataFrame to format - last_dataframe is None or empty")
            
            # Return the agent's response (either natural language or formatted DataFrame)
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