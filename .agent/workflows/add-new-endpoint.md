---
description: Steps to create a new B2B/B2C API endpoint following the "Thin Router / Fat Service" pattern.
---

1.  **Preparation**
    - Identify the correct module (`b2b`, `b2c`, or `platform`).
    - Determine required permissions (check `backend-architecture.md`).

2.  **Define Schema (`schemas/`)**
    - Create Pydantic models for request (`Create/Update`) and response (`Response`).
    - Ensure all fields have type hints and validation.
    
3.  **Implement Service Logic (`services/`)**
    - Add method to existing service or create new service.
    - Arguments must include `db: AsyncSession` and `tenant_id: UUID` (for B2B).
    - **RLS/Isolation**: 
        - Ensure all DB queries explicitly include `.where(Model.tenant_id == tenant_id)`.
        - Service layer is the primary owner of data isolation.
    - Implement business logic, DB operations, and validation.
    - Raise `HTTPException` for errors (404 for isolation failures, 400 for validation).

4.  **Create Router Endpoint (`routers/`)**
    - Define route with `@router` decorator and set the correct `status_code`.
    - Inject dependencies: `db`, `current_user` (and `tenant_id` context).
    - **RBAC Enforcement**: Check permissions here! Call `rbac_service.check_permission(db, user_id, tenant_id, "resource:action")` or use a corresponding dependency.
    - Call service method, passing the validated context components.
    - Commit transaction: `await db.commit()`.
    - **Audit Trial**: Trigger `persist_audit_log` Celery task for any state-changing operations.

5.  **Declare Permissions**
    - If new resource/action, update `scripts/b2b/core/resources.yaml` or `actions.yaml`.
    - Run seed script: `make seed-rbac`.

6.  **Verify**
    // turbo
    - Run relevant tests: `pytest backend/tests/e2e_api/test_module_name.py`
