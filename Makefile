.PHONY: help setup status up down restart build logs ps migrate b2b-migrate b2c-migrate db-shell reset-db platform-seed-system platform-seed-permissions platform-create-admin b2b-seed-roles b2b-seed-plans b2b-invite b2b-resend-invite b2c-seed-plans web-b2b web-b2c web-platform web-all up-backend dev-b2b dev-b2c dev-platform shell clean clean-all test-api test-domain-rag test-browser test test-env email-ui stripe-listen-b2b stripe-listen-b2c sast-scan sast-scan-python sast-scan-react sast-scan-containers security-update-npm dast-scan dast-scan-b2b dast-scan-platform dast-scan-b2c dast-scan-domain dast-scan-full



# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo "$(BLUE)Enterprise SSO - Development Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Installation

setup: ## Initial project setup (create .env files, install dependencies)
	@echo "$(BLUE)Setting up project...$(NC)"
	@for file in .env backend/.env frontend/.env; do \
		if [ ! -f $$file ]; then \
			cp $${file}.example $$file; \
			echo "$(GREEN)✓ Created $$file from template$(NC)"; \
		else \
			echo "$(YELLOW)✓ $$file already exists$(NC)"; \
		fi \
	done
	@if [ ! -f secrets/firebase-credentials.json ]; then \
		echo "$(YELLOW)⚠ Missing secrets/firebase-credentials.json (see secrets/README.md)$(NC)"; \
	fi
	@if [ ! -d "frontend/node_modules" ]; then cd frontend && npm install; fi
	@echo "$(GREEN)✓ Setup complete!$(NC)"

status: ## Show status of all services and configuration
	@echo "$(BLUE)=== Service Status ===$(NC)"
	@$(MAKE) ps
	@echo ""
	@echo "$(BLUE)=== Environment Files ===$(NC)"
	@$(MAKE) test-env

##@ Docker Services

db-recreate: ## Fast Database Reset (Drop DB -> Create DB). Uses POSTGRES_USER/DB from env (defaults: postgres/saas_demo_db)
	@echo "$(BLUE)Recreating database (Drop & Create)...$(NC)"
	@docker-compose up -d postgres
	@sleep 2
	@docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-postgres} postgres dropdb -U $${POSTGRES_USER:-postgres} --if-exists --force $${POSTGRES_DB:-saas_demo_db}
	@docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-postgres} postgres createdb -U $${POSTGRES_USER:-postgres} $${POSTGRES_DB:-saas_demo_db}
	@echo "$(GREEN)✓ Database recreated$(NC)"
	@$(MAKE) migrate-only
	@echo "$(BLUE)Starting backend API services (required for seeding)...$(NC)"
	@docker-compose up -d b2b-api platform-api b2c-api b2b-domain-api b2c-domain-api b2b-worker b2c-worker b2b-domain-worker b2c-domain-worker
	@echo "$(GREEN)✓ Backend services started$(NC)"
	@echo ""
	@echo "$(BLUE)=== Running Services ===$(NC)"
	@docker-compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
	@echo ""

setup-bank: ## Reset DB & Seed Bank Surveillance (Drop -> Migrate -> Seed)
	@$(MAKE) db-recreate
	@$(MAKE) seed-all USE_CASE=bank_surveillance

setup-task: ## Reset DB & Seed Task Management (Drop -> Migrate -> Seed)
	@$(MAKE) db-recreate
	@$(MAKE) seed-all USE_CASE=task_management

test-b2b-bank-full: ## Run ALL B2B tests for Bank Surveillance (Drop -> Migrate -> Test)
	@echo "$(BLUE)Running B2B Bank Surveillance Full Test Coverage...$(NC)"
	@$(MAKE) db-recreate
	@docker-compose run --rm -e USE_CASE=bank_surveillance e2e-tests pytest tests/e2e_api/b2b/core tests/e2e_api/b2b/use_cases/bank_surveillance

