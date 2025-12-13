.PHONY: help setup status up down restart build logs ps migrate db-shell reset-db platform-seed platform-create-admin b2b-seed frontend-install frontend-start frontend-build up-backend dev shell clean clean-all test-api test-browser test test-env

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
	@$(MAKE) frontend-install
	@echo "$(GREEN)✓ Setup complete!$(NC)"

status: ## Show status of all services and configuration
	@echo "$(BLUE)=== Service Status ===$(NC)"
	@$(MAKE) ps
	@echo ""
	@echo "$(BLUE)=== Environment Files ===$(NC)"
	@$(MAKE) test-env

##@ Docker Services

up: ## Start all services
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "API Gateway:  http://localhost:8080"
	@echo "Frontend:     http://localhost:3000"

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
	docker-compose logs -f b2b-api platform-api b2c-api domain-api nginx
endif

ps: ## List running services
	docker-compose ps

##@ Database

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres sh -c "psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB"

db-setup-auth: ## Setup app user and permissions
	@echo "$(BLUE)Setting up application user and permissions...$(NC)"
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_password=\$$DB_PASSWORD -c saas.app_db_user=\$$DB_USER\"; psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB -f /app/scripts/init_auth_db.sql"
	@docker-compose exec -T postgres sh -c "export PGOPTIONS=\"-c saas.app_db_user=\$$DB_USER\"; psql -U \$$POSTGRES_USER -d \$$POSTGRES_DB -f /app/scripts/grant_permissions.sql"
	@echo "$(GREEN)✓ Auth setup complete$(NC)"

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	@docker-compose exec dbmigrate python /app/migrations/run_migrations.py
	@$(MAKE) b2b-seed-roles-templates
	@$(MAKE) db-setup-auth
	@echo "$(GREEN)✓ Migrations complete$(NC)"

reset-db: ## Reset database (WARNING: deletes all data!)
	@echo "$(YELLOW)⚠ This will delete all data!$(NC)"
	@printf "Are you sure? [y/N] "; \
	read REPLY; \
	case "$$REPLY" in \
		[Yy]*) \
			docker-compose down -v; \
			docker-compose up -d postgres platform-api b2b-api b2c-api frontend dbmigrate nginx; \
			sleep 5; \
			$(MAKE) migrate; \
			docker-compose restart postgres; \
			sleep 5; \
			docker-compose restart platform-api b2b-api b2c-api domain-api; \
			docker-compose restart nginx; \
			docker-compose stop frontend; \
			echo "$(GREEN)✓ Database reset complete$(NC)"; \
			;; \
		*) echo "Cancelled."; ;; \
	esac

platform-seed: ## Seed System Tenant (Platform)
	@echo "$(BLUE)Seeding System Tenant...$(NC)"
	@docker-compose exec platform-api python /app/scripts/platform/seed_system_tenant.py

platform-create-admin: ## Create Platform Admin User
	@echo "$(BLUE)Creating Platform Admin User...$(NC)"
	@docker-compose exec platform-api python /app/scripts/platform/create_platform_admin.py

b2b-seed-roles-templates: ## Seed domain-specific roles-templates
	@echo "$(BLUE)Seeding domain data...$(NC)"
	@docker-compose run --rm dbmigrate python /app/scripts/b2b/seed_domain_data.py
	@echo "$(GREEN)✓ Domain data seeded$(NC)"

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

##@ Frontend

frontend-install: ## Install frontend dependencies (locally)
	cd frontend && npm install

frontend-start: ## Start frontend dev server
	cd frontend && npm start

frontend-build: ## Build frontend for production
	cd frontend && npm run build

##@ Development

up-backend: ## Start only backend services
	@echo "$(BLUE)Starting backend services...$(NC)"
	docker-compose up -d postgres b2b-api platform-api b2c-api domain-api nginx
	@echo "$(GREEN)✓ Backend services started$(NC)"

dev: ## Start full dev env (backend docker + frontend local)
	@$(MAKE) up-backend
	@sleep 3
	@echo "$(BLUE)Backend started, starting frontend...$(NC)"
	@$(MAKE) frontend-start

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
