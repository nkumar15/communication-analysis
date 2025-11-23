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


# Global email service instance
email_service = EmailService()
