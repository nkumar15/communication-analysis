import os
from contextlib import contextmanager
import time
from typing import Dict, Optional
import structlog

# Try to import prometheus_client, handle if missing (e.g. initial setup)
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = structlog.get_logger(__name__)

# Standard Metrics
HTTP_REQUESTS_TOTAL = None
HTTP_REQUEST_DURATION_SECONDS = None
DB_CONNECTION_POOL_SIZE = None

# Custom Metrics
USER_LOGINS_TOTAL = None
TENANT_ONBOARDING_TOTAL = None

def setup_metrics():
    """Initialize Prometheus metrics"""
    global HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS
    global USER_LOGINS_TOTAL, TENANT_ONBOARDING_TOTAL
    
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus client not installed, metrics disabled")
        return

    # Web Requests
    HTTP_REQUESTS_TOTAL = Counter(
        "http_requests_total",
        "Total count of HTTP requests",
        ["method", "path", "status_code"]
    )
    
    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path"]
    )

    # Business Metrics
    USER_LOGINS_TOTAL = Counter(
        "user_logins_total",
        "Total user logins",
        ["provider_type", "status"]
    )
    
    TENANT_ONBOARDING_TOTAL = Counter(
        "tenant_onboarding_total",
        "Total tenants onboarded",
        ["plan"]
    )


from starlette.responses import Response

def metrics_endpoint(request):
    """Serve metrics for scraping"""
    if not PROMETHEUS_AVAILABLE:
        return Response("Prometheus not installed", status_code=500)
        
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def record_request_metrics(method: str, path: str, status_code: int, duration: float):
    """Record generic request metrics"""
    if not PROMETHEUS_AVAILABLE:
        return
        
    HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status_code=status_code).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)

def increment_login(provider_type: str, status: str = "success"):
    if PROMETHEUS_AVAILABLE and USER_LOGINS_TOTAL:
        USER_LOGINS_TOTAL.labels(provider_type=provider_type, status=status).inc()

def increment_tenant_onboarding(plan: str = "default"):
    if PROMETHEUS_AVAILABLE and TENANT_ONBOARDING_TOTAL:
        TENANT_ONBOARDING_TOTAL.labels(plan=plan).inc()
