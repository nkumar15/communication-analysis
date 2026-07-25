# Environment Setup Runbook

**Audience**: Developers setting up locally, DevOps deploying to staging/production  
**Covers**: Local dev, domain use case enablement, production deployment checklist

---

## 1. Config File Overview

Two files control the environment. Keep both in sync:

| File | Used by | Contains |
|------|---------|----------|
| `.env.example` → `.env` (root) | Docker Compose | Postgres admin credentials |
| `backend/.env.example` → `backend/.env` | All API services + workers | Everything else |

The root `.env` is mounted into the `postgres` container at startup. The `backend/.env` is loaded by all FastAPI apps and Celery workers via `env_file` in `docker-compose.yml`.

---

## 2. Local Development Setup (5 steps)

```bash
# 1. Copy both env files
cp .env.example .env
cp backend/.env.example backend/.env

# 2. Copy Firebase service account (get from Firebase Console → Project Settings → Service Accounts)
cp ~/Downloads/firebase-credentials.json secrets/firebase-credentials.json

# 3. Fill in the three REQUIRED secrets in backend/.env
#    - SECRET_KEY        → openssl rand -hex 32
#    - FIREBASE_PROJECT_ID
#    - FIREBASE_API_KEY

# 4. Start the stack
make up

# 5. Run migrations + seed
make db-recreate
make seed-all
```

That's the minimum for the foundation platform (no domain, no AI, no billing).

---

## 3. Enabling a Domain Use Case

Each domain adds its own requirements on top of the foundation. Pick your domain below.

### task_management
No extra env vars needed. The foundation config is sufficient.
```bash
make seed-all USE_CASE=task_management
make b2b-invite-task
```

### bank_surveillance
Requires AI/RAG stack (LLM + embeddings + vector store + document storage).

1. Uncomment the `[DOMAIN: bank_surveillance]` section in `backend/.env`
2. Set one LLM provider (OpenAI is simplest):
   ```
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4o-mini
   OPENAI_API_KEY=sk-...
   ```
3. Set one embedding provider (use HuggingFace to avoid extra cost):
   ```
   EMBEDDING_PROVIDER=huggingface
   EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
   EMBEDDING_DIM=384
   HF_HOME=/app/.cache/huggingface
   ```
4. Start Elasticsearch (not in default `make up`):
   ```bash
   make elasticsearch
   ```
5. Seed and onboard:
   ```bash
   make seed-all USE_CASE=bank_surveillance
   make b2b-invite-bank
   ```

### marketing_agency
Same as `bank_surveillance` — requires the AI/RAG stack.

### finance_trader (B2C domain)
Same AI/RAG requirements. Uses B2C billing stack if Stripe is enabled.

---

## 4. Enabling Billing (Stripe)

Billing is off by default. To enable:

1. Create a Stripe account and get test keys from the Dashboard → Developers → API Keys
2. Create Products + Prices in Stripe Dashboard (or use `make stripe-listen-b2b` to test webhooks)
3. Uncomment the Stripe section in `backend/.env` and fill in:
   - `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`
   - All `STRIPE_PRICE_*` IDs
   - Repeat for B2B keys if enabling enterprise billing
4. For local webhook testing:
   ```bash
   make stripe-listen-b2b   # forwards Stripe events to localhost:8000
   make stripe-listen-b2c   # forwards Stripe events to localhost:8002
   ```

---

## 5. Switching Email Provider

| Environment | Provider | What to set |
|-------------|----------|-------------|
| Local dev | `mailhog` | Nothing — runs in Docker at port 8025 |
| Staging | `resend` | `EMAIL_PROVIDER=resend` + `RESEND_API_KEY=re_...` |
| Production | `resend` or `ses` | Same as staging, use live keys |

Mailhog UI: http://localhost:8025

---

## 6. Production / Staging Deployment Checklist

Go through this before any non-local deployment.

### Secrets (never use dev defaults in prod)
- [ ] `SECRET_KEY` — generate fresh: `openssl rand -hex 32`
- [ ] `POSTGRES_PASSWORD` and `DB_PASSWORD` — strong, unique passwords
- [ ] `FIREBASE_PROJECT_ID` + `FIREBASE_API_KEY` — production Firebase project
- [ ] `firebase-credentials.json` — production service account, stored in secrets manager
- [ ] `RESEND_API_KEY` or AWS SES credentials — live email sending keys
- [ ] Stripe live keys (`sk_live_...`, `pk_live_...`, `whsec_...`) — never use test keys in prod

### URLs
- [ ] `FRONTEND_URL`, `FRONTEND_URL_B2C`, `FRONTEND_URL_PLATFORM` — real domain names
- [ ] `BACKEND_URL` — real API domain
- [ ] `CORS_ORIGINS` — locked to actual frontend domains only (remove localhost)

### Infrastructure
- [ ] `DATABASE_URL` — points to managed Postgres (RDS, CloudSQL, etc.)
- [ ] `REDIS_HOST` — points to managed Redis (ElastiCache, Upstash, etc.)
- [ ] `ELASTICSEARCH_URL` — managed cluster if using AI domains
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

## 7. Environment Variable Reference

Quick lookup: which vars are needed for each scenario.

| Var | Foundation | + Billing | + AI/RAG |
|-----|-----------|-----------|----------|
| `SECRET_KEY` | ✅ | ✅ | ✅ |
| `DATABASE_URL` | ✅ | ✅ | ✅ |
| `REDIS_HOST` / `CELERY_*` | ✅ | ✅ | ✅ |
| `FIREBASE_PROJECT_ID` | ✅ | ✅ | ✅ |
| `FIREBASE_API_KEY` | ✅ | ✅ | ✅ |
| `EMAIL_PROVIDER` + credentials | ✅ | ✅ | ✅ |
| `STRIPE_*` keys | — | ✅ | — |
| `STRIPE_PRICE_*` IDs | — | ✅ | — |
| `LLM_PROVIDER` + `OPENAI_API_KEY` | — | — | ✅ |
| `EMBEDDING_PROVIDER` + model | — | — | ✅ |
| `ELASTICSEARCH_URL` | — | — | ✅ |
| `MINIO_ENDPOINT` + credentials | — | — | ✅ |

---

## 8. Common Issues

**`invalid input syntax for type uuid` on startup**  
→ `DATABASE_URL` uses the wrong credentials or host. Verify it matches `../.env`.

**Firebase: `Could not deserialize key data`**  
→ `firebase-credentials.json` is missing or corrupt. Re-download from Firebase Console.

**Celery workers not picking up tasks**  
→ `CELERY_BROKER_URL` in the worker container doesn't match the API container. Both must point to the same Redis instance (`redis://redis:6379/0` in Docker).

**Elasticsearch `service_started` but domain API crashes**  
→ ES takes ~90s to become healthy. Run `make elasticsearch` and wait before starting domain APIs.

**Stripe webhooks 400**  
→ `STRIPE_WEBHOOK_SECRET` doesn't match what `stripe listen` prints. Re-run `stripe listen --print-secret`.
