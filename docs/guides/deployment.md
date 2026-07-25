# Agriculture-Specific Deployment Notes

## Boilerplate Customization

This codebase is the **Agriculture Deployment** of the multi-tenant SSO boilerplate.

### Core System Roles (All Businesses)
- `owner` - Primary administrator
- `admin` - Administrator 
- `viewer` - Read-only user

### Agriculture-Specific Roles
- `role_name` - Manages resource_name 

These agriculture roles are marked as `is_default=True` and will be automatically seeded for all tenants.

## For Other Businesses

If adapting this codebase for a different industry:

1. **Edit** `backend/scripts/b2b/seed_domain_data.py`
2. **Replace** `projects` resource with your domain resource (e.g., `projects`)
3. **Replace** `field_manager` and `field_agent` templates with your business roles
4. **Keep** `is_default=True` for roles that are core to your business
5. **Run** `make b2b-seed-roles`

## Deployment Types

**Generic Boilerplate** (not this repo):
- Only owner, admin, viewer as defaults
- No domain-specific roles

**Agriculture Deployment** (this repo):
- owner, admin, viewer + field_manager, field_agent as defaults
- projects resource

**Retail Deployment** (hypothetical):
- owner, admin, viewer + store_manager, cashier as defaults  
- Products, inventory resources

---

## Observability & Infrastructure

### 1. Logging Strategy

The application uses `structlog` with environment-aware formatters.

| Environment | Config Variable | Output Format |
|-------------|----------------|---------------|
| **Local Dev** | `LOG_ENVIRONMENT=local` | Human-readable, colored console output |
| **GCP** | `LOG_ENVIRONMENT=gcp` | JSON structured for Cloud Logging (includes `severity`, trace ID) |
| **AWS** | `LOG_ENVIRONMENT=aws` | JSON structured for CloudWatch (includes `level`) |
| **Production** | `LOG_ENVIRONMENT=production` | Generic JSON |

**To switch environments:**
simply set the `LOG_ENVIRONMENT` environment variable in your deployment (Kubernetes/ECS/Docker).

### 2. Tracing (OpenTelemetry)

The system is instrumented with OpenTelemetry (OTEL) and exports via OTLP/HTTP.

**Configuration:**
```bash
OTEL_SERVICE_NAME=enterprise-sso
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318  # Default
```

**Supported Backends:**
- **Jaeger**: Default for local dev.
- **GCP Cloud Trace**: Use the Google Cloud Ops Agent or OpenTelemetry Collector sidecar.
- **AWS X-Ray**: Use the AWS Distro for OpenTelemetry (ADOT) Collector.
- **Datadog/NewRelic**: Point the `OTEL_EXPORTER_OTLP_ENDPOINT` to their agents.

### 3. Metric Collection

The application exposes Prometheus metrics at `/metrics`.

**Current Architecture (Pull Model):**
- **Endpoint**: `http://<service>:8000/metrics`
- **Format**: Prometheus text format
- **Standard Metrics**: HTTP request count, latency, DB pool size.
- **Custom Metrics**: User logins, tenant onboarding counts.

**Extensibility for Cloud (Push Model):**
To integrate with cloud monitoring tools (CloudWatch, GCP Operations) that prefer a "Push" model, use a **Cloud Agent Sidecar**:
1.  Deploy the agent (e.g., CloudWatch Agent, Google Ops Agent) alongside your container.
2.  Configure the agent to scrape `localhost:8000/metrics`.
3.  The agent handles the translation and pushing to the cloud service.

### 4. Email Infrastructure

Email providers are pluggable via environment variables.

**Configuration:**
```bash
EMAIL_PROVIDER=resend  # Options: resend, mailhog, console
RESEND_API_KEY=re_123...
```

**Extensibility:**
To add a new provider (e.g., SES, SendGrid):
1.  Implement the standardized `EmailProvider` interface in `backend/core/email/providers.py`.
2.  Register the new provider in the factory class.
3.  Update the configuration to select it.

---

## Queue & Background Workers

The application uses **Celery** for background processing (emails, audit logs).

### 1. Broker Configuration

By default, Celery uses Redis. For production on cloud providers, you should switch to a managed service to ensure reliability.

**AWS (SQS)**
Use Amazon SQS as the broker to ensuring high availability without managing infrastructure.
```bash
# .env configuration
CELERY_BROKER_URL=sqs://{aws_access_key}:{aws_secret_key}@
CELERY_RESULT_BACKEND=rpc://
```
*Note: Ensure the IAM user has `sqs:*` permissions.*

**GCP (Cloud Pub/Sub or Redis)**
GCP does not have a native Celery broker implementation that is as stable as SQS.
- **Recommended**: Use **Cloud Memorystore (Redis)**. This keeps the configuration identical to local/on-prem (`redis://...`) but fully managed.
- **Alternative**: Use a Pub/Sub wrapper (requires `pip install` additional dependencies not currently in `pyproject.toml`).

### 2. Reliability & No-Data-Loss

To ensure **Zero Message Loss** and **No Duplicate Emails**:

**A. Preventing Message Loss**
- The application is configured with `task_acks_late=True`. This means a task is only acknowledged (removed from queue) *after* successful execution.
- If a worker crashes mid-task, the message remains in the queue and will be redelivered to another worker.

**B. Preventing Duplicate Execution (Idempotency)**
Celery guarantees *at-least-once* delivery, meaning duplicates are possible (e.g., network timeout during ACK).
- **Critical Rule**: All tasks must be **idempotent**.
- **For Emails**: 
  - Checks if `email_log_id` exists before sending.
  - Uses a distributed lock (Redis) for the duration of the send operation.
  - If a duplicate message arrives, the second worker sees the "Sent" status and discards it.

**C. Dead Letter Queues (DLQ)**
- Configure your cloud provider (SQS/PubSub) to move failed messages to a DLQ after N retries.
- Monitor the DLQ to investigate permanently failing tasks (poison pills).
