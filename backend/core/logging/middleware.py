"""
FastAPI Logging Middleware

Adds request context to all logs:
- request_id: Unique ID per request
- tenant_id: From JWT token
- user_id: From JWT token
- HTTP metadata: method, path, client IP, user-agent
- Request duration
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logging.config import get_logger, add_context, clear_context


logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add structured logging context to all requests.
    
    For each request:
    1. Generate unique request_id
    2. Extract tenant_id and user_id from JWT (if present)
    3. Log request start
    4. Inject context variables
    5. Process request
    6. Log request completion with duration
    7. Clear context
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Start timer
        start_time = time.time()
        
        # Extract request metadata
        http_method = request.method
        http_path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Try to extract tenant_id and user_id from JWT token
        tenant_id = None
        user_id = None
        
        # Check if user context is available (set by auth middleware)
        if hasattr(request.state, "user"):
            user_info = request.state.user
            if isinstance(user_info, dict):
                tenant_id = user_info.get("tenant_id")
                user_id = user_info.get("user_id") or user_info.get("uid")
        
        # Add context for this request
        context = {
            "request_id": request_id,
            "http_method": http_method,
            "http_path": http_path,
            "client_ip": client_ip,
        }
        
        if tenant_id:
            context["tenant_id"] = tenant_id
        if user_id:
            context["user_id"] = user_id
        
        add_context(**context)
        
        # Log request start
        logger.info(
            "request_started",
            user_agent=user_agent,
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log successful response
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            
            return response
            
        except Exception as exc:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log error
            logger.error(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=duration_ms,
                exc_info=True,
            )
            
            # Re-raise exception to be handled by exception handlers
            raise
        
        finally:
            # Clear context to avoid leakage between requests
            clear_context()
