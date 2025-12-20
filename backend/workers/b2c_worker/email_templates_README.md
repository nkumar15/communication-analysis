"""
Workspace Invitation Email Template

This template is used when inviting users to join a workspace.
The actual HTML template should be created in your email service's template directory.
"""

# Email Template Context Variables:
# - workspace_name: Name of the workspace
# - inviter_name: Name of person who sent invitation  
# - role: Role being offered (member, admin, viewer)
# - invitation_url: URL to accept invitation
# - expires_days: Number of days until expiration (7)
# - support_email: Support contact email

# Example HTML template (should be created in email service):
"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Workspace Invitation</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #333;">You've been invited!</h1>
    
    <p style="font-size: 16px; color: #555;">
        <strong>{{ inviter_name }}</strong> has invited you to join 
        <strong>{{ workspace_name }}</strong> as a <strong>{{ role }}</strong>.
    </p>
    
    <div style="margin: 30px 0;">
        <a href="{{ invitation_url }}" 
           style="background-color: #007bff; color: white; padding: 12px 30px; 
                  text-decoration: none; border-radius: 5px; display: inline-block;">
            Accept Invitation
        </a>
    </div>
    
    <p style="font-size: 14px; color: #666;">
        This invitation expires in {{ expires_days }} days.
    </p>
    
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    
    <p style="font-size: 12px; color: #999;">
        If you didn't expect this invitation, you can safely ignore this email.
        <br>
        Need help? Contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a>
    </p>
</body>
</html>
"""
