# App Package - Modular Architecture

This directory contains the refactored modular architecture for the Solar Intelligence platform.

## Directory Structure

```
app/
├── __init__.py           # Package initialization
├── config.py             # Configuration management (Step 2)
├── extensions.py         # Flask extensions (Step 2)
│
├── models/               # Database models
│   ├── __init__.py
│   ├── user.py          # User, Waitlist models
│   ├── conversation.py  # Conversation, Message models
│   ├── feedback.py      # Feedback, Survey models
│   └── agent.py         # HiredAgent model
│
├── schemas/              # Pydantic schemas (validation + API)
│   ├── __init__.py
│   ├── user.py          # UserSchema, UserCreateSchema, etc.
│   ├── conversation.py  # ConversationSchema, MessageSchema
│   ├── agent.py         # AgentSchema, AgentRequestSchema
│   └── plot.py          # PlotDataSchema, PlotResultSchema
│
├── services/             # Business logic layer (framework-agnostic)
│   ├── __init__.py
│   ├── auth_service.py          # Authentication, registration
│   ├── conversation_service.py  # Conversation management
│   ├── agent_service.py         # Agent coordination
│   ├── admin_service.py         # Admin operations
│   └── export_service.py        # Export functionality
│
├── routes/              # Route handlers (thin layer)
│   ├── __init__.py
│   ├── auth.py          # Login, register, logout
│   ├── chat.py          # Chat interface, query handling
│   ├── conversation.py  # Conversation CRUD
│   ├── admin.py         # Admin panel
│   ├── api.py           # API endpoints
│   └── static_pages.py  # Landing, waitlist, etc.
│
├── agents/              # AI agent implementations
│   ├── __init__.py
│   ├── base.py          # Base agent class
│   ├── module_prices.py # ModulePricesAgent
│   ├── news.py          # NewsAgent
│   ├── leo_om.py        # LeoOMAgent
│   ├── digitalization.py # DigitalizationAgent
│   ├── market_intelligence.py # MarketIntelligenceAgent
│   └── weaviate.py      # WeaviateAgent
│
├── utils/               # Utility functions
│   ├── __init__.py
│   ├── memory.py        # Memory monitoring
│   ├── validators.py   # Input validation
│   └── helpers.py       # General helpers
│
└── static/              # Frontend assets
    ├── js/
    │   ├── modules/     # Modular ES6 JavaScript
    │   │   ├── api.js          # API client
    │   │   ├── auth.js         # Authentication
    │   │   ├── chat.js         # Chat interface
    │   │   ├── conversations.js # Conversation management
    │   │   ├── plots.js        # Plot rendering
    │   │   ├── export.js       # Export functionality
    │   │   └── utils.js        # Utilities
    │   ├── main.js      # Entry point (orchestrates modules)
    │   └── legacy/
    │       └── main.js  # Original (temporary backup)
    ├── css/
    └── images/
```

## Architecture Principles

### 1. Separation of Concerns
- **Routes**: Handle HTTP requests/responses
- **Services**: Contain business logic
- **Models**: Define data structures
- **Schemas**: Validate input/output

### 2. Framework Agnostic Business Logic
Services don't depend on Flask-specific code, making them reusable with FastAPI.

### 3. Type Safety
- Python type hints throughout
- Pydantic schemas for validation
- JSDoc comments in JavaScript

### 4. Clear Dependencies
```
Routes → Services → Models
  ↓         ↓
Schemas   Schemas
```

## Migration Status

| Step | Status | Description |
|------|--------|-------------|
| 1. Directory Structure | ✅ Complete | Created modular directory structure |
| 2. Config & Extensions | 🔄 Next | Extract configuration and extensions |
| 3. Pydantic Schemas | ⏳ Pending | Create validation schemas |
| 4. Service Layer | ⏳ Pending | Extract business logic |
| 5. Blueprint Routes | ⏳ Pending | Organize routes |
| 6. JS Modules | ⏳ Pending | Modularize frontend |
| 7. Type Hints | ⏳ Pending | Add comprehensive types |

## Current State

- **Step 1 Complete**: Directory structure created
- **Existing Code**: All existing code remains in root directory
- **No Breaking Changes**: Application still runs from root `app.py`

## Next Steps

1. Create `config.py` and `extensions.py`
2. Update root `app.py` to use new configuration
3. Test that application still works
4. Proceed to Step 3: Pydantic Schemas

---

**See**: [docs/PHASE1_REFACTORING_PLAN.md](../docs/PHASE1_REFACTORING_PLAN.md) for detailed plan.
