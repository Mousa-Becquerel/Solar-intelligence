# Complete Data Flow: From Query to Frontend Response

## Overview

This document traces the **exact journey** of a user query through the Market Agent, showing what each component returns and when.

---

## Example Query: "What's Italy's solar capacity in 2023?"

### Step 1: User sends message via Flask

```python
# app.py
user_message = "What's Italy's solar capacity in 2023?"
conversation_id = "conv_123"
```

---

### Step 2: Agent tool calls `analyze_market_data_tool`

**Location**: `pydantic_weaviate_agent.py` lines 2198-2346

```python
@self.agent.tool(name='analyze_market_data')
async def analyze_market_data_tool(ctx: RunContext[None], query: str):
    # PandasAI query
    response = self.market_data.chat(enhanced_query)

    # Extract DataFrame
    if hasattr(response, 'value') and isinstance(response.value, pd.DataFrame):
        df = response.value

    # DataFrame looks like:
    # country | year | connection | segment | applications | capacity
    # Italy   | 2023 | Total      | Total   | Total        | 5255
    # Italy   | 2023 | Distributed| Residential| BAPV      | 2100
    # ... (12 more rows)
```

---

### Step 3: Store DataFrame in request context

```python
    # Line 2278
    set_dataframe(df)  # Stores in thread-safe ContextVar
```

**What's stored:**
- Full DataFrame with all 14 rows
- NOT visible to agent memory (to avoid token bloat)
- Accessible later via `get_dataframe()`

---

### Step 4: Build and return LONG summary

```python
    # Lines 2279-2336
    summary_parts = [
        f"Found {len(df)} records.",
        "",
        "PREVIEW (first 5 rows):",
        df.head(5).to_string(),
        "",
        "COLUMN SUMMARY:",
        f"  - country: {', '.join(countries)}",
        f"  - year: {', '.join(map(str, years))}",
        f"  - capacity: ranges from {df['capacity'].min()} MW to {df['capacity'].max()} MW",
    ]

    summary_text = "\n".join(summary_parts)
    return summary_text  # ← TOOL RETURNS THIS!
```

**Tool Returns:**
```
Found 14 records.

PREVIEW (first 5 rows):
  country  year  connection      segment       applications  capacity
0 Italy    2023  Total          Total         Total         5255
1 Italy    2023  Distributed    Residential   BAPV          2100
2 Italy    2023  Distributed    Commercial    BAPV          1500
3 Italy    2023  Centralized    Utility       Ground        1655
4 Italy    2023  Total          Total         BIPV          500

COLUMN SUMMARY:
  - country: Italy
  - year: 2023
  - capacity: ranges from 500 MW to 5255 MW
```

**Agent Memory Sees**: This long text (stored in conversation history)

**Agent Doesn't See**: The actual DataFrame (stored separately)

---

### Step 5: Agent analyzes summary and responds

```python
# Agent reads the summary and generates response
agent_response = "Italy's total solar capacity in 2023 is 5,255 MW, with distributed systems accounting for 3,600 MW and centralized systems contributing 1,655 MW."
```

---

### Step 6: Result validation callback (`result_retries`)

**Location**: `pydantic_weaviate_agent.py` lines 2550-2615

**CRITICAL**: This runs AFTER the tool completes but BEFORE returning to Flask.

```python
def result_retries(ctx: RunContext[None], result: ModelResult):
    # Check if DataFrame was cached by tool
    if self.last_dataframe is not None and not self.last_dataframe.empty:
        df = self.last_dataframe

        # Build COMPACT summary (this is what user sees!)
        parts = []
        parts.append(f"{len(df)} records")  # "14 records"

        # Add year if present
        if 'year' in df.columns:
            years = sorted(df['year'].unique())
            min_year = min(years)
            parts.append(f"year: {min_year}")  # "year: 2023"

        # Add country if single country
        if 'country' in df.columns:
            countries = df['country'].unique()
            if len(countries) == 1:
                parts.append(f"country: {countries[0]}")  # "country: Italy"

        # Find total capacity (row where all hierarchies = 'Total')
        total_row = df[
            (df['connection'] == 'Total') &
            (df['segment'] == 'Total') &
            (df['applications'] == 'Total')
        ]

        if not total_row.empty:
            total_capacity = total_row['capacity'].iloc[0]
            parts.append(f"total: {total_capacity:,.0f} MW")  # "total: 5,255 MW"

        # Join with semicolons
        summary = "; ".join(parts)  # "14 records; year: 2023; country: Italy; total: 5,255 MW"

        # Create DataAnalysisResult
        result.output = DataAnalysisResult(
            result_type="dataframe",
            content=summary,  # ← COMPACT SUMMARY
            dataframe_data=df.to_dict('records')  # ← FULL TABLE DATA
        )
```

**Why Two Summaries?**
1. **Long summary** (from tool): Goes to agent memory, helps agent understand data
2. **Compact summary** (from validator): Goes to frontend, clean UX

---

### Step 7: Flask route processes response

**Location**: `app.py` lines 1450-1520

```python
# Extract agent response
agent_response = "Italy's total solar capacity in 2023 is 5,255 MW..."

# Extract tool result (DataAnalysisResult from validator)
tool_result = result.all_messages()[-1].parts[0]  # Last tool call result

if isinstance(tool_result, DataAnalysisResult):
    response_data = [{
        'type': 'dataframe',
        'value': tool_result.content,  # "14 records; year: 2023; country: Italy; total: 5,255 MW"
        'table_data': tool_result.dataframe_data,  # Full 14 rows
        'full_data': tool_result.dataframe_data
    }]
```

