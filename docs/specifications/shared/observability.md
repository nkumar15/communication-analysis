# Observability Specification

## Overview
This document outlines the architecture for introducing comprehensive observability (Logging, Metrics, Tracing) into the Enterprise SSO backend. The goal is to provide a unified, abstract interface for observability that supports both local development (console/debug) and cloud environments (GCP/AWS) with minimal application code changes.

## 1. Pillars of Observability

### 1.1 Logging (Structured)
**Current State:**
- We use `structlog` in `backend/core/logging/config.py`.
- It supports environment-based formatting (JSON for cloud, colored console for local).

**Refinement:**
- **Correlation:** We must ensure `trace_id` and `span_id` from the Tracing system are automatically injected into every log entry.
- **Abstraction:** The existing `get_logger` is a good abstraction. We will keep it.

### 1.2 Metrics (Prometheus)
**Goal:** Track application performance and health.
**Tool:** `prometheus-client`.

**Architecture:**
- **Exposition:** Expose a `/metrics` endpoint (protected or internal-only) for Prometheus to scrape.
- **Standard Metrics:**
    - `http_requests_total`: Counter (method, path, status).
    - `http_request_duration_seconds`: Histogram (method, path).
- **Custom Metrics:**
    - `user_logins_total`: Counter (provider_type).
    - `tenant_onboarding_total`: Counter.
- **Abstraction:**
    - Create `core/observability/metrics.py`.
    - Provide a `MetricsManager` singleton or helper functions to genericize metric creation.

### 1.3 Tracing (Jaeger / OpenTelemetry)
**Goal:** Visualize request flows across services (though currently monolithic, it prepares for microservices).
**Tool:** OpenTelemetry (OTEL) Python SDK.

**Architecture:**
- **Instrumentation:** specific `FastAPIInstrumentor`, `SQLAlchemyInstrumentor`.
- **Exporter:**
    - **Local:** Console or local Jaeger instance.
    - **Cloud:** OTLP (OpenTelemetry Protocol) exporter to send traces to GCP Trace / AWS X-Ray / Jaeger Collector.
- **Abstraction:**
    - Create `core/observability/tracing.py`.
    - Function `setup_tracing(service_name: str)` that auto-configures based on env vars.

---

## 2. Architecture & Abstraction

We will consolidate observability configuration in `backend/core/observability/`.

### 2.1 File Structure
```
backend/core/observability/
├── __init__.py
├── config.py         # Main entry point (calls setup_logging, setup_tracing)
├── logging.py        # (Relocated from core/logging/config.py or kept as alias)
├── metrics.py        # Prometheus setup & helpers
└── tracing.py        # OpenTelemetry setup
```

### 2.2 Configuration (Environment Variables)
- `OBSERVABILITY_ENABLED`: bool (default True)
- `LOG_LEVEL`: str (INFO, DEBUG)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: URL (e.g., `http://jaeger:4318`) - If unset, tracing might be disabled or console-only.
- `METRICS_ENABLED`: bool (default True)

### 2.3 Middleware Integration
A unified `ObservabilityMiddleware` (or utilizing existing Starlette middleware) will:
1. Start a Trace Span.
2. Initialize Metrics timer.
3. Inject `trace_id` into `structlog` context.
4. Process Request.
5. Record Metric (duration, status).
6. End Span.

---

## 3. Implementation Plan

### Phase 1: Core Setup
1.  **Dependencies:** Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation-fastapi`, `prometheus-client`.
2.  **Refactor Logging:** Move/integrate `core/logging` into `core/observability` context (or ensure tight integration). Add OTEL correlation processor.
3.  **Implement Tracing:** `setup_tracing` function in `core/observability/tracing.py`.
4.  **Implement Metrics:** `setup_metrics` and middleware in `core/observability/metrics.py`.

### Phase 2: Application Integration
1.  **FastAPI Main:** Call `setup_observability()` on startup.
2.  **Instrument Routes:** Verify standard metrics appear.
3.  **Instrument DB:** Auto-instrument SQLAlchemy.

### Phase 3: Infrastructure (Docker)
1.  **Jaeger:** Add `jaegertracing/all-in-one` to `docker-compose.yml`.
2.  **Prometheus:** Add `prom/prometheus` to `docker-compose.yml` (optional for dev, or just verify endpoint).

## 4. Usage Example

```python
# In main.py
from core.observability.config import setup_observability

app = FastAPI()
setup_observability(app, service_name="b2b-api")

# In a service
from core.observability.metrics import increment_counter
increment_counter("tenant_created_total", labels={"plan": "pro"})
```
