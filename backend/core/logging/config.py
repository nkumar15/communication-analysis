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
from opentelemetry import trace

# Reuse existing formatters 
# In a real refactor we might move these files too, but import works for now
from core.logging.formatters import (
    GCPFormatter,
    AWSFormatter,
    GenericJSONFormatter,
)

def add_open_telemetry_spans(_, __, event_dict):
    """
    Add trace_id/span_id to logs if a trace is active.
    """
    span = trace.get_current_span()
    if not span:
        return event_dict
        
    span_context = span.get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
        
    return event_dict


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
        add_open_telemetry_spans,  # <--- Added Correlation Here
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
    """
    return structlog.get_logger(name)


def add_context(**kwargs: Any) -> None:
    """
    Add context to all subsequent log messages in current execution context.
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """
    Clear all context variables.
    """
    structlog.contextvars.clear_contextvars()
