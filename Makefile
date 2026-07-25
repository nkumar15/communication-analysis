

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

# Test compose: overrides DATABASE_URL on all services → saas_test_db
# Demo targets use plain docker-compose (saas_demo_db). Never mix the two.
DC_TEST = docker-compose -f docker-compose.yml -f docker-compose.test.yml


##@ General

logs: ## View logs (usage: make logs [s=service])
ifdef s
	docker-compose logs -f $(s)
else
	docker-compose logs -f b2b-api b2b-domain-api b2b-worker b2b-domain-worker nginx
endif


display-services: ## Display running services
	@echo "$(BLUE)=== Running Services ===$(NC)"
	@docker-compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "$(YELLOW)Common URLs:$(NC)"
	@echo "API Gateway:  http://localhost:8080"
	@echo "Email UI:     http://localhost:8025 (Mailhog)"
	@echo "Grafana:      http://localhost:3002"
	@echo "Prometheus:   http://localhost:9090"
	@echo "Jaeger:       http://localhost:16686"
	@echo "Kibana:       http://localhost:5601"

elasticsearch: ## Start elasticsearch and elasticsearch-kibana
	docker-compose up -d elasticsearch elasticsearch-kibana

up: ## Start all backend services (B2B + infra, no frontend) — used by test targets
	docker-compose up -d postgres minio \
							b2b-api b2b-domain-api \
							b2b-worker b2b-domain-worker \
							redis nginx mailhog prometheus grafana jaeger
	@echo "$(GREEN)✓ Backend services started$(NC)"
	@echo "$(YELLOW) Tip: run 'make dev-full' to also start the frontend portal$(NC)"
	@echo "$(YELLOW) Tip: run 'make up-full' to also start Elasticsearch + Kibana$(NC)"

up-b2b: ## Start B2B services + infra (b2b-api, b2b-worker, b2b-domain-api, b2b-domain-worker, frontend)
	@docker-compose --profile b2b-demo up -d
	@echo "$(GREEN)✓ B2B services started$(NC)"
	@echo "  B2B Portal:      http://localhost:3000"
	@echo "  API Gateway:     http://localhost:8080"

up-full: ## Start all backend services including Elasticsearch + Kibana
	@$(MAKE) up
	@docker-compose up -d elasticsearch kibana
	@echo "$(GREEN)✓ All backend services started (including Elasticsearch)$(NC)"

dev-full: ## Start everything for manual full-stack testing (B2B + frontend portal)
	@docker-compose --profile dev-full up -d
	@echo "$(GREEN)✓ Full stack ready$(NC)"
	@echo "  B2B Portal:      http://localhost:3000"
	@echo "  API Gateway:     http://localhost:8080"
	@echo "  Mailhog:         http://localhost:8025"

down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose --profile b2b-demo --profile dev-full --profile test-api --profile test-ui down --remove-orphans
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: down up ## Restart all services (B2B stack)

##@ Database

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres sh -c "psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB"

db-setup-auth: ## Setup app user and permissions
	@echo "$(BLUE)Setting up application user and permissions...$(NC)"
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_password=\$$DB_PASSWORD -c saas.app_db_user=\$$DB_USER -c saas.app_db_name=\$$POSTGRES_DB\"; psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB -f /app/scripts/init_auth_db.sql"
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_user=\$$DB_USER\"; psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB -f /app/scripts/grant_permissions.sql"
	@echo "$(GREEN)✓ Auth setup complete$(NC)"

migrate-schema: ## Run SQL migrations only (no seeds) - requires just postgres
	@echo "$(BLUE)Running database migrations...$(NC)"
	@docker-compose run --rm dbmigrate
	@$(MAKE) db-setup-auth
	@echo "$(GREEN)✓ Migrations applied$(NC)"

db-recreate: ## Reset demo database (saas_demo_db) — never touches saas_test_db
	@echo "$(BLUE)Recreating demo database (saas_demo_db)...$(NC)"
	@docker-compose up -d postgres
	@sleep 2
	@docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-postgres} postgres dropdb -U $${POSTGRES_USER:-postgres} --if-exists --force $${POSTGRES_DB:-saas_demo_db}
	@docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-postgres} postgres createdb -U $${POSTGRES_USER:-postgres} $${POSTGRES_DB:-saas_demo_db}
	@$(MAKE) migrate-schema
	@echo "$(GREEN)✓ Demo database recreated$(NC)"

