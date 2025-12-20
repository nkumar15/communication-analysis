# Observability & Monitoring Specification

> **Status**: Implementation in Progress  
> **Last Updated**: 2025-12-20  
> **Owner**: Platform Team

---

## Executive Summary

This document defines the observability and monitoring strategy for the Enterprise SSO platform. It covers logging, tracing, metrics, alerting, and debugging requirements for production operation.

**Current Implementation Status**: 65% Complete
- ✅ Structured logging with request context
- ✅ OpenTelemetry distributed tracing
- ✅ Basic Prometheus metrics
- ❌ Error tracking (Sentry) - **Planned**
- ❌ Business metrics - **Planned**
- ❌ Alert rules - **Planned**
- ❌ Grafana dashboards - **Planned**

---

## 1. Observability Stack

### 1.1 Logging

**Technology**: Structlog + Cloud-native formatters

**Implementation**: `core/logging/`

**Features**:
- Structured JSON logging
- Automatic request context injection:
  - `request_id` - Unique per request
  - `tenant_id` - From JWT token
  - `user_id` - From JWT token
  - HTTP metadata (method, path, client IP, user-agent)
  - Request duration
- OpenTelemetry trace correlation (`trace_id`, `span_id`)
- Environment-specific formatters (GCP, AWS, Generic JSON)

**Log Levels**:
- `DEBUG` - Verbose information for development
- `INFO` - Standard operations (request start/complete)
- `WARNING` - Slow requests, auth failures, rate limits
- `ERROR` - Server errors, exceptions, failures
- `CRITICAL` - System-wide failures

### 1.2 Distributed Tracing

**Technology**: OpenTelemetry + OTLP Exporter

**Implementation**: `core/observability/tracing.py`

**Features**:
- Automatic FastAPI instrumentation
- SQLAlchemy query tracing
- OTLP HTTP exporter (Jaeger/Tempo compatible)
- Service name tagging
- Environment tagging

**Trace Attributes**:
- HTTP: method, path, status_code, duration
- SQL: query type, table name, duration
- Custom: tenant_id, user_id, operation_type

### 1.3 Metrics

**Technology**: Prometheus + prometheus_client

**Implementation**: `core/observability/metrics.py`

**Current Metrics**:

```python
# HTTP Metrics
http_requests_total{method, path, status_code}
http_request_duration_seconds{method, path}

# Business Metrics (Basic)
user_logins_total{provider_type, status}
tenant_onboarding_total{plan}
```

**Planned Metrics** (Phase 2):

```python
# Error Tracking
http_errors_total{status_code, http_method, http_path, tenant_id}

# Database
db_query_duration_seconds{query_type, table_name}
db_connection_pool_size
db_connection_pool_usage

# Authentication
auth_attempts_total{provider, result}
auth_token_validation_duration_seconds{provider}

# RBAC
permission_checks_total{resource, action, result}

# Business Operations
subscription_events_total{event_type, plan}
invitation_events_total{event_type, role}
team_operations_total{operation, team_role}

# External APIs
external_api_calls_total{service, endpoint, status_code}
external_api_duration_seconds{service, endpoint}

# Cache (if Redis)
cache_operations_total{operation, result}
```

---

## 2. HTTP Status Code Monitoring

### 2.1 Critical Status Codes (P0 Alerts)

| Code | Meaning | Alert Threshold | SRE Action |
|------|---------|----------------|------------|
| **500** | Internal Server Error | > 0.5% error rate | Check logs, rollback if recent deploy |
| **502** | Bad Gateway | > 1% | Verify upstream services |
| **503** | Service Unavailable | > 0.1% | Check DB pool, scale resources |
| **504** | Gateway Timeout | > 2% | Check slow queries, external APIs |
| **401** | Unauthorized | Spike > 10x baseline | Potential attack, check auth service |
| **403** | Forbidden | Spike > 5x baseline | RBAC misconfiguration or bypass attempt |
| **429** | Too Many Requests | > 50/min per IP | Rate limit working (info) or DDoS |

### 2.2 Warning Status Codes (P1 Monitoring)

| Code | Meaning | Monitor For | Action |
|------|---------|-------------|--------|
| **404** | Not Found | Sudden spike | Check for broken links, API changes |
| **400** | Bad Request | High sustained rate | Client integration issues |
| **422** | Validation Error | Pattern changes | Schema drift detection |

### 2.3 Success Code Metrics

| Code | Purpose | Metric to Track |
|------|---------|----------------|
| **200** | OK | p50, p95, p99 latency |
| **201** | Created | Track separately for resource creation |
| **204** | No Content | Fast operations benchmark |

---

## 3. Error Tracking (Planned - Phase 1)

### 3.1 Sentry Integration

**Priority**: HIGH (Week 1)

