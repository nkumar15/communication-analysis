

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color


##@ General

logs: ## View logs (usage: make logs [s=service])
ifdef s
	docker-compose logs -f $(s)
else
	docker-compose logs -f b2b-api platform-api b2c-api b2b-domain-api b2c-domain-api b2c-worker b2b-domain-worker b2c-domain-worker nginx
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

up: ## Start all backend services (frontend runs locally)
	docker-compose up -d postgres minio \
							b2b-api platform-api b2c-api \
							b2b-domain-api b2c-domain-api \
							b2c-worker b2b-worker \
							b2b-domain-worker b2c-domain-worker \
							dbmigrate redis \
							nginx mailhog prometheus grafana jaeger

	@echo "$(GREEN)✓ Backend services started$(NC)"
	@echo "$(YELLOW) Remember to start elasticsearch and elasticsearch-kibana manually if needed $(NC)"
	@echo "$(YELLOW) run command make elasticsearch $(NC)"

down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down --remove-orphans
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: down up ## Restart all services

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
	@docker-compose run --rm dbmigrate env ENABLED_PRODUCTS=platform,b2b,b2c python /app/migrations/run_migrations.py
	@$(MAKE) db-setup-auth
	@echo "$(GREEN)✓ Migrations applied$(NC)"

db-recreate: ## Fast Database Reset (Drop DB -> Create DB). Uses POSTGRES_USER/DB from env (defaults: postgres/saas_demo_db)
	@echo "$(BLUE)Recreating database (Drop & Create)...$(NC)"
	@docker-compose up -d postgres
	@sleep 2
	@docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-postgres} postgres dropdb -U $${POSTGRES_USER:-postgres} --if-exists --force $${POSTGRES_DB:-saas_demo_db}
	@docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-postgres} postgres createdb -U $${POSTGRES_USER:-postgres} $${POSTGRES_DB:-saas_demo_db}
	@$(MAKE) migrate-schema
	@echo "$(GREEN)✓ Schema migrations completed(NC)"
	@echo "$(GREEN)✓ Database recreated$(NC)"


##@ Seed

platform-seed-system: ## Seed System Tenant (Platform)
	@echo "$(BLUE)Seeding System Tenant...$(NC)"
	@docker-compose exec -T platform-api python /app/scripts/platform/seed_system_tenant.py

platform-seed-admin: ## Create Platform Admin User
	@echo "$(BLUE)Creating Platform Admin User...$(NC)"
	@docker-compose exec -T platform-api python /app/scripts/platform/create_platform_admin.py

platform-seed-permissions: ## Seed platform permissions
	docker-compose exec -T platform-api python /app/scripts/platform/seed_platform_permissions.py

b2b-seed-roles: ## Seed B2B RBAC Roles (Foundation + [USE_CASE])
	@echo "$(BLUE)=== SaaS Admin Console - RBAC Seeding ===$(NC)"
	@docker-compose exec -it b2b-api env USE_CASE=$(USE_CASE) python /app/modules/b2b/scripts/seeds/seed_rbac.py
ifdef USE_CASE
	@echo "$(YELLOW)Loading domain use case: $(USE_CASE)$(NC)"
	@docker-compose exec -it b2b-api env USE_CASE=$(USE_CASE) python /app/modules/domains/b2b/$(USE_CASE)/scripts/seeds/seed_rbac.py
endif

b2b-seed-plans: ## Seed B2B Subscription Plans
	@echo "$(BLUE)=== SaaS Admin Console - Subscription Seeding ===$(NC)"
	@docker-compose exec -it b2b-api env USE_CASE=$(USE_CASE) python /app/modules/b2b/scripts/seeds/seed_subscription_plans.py

b2c-seed-plans: ## Seed B2C subscription plans
	@echo "$(BLUE)Seeding B2C subscription plans...$(NC)"
	@docker-compose exec -T b2c-api python /app/scripts/b2c/seed_subscription_plans.py
	@echo "$(GREEN)✓ B2C plans seeded$(NC)"

b2b-verify-seed: ## Verify B2B Seed Data
	@echo "$(BLUE)=== SaaS Admin Console - Seed Verification ===$(NC)"
	@docker-compose exec -it b2b-api env USE_CASE=$(USE_CASE) python /app/modules/b2b/scripts/seeds/verify_seed.py