db-recreate-test: ## Reset test database (saas_test_db) — never touches saas_demo_db
	@echo "$(BLUE)Recreating test database (saas_test_db)...$(NC)"
	@docker-compose up -d postgres
	@sleep 2
	@docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-postgres} postgres dropdb -U $${POSTGRES_USER:-postgres} --if-exists --force saas_test_db
	@docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-postgres} postgres createdb -U $${POSTGRES_USER:-postgres} saas_test_db
	@$(MAKE) migrate-schema-test
	@echo "$(GREEN)✓ Test database ready$(NC)"

db-setup-auth-test: ## Setup app user permissions on saas_test_db
	@echo "$(BLUE)Setting up auth for test database...$(NC)"
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_password=\$$DB_PASSWORD -c saas.app_db_user=\$$DB_USER -c saas.app_db_name=saas_test_db\"; psql -U \$$POSTGRES_USER -d saas_test_db -f /app/scripts/init_auth_db.sql"
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_user=\$$DB_USER\"; psql -U \$$POSTGRES_USER -d saas_test_db -f /app/scripts/grant_permissions.sql"
	@echo "$(GREEN)✓ Test DB auth setup complete$(NC)"

migrate-schema-test: ## Run SQL migrations against saas_test_db
	@echo "$(BLUE)Running migrations against test database...$(NC)"
	@$(DC_TEST) run --rm dbmigrate
	@$(MAKE) db-setup-auth-test
	@echo "$(GREEN)✓ Test DB migrations applied$(NC)"


##@ Seed

b2b-seed-roles: ## Seed B2B RBAC Roles (Foundation + [USE_CASE])
	@echo "$(BLUE)=== SaaS Admin Console - RBAC Seeding ===$(NC)"
	@docker-compose exec -it b2b-api env USE_CASE=$(USE_CASE) python /app/modules/b2b/scripts/seeds/seed_rbac.py
ifdef USE_CASE
	@echo "$(YELLOW)Loading domain use case: $(USE_CASE)$(NC)"
	@docker-compose exec -it b2b-api env USE_CASE=$(USE_CASE) python /app/modules/domains/b2b/$(USE_CASE)/scripts/seeds/seed_rbac.py
endif

b2b-verify-seed: ## Verify B2B Seed Data
	@echo "$(BLUE)=== SaaS Admin Console - Seed Verification ===$(NC)"
	@docker-compose exec -it b2b-api env USE_CASE=$(USE_CASE) python /app/modules/b2b/scripts/seeds/verify_seed.py

b2b-seed-meta: ## Seed domain-specific metadata (generic - calls domain's seed_meta.py)
ifdef USE_CASE
	@echo "$(BLUE)=== $(USE_CASE) - Meta Seeding ===$(NC)"
	@docker-compose exec -T b2b-domain-api python /app/modules/domains/b2b/$(USE_CASE)/scripts/seeds/seed_meta.py
endif

seed-all: ## Run all seed scripts (requires b2b-api running)
	@echo "$(BLUE)Running seed scripts...$(NC)"
	@$(MAKE) b2b-seed-roles $(if $(USE_CASE),USE_CASE=$(USE_CASE),)
	@$(MAKE) b2b-verify-seed
	@echo "$(GREEN)✓ Seed scripts complete$(NC)"

seed-b2b: seed-all ## Alias for seed-all

seed-demo: ## Full demo system (optional USE_CASE=xxx, defaults to bank_surveillance) — starts all services
	@echo "$(BLUE)=== Setting up Demo System ===$(NC)"
	@$(MAKE) db-recreate
	@$(MAKE) restart
	@$(MAKE) seed-all USE_CASE=$(or $(USE_CASE),bank_surveillance)
	@$(MAKE) b2b-invite f=modules/domains/b2b/$(or $(USE_CASE),bank_surveillance)/scripts/seeds/demo_tenant.json
	@$(MAKE) b2b-seed-meta USE_CASE=$(or $(USE_CASE),bank_surveillance)
	@echo "$(GREEN)✅ Demo system ready$(NC)"


