---
description: Reset Database (Drop/Create), Restart all services, stabilize, and SEED data.
---

1. Stop all running containers to ensure a clean slate.
   Command: `docker compose down`

// turbo
2. Reset Database and Start Services.
   This runs `make db-recreate` which:
   - Starts Postgres.
   - Drops/Creates `saas_demo_db`.
   - Runs `make migrate-only`.
   - docker compose recreate all backend services.
   Command: `make db-recreate`

3. Wait for services to initialize (15 seconds).
   Command: `sleep 15`

4. **Stabilize Services**:
   - Check status: `docker compose ps`
   - elastic search service could be flaky if it reports unhealthy ignore it
   - If any other service except elastic search is not `Up` or is `Restarting`:
     1. Check logs: `docker compose logs <service_name>`
     2. Fix the issue.
     3. Restart: `docker compose restart <service_name>`
     4. Repeat until all services are `Up`.

5. Seed Data.
   (Requires services to be healthy).
   Command: `make seed-all`
   
   *Optional: To seed specific use case:*
   *Command: `make seed-all USE_CASE=bank_surveillance`*

6. Verify API Health:
   - Check B2B API: `curl -f http://localhost:8000/api/b2b/health || echo "B2B Check Failed"`
   - Check B2C API: `curl -f http://localhost:8002/api/b2c/health || echo "B2C Check Failed"`
   - Check Domain API: `curl -f http://localhost:8003/health || echo "Domain Check Failed"`

7. Validated Stable Environment with Data. 
