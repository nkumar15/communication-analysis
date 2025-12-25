"""
Email Provider Abstraction

Pluggable email providers for different environments:
- Mailhog: Local development (default)
- Resend: Production SaaS
- AWS SES: AWS cloud deployments

Configure via EMAIL_PROVIDER env var: mailhog, resend, ses
"""
import os
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime

from core.config import settings

class EmailProvider(ABC):
    """Abstract base class for email providers"""
    
    @abstractmethod
    def send(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None,
        attachments: Optional[list] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            from_email: Optional sender override
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass


class MailhogProvider(EmailProvider):
    """
    Mailhog SMTP provider for local development.
    
    Mailhog captures all emails at http://localhost:8025
    No authentication required.
    """
    
    def __init__(self):
        self.host = settings.mailhog_host
        self.port = settings.mailhog_port
        self.default_from = settings.email_from
    
    @property
    def name(self) -> str:
        return "Mailhog"
    
    def send(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None,
        attachments: Optional[list] = None
    ) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email or self.default_from
            msg["To"] = to_email
            
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)
            
            # Handle attachments
            if attachments:
                from email.mime.application import MIMEApplication
                for attachment in attachments:
                    try:
                        part = MIMEApplication(
                            attachment['content'],
                            Name=attachment['filename']
                        )
                        part['Content-Disposition'] = f'attachment; filename="{attachment["filename"]}"'
                        msg.attach(part)
                    except Exception as e:
                        print(f"⚠️ [{self.name}] Failed to attach file {attachment.get('filename')}: {e}")
            
            
            with smtplib.SMTP(self.host, self.port) as server:
                server.sendmail(msg["From"], [to_email], msg.as_string())
            
            print(f"📧 [{self.name}] Email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"⚠️ [{self.name}] Failed to send email: {e}")
            return False


class ResendProvider(EmailProvider):
    """
    Resend API provider for production.
    
    Requires RESEND_API_KEY environment variable.
    """
    
    def __init__(self):
        self.api_key = settings.resend_api_key
        self.default_from = settings.email_from
        
        if self.api_key:
            import resend
            resend.api_key = self.api_key
    
    @property
    def name(self) -> str:
        return "Resend"
    
    def send(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None,
        attachments: Optional[list] = None
    ) -> bool:
        if not self.api_key:
            print(f"⚠️ [{self.name}] API key not configured, falling back to console")
            self._console_fallback(to_email, subject)
            return False
        
        try:
            import resend
            
            params = {
               "from": from_email or self.default_from,
               "to": [to_email],
               "subject": subject,
               "html": html_content
            }
            
            resend_attachments = []
            if attachments:
                # Resend format: [{"filename": "invoice.pdf", "content": [bytes list/buffer]}]
                # We expect attachments to be list of dicts with 'filename' and 'content' (bytes)
                for att in attachments:
                    resend_attachments.append({
                        "filename": att['filename'],
                        "content": list(att['content']) if isinstance(att['content'], bytes) else att['content']
                    })
                params["attachments"] = resend_attachments
            
            resend.Emails.send(params)
            print(f"📧 [{self.name}] Email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"⚠️ [{self.name}] Failed to send email: {e}")
            return False
    
    def _console_fallback(self, to_email: str, subject: str):
        print(f"\n{'='*60}")
        print(f"📧 EMAIL (Console Fallback)")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"{'='*60}\n")


class SESProvider(EmailProvider):
    """
    AWS Simple Email Service provider.
    
    Uses boto3 and requires AWS credentials configured.
    Set AWS_REGION for SES region (default: us-east-1).
    """
    
    def __init__(self):
        self.region = settings.aws_region or "us-east-1"
        self.default_from = settings.email_from
        self._client = None
    
    @property
    def name(self) -> str:
        return "AWS SES"
    
    @property
    def client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("ses", region_name=self.region)
            except Exception as e:
                print(f"⚠️ [{self.name}] Failed to create client: {e}")
        return self._client
    
    def send(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None,
        attachments: Optional[list] = None
    ) -> bool:
        if not self.client:
            print(f"⚠️ [{self.name}] Client not available")
            return False
        
        try:
            response = self.client.send_email(
                Source=from_email or self.default_from,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_content, "Charset": "UTF-8"}
                    }
                }
            )
            print(f"📧 [{self.name}] Email sent to {to_email} (MessageId: {response['MessageId']})")
            return True
            
        except Exception as e:
            print(f"⚠️ [{self.name}] Failed to send email: {e}")
            return False


class ConsoleProvider(EmailProvider):
    """
    Console-only provider for testing without any email setup.
    Just prints emails to stdout.
    """
    
    @property
    def name(self) -> str:
        return "Console"
    
    def send(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None,
        attachments: Optional[list] = None
    ) -> bool:
        print("\n" + "=" * 80)
        print("📧 EMAIL (Console Provider)")
        print("=" * 80)
        print(f"From: {from_email or 'noreply@localhost'}")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print("-" * 80)
        # Strip HTML tags for console output
        import re
        text = re.sub('<[^<]+?>', '', html_content)
        text = re.sub(r'\s+', ' ', text).strip()[:500]
        text = re.sub(r'\s+', ' ', text).strip()[:500]
        print(f"Body (preview): {text}...")
        
        if attachments:
             print(f"Attachments: {len(attachments)} files")
             for att in attachments:
                 print(f" - {att.get('filename')} ({len(att.get('content', ''))} bytes)")
        
        print("=" * 80 + "\n")
        return True


def get_email_provider() -> EmailProvider:
    """
    Factory function to get the configured email provider.
    
    Set EMAIL_PROVIDER env var to: mailhog, resend, ses, console
    Default: mailhog (for local development)
    """
    provider_name = settings.email_provider.lower()
    
    providers = {
        "mailhog": MailhogProvider,
        "resend": ResendProvider,
        "ses": SESProvider,
        "console": ConsoleProvider,
    }
    
    provider_class = providers.get(provider_name)
    
    if provider_class is None:
        print(f"⚠️ Unknown email provider '{provider_name}', defaulting to mailhog")
        provider_class = MailhogProvider
    
    return provider_class()


# Global provider instance (lazy loaded)
_provider: Optional[EmailProvider] = None


def get_provider() -> EmailProvider:
    """Get or create the global email provider instance"""
    global _provider
    if _provider is None:
        _provider = get_email_provider()
        print(f"📧 Email provider initialized: {_provider.name}")
    return _provider
