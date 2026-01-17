---
trigger: always_on
---

# Python Developer Rules

## Scope
Owned by: **Senior Python Developer**
Applies to: **Code Style, FastAPI, SQLAlchemy, Testing**

## 1. Core Engineering Principles
- **DRY (Don't Repeat Yourself)**: Extract common logic into `core/utils` or `services/`.
- **KISS (Keep It Simple, Stupid)**: Prefer readable, explicit code over "clever" one-liners.
- **YAGNI (You Ain't Gonna Need It)**: Do not build features "for the future". Solve the current problem.


## 2. Code Style & Typing
- **Type Hints**: **MANDATORY** for all function arguments and return values.
- **Async/Await**: Use `async def` for all I/O bound operations (DB, API calls).
- **Docstrings**: Google-style docstrings for all modules, classes, and public methods.

## 3. FastAPI Best Practices
- **Dependency Injection**: Use `Depends()` for DB sessions, User context.
- **Pydantic**: Use Schemas for **Request Validation** and **Response Serialization**.
  - **Naming**: `UserCreate`, `UserUpdate`, `UserResponse`.
- **Status Codes**: Explicitly define `status_code` in `@router` decorators.

## 4. SQLAlchemy (Async) Patterns
- **Sessions**: Use `AsyncSession`. Do not use sync session methods.
- **Queries**: Use `select(Model).where(...)` (2.0 style). Avoid legacy `query()`.
- **Relationships**: Use `await session.refresh(obj, ['relation'])` or `options(selectinload(Model.relation))`.
- **Migrations**: Always generate migrations for schema changes (`alembic revision --autogenerate`).

## 5. Celery & Background Tasks
- **Idempotency**: Tasks must be safe to retry.
- **Arguments**: Pass **IDs** (primary keys), not full objects to tasks.
- **Eager Mode**: Use `task_always_eager = True` for unit tests.

## 6. Testing Guidelines
- **Framework**: `pytest` + `pytest-asyncio`.
- **Fixtures**: Use `conftest.py` fixtures (`api_client`, `db_session`).
- **RLS Testing**: Use `TenantAwareSession` or `set_tenant_context` helper in tests.
- **Mocking**: Mock external services (Stripe, Firebase, Email) in unit tests.
- **Reference**: Refer to pytest-testing.md rule 
