import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import logging
import os
import re

logger = logging.getLogger(__name__)

def sanitize_event(event, hint):
    """
    Sanitize sensitive data from Sentry events.
    """
    if 'request' in event:
        # Sanitize headers
        headers = event['request'].get('headers', {})
        if 'authorization' in headers:
            headers['authorization'] = '[REDACTED]'
        if 'x-api-key' in headers:
            headers['x-api-key'] = '[REDACTED]'
            
        # Sanitize body if present (though we usually rely on specialized loggers, 
        # Sentry might capture it automatically)
        if 'data' in event['request']:
             event['request']['data'] = sanitize_body(str(event['request']['data']))

    return event

def sanitize_body(body: str) -> str:
    """Redact sensitive fields from stringified body"""
    if not body:
        return body
        
    sensitive_patterns = [
        r'"password"\s*:\s*"[^"]*"',
        r'"token"\s*:\s*"[^"]*"',
        r'"access_token"\s*:\s*"[^"]*"', 
        r'"refresh_token"\s*:\s*"[^"]*"',
        r'"client_secret"\s*:\s*"[^"]*"',
        r'"credit_card"\s*:\s*"[^"]*"',
        r'Bearer\s+[\w-]+\.[\w-]+\.[\w-]+' # JWT pattern approximation
    ]
    
    sanitized = body
    for pattern in sensitive_patterns:
        sanitized = re.sub(pattern, '"***REDACTED***"', sanitized, flags=re.IGNORECASE)
        
    return sanitized

def init_sentry():
    """
    Initialize Sentry SDK if DSN is provided.
    """
    dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")
    if not dsn:
        logger.info("Sentry DSN not found, skipping initialization.")
        return

    logger.info(f"Initializing Sentry for environment: {environment}")
    
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1 if environment == 'production' else 1.0,
        profiles_sample_rate=0.1 if environment == 'production' else 1.0,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        before_send=sanitize_event,
        # Improve performance by not sending PII/local vars unless needed
        send_default_pii=False, 
    )
