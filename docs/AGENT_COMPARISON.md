# Agent Comparison: Market Agent vs Price Agent

## Overview

Both agents use **PandasAI** to query datasets, but they have different architectures and return different results.

---

## 🔵 Market Agent (Alex)

### Data Source
- **Dataset**: PV market installation data (Parquet file)
- **Size**: Large historical + forecast data
- **Columns**: country, year, scenario, duration, connection, segment, applications, type, capacity, etc.

### Tool: `analyze_market_data_tool`

**What it does:**
```python
async def analyze_market_data_tool(ctx: RunContext[None], query: str):
    # Uses PandasAI to query the dataset
    response = self.market_data.chat(enhanced_query)
    df = response.value  # Returns a DataFrame

    # Returns DataAnalysisResult with:
    return DataAnalysisResult(
        result_type="dataframe",
        content="<summary text>",
        dataframe_data=[{...}, {...}]  # List of row dictionaries
    )
```

**Return Structure:**
```python
DataAnalysisResult(
    result_type: "dataframe",       # Always dataframe
    content: "Found 5 records...",   # Summary text
    dataframe_data: [                # Actual table data
        {"country": "Canada", "year": 2024, "capacity": 321},
        {"country": "USA", "year": 2024, "capacity": 1500},
        ...
    ],
    plot_info: None                  # No plots (uses separate tool)
)
```

**Frontend Display:**
- Shows as **interactive table** with sorting/filtering
- Limited to 50 rows for display
- Full dataset cached for follow-up queries

---

## 🟢 Price Agent (Maya)

### Data Source
- **Dataset**: Module price data (Parquet file)
- **Size**: Price trends by date, region, technology
- **Columns**: date, region, item_description, price_low, price_high, price_avg, etc.

### Tool: `analyze_prices_data_tool`

**What it does:**
```python
@self.agent.tool(name="analyze_prices_data")
async def analyze_prices_data_tool(ctx: RunContext[None], query: str):
    # Uses PandasAI to query the dataset
    response = self.price_data.chat(enhanced_query)

    # Can return different types:
    if isinstance(response, str):
        return DataAnalysisResult(
            result_type="text",
            content=response  # Just text answer
        )
    elif isinstance(response, pd.DataFrame):
        return DataAnalysisResult(
            result_type="dataframe",
            content="<summary>",
            dataframe_data=df.to_dict('records')
        )
```

**Return Structure (varies by query):**

**Option 1: Text Response**
```python
DataAnalysisResult(
    result_type: "text",
    content: "The average price in China decreased by 15% from Q1 to Q2 2024",
    dataframe_data: None,
    plot_info: None
)
```

**Option 2: DataFrame Response**
```python
DataAnalysisResult(
    result_type: "dataframe",
    content: "Price comparison across regions",
    dataframe_data: [
        {"region": "China", "avg_price": 0.12, "date": "2024-01"},
        {"region": "EU", "avg_price": 0.18, "date": "2024-01"},
        ...
    ],
    plot_info: None
)
```

**Frontend Display:**
- **Text**: Markdown formatted response
- **DataFrame**: Interactive table

---

## 📊 Additional Tools

Both agents have plotting capabilities, but they work differently:

### Market Agent Plotting
Uses separate `get_plot_data_output` tool:
```python
MarketPlotDataResult(
    plot_type: "line_chart",
    title: "Canada Solar Capacity 2010-2024",
    x_axis_label: "Year",
    y_axis_label: "Capacity (MW)",
    data: [{x: 2010, y: 100}, {x: 2011, y: 150}, ...],
    series_info: [{name: "Annual", color: "blue"}]
)
```
→ Frontend renders as **D3.js interactive chart**

### Price Agent Plotting
Uses multiple tools:
- `get_plot_data_output` → D3.js JSON (same as market agent)
- `plot_price_trends_tool` → Static PNG file
- `plot_boxplot_tool` → Static PNG file
- `plot_avg_prices_tool` → Static PNG file

---

## Key Differences Summary

| Feature | Market Agent | Price Agent |
|---------|-------------|-------------|
| **Main Tool** | `analyze_market_data_tool` | `analyze_prices_data_tool` |
| **PandasAI Returns** | Always DataFrame | Text OR DataFrame |
| **Result Type** | Always `"dataframe"` | `"text"` or `"dataframe"` |
| **Table Display** | ✅ Always shows table | ✅ Only for DataFrame results |
| **Text Answers** | ❌ No | ✅ Yes (like "prices decreased 15%") |
| **Plotting** | Separate tool | Multiple dedicated plot tools |
| **Data Complexity** | High (hierarchical totals) | Medium (time series) |
| **Default Behavior** | Return raw data | Can summarize or return data |

---

## Why the Difference?

**Market Agent Design:**
- Dataset has complex hierarchical structure (totals, sub-totals)
- Always returns **full data** to avoid double-counting errors
- Agent analyzes the returned data to answer user questions
- Focus: **Show the data, let user/agent interpret**

**Price Agent Design:**
- Dataset is simpler (prices over time)
- Can safely do calculations (averages, trends)
- Can answer directly: "The price is X" (text)
- Or show data: "Here are all prices" (dataframe)
- Focus: **Answer flexibly based on query**

---

## Example Queries

### Market Agent
**Query:** "What's Canada's solar capacity in 2024?"

**Tool Returns:**
```python
DataAnalysisResult(
    result_type="dataframe",
    content="Found 1 record. Canada had 321 MW installed in 2024",
    dataframe_data=[
        {"country": "Canada", "year": 2024, "capacity": 321, ...}
    ]
)
```

**Frontend Shows:**
- Summary text
- Interactive table with 1 row
- User can click columns to sort

---

### Price Agent
**Query:** "What's the average module price in China?"

**Tool Returns (Option 1 - Text):**
```python
DataAnalysisResult(
    result_type="text",
    content="The average module price in China is $0.12/Watt as of January 2024",
    dataframe_data=None
)
```

**Frontend Shows:**
- Just the text answer
- No table

**Query:** "Show me all China module prices"

**Tool Returns (Option 2 - DataFrame):**
```python
DataAnalysisResult(
    result_type="dataframe",
    content="China module price history",
    dataframe_data=[
        {"date": "2024-01", "price_avg": 0.12},
        {"date": "2024-02", "price_avg": 0.11},
        ...
    ]
)
```

**Frontend Shows:**
- Summary text
- Interactive table with multiple rows

---

## Bottom Line

- **Market Agent** = "Here's the data table, let me explain it"
- **Price Agent** = "Here's the answer" OR "Here's the data table"

The Price Agent is more flexible in how it responds, while the Market Agent always shows you the raw data to ensure accuracy with complex hierarchical datasets.
