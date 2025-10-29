# Plot Queries Missing from Conversation History - Fix

## Issue Description

**Problem**: When users ask plot-related questions, those queries don't appear in the conversation history when they later ask "What did I ask before?"

**User Report**:
- User asks: "Plot Netherlands PV installations from 2020 to 2024 as stacked bars"
- Chart renders successfully
- User asks: "What did I ask before?"
- Agent responds: "You previously asked, 'what did I ask before?' but there was no earlier question..."
- ❌ The "Plot Netherlands..." query is completely missing from conversation history!

**Also affects**: "what were all my previous queries?" shows incomplete history with plot queries missing.

## Root Cause Analysis

### The Session Passing Issue

The market intelligence agent uses a **classification-based routing system**:

1. **Classification Agent** - Determines if query is about data or plotting
2. **Plotting Agent** - Handles plot/chart requests
3. **Market Intelligence Agent** - Handles data analysis requests

The problem was in how the `session` parameter was passed to these agents:

```python
# market_intelligence_agent.py (BEFORE FIX)

# Step 1: Classification
classification_result = await Runner.run(
    self.classification_agent,
    input=query,
    session=None,  # ✅ Correct - don't add to history
    ...
)

# Step 2a: If plot query
if intent == "plot":
    plotting_result = await Runner.run(
        self.plotting_agent,
        input=query,
        session=None,  # ❌ WRONG - query not added to history!
        ...
    )

# Step 2b: If data query
else:
    market_result = await Runner.run(
        self.market_intelligence_agent,
        input=query,
        session=session,  # ✅ Correct - query added to history
        ...
    )
```

### Why Plot Queries Were Missing

When `Runner.run()` is called with `session=None`:
- The query is NOT added to the SQLiteSession conversation history
- The agent responds but leaves no record of the user's question
- Next time the agent is asked about history, it can't find that query

**Flow Comparison**:

| Query Type | Agent Used | Session Parameter | Added to History? |
|------------|------------|-------------------|-------------------|
| "Plot Netherlands..." | Plotting Agent | `session=None` ❌ | NO ❌ |
| "What about Italy?" | Market Intelligence | `session=session` ✅ | YES ✅ |
| "What did I ask before?" | Market Intelligence | `session=session` ✅ | YES ✅ |

Result: Only non-plot queries were stored in conversation history!

### Why News/Digitalization Agents Work Correctly

The news and digitalization agents don't have this issue because they **always** pass `session=session` to their agents:

```python
# news_agent.py - CORRECT IMPLEMENTATION
if intent == "news":
    result = Runner.run_streamed(self.news_agent, query, session=session)  # ✅
elif intent == "scraping":
    result = Runner.run_streamed(self.scraping_agent, query, session=session)  # ✅
else:
    result = Runner.run_streamed(self.news_agent, query, session=session)  # ✅
```

All branches use `session=session`, so all queries get added to history regardless of intent.

## Solution

### Pass Session to Plotting Agent

Change the plotting agent to also use the session, ensuring plot queries are recorded in conversation history.

#### File: [`market_intelligence_agent.py`](../market_intelligence_agent.py#L1040-1057)

**Before (line 1048)**:
```python
plotting_result = await Runner.run(
    self.plotting_agent,
    input=query,
    session=None,  # ❌ Plot queries not added to history
    run_config=...
)
```

**After (line 1048)**:
```python
plotting_result = await Runner.run(
    self.plotting_agent,
    input=query,
    session=session,  # ✅ Plot queries now added to history
    run_config=...
)
```

**Comment updated (line 1042)**:
```python
# BEFORE
# IMPORTANT: Don't pass session here either, as plotting agent doesn't need conversation context

# AFTER
# IMPORTANT: Pass session so plot queries are added to conversation history
```

### Why This Works

When `Runner.run()` executes with a session:
1. **User query** automatically gets added to SQLiteSession
2. **Agent response** automatically gets added to SQLiteSession
3. **Conversation history** is maintained across all query types
4. **Future queries** can reference past plot requests

Now the flow is consistent:

| Query Type | Agent Used | Session Parameter | Added to History? |
|------------|------------|-------------------|-------------------|
| "Plot Netherlands..." | Plotting Agent | `session=session` ✅ | YES ✅ |
| "What about Italy?" | Market Intelligence | `session=session` ✅ | YES ✅ |
| "What did I ask before?" | Market Intelligence | `session=session` ✅ | YES ✅ |

