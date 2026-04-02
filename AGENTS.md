# Codex Execution Playbook (Deterministic Routing)

This file defines how Codex should select rules, skills, and workflows for this repository so execution stays consistent across turns.

## 1. Instruction Order

When multiple instructions exist, apply this precedence:

1. System and developer instructions from runtime.
2. This `AGENTS.md`.
3. `.agent/rules/*.md`.
4. `.agent/workflows/*.md`.
5. `.agent/skills/*/SKILL.md`.
6. User request for the current turn.

If any conflict appears, follow the highest-priority item and explicitly call out the deviation.

## 2. Always-On Rule Baseline

Apply these rule files on every implementation task:

- `.agent/rules/coding-standards.md`
- `.agent/rules/skill-matching.md`

For Python/backend work, also always apply:

- `.agent/rules/python-developer.md`
- `.agent/rules/observability-standards.md`

For Celery tasks or background workers, also always apply:

- `.agent/rules/celery-standards.md`

For tests, always apply:

- `.agent/rules/pytest-testing.md`

## 3. Deterministic Request Classifier

Classify each user request into one primary type before implementation:

1. `backend_endpoint_change`
2. `backend_service_logic_change`
3. `db_migration_or_schema_change`
4. `frontend_change`
5. `test_add_or_test_fix`
6. `documentation_change`
7. `security_audit`
8. `environment_stabilization`
9. `makefile_change`

If multiple types apply, execute in this sequence:

1. Security and schema safety
2. Business logic
3. API wiring
4. Tests
5. Documentation

## 4. Routing Matrix (Type -> Rules / Workflow / Skills)

### 4.1 `backend_endpoint_change`

- Rules:
  - `.agent/rules/backend-architecture.md`
  - `.agent/rules/python-developer.md`
  - `.agent/rules/pytest-testing.md`
- Workflow:
  - `.agent/workflows/add-new-endpoint.md`
  - `.agent/workflows/test-audit.md` (post-change coverage check)
- Skills:
  - `pytest-test-generator` (if tests are created/updated)
  - `pydantic-schema-generator` (if request/response schemas change)

### 4.2 `backend_service_logic_change`

- Rules:
  - `.agent/rules/backend-architecture.md`
  - `.agent/rules/python-developer.md`
  - `.agent/rules/pytest-testing.md`
- Workflow:
  - `.agent/workflows/test-audit.md`
- Skills:
  - `pytest-test-generator`

### 4.3 `db_migration_or_schema_change`

- Rules:
  - `.agent/rules/backend-architecture.md`
  - `.agent/rules/python-developer.md`
- Workflow:
  - `.agent/workflows/security-audit.md` (RLS/isolation checks)
- Skills:
  - `db-inspector` (mandatory)
  - `pydantic-schema-generator` (if schemas need updates)

### 4.4 `frontend_change`

- Rules:
  - `.agent/rules/frontend-architecture.md`
  - `.agent/rules/reactjs-developer.md`
- Workflow:
  - `.agent/workflows/run-e2e-tests.md` (when UI behavior changes)
- Skills:
  - None by default (unless user asks for doc generation)

### 4.5 `test_add_or_test_fix`

- Rules:
  - `.agent/rules/pytest-testing.md`
  - `.agent/rules/python-developer.md`
- Workflow:
  - `.agent/workflows/test-audit.md`
  - `.agent/workflows/run-e2e-tests.md` (if integration/e2e scope)
- Skills:
  - `pytest-test-generator` (mandatory default)

### 4.6 `documentation_change`

- Rules:
  - `.agent/rules/documentation-standards.md`
  - `.agent/rules/skill-matching.md`
- Workflow:
  - `.agent/workflows/doc-audit.md`
- Skills selection:
  - `product-doc-generator` for personas/pages/features/technical bundles
  - `doc-generator` for guides/runbooks/tool docs
  - `system-doc-maintainer` for architecture/standards/policies
  - If none match, follow `.agent/rules/skill-matching.md` fallback behavior

### 4.7 `security_audit`

- Rules:
  - `.agent/rules/backend-architecture.md`
  - `.agent/rules/python-developer.md`
- Workflow:
  - `.agent/workflows/security-audit.md`
- Skills:
  - `db-inspector` when migration/schema/RLS findings are in scope

### 4.8 `environment_stabilization`

- Rules:
  - `.agent/rules/makefile-standards.md`
- Workflow:
  - `.agent/workflows/build-verify-stable.md` or
  - `.agent/workflows/recreate-verify-stable.md`
  - `.agent/workflows/run-b2b-bank-tests.md` for bank suite requests
- Skills:
  - None

### 4.9 `makefile_change`

- Rules:
  - `.agent/rules/makefile-standards.md`
  - `.agent/rules/coding-standards.md`
- Workflow:
  - Use `build-verify-stable` after make target changes if relevant
- Skills:
  - None

## 5. Mandatory Backend Guardrails

For every backend write path:

1. Keep routers thin and services fat.
2. Enforce RBAC in router/dependencies.
3. Enforce tenant isolation in service queries (`tenant_id` filters).
4. Commit before queuing side effects.
5. Trigger audit logs for state-changing actions.
6. Do not log PII or secrets.

## 6. Skill Invocation Policy

Use a skill when either condition is true:

1. User explicitly requests that skill by name.
2. Task matches the skill trigger from `.agent/rules/skill-matching.md` or skill description.

Do not invoke unrelated skills.

## 7. Required Turn Summary Format

For non-trivial tasks, end with:

1. `Applied rules`
2. `Selected workflow(s)`
3. `Selected skill(s)`
4. `Changes made`
5. `Validation run`
6. `Deviations` (or `None`)

## 8. Deviation Policy

If a requested change conflicts with this playbook:

1. Explicitly state the conflicting rule/workflow.
2. Propose the compliant alternative.
3. Proceed only after user confirmation for the deviation.

### Deviation Request Template

When a deviation is needed, output this block before proceeding:

```
⚠️  DEVIATION REQUEST
─────────────────────────────────────────────
Conflicting rule : <rule file> § <section>
Rule says        : <exact constraint being violated>
Requested change : <what the user asked for>
Risk             : <what could go wrong if rule is bypassed>
Proposed alternative : <compliant way to achieve the same goal>
─────────────────────────────────────────────
Confirm to proceed with deviation, or approve alternative?
```

Do not proceed until the user explicitly confirms one of the options.