b2b-seed-meta: ## Seed domain-specific metadata (generic - calls domain's seed_meta.py)
ifdef USE_CASE
	@echo "$(BLUE)=== $(USE_CASE) - Meta Seeding ===$(NC)"
	@docker-compose exec -T b2b-api python /app/modules/domains/b2b/$(USE_CASE)/scripts/seeds/seed_meta.py
endif

seed-all: ## Run all seed scripts (requires API services running)
	@echo "$(BLUE)Running seed scripts...$(NC)"
	@$(MAKE) platform-seed-permissions
	@$(MAKE) b2b-seed-roles $(if $(USE_CASE),USE_CASE=$(USE_CASE),)
	@$(MAKE) b2b-seed-plans
	@$(MAKE) b2c-seed-plans
	@$(MAKE) b2b-verify-seed
	@echo "$(GREEN)✓ Seed scripts complete$(NC)"

seed-demo: ## Full demo system (optional USE_CASE=xxx)
	@echo "$(BLUE)=== Setting up Demo System ===$(NC)"
	@$(MAKE) db-recreate
	@$(MAKE) restart
	@$(MAKE) seed-all $(if $(USE_CASE),USE_CASE=$(USE_CASE),)
ifdef USE_CASE
	@$(MAKE) b2b-invite f=modules/domains/b2b/$(USE_CASE)/scripts/seeds/demo_tenant.json
	@$(MAKE) b2b-seed-meta USE_CASE=$(USE_CASE)
else
	@$(MAKE) b2b-invite f=modules/domains/b2b/task_management/scripts/seeds/demo_tenant.json
endif
	@echo "$(GREEN)✅ Demo system ready$(NC)"


## B2B Onboarding

b2b-invite: ## Invite B2B Tenant (f=file.json [PLUGINS=p1,p2])
	@echo "$(BLUE)=== SaaS Admin Console - B2B Tenant Setup ===$(NC)"
	@docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_onboard.py create-local \
		--file $(or $(f),modules/domains/b2b/task_management/scripts/seeds/task_management_demo.json) \
		$(if $(PLUGINS),--plugins $(PLUGINS),)

b2b-invite-bank: ## Invite Bank Tenant (Shortcut)
	@$(MAKE) b2b-invite f=modules/domains/b2b/bank_surveillance/scripts/seeds/bank_surveillance_demo.json

b2b-invite-marketing: ## Invite Marketing Tenant (Shortcut)
	@$(MAKE) b2b-invite f=modules/domains/b2b/marketing_agency/scripts/seeds/marketing_agency_demo.json

b2b-invite-task: ## Invite Task Management Tenant (Shortcut)
	@$(MAKE) b2b-invite f=modules/domains/b2b/task_management/scripts/seeds/task_management_demo.json

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

b2b-demo-bank: ## Full bank surveillance demo (DB reset + seed + tenant + demo data)
	@$(MAKE) seed-demo USE_CASE=bank_surveillance
	@echo ""
	@echo "$(GREEN)✅ Bank Surveillance Demo Ready!$(NC)"
	@echo "  📋 Resources: communications, investigations, alerts, surveillance_reports"
	@echo "  👥 Roles: surveillance_chief, surveillance_analyst, operations_maker, operations_checker"
	@echo ""
	@echo "$(BLUE)Login as:$(NC) owner@worldwidebank.com"


##@ Testing

test-b2b-foundation-only: ## Run B2B foundation full suite (API, Services, Units)
	@echo "$(BLUE)Running B2B Foundation Full Suite...$(NC)"
	@$(MAKE) db-recreate
	@$(MAKE) up
	@sleep 5
	@$(MAKE) seed-all
	@docker-compose run --rm e2e-tests pytest \
		tests/b2b/api/foundation \
		tests/b2b/services/foundation \
		tests/b2b/units \
		-v


test-b2b-bank-only: ## Run B2B Bank Surveillance specific suite (API, Services, Units)
	@echo "$(BLUE)Running Bank Surveillance specific suite...$(NC)"
	@$(MAKE) db-recreate
	@$(MAKE) up
	@sleep 5
	@$(MAKE) seed-all USE_CASE=bank_surveillance
	@docker-compose run --rm -e USE_CASE=bank_surveillance e2e-tests \
		pytest \
		tests/b2b/api/use_cases/bank_surveillance \
		tests/b2b/services/use_cases/bank_surveillance \
		tests/b2b/units/use_cases/bank_surveillance \
		-v