test-b2b-task-full: ## Run ALL B2B tests for Task Management (Drop -> Migrate -> Test)
	@echo "$(BLUE)Running B2B Task Management Full Test Coverage...$(NC)"
	@$(MAKE) db-recreate
	@docker-compose run --rm -e USE_CASE=task_management e2e-tests pytest tests/e2e_api/b2b/core tests/e2e_api/b2b/use_cases/task_management

up: ## Start all backend services (frontend runs locally)
	echo "Deleting containers and volumes (full reset)..."
	docker-compose down -v
	docker-compose up -d postgres elasticsearch minio b2b-api platform-api b2c-api b2b-domain-api b2c-domain-api dbmigrate redis b2b-worker b2c-worker b2b-domain-worker b2c-domain-worker nginx mailhog prometheus grafana jaeger
	@echo "$(GREEN)✓ Backend services started$(NC)"
	@echo ""
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
	@echo "Run 'make web-b2b' for B2B frontend on port 3000"

down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down --remove-orphans
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: down up ## Restart all services

build: ## Build/rebuild Docker images
	@echo "$(BLUE)Building images...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)✓ Build complete$(NC)"

logs: ## View logs (usage: make logs [s=service])
ifdef s
	docker-compose logs -f $(s)
else
	docker-compose logs -f b2b-api platform-api b2c-api b2b-domain-api b2c-domain-api b2c-worker b2b-domain-worker b2c-domain-worker nginx
endif

ps: ## List running services
	docker-compose ps

email-ui: ## Open Mailhog email UI in browser
	@echo "$(BLUE)Opening Mailhog at http://localhost:8025$(NC)"
	@xdg-open http://localhost:8025 2>/dev/null || open http://localhost:8025 2>/dev/null || echo "Open http://localhost:8025 in your browser"

##@ Database

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres sh -c "psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB"

db-setup-auth: ## Setup app user and permissions
	@echo "$(BLUE)Setting up application user and permissions...$(NC)"
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_password=\$$DB_PASSWORD -c saas.app_db_user=\$$DB_USER -c saas.app_db_name=\$$POSTGRES_DB\"; psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB -f /app/scripts/init_auth_db.sql"
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_user=\$$DB_USER\"; psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB -f /app/scripts/grant_permissions.sql"
	@echo "$(GREEN)✓ Auth setup complete$(NC)"

migrate-only: ## Run SQL migrations only (no seeds) - requires just postgres
	@echo "$(BLUE)Running database migrations...$(NC)"
	@docker-compose run --rm dbmigrate env ENABLED_PRODUCTS=platform,b2b,b2c python /app/migrations/run_migrations.py
	@$(MAKE) db-setup-auth
	@echo "$(GREEN)✓ Migrations applied$(NC)"

seed-all: ## Run all seed scripts (requires API services running)
	@echo "$(BLUE)Running seed scripts...$(NC)"
	@$(MAKE) platform-seed-permissions
	@$(MAKE) b2b-seed-roles $(if $(USE_CASE),USE_CASE=$(USE_CASE),)
	@$(MAKE) b2b-seed-plans
	@$(MAKE) b2c-seed-plans
	@echo "$(GREEN)✓ Seed scripts complete$(NC)"

migrate: ## Run migrations + seeds for all products (USE_CASE=bank_surveillance|marketing_agency)
	@echo "$(BLUE)Running full database setup (all products)...$(NC)"
	@$(MAKE) migrate-only
	@$(MAKE) seed-all $(if $(USE_CASE),USE_CASE=$(USE_CASE),)
	@echo "$(GREEN)✓ Database setup complete$(NC)"

b2b-migrate: ## Run migrations for B2B only (USE_CASE=bank_surveillance|marketing_agency)
	@echo "$(BLUE)Running B2B migrations...$(NC)"
	@docker-compose run --rm dbmigrate env ENABLED_PRODUCTS=platform,b2b python /app/migrations/run_migrations.py
	@$(MAKE) db-setup-auth
	@$(MAKE) b2b-seed-roles $(if $(USE_CASE),USE_CASE=$(USE_CASE),)
	@$(MAKE) b2b-seed-plans
	@echo "$(GREEN)✓ B2B migrations complete$(NC)"

