# Refactored Architecture Guide

## Overview

The application has been successfully migrated from a monolithic architecture (`app.py` - 147KB, 2600+ lines) to a modular, blueprint-based architecture using the Flask application factory pattern.

**Version:** 2.0.0-refactor

## Architecture Structure

```
Full_data_DH_bot/
├── app/                          # Main application package (REFACTORED)
│   ├── __init__.py              # App factory (create_app)
│   ├── config.py                # Configuration classes
│   ├── extensions.py            # Flask extensions (db, login_manager, etc.)
│   ├── routes/                  # Blueprint route definitions
│   │   ├── __init__.py         # Blueprint exports
│   │   ├── admin.py            # Admin routes (/admin/*)
│   │   ├── auth.py             # Authentication (/auth/*)
│   │   ├── chat.py             # Chat interface (/, /chat, /api/agents/*)
│   │   ├── conversation.py     # Conversation management (/conversations/*)
│   │   └── static_pages.py     # Static pages (/, /landing, /contact, etc.)
│   └── services/               # Business logic layer
│       ├── admin_service.py    # Admin operations
│       ├── auth_service.py     # Authentication logic
│       └── conversation_service.py # Conversation management
├── routes/                      # Legacy routes (being phased out)
│   └── profile.py              # Profile blueprint (temporary)
├── templates/                   # Jinja2 templates
├── static/                      # Static assets (CSS, JS, images)
├── models.py                    # SQLAlchemy models
├── run_refactored.py           # Application entry point
├── app.py                       # OLD MONOLITHIC VERSION (DO NOT USE)
└── docker-compose.yml          # Docker configuration
```

## Key Differences: Monolithic vs Refactored

### Old Monolithic Architecture (app.py)
```python
# All routes defined directly on app object
@app.route('/admin/users')
def admin_users():
    ...

# Templates reference: url_for('admin_users')
```

### New Refactored Architecture
```python
# Routes organized in blueprints
# app/routes/admin.py
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
def users():
    ...

# Templates reference: url_for('admin.users')
```

## Blueprint Structure

### 1. **admin_bp** (`/admin`)
- **File:** `app/routes/admin.py`
- **Service:** `app/services/admin_service.py`
- **Routes:**
  - `/admin/users` → `admin.users`
  - `/admin/users/pending` → `admin.pending_users`
  - `/admin/users/<id>/approve` → `admin.approve_user`
  - `/admin/users/create` → `admin.create_user`
  - `/admin/users/<id>/update` → `admin.update_user`
  - `/admin/users/<id>/delete` → `admin.delete_user`
  - `/admin/users/<id>/toggle` → `admin.toggle_user`

### 2. **auth_bp** (`/auth`)
- **File:** `app/routes/auth.py`
- **Service:** `app/services/auth_service.py`
- **Routes:**
  - `/auth/login` → `auth.login`
  - `/auth/register` → `auth.register`
  - `/auth/logout` → `auth.logout`
  - `/auth/request-reset` → `auth.request_reset`

### 3. **chat_bp** (no prefix)
- **File:** `app/routes/chat.py`
- **Routes:**
  - `/` → `chat.index`
  - `/chat` → `chat.agents`
  - `/api/agents/<agent_type>` → `chat.agent_endpoint`
  - `/health` → `chat.health`

### 4. **conversation_bp** (`/conversations`)
- **File:** `app/routes/conversation.py`
- **Service:** `app/services/conversation_service.py`
- **Routes:**
  - `/conversations` → `conversation.list_conversations`
  - `/conversations/<id>` → `conversation.get_conversation`
  - `/conversations/<id>/delete` → `conversation.delete_conversation`

### 5. **static_bp** (no prefix)
- **File:** `app/routes/static_pages.py`
- **Routes:**
  - `/landing` → `static.landing`
  - `/contact` → `static.contact`
  - `/privacy` → `static.privacy_policy`
  - `/terms` → `static.terms_of_service`

## URL Reference Migration

### Template URL Patterns

**CORRECT (Refactored):**
```html
<!-- Admin routes -->
<a href="{{ url_for('admin.users') }}">All Users</a>
<a href="{{ url_for('admin.pending_users') }}">Pending Approvals</a>

<!-- Auth routes -->
<a href="{{ url_for('auth.login') }}">Login</a>
<a href="{{ url_for('auth.register') }}">Register</a>

<!-- Chat routes -->
<a href="{{ url_for('chat.agents') }}">Dashboard</a>
<a href="{{ url_for('chat.index') }}">Home</a>
```

