"""
Email Service

High-level email service that uses the configured provider.
Provides typed methods for common email operations.
"""
import os
from datetime import datetime
from typing import Optional

from infrastructure.email.providers import get_provider, EmailProvider


class EmailService:
    """
    High-level email service with typed methods for common operations.
    Uses the configured email provider (mailhog, resend, ses, console).
    """
    
    def __init__(self, provider: Optional[EmailProvider] = None):
        self._provider = provider
    
    @property
    def provider(self) -> EmailProvider:
        if self._provider is None:
            self._provider = get_provider()
        return self._provider
    
    def send_activation_email(
        self,
        to_email: str,
        company_name: str,
        activation_url: str,
        expires_at: datetime
    ) -> bool:
        """
        Send tenant activation email.
        
        Args:
            to_email: Admin email address
            company_name: Company/tenant name
            activation_url: Full activation URL with token
            expires_at: Token expiry timestamp
        """
        subject = f"Activate your {company_name} SSO account"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 30px; }}
        .button {{ display: inline-block; background: #4F46E5; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ padding: 20px; text-align: center; color: #6b7280; font-size: 14px; }}
        .steps {{ background: white; padding: 20px; border-radius: 6px; margin: 20px 0; }}
        .steps li {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Enterprise SSO!</h1>
        </div>
        
        <div class="content">
            <p>Hi there,</p>
            
            <p>Your enterprise single sign-on account for <strong>{company_name}</strong> is ready!</p>
            
            <p>Click the button below to complete your account activation:</p>
            
            <p style="text-align: center;">
                <a href="{activation_url}" class="button">Activate Your Account</a>
            </p>
            
            <p><small>Or copy this link: {activation_url}</small></p>
            
            <div class="steps">
                <p><strong>What happens next:</strong></p>
                <ol>
                    <li>✅ Test your SSO configuration</li>
                    <li>✅ Activate your account</li>
                    <li>✅ Start inviting your team members</li>
                </ol>
            </div>
            
            <p><strong>⏰ This link expires in 48 hours</strong> ({expires_at.strftime('%B %d, %Y at %I:%M %p UTC')})</p>
            
            <p>If you didn't request this or need help, contact support@yourapp.com</p>
        </div>
        
        <div class="footer">
            <p>Enterprise SSO Platform</p>
            <p>This is an automated message, please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""
        return self.provider.send(to_email, subject, html_content)
    
    def send_user_invitation_email(
        self,
        to_email: str,
        tenant_name: str,
        inviter_name: str,
        role: str,
        invitation_url: str,
        expires_at: datetime
    ) -> bool:
        """
        Send user invitation email.
        
        Args:
            to_email: Invitee email address
            tenant_name: Tenant name
            inviter_name: Name of person who sent invite
            role: Role being assigned
            invitation_url: Full invitation URL
            expires_at: Invitation expiry timestamp
        """
        subject = f"You're invited to join {tenant_name}"
        
        html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb;">You've been invited!</h2>
        
        <p>Hi there,</p>
        
        <p><strong>{inviter_name}</strong> has invited you to join <strong>{tenant_name}</strong> as a <strong>{role}</strong>.</p>
        
        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; text-align: center;">
                <a href="{invitation_url}" 
                   style="display: inline-block; background-color: #2563eb; color: white; 
                          padding: 12px 24px; text-decoration: none; border-radius: 6px;
                          font-weight: bold;">
                    Accept Invitation
                </a>
            </p>
        </div>
        
        <p style="color: #6b7280; font-size: 14px;">
            <strong>Invitation link:</strong><br>
            <a href="{invitation_url}" style="color: #2563eb; word-break: break-all;">{invitation_url}</a>
        </p>
        
        <p style="color: #6b7280; font-size: 14px;">
            This invitation expires on {expires_at.strftime('%B %d, %Y at %H:%M UTC')}.
        </p>
        
        <p style="color: #9ca3af; font-size: 12px; margin-top: 30px;">
            If you weren't expecting this invitation, you can safely ignore this email.
        </p>
    </div>
</body>
</html>
"""
        return self.provider.send(to_email, subject, html_content)
    
    async def send_invitation_email(
        self,
        to_email: str,
        invitation_token: str,
        tenant_name: str,
        expires_at: datetime
    ) -> bool:
        """
        Send invitation email (for async Celery tasks).
        Generates the invitation URL internally.
        """
        from core.config import settings
        
        invitation_url = f"{settings.frontend_url}/join?token={invitation_token}"
        
        return self.send_user_invitation_email(
            to_email=to_email,
            tenant_name=tenant_name,
            inviter_name=tenant_name,
            role="member",
            invitation_url=invitation_url,
            expires_at=expires_at
        )


    def send_subscription_confirmation_email(
        self,
        to_email: str,
        plan_name: str,
        amount: str,
        interval: str,
        next_billing_date: str,
        dashboard_url: str,
        invoice_pdf_url: Optional[str] = None,
        invoice_pdf_content: Optional[bytes] = None
    ) -> bool:
        """
        Send subscription confirmation email.
        
        Args:
            to_email: User email address
            plan_name: Name of the plan (e.g. "Premium Monthly")
            amount: Amount paid (e.g. "$29.00")
            interval: Billing interval (e.g. "month")
            next_billing_date: Date of next billing
            dashboard_url: URL to user dashboard
            invoice_pdf_url: Optional URL to invoice PDF
            invoice_pdf_content: Optional PDF content bytes
        """
        subject = f"Welcome to {plan_name}!"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 8px 8px; }}
        .footer {{ padding: 20px; text-align: center; color: #6b7280; font-size: 14px; }}
        .detail-row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #e5e7eb; }}
        .detail-label {{ color: #6b7280; }}
        .detail-value {{ font-weight: bold; color: #111827; }}
        .button {{ display: inline-block; background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 24px; width: fit-content; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Subscription Confirmed!</h1>
        </div>
        
        <div class="content">
            <p>Hi there,</p>
            <p>Thank you for upgrading to the <strong>{plan_name}</strong> plan!</p>
            <p>Your subscription is now active and you have immediate access to all premium features.</p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e5e7eb;">
                <div class="detail-row">
                    <span class="detail-label">Plan</span>
                    <span class="detail-value">{plan_name}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Amount</span>
                    <span class="detail-value">{amount}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Billing Interval</span>
                    <span class="detail-value">{interval}</span>
                </div>
                <div class="detail-row" style="border-bottom: none;">
                    <span class="detail-label">Next Billing Date</span>
                    <span class="detail-value">{next_billing_date}</span>
                </div>
            </div>
            
            <div style="text-align: center;">
                <a href="{dashboard_url}" class="button">Go to Dashboard</a>
            </div>
            
            {f'<p style="margin-top: 20px; text-align: center;"><a href="{invoice_pdf_url}">Download Invoice</a></p>' if invoice_pdf_url else ''}
        </div>
        
        <div class="footer">
            <p>Enterprise SaaS App</p>
            <p>Need help? Contact support@yourapp.com</p>
            <p style="font-size: 12px; margin-top: 10px;">This is an automated message, please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""
        attachments = []
        if invoice_pdf_content:
            attachments.append({
                "filename": "invoice.pdf",
                "content": invoice_pdf_content,
                "content_type": "application/pdf"
            })
            
        return self.provider.send(to_email, subject, html_content, attachments=attachments)


# Global email service instance
email_service = EmailService()