**Configuration**:
```python
# core/observability/sentry_config.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT"),
    traces_sample_rate=0.1,  # 10% for prod
    profiles_sample_rate=0.1,
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
    ],
    before_send=sanitize_sensitive_data,
)
```

**Features**:
- Automatic error grouping
- Stack trace capture
- User context (tenant_id, user_id)
- Release tracking
- Performance profiling
- Sensitive data redaction (passwords, tokens)

---

## 4. Alerting Rules (Planned - Phase 1)

### 4.1 Prometheus Alert Definitions

**File**: `ops/prometheus/alerts.yml`

#### Critical Alerts

```yaml
- alert: HighServerErrorRate
  expr: |
    rate(http_requests_total{status_code=~"5.."}[5m])
    / rate(http_requests_total[5m]) > 0.01
  for: 2m
  severity: critical
  runbook: https://wiki/runbooks/high-error-rate

- alert: DatabasePoolExhausted
  expr: db_connection_pool_usage / db_connection_pool_size > 0.9
  for: 1m
  severity: critical
  runbook: https://wiki/runbooks/db-pool-exhausted

- alert: AuthenticationFailureSpike
  expr: rate(auth_attempts_total{result!="success"}[5m]) > 10
  for: 3m
  severity: critical
  runbook: https://wiki/runbooks/auth-failures
```

#### Warning Alerts

```yaml
- alert: SlowAPIRequests
  expr: |
    histogram_quantile(0.95,
      rate(http_request_duration_seconds_bucket[5m])
    ) > 3
  for: 5m
  severity: warning

- alert: FrequentPermissionDenials
  expr: rate(permission_checks_total{result="denied"}[10m]) > 50
  for: 5m
  severity: info
```

### 4.2 Notification Channels

- **Critical**: PagerDuty (on-call engineer)
- **Warning**: Slack #alerts channel
- **Info**: Slack #monitoring channel

---

## 5. Dashboards (Planned - Phase 2)

### 5.1 API Golden Signals Dashboard

**Panels**:
1. **Traffic**: Request rate per endpoint
2. **Errors**: Error rate % by status code
3. **Latency**: p50, p95, p99 response times
4. **Saturation**: DB pool usage, memory, CPU

### 5.2 Business Metrics Dashboard

**Panels**:
1. User signups per day
2. Subscription conversions
3. Failed payment attempts
4. Team creation rate
5. Invitation acceptance rate
6. SSO provider usage

### 5.3 Infrastructure Dashboard

**Panels**:
1. Container resource usage
2. Database connection pool
3. External API response times
4. Cache hit/miss ratios

---

## 6. Enhanced Logging (Planned - Phase 1)

### 6.1 Status Code Classification

**Enhancement to `LoggingMiddleware`**:

```python
# Log levels based on status code
if 500 <= status_code < 600:
    logger.error("server_error", status_code=status_code, ...)
elif status_code in [401, 403, 429]:
    logger.warning("client_auth_error", status_code=status_code, ...)
else:
    logger.info("request_completed", status_code=status_code, ...)

# Slow request detection
if duration_ms > 3000:
    logger.warning("slow_request_detected", 
                   duration_ms=duration_ms, 
                   threshold_ms=3000)
```

### 6.2 Request/Response Logging (Errors Only)

```python
# For 5xx errors, log sanitized request body
if 500 <= status_code < 600:
    body = await request.body()
    logger.error("server_error_with_context",
                 request_body_preview=sanitize_body(body[:1000]),
                 response_body=response_body[:500])
```

### 6.3 SQL Query Logging

```python
# Log slow queries (> 1s)
@event.listens_for(Engine, "after_cursor_execute")
def log_slow_queries(conn, cursor, statement, params, context, executemany):
    duration = time.time() - conn.info["query_start_time"].pop()
    if duration > 1.0:
        logger.warning("slow_query",
                       duration_seconds=duration,
                       query=statement[:500])
```

---

## 7. Debugging Support Matrix

| Scenario | Supported? | Method |
|----------|-----------|--------|
| "What caused this 500 error?" | ✅ After Phase 1 | Sentry error grouping + logs with `request_id` |
| "Why is API slow for Tenant X?" | ✅ Now | Filter logs by `tenant_id`, check duration_ms |
| "Which user triggered this error?" | ✅ Now | Logs include `user_id` |
| "What SQL queries ran?" | ✅ After Phase 1 | SQLAlchemy tracing + slow query logs |
| "Is this widespread?" | ✅ After Phase 1 | Sentry impact analysis |
| "What was request payload?" | ✅ After Phase 1 | Error-only request logging |
| "How many users affected?" | ✅ After Phase 2 | Sentry user impact + metrics |

---

## 8. Production Readiness Checklist

### Phase 1 (Critical - Week 1)

