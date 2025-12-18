.PHONY: help setup status up down restart build logs ps migrate migrate-b2b migrate-b2c db-shell reset-db platform-seed platform-create-admin b2b-seed web-b2b web-b2c web-platform web-all up-backend dev-b2b dev-b2c dev-platform shell clean clean-all test-api test-browser test test-env email-ui

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

up: ## Start all backend services (frontend runs locally)
	@echo "$(BLUE)Starting backend services...$(NC)"
	docker-compose up -d postgres b2b-api platform-api b2c-api domain-api dbmigrate redis b2b-worker b2c-worker nginx mailhog
	@echo "$(GREEN)✓ Backend services started$(NC)"
	@echo "API Gateway:  http://localhost:8080"
	@echo "Email UI:     http://localhost:8025 (Mailhog)"
	@echo "Run 'make web-b2b' for B2B frontend on port 3000"

down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down
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
	docker-compose logs -f b2b-api platform-api b2c-api domain-api b2c-worker nginx
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
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_password=\$$DB_PASSWORD -c saas.app_db_user=\$$DB_USER\"; psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB -f /app/scripts/init_auth_db.sql"
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_user=\$$DB_USER\"; psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB -f /app/scripts/grant_permissions.sql"
	@echo "$(GREEN)✓ Auth setup complete$(NC)"

migrate: ## Run migrations for all products (platform + b2b + b2c)
	@echo "$(BLUE)Running database migrations (all products)...$(NC)"
	@docker-compose run --rm dbmigrate env ENABLED_PRODUCTS=platform,b2b,b2c python /app/migrations/run_migrations.py
	@$(MAKE) b2b-seed-roles-templates
	@$(MAKE) b2b-seed-plans
	@$(MAKE) b2c-seed-plans
	@$(MAKE) db-setup-auth
	@echo "$(GREEN)✓ Migrations complete$(NC)"

migrate-b2b: ## Run migrations for B2B only (platform + b2b)
	@echo "$(BLUE)Running B2B migrations...$(NC)"
	@docker-compose run --rm dbmigrate env ENABLED_PRODUCTS=platform,b2b python /app/migrations/run_migrations.py
	@$(MAKE) b2b-seed-roles-templates
	@$(MAKE) db-setup-auth
	@echo "$(GREEN)✓ B2B migrations complete$(NC)"

migrate-b2c: ## Run migrations for B2C only (platform + b2c)
	@echo "$(BLUE)Running B2C migrations...$(NC)"
	@docker-compose run --rm dbmigrate env ENABLED_PRODUCTS=platform,b2c python /app/migrations/run_migrations.py
	@$(MAKE) db-setup-auth
	@echo "$(GREEN)✓ B2C migrations complete$(NC)"

reset-db: ## Reset database (WARNING: deletes all data!)
	@echo "$(YELLOW)⚠ This will delete all data!$(NC)"
	@printf "Are you sure? [y/N] "; \
	read REPLY; \
	case "$$REPLY" in \
		[Yy]*) \
			docker-compose down -v; \
			docker-compose up -d postgres platform-api b2b-api b2c-api domain-api dbmigrate b2b-worker b2c-worker nginx mailhog; \
			sleep 5; \
			$(MAKE) migrate; \
			docker-compose restart postgres; \
			sleep 5; \
			docker-compose restart platform-api b2b-api b2c-api domain-api nginx mailhog; \
			echo "$(GREEN)✓ Database reset complete$(NC)"; \
			;; \
		*) echo "Cancelled."; ;; \
	esac

platform-seed: ## Seed System Tenant (Platform)
	@echo "$(BLUE)Seeding System Tenant...$(NC)"
	@docker-compose exec -T platform-api python /app/scripts/platform/seed_system_tenant.py

platform-create-admin: ## Create Platform Admin User
	@echo "$(BLUE)Creating Platform Admin User...$(NC)"
	@docker-compose exec -T platform-api python /app/scripts/platform/create_platform_admin.py

b2b-seed-roles-templates: ## Seed domain-specific roles-templates
	@echo "$(BLUE)Seeding domain data...$(NC)"
	@docker-compose run --rm b2b-api python /app/scripts/b2b/seed_domain_data.py
	@echo "$(GREEN)✓ Domain data seeded$(NC)"

b2c-seed-plans: ## Seed B2C subscription plans
	@echo "$(BLUE)Seeding B2C subscription plans...$(NC)"
	@docker-compose exec -T b2c-api python /app/scripts/b2c/seed_subscription_plans.py
	@echo "$(GREEN)✓ B2C plans seeded$(NC)"

b2b-seed-plans: ## Seed B2B subscription plans
	@echo "$(BLUE)Seeding B2B subscription plans...$(NC)"
	@docker-compose exec -T b2b-api python /app/scripts/b2b/seed_b2b_plans.py
	@echo "$(GREEN)✓ B2B plans seeded$(NC)"

b2b-invite: ## Invite B2B Tenant (interactive)
	@echo "$(BLUE)=== SaaS Admin Console - B2B Tenant Setup ===$(NC)"
	@docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_onboard.py create-local

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

##@ Development

up-backend: ## Start only backend services
	@echo "$(BLUE)Starting backend services...$(NC)"
	docker-compose up -d postgres b2b-api platform-api b2c-api domain-api nginx
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
	@echo "Available services: b2b-api, platform-api, b2c-api, domain-api, postgres"
endif

clean: ## Clean up containers, volumes, and build artifacts
	@echo "$(BLUE)Cleaning up...$(NC)"
	docker-compose down -v
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


test-browser: ## Run E2E browser tests
	@echo "$(BLUE)Running E2E browser tests...$(NC)"
	docker-compose up -d
	@sleep 10
	docker-compose run --rm e2e-tests pytest tests/e2e_browser/ -v
	@echo "$(GREEN)✓ E2E browser tests complete$(NC)"

test: ## Run all tests
	@$(MAKE) test-api
	@$(MAKE) test-browser

test-coverage: ## Run tests with code coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	docker-compose run --rm e2e-tests pytest tests/e2e_api/ -v --cov=services --cov=core --cov-report=term-missing --cov-report=html:coverage_html
	@echo "$(GREEN)✓ Coverage report generated in backend/coverage_html/$(NC)"

test-coverage-xml: ## Run tests with coverage (XML for CI)
	@echo "$(BLUE)Running tests with coverage (XML)...$(NC)"
	docker-compose run --rm e2e-tests pytest tests/e2e_api/ -v --cov=services --cov=core --cov-report=xml:coverage.xml
	@echo "$(GREEN)✓ Coverage XML generated$(NC)"

test-env: ## Validate environment configuration
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	@for file in .env backend/.env frontend/.env secrets/firebase-credentials.json; do \
		if [ -f $$file ]; then echo "$(GREEN)✓ $$file exists$(NC)"; \
		else echo "$(YELLOW)✗ $$file missing$(NC)"; fi \
	done
