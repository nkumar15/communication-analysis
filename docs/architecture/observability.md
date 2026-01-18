# Observability Architecture

## Overview

The Enterprise SSO system employs a comprehensive observability strategy centered around the three pillars of observability: **Logging**, **Metrics**, and **Tracing**. This architecture is designed to provide deep visibility into request flows, system performance, and error states across the microservices landscape, supporting both local development and cloud-native deployments (GCP/AWS).

## High-Level Architecture

The observability stack allows each microservice to emit signals (logs, metrics, traces) in a standardized format, which are then collected by infrastructure components.

```mermaid
graph TD
    subgraph "Microservices Layer"
        B2B[B2B API]
        Platform[Platform API]
        B2C[B2C API]
        Domain[Domain API]
    end

    subgraph "Observability Collector Layer"
        Jaeger[Jaeger (Tracing)]
        Prometheus[Prometheus (Metrics)]
    end

    subgraph "External/Cloud"
        CloudTrace[Cloud Trace / X-Ray]
        CloudLogs[CloudLogging / CloudWatch]
    end

    %% Tracing Flow
    B2B -- OTLP/gRPC --> Jaeger
    Platform -- OTLP/gRPC --> Jaeger
    B2C -- OTLP/gRPC --> Jaeger
    Domain -- OTLP/gRPC --> Jaeger

    %% Metrics Flow
    Prometheus -- Scrape /metrics --> B2B
    Prometheus -- Scrape /metrics --> Platform
    Prometheus -- Scrape /metrics --> B2C
    Prometheus -- Scrape /metrics --> Domain

    %% Logging Flow (Stdout)
    B2B -. JSON/Text .-> CloudLogs
```

---

## 1. Structured Logging

We use **`structlog`** to provide context-rich, structured logging.

### Key Features
*   **Correlation**: Every log entry is automatically enriched with `trace_id` and `span_id` from the current OpenTelemetry context. This allows you to jump from a log error directly to the distributed trace.
*   **Contextual**: Middleware automatically injects `request_id`, `tenant_id`, `user_id`, and `http_method`.
*   **Adaptive Formatting**:
    *   **Local**: Colored, human-readable text for developer experience.
    *   **Cloud (GCP/AWS)**: JSON structured logs for machine parsing and ingestion.

### Configuration
Controlled via `backend/core/config.py`:
*   `LOG_ENVIRONMENT`: `local`, `gcp`, `aws`, `production`
*   `LOG_LEVEL`: `INFO`, `DEBUG`, etc.

---

## 2. Distributed Tracing

We use **OpenTelemetry (OTEL)** for instrumentation and **Jaeger** for local visualization.

### Architecture
*   **Instrumentation**: Auto-instrumentation for **FastAPI** (HTTP requests) and **SQLAlchemy** (DB queries).
*   **Protocol**: OTLP (OpenTelemetry Protocol).
*   **Propagation**: W3C Trace Context headers are propagated between services.

### Components
*   **Tracer Provider**: Configured in `backend/core/observability/tracing.py`.
*   **Exporter**:
    *   **Local**: Sends traces to Jaeger container via OTLP (HTTP/gRPC).
    *   **Cloud**: Can be configured to send to Google Cloud Trace or AWS X-Ray via an OTel Collector sidecar.

### Integration
To enable tracing for a service, the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable must be set.
*   **Local Default**: `http://jaeger:4318`
*   **Cloud**: URL of your OTel Collector or managed service endpoint.

---

## 3. Metrics

We use **Prometheus** for metrics collection and monitoring.

### Architecture
*   **Model**: Pull-based. Prometheus scrapes endpoints.
*   **Format**: Prometheus text format.
*   **Endpoint**: `/metrics` exposed on every microservice.

### Standard Metrics
*   `http_requests_total`: Counter for total requests (labels: method, path, status).
*   `http_request_duration_seconds`: Histogram of response latency.
*   `process_cpu_seconds_total`, `process_resident_memory_bytes`: Runtime metrics.

### Custom Metrics
Business-specific metrics are defined in `backend/core/observability/metrics.py`:
*   `user_logins_total`: Counter tracking successful logins by provider.
*   `tenant_onboarding_total`: Counter tracking new tenant creations.

---

## Cloud Integration Guide

### Google Cloud Platform (GCP)
1.  **Logging**: Set `LOG_ENVIRONMENT=gcp`. Logs will be emitted as JSON with fields mapped to Cloud Logging (e.g., `severity`, `logging.googleapis.com/trace`).
2.  **Tracing**: Deploy an **OpenTelemetry Collector** as a sidecar or distinct service. Point `OTEL_EXPORTER_OTLP_ENDPOINT` to the collector, which forwards to Cloud Trace.

### AWS
1.  **Logging**: Set `LOG_ENVIRONMENT=aws`. Logs emitted as JSON for CloudWatch.
2.  **Tracing**: similar to GCP, use ADOT (AWS Distro for OpenTelemetry) collector to forward OTLP data to **AWS X-Ray**.

---

## 4. Cloud Monitoring Adapter Guide

The refactored `backend/infrastructure/monitoring` package makes it easy to add new monitoring backends (CloudWatch, Stackdriver) using the **Factory Pattern**.

### 1. Google Cloud Monitoring (Stackdriver)

**Prerequisites:**
- Install: `pip install google-cloud-monitoring`
- Auth: `GOOGLE_APPLICATION_CREDENTIALS`

**Implementation:**
Create `backend/infrastructure/monitoring/gcp.py`:

```python
from typing import Dict
from google.cloud import monitoring_v3
import time
from .metrics import MetricsProvider

class GCPMonitoringProvider(MetricsProvider):
    def __init__(self, project_id: str):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{project_id}"
        self.series = [] # Buffer for batching

    def increment(self, name: str, labels: Dict[str, str] = None, value: int = 1):
        # Construct TimeSeries object and push to buffer or send immediately (batching recommended)
        pass 

    def observe(self, name: str, value: float, labels: Dict[str, str] = None):
        # Create distribution metric
        pass

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        # Create gauge metric
        pass

    def generate_latest(self) -> bytes:
        return b"GCP Monitoring collects metrics via API push, not scrape."

    @property
    def content_type(self) -> str:
        return "text/plain"
```

### 2. AWS CloudWatch

**Prerequisites:**
- Install: `pip install boto3`
- Auth: AWS Credentials

**Implementation:**
Create `backend/infrastructure/monitoring/aws.py`:

```python
from typing import Dict
import boto3
from .metrics import MetricsProvider

class CloudWatchProvider(MetricsProvider):
    def __init__(self, namespace: str = "EnterpriseSSO"):
        self.client = boto3.client('cloudwatch')
        self.namespace = namespace

    def increment(self, name: str, labels: Dict[str, str] = None, value: int = 1):
        dimensions = [{'Name': k, 'Value': v} for k, v in (labels or {}.items())]
        
        self.client.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': name,
                'Value': value,
                'Unit': 'Count',
                'Dimensions': dimensions
            }]
        )

    # ... implement observe (as timing/count) and set_gauge ...
```

### 3. Register in Factory

Update `backend/infrastructure/monitoring/__init__.py`:

```python
def get_metrics_provider() -> "MetricsProvider":
    # ...
    if settings.monitoring_provider == "gcp":
        from .gcp import GCPMonitoringProvider
        _metrics_provider = GCPMonitoringProvider(settings.gcp_project_id)
    elif settings.monitoring_provider == "aws":
        from .aws import CloudWatchProvider
        _metrics_provider = CloudWatchProvider()
    # ...
```
