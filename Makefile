.PHONY: help up down restart logs build migrate shell db-shell clean frontend-install frontend-start frontend-build test seed-system-tenant create-platform-admin setup-saas-admin

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
	@echo "  2. Place Firebase credentials in secrets/firebase-credentials.json"
	@echo "  3. Run 'make up' to start services"

status: ## Show status of all services and configuration
	@echo "$(BLUE)=== Service Status ===$(NC)"
	@$(MAKE) ps
	@echo ""
	@echo "$(BLUE)=== Environment Files ===$(NC)"
	@$(MAKE) test-env
	@echo ""
	@echo "$(BLUE)=== URLs ===$(NC)"
	@echo "Backend API:    http://localhost:8000"
	@echo "API Docs:       http://localhost:8000/docs"
	@echo "Frontend:       http://localhost:3000"
	@echo "PostgreSQL:     localhost:5432"

##@ Docker Services

up: ## Start all services (Postgres + Backend)
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "Backend: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: down up ## Restart all services

build: ## Build/rebuild Docker images
	@echo "$(BLUE)Building images...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)✓ Build complete$(NC)"

logs: ## View backend logs (follow mode)
	docker-compose logs -f backend

logs-all: ## View all service logs (follow mode)
	docker-compose logs -f

ps: ## List running services
	docker-compose ps


##@ Database

migrate: ## Run database migrations
	@echo "Running migrations... "
	docker-compose exec platform-api python /app/migrations/run_migrations.py
	@echo "✓ Migrations complete"

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
			docker-compose up -d b2b-api; \
			docker-compose up -d b2c-api; \
			docker-compose up -d frontend; \
			docker-compose up -d e2e-tests; \
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

b2b-seed: ## Seed B2B Tenant (interactive)
	@echo "$(BLUE)=== SaaS Admin Console - B2B Tenant Setup ===$(NC)"
	@docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_cli.py create-local

##@ Frontend

frontend-install: ## Install frontend dependencies (locally)
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd frontend && npm install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

frontend-install-docker: ## Install frontend dependencies (in Docker)
	@echo "$(BLUE)Installing frontend dependencies in Docker...$(NC)"
	docker-compose run --rm frontend npm install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

frontend-start: ## Start frontend dev server
	@echo "$(BLUE)Starting frontend...$(NC)"
	cd frontend && npm start

frontend-build: ## Build frontend for production
	@echo "$(BLUE)Building frontend...$(NC)"
	cd frontend && npm run build
	@echo "$(GREEN)✓ Frontend build complete$(NC)"

##@ Development

dev: ## Start full development environment (backend + frontend)
	@echo "$(BLUE)Starting development environment...$(NC)"
	@$(MAKE) up
	@sleep 3
	@echo "$(BLUE)Backend started, now starting frontend...$(NC)"
	@$(MAKE) frontend-start

shell: ## Open shell in backend container
	docker-compose exec backend /bin/bash

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

test: ## Run all tests (alias for test-integration)
	@$(MAKE) test-integration

test-api: ## Run all backend integration tests
	docker-compose exec backend pytest tests/e2e_api/

test-platform-api: ## Run Platform tests
	docker-compose exec backend pytest tests/e2e_api/platform/

test-b2b-api: ## Run B2B tests
	docker-compose exec backend pytest tests/e2e_api/b2b/

test-core-api: ## Run Core tests
	docker-compose exec backend pytest tests/e2e_api/core/

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	docker-compose exec backend python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-browser: ## Run E2E browser tests
	@echo "$(BLUE)Running E2E browser tests...$(NC)"
	@echo "$(YELLOW)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(YELLOW)Waiting for services to be ready...$(NC)"
	@sleep 10
	docker-compose run --rm e2e-tests
	@echo "$(GREEN)✓ E2E browser tests complete$(NC)"

test-invitation: ## Run invitation flow tests only
	@echo "$(BLUE)Testing invitation flow...$(NC)"
	docker-compose exec backend python -m pytest tests/b2b/test_invitation_flow.py -v

test-activation: ## Run activation flow tests only
	@echo "$(BLUE)Testing activation flow...$(NC)"
	docker-compose exec backend python -m pytest tests/b2b/test_activation_flow.py -v

test-security: ## Run security tests only
	@echo "$(BLUE)Running security tests...$(NC)"
	docker-compose exec backend python -m pytest tests/platform/test_platform_security.py -v

test-install: ## Install test dependencies in backend container
	@echo "$(BLUE)Installing test dependencies...$(NC)"
	docker-compose exec backend pip install -r requirements-test.txt
	@echo "$(GREEN)✓ Test dependencies installed$(NC)"

test-env: ## Validate environment configuration
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	@for file in .env backend/.env frontend/.env secrets/firebase-credentials.json; do \
		if [ -f $$file ]; then \
			echo "$(GREEN)✓ $$file exists$(NC)"; \
		else \
			echo "$(YELLOW)✗ $$file missing$(NC)"; \
		fi \
	done