b2c-migrate: ## Run migrations for B2C only (platform + b2c)
	@echo "$(BLUE)Running B2C migrations...$(NC)"
	@docker-compose run --rm dbmigrate env ENABLED_PRODUCTS=platform,b2c python /app/migrations/run_migrations.py
	@$(MAKE) db-setup-auth
	@$(MAKE) b2c-seed-plans
	@echo "$(GREEN)✓ B2C migrations complete$(NC)"

reset-db: ## Reset database (WARNING: deletes all data!)
	@echo "$(YELLOW)⚠ This will delete all data!$(NC)"
	@printf "Are you sure? [y/N] "; \
	read REPLY; \
	case "$$REPLY" in \
		[Yy]*) \
			docker-compose down -v --remove-orphans; \
			echo "$(BLUE)Starting database...$(NC)"; \
			docker-compose up -d postgres; \
			echo "$(BLUE)Waiting for database to be ready...$(NC)"; \
			sleep 5; \
			$(MAKE) migrate-only; \
			echo "$(BLUE)Starting API services...$(NC)"; \
			docker-compose up -d platform-api b2b-api b2c-api b2b-domain-api b2c-domain-api dbmigrate b2b-worker b2c-worker b2b-domain-worker b2c-domain-worker nginx mailhog; \
			echo "$(BLUE)Waiting for services to be ready...$(NC)"; \
			sleep 10; \
			$(MAKE) seed-all $(if $(USE_CASE),USE_CASE=$(USE_CASE),); \
			echo "$(GREEN)✓ Database reset complete$(NC)"; \
			$(MAKE) stop-web-all; \
			;; \
		*) echo "Cancelled."; ;; \
	esac

platform-seed-system: ## Seed System Tenant (Platform)
	@echo "$(BLUE)Seeding System Tenant...$(NC)"
	@docker-compose exec -T platform-api python /app/scripts/platform/seed_system_tenant.py

platform-seed-permissions: ## Seed platform permissions
	docker-compose exec -T platform-api python /app/scripts/platform/seed_platform_permissions.py

platform-create-admin: ## Create Platform Admin User
	@echo "$(BLUE)Creating Platform Admin User...$(NC)"
	@docker-compose exec -T platform-api python /app/scripts/platform/create_platform_admin.py

b2b-seed-roles: ## Seed RBAC roles and resources (USE_CASE=bank_surveillance|marketing_agency|task_management)
	@echo "$(BLUE)Seeding RBAC data...$(NC)"
	@if [ -n "$(USE_CASE)" ]; then \
		echo "$(YELLOW)Loading use case: $(USE_CASE)$(NC)"; \
		docker-compose run --rm b2b-api env USE_CASE=$(USE_CASE) python /app/scripts/b2b/seed_rbac.py; \
	else \
		docker-compose run --rm b2b-api python /app/scripts/b2b/seed_rbac.py; \
	fi
	@echo "$(GREEN)✓ RBAC data seeded$(NC)"

b2b-seed-plans: ## Seed B2B subscription plans
	@echo "$(BLUE)Seeding B2B subscription plans...$(NC)"
	@docker-compose exec -T b2b-api python /app/scripts/b2b/seed_subscription_plans.py
	@echo "$(GREEN)✓ B2B plans seeded$(NC)"

b2c-seed-plans: ## Seed B2C subscription plans
	@echo "$(BLUE)Seeding B2C subscription plans...$(NC)"
	@docker-compose exec -T b2c-api python /app/scripts/b2c/seed_subscription_plans.py
	@echo "$(GREEN)✓ B2C plans seeded$(NC)"

verify-seed: ## Verify B2B seed data completed successfully
	@echo "$(BLUE)Verifying seed data...$(NC)"
	@docker-compose exec -T b2b-api python /app/scripts/b2b/verify_seed.py

