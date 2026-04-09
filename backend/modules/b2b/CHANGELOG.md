# Changelog — B2B Foundation

All notable changes to the B2B foundation (auth, RBAC, billing, teams, invitations) are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/) — tagged as `b2b-foundation/vX.Y.Z`

---

## [b2b-foundation/v1.0.0] — 2026-04-09

### Added
- Multi-layered plugin-aware RBAC: `require_permission` decorator, plugin interceptor (before/after), team-role permissions with JSONB `resource:action` pairs
- Stripe subscription billing: checkout session, webhook handler, plan upgrade/downgrade, payment failure alerts
- Plugin activation/deactivation lifecycle tied to subscription plan changes — `on_tenant_enable` / `on_tenant_disable` hooks triggered on plan diff
- Geographic Boundaries plugin: region-scoped data access, global role bypass, template cloning on enable
- Data Classification plugin: clearance-level enrichment from TeamRoleDefinition, sensitivity levels cloned on enable
- Hierarchical Teams plugin: recursive team ancestry via CTE, `team_members:manage` delegation
- Pydantic v2 schemas (`PlanLimits`, `PlanFeatures`, `TenantFeatures`) for JSONB validation on subscription plan and tenant features columns
- `region_id` FK on teams for geographic plugin integration
- Docker Compose profiles for scoped B2B-only startup (`b2b-demo` profile)
- Per-domain CHANGELOG structure and release-manager skill

### Changed
- Limits (max_users, max_teams) are now always read fresh from the active subscription plan — never stored as a stale copy in `tenant.features`
- Auth service returns live plan limits on every token refresh via subscription → plan JOIN
- Team service reads `max_teams` from plan directly; removed dead `projects` fallback alias

### Fixed
- Billing webhook returning 500 instead of 400 for bad Stripe signatures (HTTPException re-wrap bug)
- RLS context not set before subscription service writes in webhook path
- UUID/string comparison bugs in RBAC permission resolution
- Mobile auth flow across B2B RBAC layers
- Celery task mock path for `send_payment_failure_alert` in tests
- Async spy lambda pattern creating unawaited coroutines in plugin integration tests
- RLS context reset after DB commit in idempotency tests (re-set platform-admin context before second checkout)
