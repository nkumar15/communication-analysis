"""
Email service using Resend for activation emails
"""
import os
import resend
from datetime import datetime


class EmailService:
    """Service for sending emails via Resend"""
    
    def __init__(self):
        self.api_key = os.getenv('RESEND_API_KEY')
        if self.api_key:
            resend.api_key = self.api_key
    
    def send_activation_email(
        self,
        to_email: str,
        company_name: str,
        activation_url: str,
        expires_at: datetime
    ):
        """
        Send activation email to admin
        
        Args:
            to_email: Admin email address
            company_name: Company/tenant name
            activation_url: Full activation URL with token
            expires_at: Token expiry timestamp
        """
        if not self.api_key:
            print("\n" + "="*80)
            print("📧 ACTIVATION EMAIL (Email service not configured)")
            print("="*80)
            print(f"To: {to_email}")
            print(f"Subject: Activate your {company_name} SSO account")
            print("-"*80)
            print("ACTIVATION URL (Copy this to browser):")
            print(f"\n    {activation_url}\n")
            print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
            print("="*80 + "\n")
            return
        
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
        
        try:
            params = {
                "from": "Enterprise SSO <onboarding@yourapp.com>",
                "to": [to_email],
                "subject": f"Activate your {company_name} SSO account",
                "html": html_content
            }
            
            resend.Emails.send(params)
            print(f"📧 Activation email sent to {to_email}")
            
        except Exception as e:
            # Fallback to console logging if email fails
            print(f"\n⚠️  Email service error: {e}")
            print("="*80)
            print("📧 ACTIVATION EMAIL (Fallback to console)")
            print("="*80)
            print(f"To: {to_email}")
            print(f"Subject: Activate your {company_name} SSO account")
            print("-"*80)
            print("ACTIVATION URL (Copy this to browser):")
            print(f"\n    {activation_url}\n")
            print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
            print("="*80 + "\n")

    def send_user_invitation_email(
        self,
        to_email: str,
        tenant_name: str,
        inviter_name: str,
        role: str,
        invitation_url: str,
        expires_at: datetime
    ):
        """Send user invitation email"""
        subject = f"You're invited to join {tenant_name}"

        if not self.api_key:
            print("\n" + "=" * 80)
            print("📧 USER INVITATION EMAIL (Email service not configured)")
            print("=" * 80)
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print("-" * 80)
            print(f"From: {inviter_name}")
            print(f"Tenant: {tenant_name}")
            print(f"Role: {role}")
            print()
            print("INVITATION URL (Copy this to browser):")
            print()
            print(f"    {invitation_url}")
            print()
            print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
            print("=" * 80)
            print()
            return
        
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
        
        try:
            params = {
                "from": "Enterprise SSO <onboarding@yourapp.com>",
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }
            resend.Emails.send(params)
            print(f"📧 User invitation email sent to {to_email}")
        except Exception as e:
            # Fallback to console if email service fails
            print(f"\n⚠️  Email service error: {str(e)}")
            print("=" * 80)
            print("📧 USER INVITATION EMAIL (Fallback to console)")
            print("=" * 80)
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print("-" * 80)
            print(f"From: {inviter_name}")
            print(f"Tenant: {tenant_name}")
            print(f"Role: {role}")
            print()
            print("INVITATION URL (Copy this to browser):")
            print()
            print(f"    {invitation_url}")
            print()
            print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
            print("=" * 80)
            print()
    
    async def send_invitation_email(
        self,
        to_email: str,
        invitation_token: str,
        tenant_name: str,
        expires_at: datetime
    ):
        """
        Send invitation email (simplified for Celery tasks).
        
        This method is called by Celery background tasks and generates
        the invitation URL internally.
        
        Args:
            to_email: Invitee email address
            invitation_token: Invitation token
            tenant_name: Tenant name
            expires_at: Expiration timestamp
        """
        from core.config import settings
        
        # Generate invitation URL
        invitation_url = f"{settings.frontend_url}/join?token={invitation_token}"
        
        # Use inviter_name as tenant name for now (can be enhanced later)
        return self.send_user_invitation_email(
            to_email=to_email,
            tenant_name=tenant_name,
            inviter_name=tenant_name,  # Using tenant name as inviter
            role="member",  # Generic role for async emails
            invitation_url=invitation_url,
            expires_at=expires_at
        )


# Global email service instance
email_service = EmailService()
