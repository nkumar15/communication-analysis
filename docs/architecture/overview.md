# Architecture Decisions

Record of significant architectural and technical decisions.

## Format

Each decision follows this structure:
- **Date:** When decided
- **Context:** What prompted this decision
- **Decision:** What we decided
- **Consequences:** Implications and trade-offs

---

## AD-001: Firebase GCIP for Multi-Tenancy (2025-11-20)

**Context:**
- Need multi-tenant SSO with isolated authentication
- Each tenant uses different OIDC provider (Auth0, Okta, Azure)
- Want to avoid managing OIDC flows ourselves

**Decision:**
- Use Firebase Google Cloud Identity Platform (GCIP)
- Create Firebase tenant per customer tenant
- Configure OIDC providers in Firebase Console
- Use Firebase SDK on frontend for auth
- Validate JWT tokens with Firebase Admin SDK on backend

**Consequences:**
- ✅ Firebase handles OIDC complexity (PKCE, state, tokens)
- ✅ Automatic multi-tenant isolation
- ✅ Enterprise-grade security
- ⚠️ Vendor lock-in to Firebase
- ⚠️ Need Firebase project setup
- ⚠️ Cost scales with users

**Alternatives Considered:**
- Custom OIDC implementation - Rejected (too complex, security risk)
- Auth0 organizations - Rejected (expensive at scale)
- Ory Hydra - Rejected (self-hosted complexity)

---

## AD-002: SQLAlchemy ORM vs Raw SQL (2025-11-22)

**Context:**
- Initial implementation used raw SQL queries
- As complexity grew, needed better data modeling
- Want type safety and easier refactoring

**Decision:**
- Migrated to SQLAlchemy ORM (async)
- Keep raw SQL only in migrations
- Use Pydantic models for API layer

**Consequences:**
- ✅ Better type safety with IDE support
- ✅ Easier to refactor schema
- ✅ Relationships handled automatically
- ✅ Query composition is cleaner
- ⚠️ Slight learning curve for team
- ⚠️ Some complex queries need raw SQL

---

## AD-003: Email Activation vs Direct Provisioning (2025-11-22)

**Context:**
- Sales team provisions tenants
- Admins need to activate their account
- Want self-service to reduce support burden

**Decision:**
- Email-based activation workflow
- Time-limited activation tokens (48 hours)
- Admin must complete SSO login before activation
- Invitation system for additional users

**Consequences:**
- ✅ Self-service reduces support
- ✅ Admin verifies email ownership
- ✅ Tenant not live until admin confirms
- ✅ Can send welcome/onboarding materials
- ⚠️ Requires email service (Resend)
- ⚠️ Admin must check email promptly
- ⚠️ Token expiry means potential re-provisioning

**Alternatives Considered:**
- Instant activation - Rejected (no admin verification)
- Manual activation by support - Rejected (doesn't scale)

---

## AD-004: Invitations Table vs Direct User Creation (2025-11-22)

**Context:**
- Users need to be invited to platform
- Want to control who can join
- Need role assignment before user exists

**Decision:**
- Separate `invitations` table
- Invitation created before user exists
- Role determined by invitation, not user creation
- Invitation accepted when user first logs in

**Consequences:**
- ✅ Clear invitation state tracking
- ✅ Can resend invitations
- ✅ Role assigned at invitation time
- ✅ Audit trail of who invited whom
- ⚠️ Extra table to maintain
- ⚠️ Must sync invitation → user on first login

---

## AD-005: CLI vs Web UI for Tenant Provisioning (2025-11-22)

**Context:**
- Sales/admin team needs to provision tenants
- Want automation and repeatability
- Need to configure Firebase + Database + Email

**Decision:**
- Python CLI tool for tenant provisioning
- Two modes: `create` (full) and `create-local` (testing)
- Interactive script for quick iterations
- No web UI for provisioning (yet)

**Consequences:**
- ✅ Scriptable and automatable
- ✅ Fast for testing iterations
- ✅ No UI development needed
- ✅ Can be run by sales team with training
- ⚠️ Requires command-line access
- ⚠️ Less user-friendly than web UI
- ⚠️ Future: May add web UI for non-technical users

---

## AD-006: Stateless JWT vs Session Cookies (2025-11-20)

**Context:**
- Need authentication for API calls
- Want horizontal scalability
- Don't want to manage session storage

**Decision:**
- Use Firebase JWT tokens
- No server-side sessions
- No Redis or session store needed
- Tokens validated on each request

**Consequences:**
- ✅ Fully stateless backend
- ✅ Easy horizontal scaling
- ✅ No session storage needed
- ✅ Firebase handles token refresh
- ⚠️ Cannot invalidate tokens before expiry
- ⚠️ Slightly larger request size (JWT in header)

---

## AD-007: Monorepo vs Separate Repos (Current)

**Context:**
- Have backend (Python) and frontend (React)
- Need to coordinate changes across both
- Small team working on everything

**Decision:**
- Keep in single repository (monorepo)
- Backend and frontend in separate directories
- Shared docker-compose for local dev

**Consequences:**
- ✅ Easy to make coordinated changes
- ✅ Single source of truth for docs
- ✅ Simplified deployment (can be together)
- ⚠️ May split later if teams specialize
- ⚠️ CI/CD needs to handle both

---

## Template for New Decisions

```markdown
## AD-XXX: [Decision Title] (YYYY-MM-DD)

**Context:**
What problem are we solving?

**Decision:**
What did we decide?

**Consequences:**
✅ Pros
⚠️ Cons / Trade-offs

**Alternatives Considered:**
- Option A - Why rejected
- Option B - Why rejected
```

---

**How to Use:**
1. When making significant technical decision, document it here
2. Include context, decision, and trade-offs
3. Update ROADMAP.md if decision affects planning
4. Discuss in PR before merging

**Last Updated:** 2025-11-29

---

## AD-008: Microservices Architecture (2025-11-29)

**Context:**
- Monolithic `app/main.py` was becoming hard to manage
- Need to scale B2B, Platform, and B2C independently
- Want clear separation of concerns and security boundaries
- Platform admin API should be isolatable from public B2B API

**Decision:**
- Split backend into 3 independent microservices:
  1. **B2B API** (Port 8000): Tenant management, auth, invitations
  2. **Platform API** (Port 8001): Admin operations, stats
  3. **B2C API** (Port 8002): Personal workspaces
- Move migrations to top-level (shared database)
- Update Docker Compose to run services independently

**Consequences:**
- ✅ Independent deployment and scaling
- ✅ Improved security (can isolate Platform API)
- ✅ Clearer code organization
- ⚠️ More complex local development (3 ports)
- ⚠️ Shared database coupling remains (intentional for now)

**Alternatives Considered:**
- Keep Monolith - Rejected (doesn't scale well for distinct workloads)
- Separate Databases - Rejected (too complex for current stage, need cross-schema queries)