test-b2b-bank: ## Run B2B Bank Surveillance full suite (Foundation + Bank)
	@echo "$(BLUE)Running Bank Surveillance full suite (Foundation + Bank)...$(NC)"
	@$(MAKE) db-recreate
	@$(MAKE) up
	@sleep 5
	@$(MAKE) seed-all USE_CASE=bank_surveillance
	@docker-compose run --rm -e USE_CASE=bank_surveillance e2e-tests \
		pytest \
		tests/b2b/api/foundation \
		tests/b2b/api/use_cases/bank_surveillance \
		tests/b2b/services/foundation \
		tests/b2b/services/use_cases/bank_surveillance \
		tests/b2b/units \
		-v

test-b2c-foundation-only: ## Run B2C foundation full suite (API, Services, Units)
	@echo "$(BLUE)Running B2C Foundation Full Suite...$(NC)"
	@$(MAKE) db-recreate
	@$(MAKE) up
	@sleep 5
	@$(MAKE) seed-all
	@docker-compose run --rm e2e-tests pytest \
		tests/b2c/api/foundation \
		tests/b2c/services/foundation \
		tests/b2c/units \
		-v


test-platform-foundation-only: ## Run Platform foundation full suite (API, Services, Units)
	@echo "$(BLUE)Running Platform Foundation Full Suite...$(NC)"
	@$(MAKE) db-recreate
	@$(MAKE) up
	@sleep 5
	@$(MAKE) seed-all
	@docker-compose run --rm e2e-tests pytest \
		tests/platform/api \
		tests/platform/services \
		tests/platform/units \
		-v


test-all-foundation: ## Run all foundation tests (B2B, B2C, Platform)
	@echo "$(BLUE)Running All Foundation Tests...$(NC)"
	@$(MAKE) db-recreate
	@$(MAKE) up
	@sleep 5
	@$(MAKE) seed-all
	@docker-compose run --rm e2e-tests pytest \
		tests/b2b/api/foundation \
		tests/b2b/services/foundation \
		tests/b2b/units \
		tests/b2c/api/foundation \
		tests/b2c/services/foundation \
		tests/b2c/units \
		tests/platform/api \
		tests/platform/services \
		tests/platform/units \
		-v

##@ Frontend (Local Development)

web-b2b: ## Start B2B portal (port 3000)
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(YELLOW)Installing frontend dependencies...$(NC)"; \
		cd frontend && npm install; \
	fi
	cd frontend && npm run start:b2b

web-b2c: ## Start B2C portal (port 3001)
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(YELLOW)Installing frontend dependencies...$(NC)"; \
		cd frontend && npm install; \
	fi
	cd frontend && npm run start:b2c

web-platform: ## Start Platform portal (port 3002)
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "$(YELLOW)Installing frontend dependencies...$(NC)"; \
		cd frontend && npm install; \
	fi
	cd frontend && npm run start:platform

stop-web-all:
	docker-compose stop frontend-b2c frontend-b2b frontend-platform || true



##@ Performance

DURATION ?= 1m

load-test-b2b: ## Run B2B Locust load test (50 users). Usage: make load-test-b2b DURATION=30s
	@echo "$(BLUE)Starting B2B Locust load test (50 users, $(DURATION))...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop early.$(NC)"
	docker-compose run --rm e2e-tests bash -c "python -m locust -f tests/load/b2b_locustfile.py --host http://b2b-api:8000 --headless -u 50 -r 10 --run-time $(DURATION)"
	@echo "$(GREEN)✓ B2B Load test complete$(NC)"