**Alternative path** (if using request context):
```python
from request_context import get_dataframe

df = get_dataframe()
if df is not None:
    response_data = [{
        'type': 'dataframe',
        'value': "14 records; year: 2023; country: Italy; total: 5,255 MW",
        'table_data': df.to_dict('records'),
        'full_data': df.to_dict('records')
    }]
```

---

### Step 8: JSON response sent to frontend

```json
{
  "response": "Italy's total solar capacity in 2023 is 5,255 MW, with distributed systems accounting for 3,600 MW...",
  "results": [
    {
      "type": "dataframe",
      "value": "14 records; year: 2023; country: Italy; total: 5,255 MW",
      "table_data": [
        {"country": "Italy", "year": 2023, "connection": "Total", "segment": "Total", "applications": "Total", "capacity": 5255},
        {"country": "Italy", "year": 2023, "connection": "Distributed", "segment": "Residential", "applications": "BAPV", "capacity": 2100},
        ...
      ],
      "full_data": [...]
    }
  ]
}
```

---

### Step 9: Frontend displays response

**Location**: `static/js/main.js`

```javascript
// Display agent text response
messageDiv.textContent = "Italy's total solar capacity in 2023 is 5,255 MW...";

// Display compact summary
const summaryDiv = document.createElement('div');
summaryDiv.textContent = "14 records; year: 2023; country: Italy; total: 5,255 MW";

// Display interactive table
const table = createDataTable(result.table_data);
```

**User Sees:**
1. Agent's natural language response
2. Compact summary badge
3. Interactive sortable table with 14 rows

---

## Visual Flow Diagram

```
User Query
    ↓
Agent decides to use tool
    ↓
┌─────────────────────────────────────────────────────┐
│ analyze_market_data_tool                            │
│                                                     │
│ 1. PandasAI.chat(query)                            │
│    → Returns DataFrame (14 rows)                   │
│                                                     │
│ 2. set_dataframe(df)                               │
│    → Stores in ContextVar (outside agent memory)   │
│                                                     │
│ 3. Build long summary                              │
│    → "Found 14 records. PREVIEW: ..."             │
│                                                     │
│ 4. return summary_text                             │
│    → Goes to agent memory                          │
└─────────────────────────────────────────────────────┘
    ↓
Agent Memory: "Found 14 records. PREVIEW: ..."
    ↓
Agent generates response: "Italy's total solar capacity is 5,255 MW..."
    ↓
┌─────────────────────────────────────────────────────┐
│ result_retries (validator callback)                 │
│                                                     │
│ 1. Check if DataFrame cached                       │
│    → Yes, found 14 rows                            │
│                                                     │
│ 2. Build compact summary                           │
│    → "14 records; year: 2023; country: Italy;     │
│       total: 5,255 MW"                             │
│                                                     │
│ 3. Create DataAnalysisResult                       │
│    → content: compact summary                      │
│    → dataframe_data: full 14 rows                  │
└─────────────────────────────────────────────────────┘
    ↓
Flask Route
    ↓
JSON Response {
  response: "Italy's total solar capacity is 5,255 MW...",
  results: [{
    type: "dataframe",
    value: "14 records; year: 2023; country: Italy; total: 5,255 MW",
    table_data: [14 rows]
  }]
}
    ↓
Frontend
    ↓
User sees:
  ✅ Agent response (text)
  ✅ Compact summary (badge)
  ✅ Interactive table (14 rows)
```

---

## Why This Complex Flow?

### Problem 1: Token Limits
If tool returned full DataFrame:
```python
return DataAnalysisResult(
    dataframe_data=[{...14 rows...}]  # ❌ 2000+ tokens in agent memory!
)
```

After 10 queries, agent memory would be FULL of table data.

### Solution: Side-Channel Storage
```python
set_dataframe(df)  # Outside agent memory
return "Found 14 records..."  # Only ~100 tokens in memory
```

---

### Problem 2: Agent Needs Details, User Needs Summary

**Agent needs**: Full preview to understand data structure
```
PREVIEW (first 5 rows):
  country  year  connection      segment       applications  capacity
0 Italy    2023  Total          Total         Total         5255
1 Italy    2023  Distributed    Residential   BAPV          2100
...
```

**User needs**: Clean compact summary
```
14 records; year: 2023; country: Italy; total: 5,255 MW
```

### Solution: Two Summaries
1. Tool creates **long summary** → agent memory
2. Validator creates **compact summary** → frontend

---

## Key Locations in Code

| Step | File | Lines | What Happens |
|------|------|-------|--------------|
| 1. Tool execution | `pydantic_weaviate_agent.py` | 2198-2346 | PandasAI query, DataFrame extraction |
| 2. Context storage | `pydantic_weaviate_agent.py` | 2278 | `set_dataframe(df)` |
| 3. Long summary | `pydantic_weaviate_agent.py` | 2279-2336 | Preview + column stats |
| 4. Compact summary | `pydantic_weaviate_agent.py` | 2563-2609 | "14 records; year: 2023; ..." |
| 5. Result wrapping | `pydantic_weaviate_agent.py` | 2611-2615 | `DataAnalysisResult(...)` |
| 6. Flask processing | `app.py` | 1450-1520 | Extract and format response |
| 7. Frontend display | `static/js/main.js` | - | Render table + summary |

---

## Bottom Line

**What tool returns**: Long preview text (goes to agent memory)

**What user sees**: Compact summary + full table (from validator callback)

**How it works**: Side-channel storage (ContextVar) keeps agent memory clean while preserving full data for frontend

This is why the Market Agent can handle 1000+ row DataFrames without exploding token limits! 🎯
