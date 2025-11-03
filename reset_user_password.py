"""
Admin script to reset a user's password manually.

Usage:
    python reset_user_password.py <email> <new_password>

Example:
    python reset_user_password.py user@example.com TempPass123!
"""

import sys
from app import create_app
from app.extensions import db
from models import User

def reset_password(email: str, new_password: str):
    """Reset a user's password."""
    app = create_app()

    with app.app_context():
        # Find user
        user = User.query.filter_by(username=email).first()

        if not user:
            print(f"❌ Error: User with email '{email}' not found")
            return False

        # Update password
        user.set_password(new_password)

        try:
            db.session.commit()
            print(f"✅ Success: Password reset for user '{user.full_name}' ({email})")
            print(f"📧 Email: {email}")
            print(f"🔑 Temporary Password: {new_password}")
            print(f"\n⚠️  Please ask the user to:")
            print(f"   1. Log in with this temporary password")
            print(f"   2. Go to their profile page")
            print(f"   3. Change their password immediately")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: Failed to update password: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_user_password.py <email> <new_password>")
        print("Example: python reset_user_password.py user@example.com TempPass123!")
        sys.exit(1)

    email = sys.argv[1]
    new_password = sys.argv[2]

    if len(new_password) < 8:
        print("❌ Error: Password must be at least 8 characters long")
        sys.exit(1)

    reset_password(email, new_password)