## Impact Analysis

### What Changes
- ✅ Plot queries now appear in conversation history
- ✅ "What did I ask before?" includes ALL previous queries
- ✅ "What were my previous queries?" shows complete history
- ✅ Consistent behavior across all query types

### What Stays the Same
- ✅ Classification agent still uses `session=None` (correct - avoids duplicate classification messages)
- ✅ Plot generation still works identically
- ✅ Data queries still work identically
- ✅ No changes to PostgreSQL storage

### Performance Considerations
- Slight increase in SQLite storage (plot queries now stored)
- No performance impact on plot generation
- Minimal memory overhead

## Testing Verification

### Test Case 1: Plot Query History
```
User: "Plot Netherlands PV installations from 2020 to 2024"
Bot: [Chart renders]
User: "What did I ask before?"
Bot: Should mention "Plot Netherlands PV installations..."
✅ Plot query appears in history
```

### Test Case 2: Mixed Query Types
```
User: "Show market trends"
Bot: [Text response]
User: "Plot market share by country"
Bot: [Chart renders]
User: "What about Italy?"
Bot: [Text response]
User: "What were all my previous queries?"
Bot: Should list all three queries in order
✅ Complete history with both text and plot queries
```

### Test Case 3: Multiple Plot Queries
```
User: "Plot installations for Netherlands"
Bot: [Chart 1]
User: "Now plot for Italy"
Bot: [Chart 2]
User: "What did I ask before?"
Bot: Should mention both plot queries
✅ Multiple plot queries all recorded
```

### Test Case 4: Follow-up on Plot
```
User: "Plot market share"
Bot: [Chart]
User: "Can you make it a line chart instead?"
Bot: Should understand context from previous plot query
✅ Agent has access to previous plot conversation
```

## Why The Original Design Was Wrong

The original comment said:
> "IMPORTANT: Don't pass session here either, as plotting agent doesn't need conversation context"

This was based on a misunderstanding:
- ❌ **Assumed**: Plotting agent doesn't need context, so don't use session
- ✅ **Reality**: Even if agent doesn't need context, session is needed to RECORD the query for future reference

The session serves TWO purposes:
1. **Input context** - Providing past messages to the agent
2. **Output recording** - Storing current query/response for future agents

Even if (1) is not needed, (2) is ALWAYS needed for conversation continuity.

## Comparison with Other Agents

| Agent | Classification | Main Agent Session | Maintains History? |
|-------|---------------|-------------------|-------------------|
| **Market Intelligence** (BEFORE FIX) | `session=None` ✅ | Plot: `None` ❌<br>Data: `session` ✅ | Partial ❌ |
| **Market Intelligence** (AFTER FIX) | `session=None` ✅ | Plot: `session` ✅<br>Data: `session` ✅ | Complete ✅ |
| **News** | `session=None` ✅ | All: `session` ✅ | Complete ✅ |
| **Digitalization** | `session=None` ✅ | All: `session` ✅ | Complete ✅ |
| **Price** | N/A (no classification) | `session=session` ✅ | Complete ✅ |

The market intelligence agent is now consistent with the other agents.

## Related Issues

### Previous Investigation
- **BUGFIX_CONVERSATION_HISTORY_SYNC_ISSUE.md** - Initially thought the issue was dual storage (PostgreSQL vs SQLite)
  - That document incorrectly disabled SQLiteSession entirely
  - This would have broken conversation memory completely
  - The real issue was selective session passing

### Lesson Learned
When debugging conversation memory issues:
1. ✅ Check if session is being passed to ALL agent branches
2. ✅ Verify session is not `None` when it should maintain history
3. ✅ Test with different query types (plot vs data vs follow-up)
4. ❌ Don't assume the issue is a storage system problem

## Files Modified

### [`market_intelligence_agent.py`](../market_intelligence_agent.py)

**Line 1048**: Changed `session=None` to `session=session`
**Line 1042**: Updated comment to reflect correct reasoning

**Impact**: Single-line fix with major improvement to conversation continuity.

## Summary

**The Problem**: Plot queries were not being added to conversation history because the plotting agent was called with `session=None`.

**The Solution**: Pass `session=session` to the plotting agent so all queries are recorded in conversation history.

**The Result**: Complete conversation history with all query types included, matching the behavior of news and digitalization agents.
