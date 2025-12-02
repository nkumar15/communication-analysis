.PHONY: help setup status up down restart build logs logs-b2b logs-platform logs-b2c logs-domain logs-all ps migrate db-shell reset-db platform-seed platform-create-admin b2b-seed frontend-install frontend-start frontend-build up-backend dev shell-b2b shell-platform shell-b2c shell-domain clean clean-all test-api test-platform-api test-b2b-api test-core-api test-browser test-all test-env

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
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ Created .env from template$(NC)"; \
		echo "$(YELLOW)⚠ Please edit .env with your configuration$(NC)"; \
	else \
		echo "$(YELLOW)✓ .env already exists$(NC)"; \
	fi
	@if [ ! -f backend/.env ]; then \
		cp backend/.env.example backend/.env; \
		echo "$(GREEN)✓ Created backend/.env from template$(NC)"; \
		echo "$(YELLOW)⚠ Please edit backend/.env with your configuration$(NC)"; \
	else \
		echo "$(YELLOW)✓ backend/.env already exists$(NC)"; \
	fi
	@if [ ! -f frontend/.env ]; then \
		cp frontend/.env.example frontend/.env; \
		echo "$(GREEN)✓ Created frontend/.env from template$(NC)"; \
		echo "$(YELLOW)⚠ Please edit frontend/.env with your Firebase config$(NC)"; \
	else \
		echo "$(YELLOW)✓ frontend/.env already exists$(NC)"; \
	fi
	@if [ ! -f secrets/firebase-credentials.json ]; then \
		echo "$(YELLOW)⚠ Please download Firebase credentials to secrets/firebase-credentials.json$(NC)"; \
		echo "$(YELLOW)  See secrets/README.md for instructions$(NC)"; \
	else \
		echo "$(GREEN)✓ Firebase credentials found$(NC)"; \
	fi
	@$(MAKE) frontend-install
	@echo "$(GREEN)✓ Setup complete!$(NC)"
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Edit .env, backend/.env, and frontend/.env"
	@echo "  2. Set REACT_APP_API_URL and REACT_APP_PLATFORM_API_URL in frontend/.env"
	@echo "  3. Place Firebase credentials in secrets/firebase-credentials.json"
	@echo "  4. Run 'make up' to start services (or 'make dev' for local frontend)"

status: ## Show status of all services and configuration
	@echo "$(BLUE)=== Service Status ===$(NC)"
	@$(MAKE) ps
	@echo ""
	@echo "$(BLUE)=== Environment Files ===$(NC)"
	@$(MAKE) test-env
	@echo ""
	@echo "$(BLUE)=== URLs ===$(NC)"
	@echo "Frontend:       http://localhost:3000"
	@echo "B2B API:        http://localhost:8000/docs"
	@echo "Platform API:   http://localhost:8001/docs"
	@echo "B2C API:        http://localhost:8002/docs"
	@echo "Domain API:     http://localhost:8003/docs"
	@echo "PostgreSQL:     localhost:5432"

##@ Docker Services

up: ## Start all services (Postgres + Backend)
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "Frontend:     http://localhost:3000"
	@echo "B2B API:      http://localhost:8000/docs"
	@echo "Platform API: http://localhost:8001/docs"
	@echo "B2C API:      http://localhost:8002/docs"
	@echo "Domain API:   http://localhost:8003/docs"

down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: down up ## Restart all services

build: ## Build/rebuild Docker images
	@echo "$(BLUE)Building images...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)✓ Build complete$(NC)"

logs: ## View all backend API logs (follow mode)
	docker-compose logs -f b2b-api platform-api b2c-api domain-api

logs-b2b: ## View B2B API logs
	docker-compose logs -f b2b-api

logs-platform: ## View Platform API logs
	docker-compose logs -f platform-api

logs-b2c: ## View B2C API logs
	docker-compose logs -f b2c-api

logs-domain: ## View Domain API logs
	docker-compose logs -f domain-api

logs-all: ## View all service logs (follow mode)
	docker-compose logs -f

ps: ## List running services
	docker-compose ps


##@ Database

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	@docker-compose exec platform-api python /app/migrations/run_migrations.py
	@echo "$(GREEN)✓ Migrations complete$(NC)"


db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U sso_user -d sso_db

reset-db: ## Reset database (WARNING: deletes all data!)
	@echo "$(YELLOW)⚠ This will delete all data!$(NC)"
	@printf "Are you sure? [y/N] "; \
	read REPLY; \
	case "$$REPLY" in \
		[Yy]*) \
			docker-compose down -v; \
			docker-compose up -d postgres; \
			docker-compose up -d platform-api; \
# 			docker-compose up -d b2b-api; \
# 			docker-compose up -d b2c-api; \
# 			docker-compose up -d frontend; \
# 			docker-compose up -d e2e-tests; \
			sleep 5; \
			$(MAKE) migrate; \
			echo "$(GREEN)✓ Database reset complete$(NC)"; \
			;; \
		*) \
			echo "Cancelled."; \
			;; \
	esac