- [ ] Sentry integration
- [ ] Enhanced status code logging
- [ ] Basic Prometheus alert rules
- [ ] Slow query detection
- [ ] Request/response logging for errors

### Phase 2 (High Priority - Week 2-3)

- [ ] Business metrics expansion
- [ ] Grafana dashboards (Golden Signals + Business)
- [ ] Database pool metrics
- [ ] Alert runbooks

### Phase 3 (Medium Priority - Month 2)

- [ ] Custom exception handlers
- [ ] Distributed tracing dashboard (Jaeger)
- [ ] Log retention policies
- [ ] On-call rotation setup

### Before Production Launch

- [ ] Sentry environment tagging configured
- [ ] Prometheus scraping all services
- [ ] Grafana dashboards deployed
- [ ] Alert rules tested and tuned
- [ ] On-call rotation defined
- [ ] Runbooks created for top 10 alerts
- [ ] Log aggregation configured (CloudWatch/ELK)
- [ ] Retention policies set (logs: 30d, metrics: 90d)
- [ ] PagerDuty/OpsGenie integration
- [ ] Health check endpoints (`/health`, `/ready`)

---

## 9. Service Level Objectives (SLOs)

### 9.1 API Availability

| Service | Target | Measurement Window | Alert Threshold |
|---------|--------|-------------------|----------------|
| B2B API | 99.9% | 30 days | < 99.5% |
| B2C API | 99.9% | 30 days | < 99.5% |
| Platform API | 99.95% | 30 days | < 99.8% |

### 9.2 API Latency

| Endpoint Type | p95 Target | p99 Target | Alert Threshold |
|--------------|------------|------------|----------------|
| Authentication | < 200ms | < 500ms | p95 > 500ms |
| Read Operations | < 300ms | < 1000ms | p95 > 1000ms |
| Write Operations | < 500ms | < 2000ms | p95 > 2000ms |
| Heavy Queries | < 1000ms | < 3000ms | p99 > 5000ms |

### 9.3 Error Budget

- **Monthly Error Budget**: 0.1% of requests = ~43 minutes downtime
- **Burn Rate Alert**: If consuming > 10x normal rate, page on-call

---

## 10. Implementation Timeline

### Week 1 (Critical)
- Day 1-2: Sentry integration
- Day 3: Enhanced logging middleware
- Day 4-5: Prometheus alert rules + testing

### Week 2-3 (High Priority)
- Week 2: Business metrics implementation
- Week 3: Grafana dashboards + documentation

### Month 2 (Enhancements)
- SQL query tracing refinement
- Custom exception handlers
- Distributed tracing dashboard
- Runbook creation

---

## 11. Cost Estimates

| Service | Tier | Monthly Cost | Notes |
|---------|------|-------------|-------|
| Sentry | Team (50K events) | $26 | Error tracking |
| Grafana Cloud | Free Tier | $0 | 10K series, 50GB logs |
| Prometheus | Self-hosted | $0 | On existing infra |
| CloudWatch Logs | 10GB/month | ~$5 | AWS log storage |
| **Total** | | **~$31/month** | Scales with usage |

---

## 12. References

### Internal Documentation
- [Logging Configuration](../../backend/core/logging/config.py)
- [Metrics Setup](../../backend/core/observability/metrics.py)
- [Tracing Setup](../../backend/core/observability/tracing.py)

### External Resources
- [OpenTelemetry Best Practices](https://opentelemetry.io/docs/best-practices/)
- [Google SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Prometheus Alert Rules Guide](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/best-practices/)

---

## Appendix A: Metric Labels Reference

### Standard Labels (All Metrics)
- `environment` - prod, staging, dev
- `service` - b2b-api, b2c-api, platform-api, domains-api

### HTTP Metrics
- `http_method` - GET, POST, PUT, PATCH, DELETE
- `http_path` - /api/b2b/teams, /api/auth/login
- `status_code` - 200, 404, 500, etc.

### Business Metrics
- `tenant_id` - UUID of tenant (high cardinality, use sparingly)
- `plan` - free, starter, professional, enterprise
- `provider` - firebase, google, microsoft
- `result` - success, failure, expired, denied

---

## Appendix B: Sanitization Rules

### Sensitive Fields to Redact
- `password`
- `token`
- `api_key`
- `secret`
- `authorization` header
- `credit_card`
- `ssn`

### Sanitization Logic
```python
def sanitize_body(body: str) -> str:
    sensitive_patterns = [
        r'"password"\s*:\s*"[^"]*"',
        r'"token"\s*:\s*"[^"]*"',
        r'Bearer\s+[\w-]+'
    ]
    for pattern in sensitive_patterns:
        body = re.sub(pattern, '"***REDACTED***"', body)
    return body
```