**INCORRECT (Monolithic - DO NOT USE):**
```html
<!-- OLD - Don't use these -->
<a href="{{ url_for('admin_users') }}">All Users</a>
<a href="{{ url_for('login') }}">Login</a>
<a href="{{ url_for('agents') }}">Dashboard</a>
```

## Docker Configuration

### Dockerfile
- **Entry Point:** `run_refactored.py`
- **Command:** `gunicorn --config scripts/deployment/gunicorn_refactored.conf.py run_refactored:app`
- **Environment:** `FLASK_APP=run_refactored.py`

### docker-compose.yml
Key volumes mounted for live development:
```yaml
volumes:
  - ./app:/app/app                    # Refactored application code
  - ./templates:/app/templates        # Jinja2 templates
  - ./static:/app/static              # CSS, JS, images
  - ./models.py:/app/models.py:ro     # Database models
  # Agent files
  - ./module_prices_agent.py:/app/module_prices_agent.py:ro
  - ./news_agent.py:/app/news_agent.py:ro
  - ./market_intelligence_agent.py:/app/market_intelligence_agent.py:ro
  # etc...
```

## Running the Application

### Development (Local)
```bash
# Set environment
export FLASK_ENV=development

# Run with Python
python run_refactored.py

# Or with Flask CLI
flask run
```

### Production (Docker)
```bash
# Build and start
docker-compose up --build

# Restart after code changes
docker-compose restart pv-market-analysis

# View logs
docker-compose logs -f pv-market-analysis
```

## Service Layer Pattern

Business logic is separated into service classes:

```python
# app/services/admin_service.py
class AdminService:
    @staticmethod
    def get_pending_users() -> List[User]:
        """Get all users pending approval."""
        return User.query.filter(
            User.is_active == False,
            or_(User.deleted == False, User.deleted == None)
        ).order_by(User.created_at.asc()).all()
```

**Benefits:**
- Clean separation of concerns
- Easier to test
- Reusable business logic
- Consistent error handling

## Database Queries - Important Notes

### Soft Delete Pattern
All user queries **must** filter out soft-deleted users:

```python
# CORRECT
pending_users = User.query.filter(
    User.is_active == False,
    or_(User.deleted == False, User.deleted == None)
).all()

# INCORRECT (includes deleted users)
pending_users = User.query.filter_by(is_active=False).all()
```

### Common Pitfalls
1. **Using `filter_by()` with NULL checks** - Won't work for NULL values
2. **Forgetting `deleted=False` filter** - Returns soft-deleted users
3. **Using wrong blueprint prefix in templates** - Causes routing errors

## Migration Checklist

When adding new routes:
- [ ] Create route in appropriate blueprint file
- [ ] Add business logic to corresponding service
- [ ] Use `url_for('blueprint.function_name')` in templates
- [ ] Add route tests
- [ ] Update this documentation

## Testing

```bash
# Run all tests
pytest

# Test specific blueprint
pytest tests/test_admin_routes.py

# Test integration
pytest tests/test_refactored_integration.py
```

## Future Improvements

1. **Complete Profile Migration**: Move profile routes from `routes/profile.py` to `app/routes/profile.py`
2. **API Versioning**: Add `/api/v1` prefix for API routes
3. **OpenAPI Documentation**: Generate Swagger docs from blueprints
4. **FastAPI Migration**: Eventual migration to FastAPI for better performance
5. **React Frontend**: Decouple frontend from Jinja2 templates

## Troubleshooting

### "Could not build url for endpoint 'X'"
**Cause:** Template using old monolithic URL reference
**Fix:** Update to blueprint format: `url_for('blueprint.function')`

### "Failed to load pending users"
**Cause:** Exception in route (check logs)
**Fix:**
```bash
docker-compose logs pv-market-analysis | grep ERROR
```

### Template changes not reflected
**Cause:** Templates not mounted in docker-compose
**Fix:** Ensure `./templates:/app/templates` is in volumes

## Support

For questions or issues with the refactored architecture:
1. Check this documentation
2. Review blueprint files in `app/routes/`
3. Check service layer in `app/services/`
4. Review logs: `docker-compose logs -f`

---

**Last Updated:** 2025-10-29
**Version:** 2.0.0-refactor
**Status:** ✅ Production Ready
