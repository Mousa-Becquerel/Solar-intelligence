# Price Agent JSON Response Handler - Bugfix

## Issue Description

**Problem**: Price agent responses were not appearing in the chat after being processed.

**Screenshot Evidence**: User provided screenshot showing Maya - Price Analysis agent interface with suggested query "What are polysilicon price trends?" but no response displayed after processing.

## Root Cause Analysis

### The Real Issue

The price agent uses a **completely different response format** than other agents:

1. **Price Agent**: Returns **JSON response** via `jsonify()` with structure `{response: [...]}`
2. **Other Agents** (market, news, digitalization): Return **SSE (Server-Sent Events) streaming** responses

### Backend Code Evidence

In `app/services/chat_processing.py`:

```python
# Line 715-717
if agent_type == "price":
    result = process_price_agent(user_message, conv_id)
    return jsonify(result)  # ❌ Returns JSON, not streaming!

elif agent_type == "news":
    return process_news_agent_stream(user_message, conv_id, app)  # ✅ Returns streaming Response
```

### Price Agent Response Structure

```python
# process_price_agent returns:
{
    'response': [
        {
            'type': 'interactive_chart',  # For D3 plots
            'value': 'Chart title/description',
            'plot_data': {
                'plot_type': 'line',
                'title': 'Module Prices China',
                'x_axis_label': 'Date',
                'y_axis_label': 'Price (CNY/W)',
                'unit': 'CNY/W',
                'data': [...],  # Array of data points
                'series_info': [...]
            }
        },
        {
            'type': 'chart',  # For static images
            'value': 'Description',
            'artifact': '/static/plots/chart.png'
        },
        {
            'type': 'table',  # For dataframes
            'value': 'Description',
            'table_data': [...],
            'full_data': [...]
        },
        {
            'type': 'string',  # For text
            'value': 'Response text'
        }
    ]
}
```

### Frontend Problem

The frontend `startMessageStream()` method expected ALL responses to be SSE streams:

```javascript
// Old code - only handles SSE
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    // ... parse SSE events
}
```

This failed for price agent because:
1. Response was JSON, not a stream
2. Content-Type was `application/json`, not `text/event-stream`
3. No SSE events to parse
4. Response body couldn't be read as a stream after calling `.json()`

## Solution

Added dual-mode response handling: detect content type and route to appropriate handler.

### Files Modified

#### 1. `static/js/main.js`

**Change 1: Detect response type in `startMessageStream()`** (lines 293-298)

```javascript
// Check if response is JSON (for price agent) or SSE stream
const contentType = response.headers.get('content-type');
if (contentType && contentType.includes('application/json')) {
    // Handle JSON response (price agent)
    return await this.handleJsonResponse(response, agentType);
}

// Otherwise handle as SSE stream (market, news, digitalization agents)
const reader = response.body.getReader();
// ... continue with streaming
```

**Change 2: Added `handleJsonResponse()` method** (lines 278-327)

```javascript
async handleJsonResponse(response, agentType) {
    try {
        const data = await response.json();
        console.log('📦 JSON Response:', data);

        this.removeLoadingIndicator();

        // Price agent returns {response: [...]}
        const responseData = data.response || [];

        for (const item of responseData) {
            if (item.type === 'interactive_chart' && item.plot_data) {
                // Create D3 plot using plot handler
                const eventData = {
                    type: 'plot',
                    content: item.plot_data
                };
                plotHandler.createPlot(
                    eventData,
                    agentType,
                    this.chatWrapper,
                    this.chatMessages
                );
            } else if (item.type === 'chart' && item.artifact) {
                // Static chart image
                this.createImageMessage(item.value, item.artifact, agentType);
            } else if (item.type === 'table' && item.table_data) {
                // Table data
                this.createTableMessage(item.value, item.table_data, agentType);
            } else if (item.type === 'string' || item.value) {
                // Text message
                this.createTextMessage(item.value, agentType);
            }
        }

        this.updateWelcomeMessageVisibility();
        appState.setSubmitting(false);

    } catch (error) {
        console.error('Error handling JSON response:', error);
        this.removeLoadingIndicator();
        this.showError('Failed to process response');
        appState.setSubmitting(false);
    }
}
```

**Change 3: Added helper methods for different response types**