b2b-invite: ## Invite B2B Tenant (f=file.json [PLUGINS=p1,p2])
	@echo "$(BLUE)=== SaaS Admin Console - B2B Tenant Setup ===$(NC)"
	@docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_onboard.py create-local \
		--file $(or $(f),scripts/b2b/use_cases/task_management/task_management_demo.json) \
		$(if $(PLUGINS),--plugins $(PLUGINS),)

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

b2b-invite-bank: ## Invite Bank Tenant (Shortcut)
	@$(MAKE) b2b-invite f=scripts/b2b/use_cases/bank_surveillance/bank_surveillance_demo.json

b2b-invite-marketing: ## Invite Marketing Tenant (Shortcut)
	@$(MAKE) b2b-invite f=scripts/b2b/use_cases/marketing_agency/marketing_agency_demo.json

b2b-invite-task: ## Invite Task Management Tenant (Shortcut)
	@$(MAKE) b2b-invite f=scripts/b2b/use_cases/task_management/task_management_demo.json

b2b-update-plugin-bank: ## Update Bank Tenant Plugins from Config
	@echo "$(BLUE)Updating Bank Tenant Config...$(NC)"
	@docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_onboard.py manage-plugins --file scripts/b2b/use_cases/bank_surveillance/bank_surveillance_demo.json

b2b-update-plugin-marketing: ## Update Marketing Tenant Plugins from Config
	@echo "$(BLUE)Updating Marketing Tenant Config...$(NC)"
	@docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_onboard.py manage-plugins --file scripts/b2b/use_cases/marketing_agency/marketing_agency_demo.json

b2b-update-plugin-task: ## Update Task Tenant Plugins from Config
	@echo "$(BLUE)Updating Task Management Tenant Config...$(NC)"
	@docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_onboard.py manage-plugins --file scripts/b2b/use_cases/task_management/task_management_demo.json

##@ B2B Demos

b2b-demo-bank: ## Reset DB and seed bank surveillance RBAC (then create tenant via UI)
	@echo "$(BLUE)🏦 Resetting DB for Bank Surveillance Demo...$(NC)"
	@$(MAKE) setup-bank
	@$(MAKE) verify-seed
	@echo ""
	@echo "$(GREEN)✅ Bank Surveillance RBAC Ready!$(NC)"
	@echo "  📋 Resources: communications, investigations, alerts, surveillance_reports"
	@echo "  👥 Roles: surveillance_lead (STL), surveillance_analyst (SA), operations_maker, operations_checker, compliance_officer (LCO), guest_analyst"
	@echo ""
	@echo "$(YELLOW)Next: Create demo tenant + owner user:$(NC)"
	@echo "  make b2b-invite-bank"
	@echo ""
	@echo "$(BLUE)Then login as:$(NC) owner@worldwidebank.com and invite users via UI"

b2b-demo-marketing: ## Reset DB and seed marketing agency RBAC (then create tenant via UI)
	@echo "$(BLUE)📱 Resetting DB for Marketing Agency Demo...$(NC)"
	@$(MAKE) db-recreate
	@$(MAKE) seed-all USE_CASE=marketing_agency
	@$(MAKE) verify-seed
	@echo ""
	@echo "$(GREEN)✅ Marketing Agency RBAC Ready!$(NC)"
	@echo "  📋 Resources: campaigns, social_posts, creative_assets, analytics_reports, client_communications"
	@echo "  👥 Roles: agency_owner, account_director, account_manager, creative_lead, specialist"
	@echo ""
	@echo "$(YELLOW)Next: Create demo tenant + owner user:$(NC)"
	@echo "  make b2b-invite-marketing"
	@echo ""
	@echo "$(BLUE)Then login as:$(NC) owner@merlionmarketing.com and invite users via UI"

b2b-demo-task: ## Reset DB and seed task management RBAC (then create tenant via UI)
	@echo "$(BLUE)✅ Resetting DB for Task Management Demo...$(NC)"
	@$(MAKE) setup-task
	@$(MAKE) verify-seed
	@echo ""
	@echo "$(GREEN)✅ Task Management RBAC Ready!$(NC)"
	@echo "  📋 Resources: projects, tasks, comments, rag_documents"
	@echo "  👥 Roles: owner, admin, member, viewer (base roles)"
	@echo ""
	@echo "$(YELLOW)Next: Create demo tenant + owner user:$(NC)"
	@echo "  make b2b-invite-task"
	@echo ""
	@echo "$(BLUE)Then login as tenant owner and invite users via UI$(NC)"

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

