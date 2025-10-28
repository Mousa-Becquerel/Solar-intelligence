"""
Flask route blueprints package.

This package contains thin route handlers organized by feature area.
Routes call services for business logic and return responses.

Blueprints:
- auth: Login, register, logout
- chat: Chat interface, query handling
- conversation: Conversation CRUD operations
- admin: Admin panel operations
- static_pages: Landing, waitlist, etc.

Usage:
------
Import blueprints in app factory:

    from app.routes import auth_bp, chat_bp, conversation_bp, admin_bp, static_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(conversation_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(static_bp)
"""

from app.routes.auth import auth_bp
from app.routes.chat import chat_bp
from app.routes.conversation import conversation_bp
from app.routes.admin import admin_bp
from app.routes.static_pages import static_bp

__all__ = [
    'auth_bp',
    'chat_bp',
    'conversation_bp',
    'admin_bp',
    'static_bp',
]
