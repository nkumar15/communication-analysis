import os
from contextlib import contextmanager
import time
from typing import Dict, Optional, Any
from abc import ABC, abstractmethod
import structlog
from starlette.responses import Response

logger = structlog.get_logger(__name__)

# =============================================================================
# Abstract Base Class
# =============================================================================

class MetricsProvider(ABC):
    """Abstract base class for metrics collection"""
    
    @abstractmethod
    def increment(self, name: str, labels: Dict[str, str] = None, value: int = 1):
        """Increment a counter metric"""
        pass
    
    @abstractmethod
    def observe(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a value (histogram/summary)"""
        pass
        
    @abstractmethod
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value"""
        pass

    @abstractmethod
    def generate_latest(self) -> bytes:
        """Generate metrics output for scraping"""
        pass
        
    @property
    @abstractmethod
    def content_type(self) -> str:
        """Content type for the scrape endpoint"""
        pass


# =============================================================================
# Concrete Implementation: Prometheus
# =============================================================================

class PrometheusProvider(MetricsProvider):
    """Prometheus implementation using official client"""
    
    def __init__(self):
        try:
            from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
            self._client_available = True
            self._generate_latest = generate_latest
            self._content_type = CONTENT_TYPE_LATEST
            self._metrics: Dict[str, Any] = {}
            
            # Initialize Standard Metrics
            self._register_metrics(Counter, Histogram, Gauge)
            
        except ImportError:
            self._client_available = False
            logger.warning("Prometheus client not installed. Metrics will be no-ops.")

    def _register_metrics(self, Counter, Histogram, Gauge):
        # Web Requests
        self._metrics['http_requests_total'] = Counter(
            "http_requests_total", "Total count of HTTP requests", ["method", "path", "status_code"]
        )
        self._metrics['http_request_duration_seconds'] = Histogram(
            "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "path"]
        )
        
        # Business Metrics
        self._metrics['user_logins_total'] = Counter(
            "user_logins_total", "Total user logins", ["provider_type", "status"]
        )
        self._metrics['tenant_onboarding_total'] = Counter(
            "tenant_onboarding_total", "Total tenants onboarded", ["plan"]
        )
        self._metrics['auth_failures_total'] = Counter(
            "auth_failures_total", "Total authentication failures", ["provider"]
        )
        self._metrics['rbac_denials_total'] = Counter(
            "rbac_denials_total", "Total RBAC permission denials", ["resource", "action"]
        )
        self._metrics['subscription_events_total'] = Counter(
            "subscription_events_total", "Total subscription events", ["event_type", "plan"]
        )

        # Performance
        self._metrics['external_api_duration_seconds'] = Histogram(
            "external_api_duration_seconds", "Duration of external API calls", ["service", "endpoint"]
        )
        self._metrics['db_query_duration_seconds'] = Histogram(
            "db_query_duration_seconds", "Database query duration", ["query_type", "table_name"]
        )
        self._metrics['auth_token_validation_duration_seconds'] = Histogram(
            "auth_token_validation_duration_seconds", "Time taken to validate auth tokens", ["provider"]
        )
        
        # Gauges
        self._metrics['db_connection_pool_size'] = Gauge(
            "db_connection_pool_size", "Current total size of database connection pool"
        )
        self._metrics['db_connection_pool_checkedout'] = Gauge(
            "db_connection_pool_checkedout", "Number of database connections currently checked out"
        )

    def increment(self, name: str, labels: Dict[str, str] = None, value: int = 1):
        if not self._client_available: return
        metric = self._metrics.get(name)
        if metric:
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)

    def observe(self, name: str, value: float, labels: Dict[str, str] = None):
        if not self._client_available: return
        metric = self._metrics.get(name)
        if metric:
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        if not self._client_available: return
        metric = self._metrics.get(name)
        if metric:
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
                
    def generate_latest(self) -> bytes:
        if not self._client_available: return b""
        return self._generate_latest()
        
    @property
    def content_type(self) -> str:
        return self._content_type if self._client_available else "text/plain"


# =============================================================================
# Concrete Implementation: NoOp / Console
# =============================================================================

class ConsoleProvider(MetricsProvider):
    """No-op provider for local dev without Prometheus"""
    
    def increment(self, name: str, labels: Dict[str, str] = None, value: int = 1):
        # logger.debug(f"Counter: {name} +{value} {labels or ''}")
        pass
        
    def observe(self, name: str, value: float, labels: Dict[str, str] = None):
        # logger.debug(f"Histogram: {name} = {value} {labels or ''}")
        pass
        
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        # logger.debug(f"Gauge: {name} = {value} {labels or ''}")
        pass
        
    def generate_latest(self) -> bytes:
        return b"Prometheus not available"
        
    @property
    def content_type(self) -> str:
        return "text/plain"


# =============================================================================
# Factory & Facade
# =============================================================================

_provider: Optional[MetricsProvider] = None

def get_provider() -> MetricsProvider:
    global _provider
    if _provider is None:
        try:
            import prometheus_client
            # In production we might check settings.metrics_enabled
            _provider = PrometheusProvider()
            logger.info("Initialized Prometheus Metrics Provider")
        except ImportError:
            _provider = ConsoleProvider()
            logger.info("Initialized Console Metrics Provider (Prometheus not found)")
    return _provider


def setup_metrics():
    """Initialize metrics provider (Idempotent)"""
    get_provider()


def metrics_endpoint(request):
    """Serve metrics for scraping"""
    provider = get_provider()
    return Response(provider.generate_latest(), media_type=provider.content_type)


# =============================================================================
# Facade Functions (Backward Compatibility)
# =============================================================================

def record_request_metrics(method: str, path: str, status_code: int, duration: float):
    get_provider().increment(
        "http_requests_total", 
        labels={"method": method, "path": path, "status_code": str(status_code)}
    )
    get_provider().observe(
        "http_request_duration_seconds", 
        duration, 
        labels={"method": method, "path": path}
    )

def increment_login(provider_type: str, status: str = "success"):
    get_provider().increment(
        "user_logins_total", 
        labels={"provider_type": provider_type, "status": status}
    )

def increment_tenant_onboarding(plan: str = "default"):
    get_provider().increment(
        "tenant_onboarding_total", 
        labels={"plan": plan}
    )

def increment_auth_failure(provider: str):
    get_provider().increment(
        "auth_failures_total", 
        labels={"provider": provider}
    )

def increment_rbac_denial(resource: str, action: str):
    get_provider().increment(
        "rbac_denials_total", 
        labels={"resource": resource, "action": action}
    )

@contextmanager
def record_external_api(service: str, endpoint: str):
    start = time.time()
    yield
    duration = time.time() - start
    get_provider().observe(
        "external_api_duration_seconds", 
        duration, 
        labels={"service": service, "endpoint": endpoint}
    )

def record_db_pool_metrics(size: int, checked_out: int):
    get_provider().set_gauge("db_connection_pool_size", size)
    get_provider().set_gauge("db_connection_pool_checkedout", checked_out)

def record_db_query_duration(duration: float, query_type: str = "unknown", table_name: str = "unknown"):
    get_provider().observe(
        "db_query_duration_seconds", 
        duration, 
        labels={"query_type": query_type, "table_name": table_name}
    )

@contextmanager
def record_token_validation(provider: str = "firebase"):
    start = time.time()
    yield
    duration = time.time() - start
    get_provider().observe(
        "auth_token_validation_duration_seconds", 
        duration, 
        labels={"provider": provider}
    )

def increment_subscription_event(event_type: str, plan: str):
    get_provider().increment(
        "subscription_events_total", 
        labels={"event_type": event_type, "plan": plan}
    )