load-test-b2c: ## Run B2C Locust load test (50 users). Usage: make load-test-b2c DURATION=30s
	@echo "$(BLUE)Starting B2C Locust load test (50 users, $(DURATION))...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop early.$(NC)"
	docker-compose run --rm e2e-tests bash -c "python -m locust -f tests/load/b2c_locustfile.py --host http://b2c-api:8002 --headless -u 50 -r 10 --run-time $(DURATION)"
	@echo "$(GREEN)✓ B2C Load test complete$(NC)"

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
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --timeout 10m --severity HIGH,CRITICAL enterprisesso-platform-api:latest 2>&1 | tee -a backend/trivy-report.txt || true
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --timeout 10m --severity HIGH,CRITICAL enterprisesso-b2c-api:latest 2>&1 | tee -a backend/trivy-report.txt || true
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --timeout 10m --severity HIGH,CRITICAL enterprisesso-b2b-domain-api:latest 2>&1 | tee -a backend/trivy-report.txt || true
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --timeout 10m --severity HIGH,CRITICAL enterprisesso-b2c-domain-api:latest 2>&1 | tee -a backend/trivy-report.txt || true
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
	@$(MAKE) dast-scan-platform
	@$(MAKE) dast-scan-b2c
	@$(MAKE) dast-scan-domain

dast-scan-b2b: ## Run OWASP ZAP scan on B2B API
	@echo "$(BLUE)Scanning B2B API...$(NC)"
	@docker run --rm --network="host" -v $(PWD)/backend:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -t http://localhost:8080/docs/b2b/openapi.json -f openapi -r zap-b2b-report.html -w zap-b2b-report.md -J zap-b2b-report.json 2>&1 | tee backend/zap-b2b-output.log || true
	@echo "$(GREEN)✓ B2B API scan complete - Reports: backend/zap-b2b-report.*$(NC)"

dast-scan-platform: ## Run OWASP ZAP scan on Platform API
	@echo "$(BLUE)Scanning Platform API...$(NC)"
	@docker run --rm --network="host" -v $(PWD)/backend:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -t http://localhost:8080/docs/platform/openapi.json -f openapi -r zap-platform-report.html -w zap-platform-report.md -J zap-platform-report.json 2>&1 | tee backend/zap-platform-output.log || true
	@echo "$(GREEN)✓ Platform API scan complete - Reports: backend/zap-platform-report.*$(NC)"

dast-scan-b2c: ## Run OWASP ZAP scan on B2C API
	@echo "$(BLUE)Scanning B2C API...$(NC)"
	@docker run --rm --network="host" -v $(PWD)/backend:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -t http://localhost:8080/docs/b2c/openapi.json -f openapi -r zap-b2c-report.html -w zap-b2c-report.md -J zap-b2c-report.json 2>&1 | tee backend/zap-b2c-output.log || true
	@echo "$(GREEN)✓ B2C API scan complete - Reports: backend/zap-b2c-report.*$(NC)"

dast-scan-domain: ## Run OWASP ZAP scan on Domain API
	@echo "$(BLUE)Scanning Domain API...$(NC)"
	@docker run --rm --network="host" -v $(PWD)/backend:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py -t http://localhost:8080/docs/domain/openapi.json -f openapi -r zap-domain-report.html -w zap-domain-report.md -J zap-domain-report.json 2>&1 | tee backend/zap-domain-output.log || true
	@echo "$(GREEN)✓ Domain API scan complete - Reports: backend/zap-domain-report.*$(NC)"

dast-scan-full: ## Run OWASP ZAP full active scan (comprehensive but slow)
	@echo "$(BLUE)Running OWASP ZAP full active scan...$(NC)"
	@echo "$(YELLOW)⚠ This may take 30+ minutes. Ensure services are running: make up$(NC)"
	@docker run --rm --network="host" -v $(PWD)/backend:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable zap-full-scan.py -t http://localhost:8080 -r zap-full-report.html -w zap-full-report.md -J zap-full-report.json 2>&1 | tee backend/zap-full-output.log || true
	@echo "$(GREEN)✓ DAST full scan complete - Reports: backend/zap-full-report.*$(NC)"


##@ Stripe

stripe-listen-b2b: ## Forward Stripe webhooks to B2B service (Port 8000)
	@echo "$(BLUE)Forwarding Stripe events to B2B Service...$(NC)"
	stripe listen --forward-to localhost:8000/api/b2b/billing/webhooks/stripe

stripe-listen-b2c: ## Forward Stripe webhooks to B2C service (Port 8002)
	@echo "$(BLUE)Forwarding Stripe events to B2C Service...$(NC)"
	stripe listen --forward-to localhost:8002/api/b2c/billing/webhooks/stripe
