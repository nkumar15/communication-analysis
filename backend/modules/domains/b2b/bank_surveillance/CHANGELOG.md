# Changelog — Bank Surveillance

All notable changes to the bank_surveillance domain are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/) — tagged as `bank/vX.Y.Z`

---

## [Unreleased]

### Fixed
- RBAC sidebar visibility for surveillance_chief and domain roles — permission checks now use `resource:action` strings directly from DB, eliminating frontend/DB permission map drift
- Data Ingestion page now shows a 403-specific error message instead of a generic failure when accessed without `ingestion:read` permission
- tenant.domain_type not being set to `bank_surveillance` during demo onboarding (use_case from demo_tenant.json was never read)
- Orphan section headers in sidebar now filtered when all child items are hidden by RBAC

---

## [bank/v1.2.0] — 2026-03-xx (pre-release history)

### Added
- Alert ego-network visualization on alert detail page with dedicated API and React component
- Hybrid search with keyword highlighting and full message toggle in Intelligence Archive
- Command Center page with operational overview
- Deterministic numeric display IDs for alerts and cases
- Alert detail page with AI investigation functionality (replaced inline drawer)
- "Pick Next Alert" workflow for sequential alert investigation
- Alert assignment with user selection and status update
- Dashboard statistics and region filtering for alerts
- Alert conversation threads with full history
- Regulatory Library and Surveillance Controls pages with dedicated APIs and models
- Enron CSV ingestion pipeline with incident generation scripts
- Agentic investigation feature with RAG-powered analysis
- Email ingestion pipeline with RLS-aware processing

### Changed
- Smart routing for surveillance users redirects to domain dashboard on login
- Sidebar navigation redesigned for surveillance portal
- User profile dropdown enhanced with team roles display
- Content storage refactored to Elasticsearch for search performance
- Alert schemas and aggregation endpoints streamlined

### Fixed
- RBAC plugin architecture — schema gaps, fail-safe enforcement, geographic enrichment
- Geographic bypass tests (45/45 bank surveillance tests passing)
- Alert RBAC enforcement for regional and clearance-level constraints

---

## [bank/v1.0.0] — 2025-xx-xx (initial implementation)

### Added
- Initial bank surveillance domain: alerts, cases, communications, ingestion
- B2B sub-app mounted at `/bank_surveillance` in b2b-domain-api
- Base alert architecture with ingestion detection
- FastAPI sub-app mount and B2B seed standardization