## B2B Onboarding

b2b-invite: ## Invite B2B Tenant (f=file.json [PLUGINS=p1,p2])
	@echo "$(BLUE)=== SaaS Admin Console - B2B Tenant Setup ===$(NC)"
	@docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_onboard.py create-local \
		--file $(or $(f),modules/domains/b2b/bank_surveillance/scripts/seeds/bank_surveillance_demo.json) \
		$(if $(PLUGINS),--plugins $(PLUGINS),)

b2b-invite-bank: ## Invite Bank Tenant (Shortcut)
	@$(MAKE) b2b-invite f=modules/domains/b2b/bank_surveillance/scripts/seeds/bank_surveillance_demo.json

b2b-resend-invite: ## Resend activation email (usage: make b2b-resend-invite d=domain.com)
ifdef d
	@echo "$(BLUE)Resending activation for domain: $(d)$(NC)"
	@docker-compose exec b2b-api python -m scripts.b2b.tenant_onboard resend --domain $(d)
else ifdef t
	@echo "$(BLUE)Resending activation for tenant: $(t)$(NC)"
	@docker-compose exec b2b-api python -m scripts.b2b.tenant_onboard resend --tenant-id $(t)
else
	@echo "$(YELLOW)Usage: make b2b-resend-invite d=<domain> OR t=<tenant-id>$(NC)"
	@echo "Example: make b2b-resend-invite d=acme.com"
endif

##@ B2B Demos

b2b-demo-bank: ## Bank Surveillance demo — starts B2B containers
	@echo "$(BLUE)=== Bank Surveillance Demo Setup ===$(NC)"
	@$(MAKE) db-recreate
	@echo "$(BLUE)Starting B2B services...$(NC)"
	@docker-compose --profile b2b-demo up -d
	@sleep 5
	@$(MAKE) seed-b2b USE_CASE=bank_surveillance
	@$(MAKE) b2b-invite f=modules/domains/b2b/bank_surveillance/scripts/seeds/demo_tenant.json
	@$(MAKE) b2b-seed-meta USE_CASE=bank_surveillance
	@echo ""
	@echo "$(GREEN)✅ Bank Surveillance Demo Ready!$(NC)"
	@echo "  📋 Resources: communications, investigations, alerts, surveillance_reports"
	@echo "  👥 Roles: surveillance_chief, surveillance_analyst, operations_maker, operations_checker"
	@echo ""
	@echo "$(BLUE)Login as:$(NC)         owner@worldwidebank.com"
	@echo "$(BLUE)B2B Portal:$(NC)       http://localhost:3000"
	@echo "$(BLUE)API Gateway:$(NC)      http://localhost:8080"
	@echo "$(BLUE)Mailhog:$(NC)          http://localhost:8025"


##@ Testing

test-api: ## Run backend API pytest suite — uses saas_test_db, never touches demo data. Usage: make test-api [USE_CASE=bank_surveillance] [path=tests/b2b/api]
	@echo "$(BLUE)Running backend API tests (saas_test_db)...$(NC)"
	@$(MAKE) db-recreate-test
	@$(DC_TEST) up -d postgres minio redis nginx mailhog prometheus grafana jaeger \
		b2b-api b2b-domain-api b2b-worker b2b-domain-worker
	@sleep 5
	@$(MAKE) seed-all $(if $(USE_CASE),USE_CASE=$(USE_CASE),)
	@$(DC_TEST) --profile test-api run --rm e2e-tests pytest \
		$(or $(path),tests/) \
		-v
	@echo "$(GREEN)✓ Backend API tests complete$(NC)"