web-all: ## Build all portals for production
	cd frontend && npm run build:all

stop-web-all:
	docker-compose stop frontend-b2c frontend-b2b frontend-platform || true

##@ Development

up-backend: ## Start only backend services
	@echo "$(BLUE)Starting backend services...$(NC)"
	docker-compose up -d postgres b2b-api platform-api b2c-api b2b-domain-api b2c-domain-api b2b-worker b2c-worker b2b-domain-worker b2c-domain-worker nginx
	@echo "$(GREEN)✓ Backend services started$(NC)"

dev-b2b: ## Start dev env: backend + B2B frontend (port 3000)
	@$(MAKE) up-backend
	@sleep 3
	@echo "$(BLUE)Backend started, starting B2B frontend...$(NC)"
	@$(MAKE) web-b2b

dev-b2c: ## Start dev env: backend + B2C frontend (port 3001)
	@$(MAKE) up-backend
	@sleep 3
	@echo "$(BLUE)Backend started, starting B2C frontend...$(NC)"
	@$(MAKE) web-b2c

dev-platform: ## Start dev env: backend + Platform frontend (port 3002)
	@$(MAKE) up-backend
	@sleep 3
	@echo "$(BLUE)Backend started, starting Platform frontend...$(NC)"
	@$(MAKE) web-platform

shell: ## Open shell (usage: make shell s=b2b-api)
ifdef s
	docker-compose exec $(s) /bin/bash
else
	@echo "$(YELLOW)Usage: make shell s=<service_name>$(NC)"
	@echo "Available services: b2b-api, platform-api, b2c-api, b2b-domain-api, b2c-domain-api, postgres"
endif

clean: ## Clean up containers, volumes, and build artifacts
	@echo "$(BLUE)Cleaning up...$(NC)"
	docker-compose down -v --remove-orphans
	rm -rf frontend/node_modules/.cache
	rm -rf frontend/dist
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-all: clean ## Complete cleanup including node_modules
	rm -rf frontend/node_modules

##@ Testing

test-api: ## Run all API integration tests
	@echo "$(BLUE)Running API integration tests...$(NC)"
	docker-compose run --rm e2e-tests pytest -n auto tests/e2e_api/ -v
	@echo "$(GREEN)✓ API tests complete$(NC)"

test-domain-rag: ## Run Finance Trader RAG domain integration tests
	@echo "$(BLUE)Running Finance Trader RAG domain tests...$(NC)"
	docker-compose run --rm e2e-tests pytest tests/e2e_api/b2c/use_cases/finance_trader/ -v
	@echo "$(GREEN)✓ Finance Trader RAG domain tests complete$(NC)"

test-b2b: ## Run ALL B2B tests (Combines Core+Bank and Core+Task)
	@echo "$(BLUE)Running ALL B2B Tests...$(NC)"
	@$(MAKE) test-b2b-bank-full
	@$(MAKE) test-b2b-task-full
	@echo "$(GREEN)✓ ALL B2B Tests Complete$(NC)"



# Individual Component Helpers
test-b2b-core: ## Run core platform tests only (defaults to bank seed)
	docker-compose run --rm e2e-tests pytest tests/e2e_api/b2b/core -v

test-b2b-bank: ## Run bank surveillance specific tests only
	docker-compose run --rm e2e-tests env USE_CASE=bank_surveillance pytest tests/e2e_api/b2b/use_cases/bank_surveillance -v

test-b2b-task: ## Run task management tests only
	docker-compose run --rm e2e-tests env USE_CASE=task_management pytest tests/e2e_api/b2b/use_cases/task_management -v

