import os
from typing import Dict, Optional, Any
from abc import ABC, abstractmethod
import structlog

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
            "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "path"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0, 90.0, 120.0]
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
            "external_api_duration_seconds", "Duration of external API calls", ["service", "endpoint"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0]
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
        
        # Domain: RAG
        self._metrics['rag_processing_duration_seconds'] = Histogram(
            "rag_processing_duration_seconds", "Duration of RAG pipeline stages", ["domain", "stage"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0, 90.0]
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
# Factory & Facade have been moved to __init__.py to prevent circular imports
# =============================================================================