test-ui: ## Run automated Playwright browser tests — uses saas_test_db. Usage: make test-ui [USE_CASE=bank_surveillance]
	@echo "$(BLUE)Running automated UI tests (saas_test_db)...$(NC)"
	@$(MAKE) db-recreate-test
	@$(DC_TEST) up -d postgres minio redis nginx mailhog prometheus grafana jaeger \
		b2b-api b2b-domain-api b2b-worker b2b-domain-worker
	@$(DC_TEST) --profile test-ui up -d
	@sleep 8
	@$(MAKE) seed-all $(if $(USE_CASE),USE_CASE=$(USE_CASE),)
	@$(DC_TEST) --profile test-ui run --rm e2e-tests pytest \
		tests/e2e_browser \
		-v
	@echo "$(GREEN)✓ UI tests complete$(NC)"

test-b2b-foundation-only: ## Run B2B foundation full suite (API, Services, Units) — uses saas_test_db
	@echo "$(BLUE)Running B2B Foundation Full Suite (saas_test_db)...$(NC)"
	@$(MAKE) db-recreate-test
	@$(DC_TEST) up -d postgres minio redis nginx mailhog prometheus grafana jaeger \
		b2b-api b2b-domain-api b2b-worker b2b-domain-worker
	@sleep 5
	@$(MAKE) seed-all
	@$(DC_TEST) --profile test-api run --rm e2e-tests pytest \
		tests/b2b/api/foundation \
		tests/b2b/services/foundation \
		tests/b2b/units \
		-v


test-b2b-bank-only: ## Run B2B Bank Surveillance specific suite (API, Services, Units) — uses saas_test_db
	@echo "$(BLUE)Running Bank Surveillance specific suite (saas_test_db)...$(NC)"
	@$(MAKE) db-recreate-test
	@$(DC_TEST) up -d postgres minio redis nginx mailhog prometheus grafana jaeger \
		b2b-api b2b-domain-api b2b-worker b2b-domain-worker
	@sleep 5
	@$(MAKE) seed-all USE_CASE=bank_surveillance
	@$(DC_TEST) run --rm -e USE_CASE=bank_surveillance e2e-tests \
		pytest \
		tests/b2b/api/use_cases/bank_surveillance \
		tests/b2b/services/use_cases/bank_surveillance \
		tests/b2b/units/use_cases/bank_surveillance \
		-v

test-b2b-bank: ## Run B2B Bank Surveillance full suite (Foundation + Bank) — uses saas_test_db
	@echo "$(BLUE)Running Bank Surveillance full suite (saas_test_db)...$(NC)"
	@$(MAKE) db-recreate-test
	@$(DC_TEST) up -d postgres minio redis nginx mailhog prometheus grafana jaeger \
		b2b-api b2b-domain-api b2b-worker b2b-domain-worker
	@sleep 5
	@$(MAKE) seed-all USE_CASE=bank_surveillance
	@$(DC_TEST) run --rm -e USE_CASE=bank_surveillance e2e-tests \
		pytest \
		tests/b2b/api/foundation \
		tests/b2b/api/use_cases/bank_surveillance \
		tests/b2b/services/foundation \
		tests/b2b/services/use_cases/bank_surveillance \
		tests/b2b/units \
		-v

test-all-foundation: test-b2b-foundation-only ## Alias for test-b2b-foundation-only

##@ Frontend (Local Development)

web-b2b: ## Start B2B portal (port 3000)
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(YELLOW)Installing frontend dependencies...$(NC)"; \
		cd frontend && npm install; \
	fi
	cd frontend && npm run start:b2b

stop-web-all:
	docker-compose stop frontend-b2b || true



##@ Performance

DURATION ?= 1m

load-test-b2b: ## Run B2B Locust load test (50 users). Usage: make load-test-b2b DURATION=30s
	@echo "$(BLUE)Starting B2B Locust load test (50 users, $(DURATION))...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop early.$(NC)"
	$(DC_TEST) --profile test-api run --rm e2e-tests bash -c "python -m locust -f tests/load/b2b_locustfile.py --host http://b2b-api:8000 --headless -u 50 -r 10 --run-time $(DURATION)"
	@echo "$(GREEN)✓ B2B Load test complete$(NC)"

##@ SAST (Static Application Security Testing)

sast-scan: ## Run all SAST scans (Python + React + Containers)
	@$(MAKE) sast-scan-python
	@$(MAKE) sast-scan-react
	@$(MAKE) sast-scan-containers