test-b2b-core-only: ## Run core platform tests with base roles only
	@echo "$(BLUE)Running Core Platform Tests (base roles only)...$(NC)"
	@echo "$(YELLOW)Resetting database and seeding base layer...$(NC)"
	@$(MAKE) reset-db
	@docker-compose run --rm dbmigrate env ENABLED_PRODUCTS=platform,b2b python /app/migrations/run_migrations.py
	@$(MAKE) db-setup-auth
	@docker-compose run --rm b2b-api python scripts/b2b/seed_rbac.py
	@docker-compose run --rm b2b-api python scripts/b2b/seed_subscription_plans.py
	@echo "$(YELLOW)Running core tests...$(NC)"
	@docker-compose run --rm e2e-tests pytest tests/e2e_api/b2b/core/ -v
	@echo "$(GREEN)✓ Core platform tests complete$(NC)"

test-b2b-bank-use-case: ## Run bank surveillance tests (core + domain with base + bank roles)
	@echo "$(BLUE)Running Bank Surveillance Use Case Tests...$(NC)"
	@echo "$(YELLOW)Resetting database and seeding base + bank roles...$(NC)"
	@$(MAKE) reset-db
	@docker-compose run --rm dbmigrate env ENABLED_PRODUCTS=platform,b2b python /app/migrations/run_migrations.py
	@$(MAKE) db-setup-auth
	@docker-compose run -e USE_CASE=bank_surveillance -e INCLUDE_BASE_ROLES=true --rm b2b-api python scripts/b2b/seed_rbac.py
	@docker-compose run --rm b2b-api python scripts/b2b/seed_subscription_plans.py
	@echo "$(YELLOW)Running core + bank surveillance tests...$(NC)"
	@docker-compose run -e USE_CASE=bank_surveillance --rm e2e-tests pytest tests/e2e_api/b2b/core/ tests/e2e_api/b2b/use_cases/bank_surveillance/ -v
	@echo "$(GREEN)✓ Bank surveillance tests complete$(NC)"

test-b2b-all-new: ## Run complete B2B test suite (core + all use cases)
	@echo "$(BLUE)Running Full B2B Test Suite...$(NC)"
	@$(MAKE) test-b2b-core-only
	@$(MAKE) test-b2b-bank-use-case
	@echo "$(GREEN)✓ Full B2B test suite complete$(NC)"


# Test Runner Config
ifdef LOCAL
TEST_CMD := cd backend && pytest
PROVISION_BACKEND := docker-compose up -d postgres b2b-api platform-api b2c-api b2b-domain-api b2c-domain-api nginx
else
TEST_CMD := docker-compose run --rm e2e-tests pytest
PROVISION_BACKEND := docker-compose up -d
endif

test-browser: ## Run E2E browser tests (Use LOCAL=1 to run locally)
	@echo "$(BLUE)Running E2E browser tests...$(NC)"
	@if [ "$(HEADED)" = "1" ] && [ -z "$(LOCAL)" ]; then \
		echo "$(YELLOW)Note: Running in HEADED mode requires X11 forwarding for Docker.$(NC)"; \
	fi
	$(PROVISION_BACKEND)
	@if [ -z "$(LOCAL)" ]; then sleep 10; else sleep 3; fi
	$(TEST_CMD) tests/e2e_browser/ $(if $(filter 1,$(HEADED)),--headed,) $(if $(filter 1,$(SLOW)),--slowmo 2000,) $(ARGS) -v
	@echo "$(GREEN)✓ E2E browser tests complete$(NC)"

test-browser-b2c: ## Run B2C E2E browser tests (usage: make test-browser-b2c TEST_PATH=tests/e2e_browser/b2c/test_file.py)
	@echo "$(BLUE)Running B2C E2E tests...$(NC)"
	@echo "$(YELLOW)Starting frontend containers for E2E tests...$(NC)"
	docker-compose --profile e2e up -d frontend-b2c
	$(PROVISION_BACKEND)
	@if [ -z "$(LOCAL)" ]; then sleep 5; else sleep 3; fi
	$(TEST_CMD) $(if $(TEST_PATH),$(TEST_PATH),tests/e2e_browser/b2c/) $(if $(filter 1,$(HEADED)),--headed,) $(if $(filter 1,$(SLOW)),--slowmo 2000,) $(ARGS) -v || (docker-compose stop frontend-b2c && exit 1)
	docker-compose stop frontend-b2c

