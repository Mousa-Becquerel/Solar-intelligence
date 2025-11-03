"""
Email service for sending transactional emails.

This service handles sending password reset emails and other notifications.
"""

import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

from app.config import Config
from app.extensions import db

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    @staticmethod
    def send_email(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Send an email using SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Check if email is configured
            if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
                logger.warning("Email not configured. Skipping email send.")
                logger.info(f"Would send email to {to_email} with subject: {subject}")
                logger.info(f"Body: {text_body or html_body[:200]}...")
                return True, None  # Return success in development without actual email

            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = Config.MAIL_DEFAULT_SENDER
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add plain text and HTML parts
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
                if Config.MAIL_USE_TLS:
                    server.starttls()
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True, None

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False, str(e)

    @staticmethod
    def generate_reset_token() -> str:
        """Generate a secure random token for password reset."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def send_password_reset_email(user, reset_url: str) -> Tuple[bool, Optional[str]]:
        """
        Send password reset email to user.

        Args:
            user: User object
            reset_url: Full URL for password reset

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        # Generate reset token
        token = EmailService.generate_reset_token()
        user.reset_token = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)

        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to save reset token: {e}")
            db.session.rollback()
            return False, "Failed to generate reset token"

        # Build reset link
        reset_link = f"{reset_url}?token={token}"

        # Email content
        subject = "Password Reset Request - Solar Intelligence"

        text_body = f"""
Hello {user.full_name},

You recently requested to reset your password for your Solar Intelligence account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email or contact support if you have concerns.

Best regards,
Solar Intelligence Team
"""

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: 'Inter', Arial, sans-serif;
            line-height: 1.6;
            color: #1e3a8a;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            padding: 30px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            color: #1e3a8a;
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            background: white;
            padding: 30px;
            border: 1px solid #e5e7eb;
            border-top: none;
        }}
        .button {{
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            color: #1e3a8a;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }}
        .footer {{
            background: #f3f4f6;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #6b7280;
            border-radius: 0 0 8px 8px;
        }}
        .warning {{
            background: #fef3c7;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
            border-left: 4px solid #f59e0b;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔐 Password Reset Request</h1>
    </div>
    <div class="content">
        <p>Hello <strong>{user.full_name}</strong>,</p>

        <p>You recently requested to reset your password for your Solar Intelligence account.</p>

        <p>Click the button below to reset your password:</p>

        <p style="text-align: center;">
            <a href="{reset_link}" class="button">Reset Password</a>
        </p>

        <div class="warning">
            <strong>⏰ This link will expire in 1 hour.</strong>
        </div>

        <p>If the button doesn't work, copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #6b7280; font-size: 12px;">{reset_link}</p>

        <p>If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>

        <p>Best regards,<br><strong>Solar Intelligence Team</strong></p>
    </div>
    <div class="footer">
        <p>© 2025 Solar Intelligence. All rights reserved.</p>
        <p>This is an automated message, please do not reply to this email.</p>
    </div>
</body>
</html>
"""

        # Send email
        return EmailService.send_email(user.username, subject, html_body, text_body)

    @staticmethod
    def verify_reset_token(token: str):
        """
        Verify reset token and return user if valid.

        Args:
            token: Reset token to verify

        Returns:
            User object if token is valid, None otherwise
        """
        from models import User

        user = User.query.filter_by(reset_token=token).first()

        if not user:
            return None

        # Check if token is expired
        if user.reset_token_expiry and user.reset_token_expiry < datetime.utcnow():
            return None

        return user

    @staticmethod
    def clear_reset_token(user) -> None:
        """
        Clear reset token after successful password reset.

        Args:
            user: User object
        """
        user.reset_token = None
        user.reset_token_expiry = None
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to clear reset token: {e}")
            db.session.rollback()
