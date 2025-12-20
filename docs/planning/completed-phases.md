# Tenant Onboarding Implementation Tasks

## Phase 0: SQLAlchemy Migration ✅ COMPLETE
- [x] Add SQLAlchemy dependencies
- [x] Create SQLAlchemy ORM models (Tenant, User)
- [x] Update database.py with async session
- [x] Migrate tenant_service to ORM
- [x] Migrate user_service to ORM
- [x] Migrate auth endpoints
- [x] Test all APIs work with ORM

## Phase 1: Database Schema ✅ COMPLETE
- [x] Add activation_token to tenants table
- [x] Add activation_status to tenants table  
- [x] Add activation_expires_at to tenants table
- [x] Add role field to users table
- [x] Create migration file
- [x] Test migration

## Phase 2: Python CLI Tool ✅ COMPLETE
- [x] Create tenant_onboard.py script
- [x] Implement Firebase tenant creation
- [x] Implement OIDC provider configuration
- [x] Implement activation token generation
- [x] Implement email sending (Resend)
- [x] Add error handling and validation
- [x] Create CLI documentation
- [x] Add create-local command for testing
- [x] Fix database session cleanup

## Phase 3: Backend API ✅ COMPLETE
- [x] Create activation token validation endpoint
- [x] Create tenant-info endpoint for SSO config
- [x] Create activation status check endpoint
- [x] Create activation completion endpoint
- [x] Add timezone-aware datetime handling
- [x] Add graceful email fallback to console
- [x] Fix firebase_uid extraction from token
- [x] Fix user role assignment from invitation

## Phase 4: Frontend - Activation UI ✅ COMPLETE
- [x] Create ActivationPage component
- [x] Create Card UI components
- [x] Create Button UI component
- [x] Add activation route to App.js
- [x] Test end-to-end activation flow
- [x] Debug and fix activation errors
- [x] Verify complete workflow

## Phase 5: Testing & Documentation ✅ COMPLETE
- [x] Test end-to-end flow (Successfully completed!)
- [x] Document testing workflow
- [x] Create development guide
- [x] Update main README
- [x] Copy documentation to docs/ folder

## Phase 4: DevOps Foundation ✅ COMPLETE (2025-11-29)

### Docker Optimization
- [x] Unified multi-stage Dockerfile (single source of truth)
- [x] Build targets: b2b, platform, b2c, domain, test
- [x] Aggressive build caching for fast iteration
- [x] Lean production images (service-specific code only)
- [x] Test image with Playwright browsers cached

### Microservices Expansion
- [x] Added Domain microservice (port 8003)
- [x] Farming router integrated
- [x] All 4 services in docker-compose.yml

### Development Workflow
- [x] Interactive setup scripts (platform-seed, platform-create-admin, b2b-seed)
- [x] Makefile modernization:
  - [x] `make dev` - Hybrid development (Docker backend + local frontend)
  - [x] `make up-backend` - Backend services only
  - [x] `make logs-*` - Per-service log viewing
  - [x] `make shell-*` - Per-service shell access
  - [x] Updated test commands (test-api, test-browser, test-all)
- [x] Removed obsolete commands (frontend-install-docker, outdated test targets)

### Frontend Configuration
- [x] Fixed Docker environment variables (localhost URLs for browser)
- [x] Added REACT_APP_PLATFORM_API_URL for platform service
- [x] Updated `.env.example` with all required variables

### Documentation
- [x] Updated `docs/guides/development.md` with new workflows
- [x] Updated `docs/guides/platform-admin.md` with interactive commands
- [x] Verified `docs/architecture/system-architecture.md` accuracy
- [x] Updated `README.md` with all 4 microservices
- [x] Created comprehensive walkthroughs

## Phase 5: CI/CD & Observability 🚧 NEXT
- [ ] GitHub Actions pipeline
- [ ] Structured logging
- [ ] OpenTelemetry integration
- [ ] Automated deployment