test-browser-b2b: ## Run B2B E2E browser tests (usage: make test-browser-b2b TEST_PATH=tests/e2e_browser/b2b/test_file.py)
	@echo "$(BLUE)Running B2B E2E tests...$(NC)"
	@echo "$(YELLOW)Starting frontend containers for E2E tests...$(NC)"
	docker-compose --profile e2e up -d frontend-b2b
	$(PROVISION_BACKEND)
	@if [ -z "$(LOCAL)" ]; then sleep 5; else sleep 3; fi
	$(TEST_CMD) $(if $(TEST_PATH),$(TEST_PATH),tests/e2e_browser/b2b/) $(if $(filter 1,$(HEADED)),--headed,) $(if $(filter 1,$(SLOW)),--slowmo 2000,) $(ARGS) -v || (docker-compose stop frontend-b2b && exit 1)
	docker-compose stop frontend-b2b

test-browser-platform: ## Run Platform E2E browser tests
	@echo "$(BLUE)Running Platform E2E tests...$(NC)"
	@echo "$(YELLOW)Starting frontend containers for E2E tests...$(NC)"
	docker-compose --profile e2e up -d frontend-platform
	$(PROVISION_BACKEND)
	@if [ -z "$(LOCAL)" ]; then sleep 5; else sleep 3; fi
	$(TEST_CMD) tests/e2e_browser/platform/ $(if $(filter 1,$(HEADED)),--headed,) $(if $(filter 1,$(SLOW)),--slowmo 2000,) $(ARGS) -v || (docker-compose stop frontend-platform && exit 1)
	docker-compose stop frontend-platform

local-test-browser-b2b: ## Run B2B browser tests locally with venv (headed)
	cd backend && .venv/bin/pytest tests/e2e_browser/b2b/ --headed -v

local-test-browser-b2c: ## Run B2C browser tests locally with venv (headed)
	cd backend && .venv/bin/pytest tests/e2e_browser/b2c/ --headed -v

local-test-browser-platform: ## Run Platform browser tests locally with venv (headed)
	cd backend && .venv/bin/pytest tests/e2e_browser/platform/ --headed -v

test: ## Run all tests
	@$(MAKE) test-api
	@$(MAKE) test-browser

test-coverage: ## Run tests with code coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	docker-compose run --rm e2e-tests pytest tests/e2e_api/ -v --cov=modules --cov=core --cov-report=term-missing --cov-report=html:coverage_html
	@echo "$(GREEN)✓ Coverage report generated in backend/coverage_html/$(NC)"

test-coverage-xml: ## Run tests with coverage (XML for CI)
	@echo "$(BLUE)Running tests with coverage (XML)...$(NC)"
	docker-compose run --rm e2e-tests pytest tests/e2e_api/ -v --cov=modules --cov=core --cov-report=xml:coverage.xml
	@echo "$(GREEN)✓ Coverage XML generated$(NC)"

test-env: ## Validate environment configuration
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	@for file in .env backend/.env frontend/.env secrets/firebase-credentials.json; do \
		if [ -f $$file ]; then echo "$(GREEN)✓ $$file exists$(NC)"; \
		else echo "$(YELLOW)✗ $$file missing$(NC)"; fi \
	done

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

eval-run: ## Run RAG experiment (Usage: make eval-run CONFIG=scripts/evaluation/projects/nse/experiment_v1.yaml)
		@echo "$(BLUE)Running Experiment with config: $(CONFIG)$(NC)"
		@if [ -z "$(CONFIG)" ]; then echo "Error: CONFIG argument is required"; exit 1; fi
		docker-compose run --rm e2e-tests python3 -m scripts.evaluation.core.runner --config $(CONFIG) $(ARGS)
