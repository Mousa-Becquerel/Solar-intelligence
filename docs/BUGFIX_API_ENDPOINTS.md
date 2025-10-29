# API Endpoint Bugfix

## Issue

After refactoring to modular architecture, the application was trying to use incorrect API endpoints:
- ❌ Using `/api/chat` for creating conversations (404 error)
- ❌ Using EventSource with query parameters for streaming

## Root Cause

The new modular code assumed different endpoints than what the backend actually implements.

## Backend Endpoints (Actual)

```python
# Conversation endpoints
POST /conversations/fresh      # Create new conversation
GET  /conversations            # Get all conversations
GET  /conversations/<id>       # Get specific conversation
DELETE /conversations/<id>     # Delete conversation

# Chat endpoints
POST /chat                     # Send message (returns SSE stream)
  Body: {
    message: string,
    conversation_id: number,
    agent_type: string
  }

# Approval endpoint
POST /api/approval_response    # Send approval response
  Body: {
    approved: boolean,
    conversation_id: number,
    context: string
  }
```

## Fixes Applied

### 1. Fixed `modules/core/api.js`

**Before:**
```javascript
async createConversation(agentType) {
    return this.post('/api/chat', { agent_type: agentType });
}

createChatStream(conversationId, message, agentType) {
    const params = new URLSearchParams({
        message: message,
        conversation_id: conversationId || '',
        agent_type: agentType
    });
    return new EventSource(`/api/chat?${params.toString()}`);
}
```

**After:**
```javascript
async createConversation() {
    return this.post('/conversations/fresh');
}

async sendChatMessage(conversationId, message, agentType) {
    const response = await this.request('/chat', {
        method: 'POST',
        body: JSON.stringify({
            message: message,
            conversation_id: conversationId,
            agent_type: agentType
        })
    });
    return response;
}
```

### 2. Fixed `modules/conversation/conversationManager.js`

**Before:**
```javascript
async createConversation(agentType) {
    const data = await api.createConversation(agentType);
    const newConvId = data.conversation_id;
    // ...
}
```

**After:**
```javascript
async createConversation() {
    const data = await api.createConversation();
    const newConvId = data.id;  // Backend returns { id: number }
    // ...
}
```

### 3. Fixed `main.js` - Stream Handling

**Before (EventSource):**
```javascript
this.currentEventSource = api.createChatStream(conversationId, message, agentType);

this.currentEventSource.onmessage = (event) => {
    const eventData = JSON.parse(event.data);
    // ...
};

this.currentEventSource.onerror = (error) => {
    // ...
};
```

**After (Fetch Streaming):**
```javascript
const response = await api.sendChatMessage(conversationId, message, agentType);
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');

    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const eventData = JSON.parse(line.slice(6));
            // Handle event
        }
    }
}
```

### 4. Fixed `main.js` - Conversation Creation Call

**Before:**
```javascript
conversationId = await conversationManager.createConversation(agentType);
```

**After:**
```javascript
conversationId = await conversationManager.createConversation();
```

## Why Fetch Streaming Instead of EventSource?

The backend returns SSE events via a POST request with JSON body. EventSource only supports GET requests with query parameters, so we use fetch with manual stream reading instead.

## Testing

Test the following flow:
1. ✅ Load page - no errors
2. ✅ Type message and send
3. ✅ Conversation created (check Network tab: POST /conversations/fresh)
4. ✅ Message sent (check Network tab: POST /chat)
5. ✅ Response streams back
6. ✅ Conversation appears in sidebar
7. ✅ Send another message in same conversation
8. ✅ Select different conversation
9. ✅ Delete conversation

## Network Requests (Expected)

**First Message:**
```
1. POST /conversations/fresh → { id: 123 }
2. POST /chat (body: { message, conversation_id: 123, agent_type })
   Response: SSE stream
3. GET /conversations → Update sidebar list
```

**Subsequent Messages:**
```
1. POST /chat (body: { message, conversation_id: 123, agent_type })
   Response: SSE stream
```

## Files Modified

- ✅ `static/js/modules/core/api.js`
- ✅ `static/js/modules/conversation/conversationManager.js`
- ✅ `static/js/main.js`

## Backward Compatibility

No breaking changes for users. The UI and behavior remain identical.

## Status

**FIXED** ✅ - Application should now work correctly with proper endpoints.
