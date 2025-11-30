"""
Logging Configuration

Central configuration for structured logging across all services.
Detects environment and configures appropriate formatters.
"""

import logging
import sys
from typing import Any, Optional
import structlog
from structlog.types import BindableLogger, Processor

from core.logging.formatters import (
    GCPFormatter,
    AWSFormatter,
    GenericJSONFormatter,
)


def setup_logging(environment: str = "local", log_level: str = "INFO") -> None:
    """
    Configure structured logging based on environment.
    
    Args:
        environment: Logging environment (local, gcp, aws, production)
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )
    
    # Common processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    # Select formatter based on environment
    if environment == "local":
        # Development: Human-readable colored output
        processors = shared_processors + [
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    elif environment == "gcp":
        # Google Cloud Platform
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            GCPFormatter(),
        ]
    elif environment == "aws":
        # Amazon Web Services
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            AWSFormatter(),
        ]
    else:
        # Generic production (any cloud or on-prem)
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            GenericJSONFormatter(),
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> BindableLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Structured logger with bound context
        
    Example:
        logger = get_logger(__name__)
        logger.info("user_created", user_id="123", email="user@example.com")
    """
    return structlog.get_logger(name)


def add_context(**kwargs: Any) -> None:
    """
    Add context to all subsequent log messages in current execution context.
    
    Uses structlog's context variables to inject fields into logs.
    Useful for adding request_id, tenant_id, etc.
    
    Args:
        **kwargs: Key-value pairs to add to log context
        
    Example:
        add_context(request_id="abc-123", tenant_id="tenant-xyz")
        logger.info("processing_request")  # Will include request_id and tenant_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """
    Clear all context variables.
    Should be called after request processing to avoid context leakage.
    """
    structlog.contextvars.clear_contextvars()
