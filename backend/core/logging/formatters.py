"""
Cloud-Specific Log Formatters

Provides formatters for different cloud environments:
- Local: Human-readable console output (handled by structlog.dev.ConsoleRenderer)
- GCP: Google Cloud Logging JSON format
- AWS: CloudWatch Logs JSON format
- Generic: Standard JSON for other environments
"""

import json
from typing import Any
from datetime import datetime


class GCPFormatter:
    """
    Google Cloud Platform Log Formatter
    
    Formats logs according to GCP Cloud Logging structured format.
    See: https://cloud.google.com/logging/docs/structured-logging
    """
    
    # Map Python logging levels to GCP severity
    SEVERITY_MAP = {
        "debug": "DEBUG",
        "info": "INFO",
        "warning": "WARNING",
        "error": "ERROR",
        "critical": "CRITICAL",
    }
    
    def __call__(self, logger: Any, name: str, event_dict: dict) -> str:
        """
        Format log entry for GCP Cloud Logging.
        
        GCP expects specific field names:
        - severity: Log level
        - timestamp: ISO 8601 timestamp
        - message: Log message
        - logging.googleapis.com/trace: Trace ID for request tracing
        - logging.googleapis.com/spanId: Span ID for distributed tracing
        """
        # Extract and transform fields
        level = event_dict.pop("level", "info")
        severity = self.SEVERITY_MAP.get(level.lower(), "INFO")
        
        # Build GCP-formatted log entry
        gcp_entry = {
            "severity": severity,
            "timestamp": event_dict.pop("timestamp", datetime.utcnow().isoformat() + "Z"),
            "message": event_dict.pop("event", ""),
        }
        
        # Add trace context if available (for request tracing)
        if "request_id" in event_dict:
            request_id = event_dict.pop("request_id")
            # GCP trace format: projects/PROJECT_ID/traces/TRACE_ID
            gcp_entry["logging.googleapis.com/trace"] = f"traces/{request_id}"
        
        if "span_id" in event_dict:
            gcp_entry["logging.googleapis.com/spanId"] = event_dict.pop("span_id")
        
        # Add logger name
        if "logger" in event_dict:
            gcp_entry["logger"] = event_dict.pop("logger")
        
        # Add exception info if present
        if "exception" in event_dict:
            gcp_entry["exception"] = event_dict.pop("exception")
        
        # Add all remaining fields as custom labels
        gcp_entry.update(event_dict)
        
        return json.dumps(gcp_entry)


class AWSFormatter:
    """
    Amazon Web Services CloudWatch Logs Formatter
    
    Formats logs for AWS CloudWatch Logs.
    See: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/
    """
    
    # Map Python logging levels to AWS conventions
    LEVEL_MAP = {
        "debug": "DEBUG",
        "info": "INFO",
        "warning": "WARN",
        "error": "ERROR",
        "critical": "FATAL",
    }
    
    def __call__(self, logger: Any, name: str, event_dict: dict) -> str:
        """
        Format log entry for AWS CloudWatch.
        
        AWS expects:
        - level: Log level
        - timestamp: Unix timestamp in milliseconds
        - message: Log message
        - aws_request_id: Lambda request ID (if in Lambda)
        - x_ray_trace_id: X-Ray trace ID for request tracing
        """
        # Extract and transform fields
        level = event_dict.pop("level", "info")
        aws_level = self.LEVEL_MAP.get(level.lower(), "INFO")
        
        # Parse timestamp to Unix milliseconds
        timestamp_str = event_dict.pop("timestamp", None)
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                timestamp_ms = int(dt.timestamp() * 1000)
            except (ValueError, AttributeError):
                timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        else:
            timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        
        # Build AWS-formatted log entry
        aws_entry = {
            "level": aws_level,
            "timestamp": timestamp_ms,
            "message": event_dict.pop("event", ""),
        }
        
        # Add AWS-specific tracing fields
        if "request_id" in event_dict:
            aws_entry["aws_request_id"] = event_dict.pop("request_id")
        
        if "trace_id" in event_dict:
            aws_entry["x_ray_trace_id"] = event_dict.pop("trace_id")
        
        # Add logger name
        if "logger" in event_dict:
            aws_entry["logger"] = event_dict.pop("logger")
        
        # Add exception info if present
        if "exception" in event_dict:
            aws_entry["exception"] = event_dict.pop("exception")
        
        # Add all remaining fields
        aws_entry.update(event_dict)
        
        return json.dumps(aws_entry)


class GenericJSONFormatter:
    """
    Generic JSON Formatter
    
    Standard JSON format for any cloud provider or on-premises deployment.
    """
    
    def __call__(self, logger: Any, name: str, event_dict: dict) -> str:
        """
        Format log entry as generic JSON.
        """
        # Simple JSON serialization with consistent field names
        json_entry = {
            "level": event_dict.pop("level", "info").upper(),
            "timestamp": event_dict.pop("timestamp", datetime.utcnow().isoformat() + "Z"),
            "logger": event_dict.pop("logger", name),
            "message": event_dict.pop("event", ""),
        }
        
        # Add exception info if present
        if "exception" in event_dict:
            json_entry["exception"] = event_dict.pop("exception")
        
        # Add all remaining fields
        json_entry.update(event_dict)
        
        return json.dumps(json_entry)


# LocalFormatter is handled by structlog.dev.ConsoleRenderer
# No need for a custom class
