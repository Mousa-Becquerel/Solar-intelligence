# Architecture Improvements for Concurrent User Support

## Current Issues (Why User 2 Waits for User 1)

### 1. Blocking Synchronous Calls
```python
# ❌ PROBLEM: Blocks entire thread for 10-30 seconds
result = loop.run_until_complete(run_agent())
```

### 2. Shared Mutable State
```python
# ❌ PROBLEM: Race conditions
self.last_user_query = user_message        # Shared across all users
self.last_dataframe = None                 # Shared across all users
self.last_market_plot_data_result = None   # Shared across all users
```

### 3. Limited Concurrency
```
workers = 1
threads = 4
= Only 4 concurrent requests maximum
```

---

## Improvement Strategy

### Phase 1: Async Endpoints (Immediate - 1 hour)

#### 1.1 Convert Flask to Async
```python
# app.py - Change from sync to async

# BEFORE (Blocking)
@app.route('/chat', methods=['POST'])
@login_required
def chat():
    result = pydantic_agent.process_query(user_message, conversation_id=str(conv_id))
    # ❌ Blocks thread waiting for result

# AFTER (Non-blocking)
@app.route('/chat', methods=['POST'])
@login_required
async def chat():
    result = await pydantic_agent.process_query_async(user_message, conversation_id=str(conv_id))
    # ✅ Releases thread while waiting for LLM
```

#### 1.2 Make Agent Method Truly Async
```python
# pydantic_weaviate_agent.py

class PydanticWeaviateAgent:
    async def process_query_async(self, user_message: str, conversation_id: str = None):
        """Non-blocking async query processing"""

        # Create request-scoped context (no shared state)
        request_context = {
            'user_query': user_message,
            'dataframe': None,
            'plot_result': None
        }

        # Get conversation history
        message_history = []
        if conversation_id and conversation_id in self.conversation_memory:
            async with self.memory_lock:  # Thread-safe read
                message_history = self.conversation_memory[conversation_id].copy()

        # ✅ Await directly - no blocking
        result = await self.data_analysis_agent.run(
            user_message,
            message_history=message_history,
            usage_limits=UsageLimits(request_limit=10, total_tokens_limit=20000)
        )

        # Store conversation memory (thread-safe)
        if conversation_id:
            async with self.memory_lock:  # Thread-safe write
                self.conversation_memory[conversation_id] = result.all_messages()

        # Use request context instead of self.last_*
        return self._process_result(result, request_context)
```

---

### Phase 2: Thread Safety (1 hour)

#### 2.1 Add Async Locks
```python
import asyncio

class PydanticWeaviateAgent:
    def __init__(self):
        self.conversation_memory: Dict[str, List[ModelMessage]] = {}
        self.memory_lock = asyncio.Lock()  # Protect conversation_memory
```

#### 2.2 Use Request-Scoped State
```python
# Instead of instance variables, use context manager
from contextvars import ContextVar

request_state = ContextVar('request_state', default=None)

class RequestContext:
    def __init__(self):
        self.user_query = None
        self.dataframe = None
        self.plot_result = None

async def process_query_async(self, user_message: str, conversation_id: str = None):
    # Create isolated context for this request
    ctx = RequestContext()
    ctx.user_query = user_message
    request_state.set(ctx)

    # Now all code uses: request_state.get().user_query
    # Instead of: self.last_user_query
```

---

### Phase 3: Scale Workers (30 mins)

#### 3.1 Update Gunicorn Config
```python
# scripts/deployment/gunicorn.conf.py

# BEFORE
workers = 1
threads = 4
# = 4 concurrent requests

# AFTER
workers = 4              # 4 worker processes
threads = 8              # 8 threads per worker
worker_class = "uvicorn.workers.UvicornWorker"  # Async worker
# = 32 concurrent requests
```

#### 3.2 Move Memory to Redis (Optional - for true scalability)
```python
import redis.asyncio as redis

class PydanticWeaviateAgent:
    def __init__(self):
        self.redis = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost'))

    async def get_conversation_memory(self, conversation_id: str):
        data = await self.redis.get(f"conv:{conversation_id}")
        return json.loads(data) if data else []

    async def set_conversation_memory(self, conversation_id: str, messages):
        await self.redis.set(
            f"conv:{conversation_id}",
            json.dumps(messages),
            ex=3600  # 1 hour TTL
        )
```

---

## Implementation Priority

### 🔴 Critical (Do First)
1. **Make process_query async** - Eliminates blocking
2. **Add thread locks to conversation_memory** - Prevents race conditions
3. **Use request context for shared state** - Isolates user data

### 🟡 Important (Do Soon)
4. **Increase workers to 4, threads to 8** - 32 concurrent users
5. **Convert Flask endpoints to async** - Full async pipeline

### 🟢 Nice to Have (Future)
6. **Move conversation memory to Redis** - Horizontal scaling
7. **Add connection pooling** - Better resource usage
8. **Implement queue system (Celery)** - Handle spikes

---

## Expected Results

### Before Improvements
- **Concurrent users:** 4
- **User experience:** User 2 waits for User 1 to finish
- **Response time:** 10-30s (blocking)

### After Phase 1 + 2 (Async + Thread Safety)
- **Concurrent users:** 32+
- **User experience:** All users get immediate responses
- **Response time:** 10-30s (but non-blocking - server stays responsive)

### After Phase 3 (Redis + Scaling)
- **Concurrent users:** 100+
- **User experience:** Instant responses, even under load
- **Response time:** 10-30s (LLM bound, not server bound)
- **Horizontal scaling:** Can add more servers

---

## Files to Modify

1. **pydantic_weaviate_agent.py**
   - Add `async def process_query_async()`
   - Add `asyncio.Lock()` for conversation_memory
   - Replace `self.last_*` with `RequestContext`

2. **app.py**
   - Change `@app.route` to `async def`
   - Change `pydantic_agent.process_query()` to `await pydantic_agent.process_query_async()`

3. **scripts/deployment/gunicorn.conf.py**
   - Increase workers and threads
   - Use async worker class

4. **requirements.txt** (if using Redis)
   - Add `redis[hiredis]>=5.0.0`
   - Add `uvicorn[standard]>=0.24.0`

---

## Testing Concurrent Users

```bash
# Test script to simulate 10 concurrent users
import asyncio
import aiohttp

async def test_user(session, user_id):
    async with session.post('http://localhost:5000/chat', json={
        'message': f'User {user_id} query',
        'conversation_id': user_id
    }) as resp:
        print(f"User {user_id}: {resp.status}")

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [test_user(session, i) for i in range(10)]
        await asyncio.gather(*tasks)  # All run concurrently

asyncio.run(main())
```

Expected: All 10 users get responses simultaneously (not sequential)