platform-seed: ## Seed System Tenant (Platform)
	@echo "$(BLUE)Seeding System Tenant...$(NC)"
	@docker-compose exec platform-api python /app/scripts/platform/seed_system_tenant.py

platform-create-admin: ## Create Platform Admin User
	@echo "$(BLUE)Creating Platform Admin User...$(NC)"
	@docker-compose exec platform-api python /app/scripts/platform/create_platform_admin.py

b2b-seed-roles-templates: ## Seed domain-specific roles-templates
	@echo "$(BLUE)Seeding domain data...$(NC)"
	@docker-compose run --rm b2b-api python /app/scripts/b2b/seed_domain_data.py
	@echo "$(GREEN)✓ Domain data seeded$(NC)"

b2b-invite: ## Invite B2B Tenant (interactive)
	@echo "$(BLUE)=== SaaS Admin Console - B2B Tenant Setup ===$(NC)"
	@docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_onboard.py create-local

##@ Frontend

frontend-install: ## Install frontend dependencies (locally)
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd frontend && npm install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

frontend-start: ## Start frontend dev server
	@echo "$(BLUE)Starting frontend...$(NC)"
	cd frontend && npm start

frontend-build: ## Build frontend for production
	@echo "$(BLUE)Building frontend...$(NC)"
	cd frontend && npm run build
	@echo "$(GREEN)✓ Frontend build complete$(NC)"

##@ Development

up-backend: ## Start only backend services (for local frontend dev)
	@echo "$(BLUE)Starting backend services...$(NC)"
	docker-compose up -d postgres b2b-api platform-api b2c-api domain-api
	@echo "$(GREEN)✓ Backend services started$(NC)"

dev: ## Start full development environment (backend docker + frontend local)
	@echo "$(BLUE)Starting development environment...$(NC)"
	@$(MAKE) up-backend
	@sleep 3
	@echo "$(BLUE)Backend started, now starting frontend...$(NC)"
	@$(MAKE) frontend-start

shell-b2b: ## Open shell in B2B API container
	docker-compose exec b2b-api /bin/bash

shell-platform: ## Open shell in Platform API container
	docker-compose exec platform-api /bin/bash

shell-b2c: ## Open shell in B2C API container
	docker-compose exec b2c-api /bin/bash

shell-domain: ## Open shell in Domain API container
	docker-compose exec domain-api /bin/bash

clean: ## Clean up containers, volumes, and build artifacts
	@echo "$(BLUE)Cleaning up...$(NC)"
	docker-compose down -v
	rm -rf frontend/node_modules/.cache
	rm -rf frontend/dist
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-all: clean ## Complete cleanup including node_modules
	@echo "$(BLUE)Removing node_modules...$(NC)"
	rm -rf frontend/node_modules
	@echo "$(GREEN)✓ Complete cleanup done$(NC)"

##@ Testing & Validation

test-api: ## Run all API integration tests
	@echo "$(BLUE)Running API integration tests...$(NC)"
	docker-compose run --rm e2e-tests pytest tests/e2e_api/ -v
	@echo "$(GREEN)✓ API tests complete$(NC)"

test-platform-api: ## Run Platform API tests
	@echo "$(BLUE)Running Platform API tests...$(NC)"
	docker-compose run --rm e2e-tests pytest tests/e2e_api/platform/ -v

test-b2b-api: ## Run B2B API tests
	@echo "$(BLUE)Running B2B API tests...$(NC)"
	docker-compose run --rm e2e-tests pytest tests/e2e_api/b2b/ -v

test-core-api: ## Run Core API tests
	@echo "$(BLUE)Running Core API tests...$(NC)"
	docker-compose run --rm e2e-tests pytest tests/e2e_api/core/ -v

test-browser: ## Run E2E browser tests
	@echo "$(BLUE)Running E2E browser tests...$(NC)"
	@echo "$(YELLOW)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(YELLOW)Waiting for services to be ready...$(NC)"
	@sleep 10
	docker-compose run --rm e2e-tests pytest tests/e2e_browser/ -v
	@echo "$(GREEN)✓ E2E browser tests complete$(NC)"

test-all: ## Run all tests (API + Browser)
	@echo "$(BLUE)Running all tests...$(NC)"
	@$(MAKE) test-api
	@$(MAKE) test-browser
	@echo "$(GREEN)✓ All tests complete$(NC)"

test-env: ## Validate environment configuration
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	@for file in .env backend/.env frontend/.env secrets/firebase-credentials.json; do \
		if [ -f $$file ]; then \
			echo "$(GREEN)✓ $$file exists$(NC)"; \
		else \
			echo "$(YELLOW)✗ $$file missing$(NC)"; \
		fi \
	done