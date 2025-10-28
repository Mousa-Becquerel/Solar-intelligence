# Why Market Agent and Price Agent Return Different Things

## The Key Difference: How They Handle PandasAI Responses

---

## PandasAI's `.chat()` Can Return Different Types

```python
response = pandasai_agent.chat(query)

# Can be:
# 1. String: "The average price is $0.12"
# 2. DataFrame: pd.DataFrame([...])
# 3. Number: 0.12
# 4. SmartDataFrame with .value property
```

---

## Market Agent Behavior

### Code (pydantic_weaviate_agent.py:2269-2346)

```python
response = self.market_data.chat(enhanced_query)

# Step 1: Extract DataFrame
df = None
if hasattr(response, 'value') and isinstance(response.value, pd.DataFrame):
    df = response.value
elif isinstance(response, pd.DataFrame):
    df = response

# Step 2: If DataFrame exists
if df is not None and not df.empty:
    set_dataframe(df)  # ← Store in REQUEST CONTEXT

    # Build summary
    summary = f"Found {len(df)} records.\n\nPREVIEW..."
    return summary  # ← ALWAYS returns text summary

# Step 3: If NOT a DataFrame
else:
    return str(response)  # Fallback
```

### Result

**PandasAI returns DataFrame:**
```python
Tool returns: "Found 50 records.\n\nPREVIEW..."
Context stores: DataFrame (50 rows)
Frontend gets: Table with 50 rows
```

**PandasAI returns String:**
```python
Tool returns: "The total is 5000 MW"
Context stores: Nothing
Frontend gets: Just the text
```

### Why Always DataFrame?

The Market Agent's system prompt **explicitly instructs PandasAI**:
```python
enhanced_query = f"""
🚨 CRITICAL INSTRUCTION: DO NOT SUM, AGGREGATE, OR TOTAL ANY VALUES! 🚨
- Return the raw DataFrame as-is, without any calculations
- Do NOT use .sum(), .total(), .aggregate()
- NEVER calculate totals even if the user asks for "total capacity"

USER QUERY: {query}
"""
```

**Result:** PandasAI **always returns DataFrame**, never text answers!

---

## Price Agent Behavior

### Code (module_prices_agent.py:1099-1189)

```python
response = self.component_prices.chat(enriched_query)

# Step 1: Extract DataFrame
df = None
if hasattr(response, 'value') and isinstance(response.value, pd.DataFrame):
    df = response.value
elif isinstance(response, pd.DataFrame):
    df = response

# Step 2: If DataFrame exists
if df is not None and not df.empty:
    self.last_dataframe = df  # ← Store in AGENT INSTANCE (not context!)

    # Build summary
    header = "10 records; period: 2023-01 → 2024-12..."
    return header  # ← Returns text summary

# Step 3: If NOT a DataFrame (THIS IS THE KEY DIFFERENCE!)
else:
    # ✅ Returns whatever PandasAI returned!
    if response is None:
        return "No data found for your query."
    elif hasattr(response, 'to_string'):
        return response.to_string()
    else:
        return str(response)  # ← Direct text answer!
```

### Result

**PandasAI returns DataFrame:**
```python
Tool returns: "10 records; period: 2023-01 → 2024-12..."
Agent stores: self.last_dataframe = DataFrame
Frontend gets: Table with 10 rows
```

**PandasAI returns String:**
```python
Tool returns: "The average module price in China is $0.12/Watt"
Agent stores: Nothing
Frontend gets: Just the text answer
```

### Why Different Responses?

The Price Agent **does NOT force DataFrame returns**. Its prompt allows PandasAI to decide:

```python
dataset_info = f"""
Available items: Aluminium, Cell, Copper...
Available regions: China, EU, US...

IMPORTANT SQL GUIDELINES:
- Use DuckDB syntax
- For averages: use AVG(base_price)
- For latest: use ORDER BY date DESC LIMIT 1

Query: {user_query}
"""
```

