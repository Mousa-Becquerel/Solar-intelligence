# What PandasAI Tools Actually Return

## The Truth: Tools Return Text, Data is Stored in Context

You're correct - the PandasAI tool doesn't return the DataFrame directly. Here's what actually happens:

---

## Market Agent: `analyze_market_data_tool`

### Step 1: PandasAI Query
```python
response = self.market_data.chat(enhanced_query)
df = response.value  # Extract DataFrame from PandasAI response
```

### Step 2: Store DataFrame in Request Context
```python
set_dataframe(df)  # Stores in thread-safe request context
```

### Step 3: Build Summary Text
```python
summary_text = f"""
Found {len(df)} records.

PREVIEW (first 5 rows):
{df.head(5).to_string()}

COLUMN SUMMARY:
  - country: Canada, USA, Germany...
  - year: 2010, 2011, ..., 2024
  - capacity: ranges from 10 MW to 5.2 GW
"""
```

### Step 4: Tool Returns ONLY THE SUMMARY
```python
return summary_text  # ← This is ALL the tool returns!
```

### Step 5: Flask Route Retrieves DataFrame from Context
```python
# In app.py - AFTER the agent finishes
from request_context import get_dataframe

df = get_dataframe()  # Retrieves the cached DataFrame

if df is not None:
    response_data = [{
        'type': 'dataframe',
        'value': result.data,  # Summary text
        'table_data': df.to_dict('records'),  # ← Table from context!
        'full_data': df.to_dict('records')
    }]
```

---

## Why This Design?

### Problem: Pydantic AI Token Limits
```python
# If tool returned full DataFrame:
return DataAnalysisResult(
    result_type="dataframe",
    dataframe_data=[{...1000 rows...}]  # ❌ TOO BIG! Exceeds token limits
)
```

The agent's conversation memory would **explode** with large DataFrames, hitting token limits quickly.

### Solution: Side-Channel Storage
```python
# Tool returns: Small summary (100 tokens)
return "Found 50 records. Preview: ..."

# DataFrame stored: Outside conversation memory
set_dataframe(df)  # Stored in request context (not in agent memory)
```

**Benefits:**
- ✅ Agent memory stays small (only summary text)
- ✅ Full DataFrame available to Flask route
- ✅ Can handle 1000+ row DataFrames without token issues
- ✅ Conversation doesn't bloat with repeated data

---

## Data Flow Diagram

```
User Query
    ↓
PandasAI.chat(query)
    ↓
Extract DataFrame
    ↓
┌────────────────────────────┬─────────────────────────┐
│                            │                         │
│  set_dataframe(df)         │  Build summary_text     │
│  (Request Context)         │  (First 5 rows + stats) │
│                            │                         │
└────────────────────────────┴─────────────────────────┘
                             ↓
                    return summary_text
                             ↓
                      Agent Memory
                    (Only stores summary)
                             ↓
                    Agent generates response
                             ↓
                      Flask Route
                             ↓
                    get_dataframe()
              (Retrieves full DataFrame from context)
                             ↓
                    Build JSON response
                   {type: 'dataframe',
                    value: summary,
                    table_data: df.to_dict()}
                             ↓
                        Frontend
               (Displays table + summary)
```

---

## Memory Filtering

The agent also filters conversation memory to prevent bloat:

```python
def filter_large_tool_returns(messages, max_content_length=500):
    """
    Truncates large tool returns in conversation history.

    Before: "Tool returned: [5000 chars of DataFrame]"
    After:  "Tool returned: [DataFrame: 100 rows - truncated for memory]"
    """
```

This is in `pydantic_weaviate_agent.py` lines 23-117.

---

## Price Agent: Same Pattern

```python
@self.agent.tool(name="analyze_prices_data")
async def analyze_prices_data_tool(ctx, query):
    response = self.price_data.chat(query)

    if isinstance(response, str):
        return response  # Just text answer

    elif isinstance(response, pd.DataFrame):
        # Store DataFrame (not shown in this simplified version)
        return f"Found {len(response)} price records"  # Summary only
```

The Price Agent follows the same pattern but is simpler because:
- Smaller datasets (prices vs market installations)
- Sometimes returns direct text answers ("The price is $0.12")
- Less memory pressure

---

## Key Takeaway

### What Tool Returns
```python
"Found 50 records.

PREVIEW (first 5 rows):
country  year  capacity
Canada   2024  321
USA      2024  1500
...

COLUMN SUMMARY:
  - country: 2 unique values
  - year: 2024
  - capacity: ranges from 321 MW to 1500 MW"
```

### What Frontend Gets
```json
{
  "type": "dataframe",
  "value": "Found 50 records...",
  "table_data": [
    {"country": "Canada", "year": 2024, "capacity": 321},
    {"country": "USA", "year": 2024, "capacity": 1500},
    ... all 50 rows ...
  ]
}
```

The magic happens in the **Flask route** which combines:
1. Tool's summary text (`value`)
2. Context's DataFrame (`table_data`)

This keeps agent memory small while still providing full data to the user! 🎯
