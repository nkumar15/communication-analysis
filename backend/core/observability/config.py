from fastapi import FastAPI
from .metrics import setup_metrics, metrics_endpoint
from .tracing import setup_tracing
from .sentry_utils import init_sentry

def setup_observability(app: FastAPI, service_name: str, sqlalchemy_engine=None):
    """
    Central setup for all observability stack:
    1. Tracing (OpenTelemetry)
    2. Metrics (Prometheus)
    3. Error Tracking (Sentry)
    
    Logging should be configured at the start of main, before this.
    """
    
    # 0. Setup Sentry (Error Tracking)
    init_sentry()
    
    # 1. Setup Tracing
    setup_tracing(app, service_name, sqlalchemy_engine)
    
    # 2. Setup Metrics
    setup_metrics()
    
    # 3. Add Metrics Endpoint
    # We add this manually to avoid using a middleware that might expose it publicly by default
    # If the app has global auth middleware, this might need exclusion
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])
