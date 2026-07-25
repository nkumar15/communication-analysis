# Environment Setup Runbook

**Audience**: Developers setting up locally, DevOps deploying to staging/production
**Covers**: Local dev setup, production deployment checklist

---

## 1. Config File Overview

Two files control the environment. Keep both in sync:

| File | Used by | Contains |
|------|---------|----------|
| `.env.example` → `.env` (root) | Docker Compose | Postgres admin credentials |
| `backend/.env.example` → `backend/.env` | All API services + workers | Everything else |

The root `.env` is mounted into the `postgres` container at startup. The `backend/.env` is loaded by all FastAPI apps and Celery workers via `env_file` in `docker-compose.yml`.

---

## 2. Local Development Setup

```bash
# 1. Copy both env files
cp .env.example .env
cp backend/.env.example backend/.env

# 2. Copy Firebase service account (get from Firebase Console → Project Settings → Service Accounts)
cp ~/Downloads/firebase-credentials.json secrets/firebase-credentials.json

# 3. Fill in the required secrets in backend/.env
#    - SECRET_KEY        → openssl rand -hex 32
#    - FIREBASE_PROJECT_ID
#    - FIREBASE_API_KEY
#
#    Bank Surveillance needs the AI/RAG stack too — set one LLM provider:
#      LLM_PROVIDER=openai
#      LLM_MODEL=gpt-4o-mini
#      OPENAI_API_KEY=sk-...
#    and one embedding provider (HuggingFace avoids extra cost):
#      EMBEDDING_PROVIDER=huggingface
#      EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
#      EMBEDDING_DIM=384
#      HF_HOME=/app/.cache/huggingface

# 4. Start the full stack (Postgres, Redis, Elasticsearch, Kibana, MinIO, B2B API/worker,
#    Bank Surveillance domain API/worker, frontend, observability)
make up

# 5. Run migrations + seed RBAC roles
make db-recreate
make seed-all

# 6. Onboard a demo tenant, or run the full seeded demo in one step
make b2b-invite            # onboard using backend/modules/domains/b2b/bank_surveillance/scripts/seeds/demo_tenant.json
# — or —
make b2b-demo-bank         # recreates the DB, starts everything, seeds roles, onboards the demo tenant
```

---

## 3. Switching Email Provider

| Environment | Provider | What to set |
|-------------|----------|-------------|
| Local dev | `mailhog` | Nothing — runs in Docker at port 8025 |
| Staging | `resend` | `EMAIL_PROVIDER=resend` + `RESEND_API_KEY=re_...` |
| Production | `resend` or `ses` | Same as staging, use live keys |

Mailhog UI: http://localhost:8025

---

## 4. Production / Staging Deployment Checklist

Go through this before any non-local deployment.

### Secrets (never use dev defaults in prod)
- [ ] `SECRET_KEY` — generate fresh: `openssl rand -hex 32`
- [ ] `POSTGRES_PASSWORD` and `DB_PASSWORD` — strong, unique passwords
- [ ] `FIREBASE_PROJECT_ID` + `FIREBASE_API_KEY` — production Firebase project
- [ ] `firebase-credentials.json` — production service account, stored in secrets manager
- [ ] `RESEND_API_KEY` or AWS SES credentials — live email sending keys

### URLs
- [ ] `FRONTEND_URL` — real domain name
- [ ] `BACKEND_URL` — real API domain
- [ ] `CORS_ORIGINS` — locked to the actual frontend domain only (remove localhost)

### Infrastructure
- [ ] `DATABASE_URL` — points to managed Postgres (RDS, CloudSQL, etc.)
- [ ] `REDIS_HOST` — points to managed Redis (ElastiCache, Upstash, etc.)
- [ ] `ELASTICSEARCH_URL` — managed cluster
- [ ] `MINIO_ENDPOINT` + credentials — or replace with S3 config

### Observability
- [ ] `SENTRY_DSN` — production Sentry project
- [ ] `OTEL_EXPORTER_OTLP_ENDPOINT` — production tracing backend
- [ ] `LOG_ENVIRONMENT=production` — structured JSON logs
- [ ] `LOG_LEVEL=WARNING` — reduce noise in prod

### Feature flags
- [ ] `AUTH_PROVIDER=firebase` — never `mock` in prod
- [ ] `EMAIL_PROVIDER=resend` (or `ses`) — never `mailhog` in prod
- [ ] `MINIO_SECURE=true` — TLS for object storage in prod

---

## 5. Environment Variable Reference

| Var | Required |
|-----|----------|
| `SECRET_KEY` | ✅ |
| `DATABASE_URL` | ✅ |
| `REDIS_HOST` / `CELERY_*` | ✅ |
| `FIREBASE_PROJECT_ID` | ✅ |
| `FIREBASE_API_KEY` | ✅ |
| `EMAIL_PROVIDER` + credentials | ✅ |
| `LLM_PROVIDER` + `OPENAI_API_KEY` | ✅ (Bank Surveillance RAG) |
| `EMBEDDING_PROVIDER` + model | ✅ (Bank Surveillance RAG) |
| `ELASTICSEARCH_URL` | ✅ (Bank Surveillance RAG) |
| `MINIO_ENDPOINT` + credentials | ✅ (document storage) |

---

## 6. Common Issues

**`invalid input syntax for type uuid` on startup**
→ `DATABASE_URL` uses the wrong credentials or host. Verify it matches `../.env`.

**Firebase: `Could not deserialize key data`**
→ `firebase-credentials.json` is missing or corrupt. Re-download from Firebase Console.

**Celery workers not picking up tasks**
→ `CELERY_BROKER_URL` in the worker container doesn't match the API container. Both must point to the same Redis instance (`redis://redis:6379/0` in Docker).

**Elasticsearch `service_started` but domain API crashes**
→ ES takes ~90s to become healthy. Run `make elasticsearch` and wait for it before starting the domain API, or just re-run `make up` once ES reports healthy.
