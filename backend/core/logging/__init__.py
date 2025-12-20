"""
Cloud-Adaptive Structured Logging

This module provides structured logging that adapts to different environments:
- Local: Human-readable colored console output
- GCP: Google Cloud Logging JSON format
- AWS: CloudWatch Logs JSON format

Usage:
    from core.logging import get_logger
    
    logger = get_logger(__name__)
    logger.info("user_login", user_id="123", tenant_id="abc")
"""

from core.logging.config import setup_logging, get_logger, add_context

__all__ = ["setup_logging", "get_logger", "add_context"]