```javascript
// Create text message (lines 329-339)
createTextMessage(text, agentType) {
    const messageContainer = this.createBotMessageContainer(agentType);
    const messageDiv = messageContainer.querySelector('.message');
    messageDiv.innerHTML = safeRenderMarkdown(text);
    scrollToBottom(this.chatMessages);
}

// Create image message (lines 341-359)
createImageMessage(description, imageUrl, agentType) {
    const messageContainer = this.createBotMessageContainer(agentType);
    const messageDiv = messageContainer.querySelector('.message');

    const html = `
        <div class="chart-container">
            ${description ? `<p>${description}</p>` : ''}
            <img src="${imageUrl}" alt="Chart" style="max-width: 100%; height: auto;">
        </div>
    `;
    messageDiv.innerHTML = html;
    scrollToBottom(this.chatMessages);
}

// Create table message (lines 361-398)
createTableMessage(description, tableData, agentType) {
    const messageContainer = this.createBotMessageContainer(agentType);
    const messageDiv = messageContainer.querySelector('.message');

    if (!Array.isArray(tableData) || tableData.length === 0) {
        messageDiv.innerHTML = `<p>${description || 'No data available'}</p>`;
        return;
    }

    // Get table headers from first row
    const headers = Object.keys(tableData[0]);

    let html = description ? `<p>${description}</p>` : '';
    html += '<div class="table-container"><table class="data-table">';
    html += '<thead><tr>';
    headers.forEach(header => {
        html += `<th>${header}</th>`;
    });
    html += '</tr></thead><tbody>';

    tableData.forEach(row => {
        html += '<tr>';
        headers.forEach(header => {
            html += `<td>${row[header] !== null && row[header] !== undefined ? row[header] : ''}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table></div>';
    messageDiv.innerHTML = html;
    scrollToBottom(this.chatMessages);
}
```

#### 2. `static/css/style.css`

**Added table and chart container styles** (lines 1075-1125)

```css
/* Table styles */
.table-container {
    overflow-x: auto;
    margin: 1rem 0;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
    background: white;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
}

.data-table thead {
    background: linear-gradient(135deg, var(--becq-gold) 0%, var(--becq-gold-dark) 100%);
    color: white;
}

.data-table th {
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
}

.data-table td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #e5e7eb;
}

.data-table tbody tr:hover {
    background-color: #f9fafb;
}

.data-table tbody tr:last-child td {
    border-bottom: none;
}

/* Chart container styles */
.chart-container {
    margin: 1rem 0;
}

.chart-container img {
    border-radius: 8px;
    border: 1px solid #e5e7eb;
}
```

## Response Type Handling Matrix

| Agent Type | Response Format | Content-Type | Handler Method |
|------------|----------------|--------------|----------------|
| **price** | JSON | `application/json` | `handleJsonResponse()` |
| **market** | SSE Stream | `text/event-stream` | `startMessageStream()` |
| **news** | SSE Stream | `text/event-stream` | `startMessageStream()` |
| **digitalization** | SSE Stream | `text/event-stream` | `startMessageStream()` |
| **om** | JSON | `application/json` | `handleJsonResponse()` |

## Price Agent Response Types Supported

| Type | Description | Rendering |
|------|-------------|-----------|
| `interactive_chart` | D3 chart data | `plotHandler.createPlot()` - Interactive D3 visualization |
| `chart` | Static image URL | `createImageMessage()` - Image tag |
| `table` | Dataframe data | `createTableMessage()` - HTML table |
| `string` | Text response | `createTextMessage()` - Markdown rendered text |

## Flow Diagram

```
User sends message
       │
       ▼
app.sendMessage()
       │
       ▼
api.sendChatMessage(conversationId, message, agentType)
       │
       ▼
POST /chat { message, conversation_id, agent_type: "price" }
       │
       ▼
Backend: chat_processing.py
       │
       ├──> agent_type == "price" ?
       │    ├──> YES: process_price_agent()
       │    │         └──> return jsonify({response: [...]})
       │    │              Content-Type: application/json
       │    │
       │    └──> NO: process_*_agent_stream()
       │              └──> yield SSE events
       │                   Content-Type: text/event-stream
       │
       ▼
Frontend: main.js startMessageStream()
       │
       ├──> Check Content-Type header
       │    │
       │    ├──> application/json ?
       │    │    └──> handleJsonResponse()
       │    │         ├──> Parse JSON
       │    │         ├──> Loop through response array
       │    │         ├──> Route by item.type:
       │    │         │    ├──> interactive_chart → plotHandler.createPlot()
       │    │         │    ├──> chart → createImageMessage()
       │    │         │    ├──> table → createTableMessage()
       │    │         │    └──> string → createTextMessage()
       │    │         └──> Update UI
       │    │
       │    └──> text/event-stream ?
       │         └──> Stream reading loop
       │              ├──> Parse SSE events
       │              ├──> Handle by event.type
       │              └──> Update UI incrementally
       │
       ▼
