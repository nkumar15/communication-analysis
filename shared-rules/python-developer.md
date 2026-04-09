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
- **SOLID**: Adhere to Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion principles to ensure robust and maintainable code.


## 2. Code Style & Typing
- **Type Hints**: **MANDATORY** for all function arguments and return values.
- **Async/Await**: Use `async def` for all I/O bound operations (DB, API calls).
- **Docstrings**: Google-style docstrings for all modules, classes, and public methods.
- **No Print**: Use `from infrastructure.logging import get_logger`. `print()` is forbidden in production code.

## 3. FastAPI & Error Handling
- **Schemas**: Use Pydantic for validation/serialization. Naming: `EntityCreate`, `EntityUpdate`, `EntityResponse`.
- **Status Codes**: 
  - `201 Created` for POST success.
  - `204 No Content` for DELETE success.
  - `400 Bad Request` for business rule violations.
  - `403 Forbidden` for RBAC failures.
- **Dependency Injection**: Use `Depends()` for DB and context.

## 4. SQLAlchemy (Async) Patterns
- **Queries**: Use 2.0 style (`select(Model).where(...)`).
- **N+1 Prevention**: Always use `options(selectinload(Model.relation))` in async queries.
- **Sessions**: Use `AsyncSession`. Ensure `db.commit()` is called in the Router layer for atomic operations.
- **Migrations**: Write raw SQL files in `backend/migrations/{product}/` following `db-migration-standards.md`. Run via `make migrate-schema`. Do NOT use `alembic revision --autogenerate` — this project uses hand-written SQL migrations, not Alembic autogenerate.

## 5. Celery & Background Tasks
- **Arguments**: ONLY pass primitive IDs (UUID/int) to tasks. Never pass full SQLAlchemy objects.
- **Idempotency**: All tasks must be safe to retry.
- **Trigger**: Initialize from Router AFTER successful DB commit.

## 6. Logging Standards
- **Logger**: import from infrastructure logging 
- **PII**: Never log emails, names, or cleartext secrets.
- **Levels**: Use `ERROR` with `exc_info=True` for exceptions.

## 7. Security & Secrets
- **Credential Safety**: Never hardcode API keys or secrets. Use `Settings` or environment variables to inject them at runtime.
- **Verification**: If a secret is required, check `.env.example` for the key and prompt the user if it's missing from the local environment.

## 8. Testing Guidelines
- **Framework**: `pytest` + `pytest-asyncio`.
- **Fixtures**: Use `conftest.py` fixtures (`api_client`, `db_session`).
- **RLS Testing**: Use `TenantAwareSession` or `set_tenant_context` helper in tests.
- **Mocking**: Mock external services (Stripe, Firebase, Email) in unit tests.
- **Reference**: Refer to pytest-testing.md rule