**Result:** PandasAI chooses based on the query:
- **"Show me China prices"** → Returns DataFrame
- **"What's the average price?"** → Returns String "The average is $0.12"

---

## Storage Location Difference

### Market Agent: Request Context (Thread-Safe)
```python
set_dataframe(df)  # Stored in ContextVar (thread-safe, async-safe)

# Later in Flask route:
from request_context import get_dataframe
df = get_dataframe()  # ✅ Works across async/threading
```

**Why:** Market agent needs thread-safe storage for concurrent requests.

### Price Agent: Instance Variable (Not Thread-Safe!)
```python
self.last_dataframe = df  # ⚠️ Stored on agent object

# Later in agent:
df = self.last_dataframe  # ❌ Race condition if multiple users!
```

**Why:** Price agent is older code, not yet refactored for thread safety.

---

## Summary Table

| Feature | Market Agent | Price Agent |
|---------|-------------|-------------|
| **PandasAI Response** | Forced DataFrame | DataFrame OR String |
| **Tool Returns DataFrame** | Text summary | Text summary |
| **Tool Returns String** | Rare (error only) | Common ("avg is $0.12") |
| **Storage** | Request Context (thread-safe) | `self.last_dataframe` (not thread-safe) |
| **Frontend Gets DataFrame** | Via `get_dataframe()` | Via `self.last_dataframe` |
| **Frontend Gets Text** | Rare | Common |

---

## Real Examples

### Market Agent

**Query:** "What's Canada's total solar capacity in 2024?"

**PandasAI Query Sent:**
```
🚨 DO NOT CALCULATE TOTALS! Return raw DataFrame.
User query: Canada's total solar capacity in 2024
```

**PandasAI Returns:** DataFrame with rows
```
country  year  connection  segment  applications  capacity
Canada   2024  Total      Total    Total         321
Canada   2024  Distributed Residential BAPV      150
...
```

**Tool Returns:**
```
"Found 5 records.

PREVIEW:
country  year  capacity
Canada   2024  321
...

COLUMN SUMMARY:
  - capacity: ranges from 150 MW to 321 MW (hierarchical data)"
```

**Agent Analyzes:** Reads summary, identifies row with all "Total" = 321 MW

**Agent Responds:** "Canada's total solar capacity in 2024 is 321 MW."

---

### Price Agent

**Query:** "What's the average module price in China?"

**PandasAI Query Sent:**
```
Available regions: China, EU, US...
Use AVG(base_price) for averages.
Query: average module price in China
```

**PandasAI Returns:** String
```
"The average module price in China is $0.12/Watt"
```

**Tool Returns:**
```
"The average module price in China is $0.12/Watt"
```

**Agent Responds:** "The average module price in China is $0.12/Watt."

---

## Why This Matters

### For Market Data (Complex, Hierarchical)
- Must return raw data to avoid calculation errors
- Agent needs full context to interpret totals vs breakdowns
- User needs to see the data structure

### For Price Data (Simple, Time-Series)
- Can safely calculate averages, trends
- Direct answers are more useful ("price is $0.12")
- Tables only needed for detailed analysis

---

## Thread Safety Issue in Price Agent

⚠️ **The Price Agent has a race condition:**

```python
# User A's request
self.last_dataframe = df_for_user_A  # Stores User A's data

# User B's request (happens before A finishes)
self.last_dataframe = df_for_user_B  # OVERWRITES User A's data!

# User A tries to create plot
df = self.last_dataframe  # ❌ Gets User B's data instead!
```

**Fix needed:** Migrate Price Agent to use `request_context` like Market Agent.

---

## Bottom Line

Both agents use PandasAI, but:

- **Market Agent:** Forces DataFrame returns, stores in thread-safe context
- **Price Agent:** Allows flexible responses (text or DataFrame), stores in instance variable

The Market Agent's approach is more robust for concurrent users, but the Price Agent's flexibility gives better UX for simple queries.
