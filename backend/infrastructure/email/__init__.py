"""
Email Package

Provides pluggable email providers for different environments.

Configuration via EMAIL_PROVIDER env var:
- mailhog: Local development (default)
- resend: Production SaaS
- ses: AWS SES
- console: Print to stdout only

Example:
    from infrastructure.email import email_service
    
    email_service.send_activation_email(
        to_email="user@example.com",
        company_name="Acme Corp",
        activation_url="https://app.example.com/activate?token=...",
        expires_at=datetime.now()
    )
"""
from infrastructure.email.service import EmailService, email_service
from infrastructure.email.providers import (
    EmailProvider,
    MailhogProvider,
    ResendProvider,
    SESProvider,
    ConsoleProvider,
    get_provider,
)

__all__ = [
    "EmailService",
    "email_service",
    "EmailProvider",
    "MailhogProvider",
    "ResendProvider",
    "SESProvider",
    "ConsoleProvider",
    "get_provider",
]
