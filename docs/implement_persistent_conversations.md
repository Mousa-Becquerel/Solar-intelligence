# Implementing Persistent Conversations

## Problem

With multiple Gunicorn workers, conversation memory is lost when requests go to different workers because each worker has isolated RAM.

## Solution

Store conversations in PostgreSQL database instead of in-memory dictionaries.

---

## Step 1: Modify Agent Base Class

Create a helper class to manage database conversations:

```python
# Add to app.py

class ConversationManager:
    """Manages conversation persistence in database"""

    @staticmethod
    def save_message(conversation_id: int, sender: str, content: str):
        """Save a message to the database"""
        try:
            message = Message(
                conversation_id=conversation_id,
                sender=sender,
                content=content,
                timestamp=datetime.utcnow()
            )
            db.session.add(message)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error saving message: {e}")

    @staticmethod
    def get_conversation_messages(conversation_id: int, limit: int = 50):
        """Get conversation messages from database"""
        try:
            messages = Message.query.filter_by(
                conversation_id=conversation_id
            ).order_by(
                Message.timestamp.asc()
            ).limit(limit).all()

            return [
                {
                    'role': 'user' if msg.sender == 'user' else 'assistant',
                    'content': msg.content
                }
                for msg in messages
            ]
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []

    @staticmethod
    def clear_conversation(conversation_id: int):
        """Clear all messages for a conversation"""
        try:
            Message.query.filter_by(conversation_id=conversation_id).delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing conversation: {e}")
```

---

## Step 2: Modify Agent to Use Database

### Current Code (In-Memory - BAD):

```python
# pydantic_weaviate_agent.py:452
class MarketAgent:
    def __init__(self):
        self.conversation_memory: Dict[str, List[ModelMessage]] = {}  # ❌ RAM

    def query(self, user_message: str, conversation_id: str):
        # Get history from RAM
        if conversation_id in self.conversation_memory:
            message_history = self.conversation_memory[conversation_id]

        # ... process message ...

        # Save to RAM
        self.conversation_memory[conversation_id] = all_messages
```

### New Code (Database - GOOD):

```python
# pydantic_weaviate_agent.py
class MarketAgent:
    def __init__(self):
        # Remove in-memory storage
        pass

    def query(self, user_message: str, conversation_id: int):
        # Get history from DATABASE
        from app import ConversationManager

        db_messages = ConversationManager.get_conversation_messages(conversation_id)
        message_history = [
            ModelMessage(role=msg['role'], content=msg['content'])
            for msg in db_messages
        ]

        # ... process message with AI ...

        # Save user message to DATABASE
        ConversationManager.save_message(
            conversation_id=conversation_id,
            sender='user',
            content=user_message
        )

        # Save agent response to DATABASE
        ConversationManager.save_message(
            conversation_id=conversation_id,
            sender='assistant',
            content=agent_response
        )
```

---

## Step 3: Update Chat Endpoint

Modify `/chat` endpoint to use conversation IDs properly:

```python
@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_message = data.get('message', '')
    conversation_id = data.get('conversation_id')
    agent_type = data.get('agent', 'market')

    # Get or create conversation
    if not conversation_id:
        conversation = Conversation(
            user_id=current_user.id,
            agent_type=agent_type,
            title=user_message[:50]  # First 50 chars as title
        )
        db.session.add(conversation)
        db.session.commit()
        conversation_id = conversation.id

    # Call agent with conversation ID
    if agent_type == 'market':
        response = pydantic_agent.query(
            user_message=user_message,
            conversation_id=conversation_id  # Pass as int, not string
        )
    elif agent_type == 'price':
        response = module_prices_agent.query(
            user_message=user_message,
            conversation_id=conversation_id
        )
    elif agent_type == 'om':
        response = leo_om_agent.query(
            user_message=user_message,
            conversation_id=conversation_id
        )

    return jsonify({
        'response': response,
        'conversation_id': conversation_id  # Return to frontend
    })
```

---

## Step 4: Update Frontend to Track Conversation ID

Modify `main.js` to maintain conversation ID:

```javascript
// static/js/main.js

let currentConversationId = null;

async function sendMessage() {
    const message = messageInput.value.trim();

    const response = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            message: message,
            conversation_id: currentConversationId,  // Send current ID
            agent: currentAgent
        })
    });

    const data = await response.json();

    // Store conversation ID for next message
    currentConversationId = data.conversation_id;

    // Display response...
}

// Reset conversation ID when starting new chat
function newChat() {
    currentConversationId = null;  // Reset ID
    // Clear messages...
}
```

---

## Step 5: Update Gunicorn Config

Now you can safely use multiple workers:

```python
# scripts/deployment/gunicorn.conf.py

# Multiple workers are now safe!
workers = 4  # Changed from 1
worker_class = "gthread"
threads = 4
```

---

## Step 6: Performance Optimization

Add database indexes for fast lookups:

```sql
-- Run in PostgreSQL

CREATE INDEX IF NOT EXISTS idx_message_conversation_id
ON message(conversation_id);

CREATE INDEX IF NOT EXISTS idx_message_timestamp
ON message(timestamp);

CREATE INDEX IF NOT EXISTS idx_conversation_user_id
ON conversation(user_id);
```

---

## Migration Strategy

### Phase 1: Test Locally

1. Implement `ConversationManager` class
2. Update one agent (e.g., Market agent) to use database
3. Test thoroughly with `workers = 2` locally
4. Verify conversations persist across requests

### Phase 2: Deploy to AWS

1. Run database migration (create indexes)
2. Deploy updated code
3. Update task definition to use `workers = 4`
4. Monitor CloudWatch logs for errors

### Phase 3: Update Remaining Agents

1. Update Price agent to use database
2. Update O&M agent to use database
3. Update News agent to use database
4. Remove all `conversation_memory` dictionaries

---

## Benefits After Implementation

| Metric | Before | After |
|--------|--------|-------|
| **Workers** | 1 | 4 |
| **Concurrent Requests** | 4 | 16 |
| **Concurrent Users** | 8-15 | 50-100 |
| **Conversation Persistence** | ❌ Lost on restart | ✅ Persists forever |
| **Cross-Session History** | ❌ No | ✅ Yes |
| **Worker Crash Recovery** | ❌ All conversations lost | ✅ No data loss |

---

## Estimated Implementation Time

- **Day 1:** Implement `ConversationManager` class (2-3 hours)
- **Day 2:** Update Market agent + testing (4-6 hours)
- **Day 3:** Update remaining agents (4-6 hours)
- **Day 4:** Deploy and monitor (2-3 hours)

**Total: 2-3 days of focused development**

---

## Testing Checklist

- [ ] Create new conversation
- [ ] Send multiple messages
- [ ] Verify conversation persists across requests
- [ ] Restart application
- [ ] Verify conversation still exists
- [ ] Test with `workers = 4`
- [ ] Send messages rapidly (test concurrency)
- [ ] Clear conversation
- [ ] Verify all messages deleted

---

## Alternative: Quick Redis Solution

If you need a faster implementation (4-6 hours), use Redis instead:

```python
import redis

# Connect to Redis (AWS ElastiCache)
redis_client = redis.Redis(
    host='your-redis.cache.amazonaws.com',
    port=6379,
    decode_responses=True
)

class ConversationManager:
    @staticmethod
    def save_message(conversation_id: str, messages: list):
        # Store as JSON in Redis
        redis_client.setex(
            f"conversation:{conversation_id}",
            3600,  # 1 hour expiry
            json.dumps(messages)
        )

    @staticmethod
    def get_messages(conversation_id: str):
        data = redis_client.get(f"conversation:{conversation_id}")
        return json.loads(data) if data else []
```

**Pros:**
- Faster implementation (4-6 hours vs 2-3 days)
- Better performance than PostgreSQL
- Easy to implement

**Cons:**
- Additional AWS service ($15-30/month)
- Conversations expire after timeout
- Need to manage Redis separately

---

## Recommendation

Use **PostgreSQL solution** because:
1. You already have the database and models
2. No additional cost
3. Conversations persist forever
4. Better for long-term scalability
5. Users can see conversation history

Start with Market agent only, test thoroughly, then migrate the rest.
