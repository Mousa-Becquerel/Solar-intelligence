# Digitalization Agent Memory Configuration

The digitalization agent uses SQLite for conversation memory storage.

## 🏠 SQLite Session Storage

**Default and only option** - No configuration needed!

- ✅ Automatically uses SQLite for local storage
- ✅ Conversations stored in local database file
- ✅ No external dependencies required
- ✅ Simple and reliable
- ⚠️ Sessions may be lost on container restart (depending on volume mounting)
- ⚠️ Not ideal for multi-instance deployments (use sticky sessions in load balancer)

## Why SQLite Only?

PostgreSQL and Redis session storage require async database drivers:
- PostgreSQL needs `asyncpg` (not regular `psycopg`)
- Redis needs async Redis client
- Adds complexity and dependencies

For most use cases, SQLite is sufficient:
- ✅ Works perfectly for single-instance deployments
- ✅ No additional infrastructure costs
- ✅ Zero configuration required
- ✅ Conversations persist across requests

## Future: Multi-Instance Support

If you need to scale to multiple instances, consider:
1. **Sticky sessions** in your load balancer (simplest)
2. **Shared volume** for SQLite database file
3. **Migrate to async drivers** for PostgreSQL/Redis (more complex)

## Session File Location

SQLite sessions are stored in the working directory:
- File: `agent_sessions_digitalization_<conversation_id>.db`
- Each conversation has its own database file
- Files persist until manually deleted or container is destroyed

## Monitoring Sessions

Check logs for session creation:
```
✅ Digitalization Agent initialized (Memory: SQLite)
Created SQLite session for conversation <id>
```

## Cleanup

To clear old sessions, delete the session files:
```bash
rm agent_sessions_digitalization_*.db
```

Or use the agent's cleanup method:
```python
agent.clear_conversation_memory(conversation_id="<id>")  # Clear specific conversation
agent.clear_conversation_memory()  # Clear all conversations
```
