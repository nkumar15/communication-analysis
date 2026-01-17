---
description: Steps to create a new B2B/B2C API endpoint following the "Thin Router / Fat Service" pattern.
---

1.  **Preparation**
    - Identify the correct module (`b2b`, `b2c`, or `platform`).
    - Determine required permissions (check `backend-architect.md`).

2.  **Define Schema (`schemas/`)**
    - Create Pydantic models for request (`Create/Update`) and response (`Response`).
    - Ensure all fields have type hints and validation.
    
3.  **Implement Service Logic (`services/`)**
    - Add method to existing service or create new service.
    - Arguments must include `db: AsyncSession` and `tenant_id: UUID` (for B2B).
    - Implement business logic, DB operations, and validation.
    - Raise `HTTPException` for errors.

4.  **Create Router Endpoint (`routers/`)**
    - Define route with `@router` decorator.
    - Inject dependencies: `db`, `current_user` (and `tenant_id` context).
    - Call service method.
    - Commit transaction: `await db.commit()`.
    - Trigger audit log (if state changed).

5.  **Add Permissions (if needed)**
    - If new resource/action, update `scripts/b2b/core/actions.yaml` or `resources.yaml`.
    - Run seed script: `python backend/scripts/b2b/seed_rbac.py`.

6.  **Verify**
    // turbo
    - Run relevant tests: `pytest backend/tests/e2e_api/test_module_name.py`
