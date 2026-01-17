# Backend Architecture Rules

## Scope
Owned by: **Backend Architect**
Applies to: **System Design, API Patterns, Security, Data Models**

## 1. Service Layer Pattern (Thin Router / Fat Service)
- **Constraint**: Business logic **MUST** reside in `services/`, never in `routers/`.
- **Routers**:
  - Handle HTTP request/response.
  - Extract user context (current_user, tenant_id).
  - Call Service layer.
  - Commit transaction (`await db.commit()`).
  - Trigger background tasks (audit logs, emails).
- **Services**:
  - Perform validation, DB operations, logic.
  - Raise `HTTPException` for errors (400, 403, 404).
  - Accept `db: AsyncSession` and explicitly passed `tenant_id`.

## 2. Multi-Tenancy & Isolation
- **Primary Defense**: **Row Level Security (RLS)** via `rls_service.set_tenant_context()`.
- **Secondary Defense**: Explicit `.where(Model.tenant_id == tenant_id)` in **ALL** queries.
- **Validation**: Never trust client-provided `tenant_id`; verify against authenticated token.

## 3. RBAC & Authorization (B2B)
- **3-Layer Model**:
  1.  **System Role** (Tenant Owner/Admin) -> Controls billing/team-structure.
  2.  **Business Role** (Team Specific) -> Controls operational data.
  3.  **Plugins** -> Cross-cutting constraints (Geo, Data Classification).
- **Enforcement**:
  - **Middleware**: Validates token & sets RLS context.
  - **Service**: Checks permissions via `rbac_service`.

## 4. Error Handling Strategy
- **400 Bad Request**: Validation failure (Client error).
- **401 Unauthorized**: Missing/Invalid token.
- **403 Forbidden**: Valid token, but insufficient permission (Process logic).
- **404 Not Found**: Resource doesn't exist OR belongs to another tenant.
- **500 Internal Error**: Uncaught exception (Server error). **NEVER** expose internal details.

## 5. Subscription Limits
- **Definition**: All limits (`max_teams`, `max_users`) defined in `subscription_plans.yaml`.
- **Enforcement**: Checked in **SERVICE** layer *before* resources creation.
- **Unlimited**: Value `-1` denotes unlimited.

## 6. Audit Logging
- **Requirement**: All state-changing actions (Create/Update/Delete) must be audited.
- **Mechanism**: Async Celery task `persist_audit_log` triggered from Router after successful commit.
- **Schema**: `tenant_id`, `actor_id`, `event_type` (noun.verb), `resource_id`.

## 7. Folder Structure Policies
- **Shared Code**: `core/` (Framework), `infrastructure/` (3rd Party), `plugins/` (RBAC Extensions).
- **Modules**: `modules/b2b`, `modules/b2c`, `modules/platform`.
- **Strict Separation**: B2B code cannot import B2C code, and vice-versa.

## 8. HTTP Status Codes Standards
- **200 OK**: Standard response for successful synchronous requests (GET, PUT, PATCH, DELETE if returning data).
- **201 Created**: Resource creation successful (POST). MUST return the created resource location or details.
- **202 Accepted**: Request accepted for background processing (e.g., bulk uploads, async exports). MUST return a Job ID.
- **204 No Content**: Successful request with no return body (DELETE).
- **400 Bad Request**: Validation failure, malformed JSON, or business rule violation (e.g., "User limit reached").
- **401 Unauthorized**: Authentication missing or invalid.
- **403 Forbidden**: Authentication valid, but permission denied.
- **404 Not Found**: Resource does not exist or user has no access (tenant isolation).
- **429 Too Many Requests**: Rate limit exceeded.
- **500 Internal Server Error**: Unhandled exception.

## 9. PostgreSQL Best Practices
- **Schema Design**:
  - **UUIDs**: Use `UUID(as_uuid=True)` for all Primary Keys.
  - **JSONB**: Use `JSONB` for flexible/unstructured data (`features`, `config`). **DO NOT** use it for relational data (foreign keys).
  - **Timestamps**: Use `TIMESTAMPTZ` (shorthand for `TIMESTAMP WITH TIME ZONE`). Always include `created_at` and `updated_at` with defaults (`DEFAULT now()`).
- **Indexing**:
  - **Tenant Isolation**: EVERY tenant-scoped table **MUST** have a `tenant_id` column and an index on it (or compound index starting with `tenant_id`).
  - **Foreign Keys**: Explicitly index all Foreign Key columns (Postgres does not do this automatically).
  - **JSONB**: Use **GIN** indexes for JSONB columns if querying by keys (`features ->> 'sso'`).
- **Concurrency**:
  - **Atomic Updates**: Use `with_for_update()` (SELECT ... FOR UPDATE) for critical read-modify-write chains (Inventory, Billing, Activation).
  - **No Table Locks**: Never explicit lock an entire table.
- **Async SQLAlchemy**:
  - **N+1 Prevention**: Use `options(selectinload(Model.relation))` for fetching related data in async mode.
  - **Sessions**: Correctly scope sessions. Rollback on error in middlewares/dependencies.

