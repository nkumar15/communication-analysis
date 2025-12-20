"""
Logging Utility Functions

Helper functions for logging operations:
- PII sanitization
- Data masking
- Duration formatting
"""

import re
from typing import Any, Dict


def sanitize_pii(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize personally identifiable information from log data.
    
    Removes or masks sensitive fields:
    - password, api_key, secret, token
    - email addresses (in production)
    - credit card numbers
    
    Args:
        data: Dictionary of log data
        
    Returns:
        Sanitized dictionary
    """
    sensitive_keys = {
        "password", "passwd", "pwd",
        "api_key", "apikey", "api-key",
        "secret", "token", "auth",
        "credit_card", "card_number", "cvv",
    }
    
    sanitized = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Remove sensitive keys entirely
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        # Mask email addresses
        elif key_lower in ("email", "user_email", "admin_email"):
            sanitized[key] = mask_email(str(value)) if value else value
        else:
            sanitized[key] = value
    
    return sanitized


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    
    Examples:
        john.doe@example.com -> j***@example.com
        a@test.com -> a***@test.com
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email address
    """
    if not email or "@" not in email:
        return email
    
    local, domain = email.split("@", 1)
    
    if len(local) <= 1:
        masked_local = local + "***"
    else:
        masked_local = local[0] + "***"
    
    return f"{masked_local}@{domain}"


def mask_string(value: str, visible_chars: int = 4) -> str:
    """
    Mask a string, keeping only first few characters visible.
    
    Args:
        value: String to mask
        visible_chars: Number of characters to keep visible
        
    Returns:
        Masked string
    
    Example:
        mask_string("sk_live_abc123xyz", 7) -> "sk_live***"
    """
    if not value or len(value) <= visible_chars:
        return value
    
    return value[:visible_chars] + "***"


def format_duration(duration_seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        duration_seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
    
    Examples:
        0.001 -> "1ms"
        0.5 -> "500ms"
        1.5 -> "1.50s"
        65 -> "1m 5s"
    """
    if duration_seconds < 0.001:
        return "<1ms"
    elif duration_seconds < 1:
        return f"{int(duration_seconds * 1000)}ms"
    elif duration_seconds < 60:
        return f"{duration_seconds:.2f}s"
    else:
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        return f"{minutes}m {seconds}s"


def extract_correlation_id_from_request(request_data: Dict[str, Any]) -> str:
    """
    Extract correlation ID from request data.
    
    Checks common headers and fields for trace/correlation IDs:
    - X-Request-ID
    - X-Correlation-ID
    - X-Trace-ID
    
    Args:
        request_data: Request metadata dictionary
        
    Returns:
        Correlation ID or None
    """
    headers = request_data.get("headers", {})
    
    # Check common correlation ID headers
    for header_name in ["x-request-id", "x-correlation-id", "x-trace-id"]:
        if header_name in headers:
            return headers[header_name]
    
    return request_data.get("request_id")
