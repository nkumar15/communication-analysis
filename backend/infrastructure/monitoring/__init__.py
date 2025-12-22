"""
Monitoring Infrastructure Package

Exposes MetricsProvider factory and facade functions for easy usage.
"""
from typing import Optional, Dict
import structlog
import time
from contextlib import contextmanager
from .metrics import MetricsProvider, PrometheusProvider, ConsoleProvider

logger = structlog.get_logger(__name__)

_metrics_provider: Optional["MetricsProvider"] = None

def get_metrics_provider() -> "MetricsProvider":
    """Factory to return the active metrics provider"""
    global _metrics_provider
    if _metrics_provider is None:
        from core.config import settings
        
        if settings.monitoring_provider == "prometheus":
            _metrics_provider = PrometheusProvider()
            logger.info("Initialized Prometheus Metrics Provider")
        elif settings.monitoring_provider == "console":
            _metrics_provider = ConsoleProvider()
            logger.info("Initialized Console Metrics Provider")
        else:
            _metrics_provider = ConsoleProvider()
            logger.info(f"Unknown monitoring provider '{settings.monitoring_provider}', defaulting to Console")

    return _metrics_provider

# =============================================================================
# Facade Functions - Exposed at package level for convenience
# =============================================================================

def increment(name: str, labels: Dict[str, str] = None, value: int = 1):
    get_metrics_provider().increment(name, labels, value)

def observe(name: str, value: float, labels: Dict[str, str] = None):
    get_metrics_provider().observe(name, value, labels)

def set_gauge(name: str, value: float, labels: Dict[str, str] = None):
    get_metrics_provider().set_gauge(name, value, labels)


# =============================================================================
# Domain Facades
# =============================================================================

def record_request_metrics(method: str, path: str, status_code: int, duration: float):
    get_metrics_provider().increment(
        "http_requests_total", 
        labels={"method": method, "path": path, "status_code": str(status_code)}
    )
    get_metrics_provider().observe(
        "http_request_duration_seconds", 
        duration, 
        labels={"method": method, "path": path}
    )

def increment_login(provider_type: str, status: str = "success"):
    get_metrics_provider().increment(
        "user_logins_total", 
        labels={"provider_type": provider_type, "status": status}
    )

def increment_tenant_onboarding(plan: str = "default"):
    get_metrics_provider().increment(
        "tenant_onboarding_total", 
        labels={"plan": plan}
    )

def increment_auth_failure(provider: str):
    get_metrics_provider().increment(
        "auth_failures_total", 
        labels={"provider": provider}
    )

def increment_rbac_denial(resource: str, action: str):
    get_metrics_provider().increment(
        "rbac_denials_total", 
        labels={"resource": resource, "action": action}
    )

@contextmanager
def record_external_api(service: str, endpoint: str):
    start = time.time()
    yield
    duration = time.time() - start
    get_metrics_provider().observe(
        "external_api_duration_seconds", 
        duration, 
        labels={"service": service, "endpoint": endpoint}
    )

def record_db_pool_metrics(size: int, checked_out: int):
    get_metrics_provider().set_gauge("db_connection_pool_size", size)
    get_metrics_provider().set_gauge("db_connection_pool_checkedout", checked_out)

def record_db_query_duration(duration: float, query_type: str = "unknown", table_name: str = "unknown"):
    get_metrics_provider().observe(
        "db_query_duration_seconds", 
        duration, 
        labels={"query_type": query_type, "table_name": table_name}
    )

@contextmanager
def record_token_validation(provider: str = "firebase"):
    start = time.time()
    yield
    duration = time.time() - start
    get_metrics_provider().observe(
        "auth_token_validation_duration_seconds", 
        duration, 
        labels={"provider": provider}
    )

def increment_subscription_event(event_type: str, plan: str):
    get_metrics_provider().increment(
        "subscription_events_total", 
        labels={"event_type": event_type, "plan": plan}
    )

def setup_metrics():
    """Initialize metrics provider (Idempotent)"""
    get_metrics_provider()

def metrics_endpoint(request):
    """Serve metrics for scraping"""
    from starlette.responses import Response
    provider = get_metrics_provider()
    return Response(provider.generate_latest(), media_type=provider.content_type)

