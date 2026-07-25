---
description: Workflow for reviewing and auditing existing test coverage against functional code.
---

# Test Audit Workflow

Use this workflow to review test coverage and quality for a module.

## 1. Identify Target Module
- Determine the module path (e.g., `backend/modules/b2b/routers/teams.py`).
- Identify corresponding test path (e.g., `backend/tests/e2e_api/b2b/organization/test_teams.py`).

## 2. Inventory Endpoints
- List all endpoints in the router.
- For each endpoint, note:
  - HTTP Method
  - Path
  - Required permissions
  - Expected status codes

## 3. Check Test Coverage
For each endpoint, verify these test cases exist:
- [ ] `test_{action}_success`
- [ ] `test_{action}_unauthorized` (401)
- [ ] `test_{action}_forbidden` (403)
- [ ] `test_{action}_not_found` (404)
- [ ] `test_{action}_validation_error` (400/422)
- [ ] `test_{action}_tenant_isolation`

## 4. Review Fixture Usage
- Verify tests use shared fixtures from `conftest.py`.
- Identify any duplicated setup logic that should be extracted.
- Check RLS context is properly handled.

## 5. Pattern Compliance
Verify tests follow:
- **AAA Pattern**: Arrange-Act-Assert clearly separated.
- **Naming**: `test_{action}_{scenario}`.
- **Isolation**: No shared mutable state between tests.

## 6. Generate Report
Create a coverage matrix:
```markdown
| Endpoint | Success | 401 | 403 | 404 | Validation | Isolation |
|----------|---------|-----|-----|-----|------------|-----------|
| POST /teams | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| GET /teams/{id} | ✅ | ✅ | ✅ | ✅ | N/A | ❌ |
```

## 7. Remediation
For missing tests:
1. Use `/pytest-test-generator` skill to create boilerplate.
2. Customize for specific endpoint requirements.
3. Run tests to verify: `pytest {test_file} -v`