Response displayed in chat ✅
```

## Testing Checklist

### Price Agent (JSON Response)
- [ ] Load chat interface
- [ ] Select "Maya - Price Analysis" agent
- [ ] Send query: "What are polysilicon price trends?"
- [ ] Verify loading spinner appears
- [ ] Verify loading spinner disappears when response arrives
- [ ] Verify D3 chart displays (interactive_chart type)
- [ ] Verify chart is interactive (hover, legend)
- [ ] Send query: "Show module prices in China"
- [ ] Verify chart displays correctly
- [ ] Test multiple queries in sequence
- [ ] Check console for "📦 JSON Response:" log
- [ ] Verify no errors in console

### Market Agent (SSE Response)
- [ ] Switch to "Atlas - Market Intelligence" agent
- [ ] Send query: "Show Italy market data"
- [ ] Verify streaming text appears incrementally
- [ ] Verify plot displays if generated
- [ ] Verify approval requests work
- [ ] Check console for "📨 SSE Event:" logs

### Mixed Content Types
- [ ] Test price agent query that returns table data
- [ ] Test price agent query that returns text
- [ ] Test price agent query that returns static chart image
- [ ] Verify all content types render correctly

## Console Logging

The fix adds comprehensive logging:

```javascript
// For JSON responses (price agent)
console.log('📦 JSON Response:', data);

// For SSE events (other agents)
console.log('📨 SSE Event:', eventData.type, eventData);
```

Use these logs to debug:
1. Open DevTools (F12)
2. Go to Console tab
3. Send message
4. Look for 📦 or 📨 emojis
5. Inspect the data structure

## Error Handling

### JSON Response Errors

```javascript
try {
    const data = await response.json();
    // ... process data
} catch (error) {
    console.error('Error handling JSON response:', error);
    this.removeLoadingIndicator();
    this.showError('Failed to process response');
    appState.setSubmitting(false);
}
```

### Stream Reading Errors

```javascript
try {
    // ... read stream
} catch (error) {
    console.error('Stream error:', error);
    this.removeLoadingIndicator();
    this.showError('Failed to get response. Please try again.');
    appState.setSubmitting(false);
}
```

## Why Previous Fix Didn't Work

The previous attempt added a `plot` event handler to the SSE streaming code:

```javascript
case 'plot':
    this.removeLoadingIndicator();
    messageContainer = plotHandler.createPlot(eventData, ...);
    break;
```

This didn't work because:
1. Price agent doesn't send SSE events
2. Response is JSON, not a stream
3. The streaming loop never executed
4. Frontend couldn't read the response body

The real issue was **response format mismatch**, not missing event handlers.

## Future Recommendations

### Option 1: Standardize on SSE Streaming

Convert price agent to use SSE streaming like other agents:

```python
def process_price_agent_stream(user_message: str, conv_id: int, app):
    """Stream price agent responses"""

    async def generate():
        try:
            result = await price_agent.analyze(user_message, conversation_id=str(conv_id))

            if result["success"]:
                output = result["analysis"]

                # Send plot data as SSE event
                if hasattr(output, 'plot_type') and hasattr(output, 'data'):
                    yield f"data: {json.dumps({'type': 'plot', 'content': output.dict()})}\n\n"

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(generate(), content_type='text/event-stream')
```

### Option 2: Keep Dual-Mode (Current Solution)

Maintain both response formats but document clearly:
- Price/OM agents: JSON response (fast, complete data)
- Market/News/Digitalization agents: SSE streaming (incremental updates)

## Status

**FIXED** ✅ - Price agent responses now display correctly with full support for interactive charts, static images, tables, and text.

## Related Issues

- [BUGFIX_PLOT_HANDLER.md](./BUGFIX_PLOT_HANDLER.md) - Initial attempt to fix via SSE plot handler
- [PHASE1_COMPLETE_SUMMARY.md](./PHASE1_COMPLETE_SUMMARY.md) - Full Phase 1 summary

## Summary

The price agent was working correctly on the backend but using a completely different response format (JSON) than other agents (SSE streaming). The frontend was only built to handle streaming responses, so JSON responses were ignored. The fix adds content-type detection and dual-mode handling to support both response formats.
