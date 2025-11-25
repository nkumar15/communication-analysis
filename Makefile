.PHONY: help up down restart logs build migrate shell db-shell clean frontend-install frontend-start frontend-build test

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
	docker-compose exec backend python app/migrations/run_migrations.py
	@echo "✓ Migrations complete"

tenant-create-local: ## Create a local test tenant (interactive)
	@echo "$(BLUE)Creating local tenant...$(NC)"
	docker-compose exec -it backend python -m cli.tenant_cli create-local
	@echo "$(GREEN)✓ Tenant created$(NC)"

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
			sleep 5; \
			docker-compose up -d backend; \
			sleep 3; \
			$(MAKE) migrate; \
			echo "$(GREEN)✓ Database reset complete$(NC)"; \
			;; \
		*) \
			echo "Cancelled."; \
			;; \
	esac

##@ Frontend

frontend-install: ## Install frontend dependencies
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

test-backend: ## Run backend tests
	docker-compose exec backend pytest

test-env: ## Validate environment configuration
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	@for file in .env backend/.env frontend/.env secrets/firebase-credentials.json; do \
		if [ -f $$file ]; then \
			echo "$(GREEN)✓ $$file exists$(NC)"; \
		else \
			echo "$(YELLOW)✗ $$file missing$(NC)"; \
		fi \
	done

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