sast-scan-python: ## Run Bandit SAST scan on Python code
	@echo "$(BLUE)Running Bandit SAST scan on Python code...$(NC)"
	@docker-compose run --rm e2e-tests bandit -r . -ll -f screen --exclude './tests,./tests_e2e,./.pytest_cache,./venv,./env,./.venv' | tee backend/bandit-report.txt || true
	@echo "$(GREEN)✓ Python SAST scan complete - Report saved to backend/bandit-report.txt$(NC)"

sast-scan-react: ## Run Semgrep SAST scan on React code
	@echo "$(BLUE)Running Semgrep SAST scan on React code...$(NC)"
	@docker-compose run --rm e2e-tests semgrep --config=auto frontend/src/ --exclude='*.test.js' --exclude='*.spec.js' --verbose || true
	@echo "$(GREEN)✓ React SAST scan complete$(NC)"

sast-scan-containers: ## Run Trivy vulnerability scan on Docker images
	@echo "$(BLUE)Running Trivy container security scans...$(NC)"
	@echo "$(YELLOW)Scanning backend images...$(NC)"
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --timeout 10m --severity HIGH,CRITICAL enterprisesso-b2b-api:latest 2>&1 | tee -a backend/trivy-report.txt || true
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --timeout 10m --severity HIGH,CRITICAL enterprisesso-b2b-domain-api:latest 2>&1 | tee -a backend/trivy-report.txt || true
	@echo "$(YELLOW)Scanning frontend image...$(NC)"
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --timeout 10m --severity HIGH,CRITICAL enterprisesso-frontend:latest 2>&1 | tee -a backend/trivy-report.txt || true
	@echo "$(GREEN)✓ Container security scan complete - Report saved to backend/trivy-report.txt$(NC)"

security-update-npm: ## Fix npm vulnerabilities identified by Trivy scan
	@echo "$(BLUE)Applying security updates to npm packages...$(NC)"
	@./ops/scripts/security-update-npm.sh
	@echo "$(GREEN)✓ Security updates applied. Rebuild frontend with: docker-compose build frontend$(NC)"

##@ DAST (Dynamic Application Security Testing)

dast-scan: ## Run OWASP ZAP baseline scan on all APIs
	@echo "$(BLUE)Running OWASP ZAP baseline scans on all APIs...$(NC)"
	@echo "$(YELLOW)Ensure services are running: make up$(NC)"
	@$(MAKE) dast-scan-b2b
	@$(MAKE) dast-scan-domain

dast-scan-b2b: ## Run OWASP ZAP scan on B2B API
	@echo "$(BLUE)Scanning B2B API...$(NC)"
	@docker run --rm --network="host" -v $(PWD)/backend:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -t http://localhost:8080/docs/b2b/openapi.json -f openapi -r zap-b2b-report.html -w zap-b2b-report.md -J zap-b2b-report.json 2>&1 | tee backend/zap-b2b-output.log || true
	@echo "$(GREEN)✓ B2B API scan complete - Reports: backend/zap-b2b-report.*$(NC)"

dast-scan-domain: ## Run OWASP ZAP scan on Domain API
	@echo "$(BLUE)Scanning Domain API...$(NC)"
	@docker run --rm --network="host" -v $(PWD)/backend:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -t http://localhost:8080/docs/domain/openapi.json -f openapi -r zap-domain-report.html -w zap-domain-report.md -J zap-domain-report.json 2>&1 | tee backend/zap-domain-output.log || true
	@echo "$(GREEN)✓ Domain API scan complete - Reports: backend/zap-domain-report.*$(NC)"

dast-scan-full: ## Run OWASP ZAP full active scan (comprehensive but slow)
	@echo "$(BLUE)Running OWASP ZAP full active scan...$(NC)"
	@echo "$(YELLOW)⚠ This may take 30+ minutes. Ensure services are running: make up$(NC)"
	@docker run --rm --network="host" -v $(PWD)/backend:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable zap-full-scan.py -t http://localhost:8080 -r zap-full-report.html -w zap-full-report.md -J zap-full-report.json 2>&1 | tee backend/zap-full-output.log || true
	@echo "$(GREEN)✓ DAST full scan complete - Reports: backend/zap-full-report.*$(NC)"
