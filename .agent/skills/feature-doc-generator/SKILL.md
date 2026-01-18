---
description: Generate comprehensive, standardized documentation for a specific feature or module.
---

# Feature Documentation Generator

This skill generates a standardized `README.md` or technical documentation file for a specific feature module (e.g., `modules/b2b/projects` or `modules/b2c/todos`).

## Usage

When asked to "document the [Feature Name] feature" or "update docs for [Path]", follow these steps:

1.  **Analyze the Codebase**:
    *   **Models**: Look for SQLAlchemy models to understand the database schema. Identify tables, columns, relationships, and constraints.
    *   **Routers**: Look for FastAPI routers to identify API endpoints (Methods, Paths, Request/Response models).
    *   **Services**: Look for service classes or functions to understand the core business logic and workflows.
    *   **Dependencies**: Identify external services (Celery, Stripe, etc.) or cross-module dependencies.

2.  **Generate Documentation**:
    Create a markdown file (or update `README.md` in the module root) following the **Standard Template** below.
    *   **Do not** skip sections unless they are truly not applicable.
    *   **Do** use Mermaid diagrams for complex data flows or state machines.

## Standard Template

```markdown
# [Feature Name]

## 1. Overview
[Brief description of what this feature does. Who is it for? What problem does it solve?]

## 2. Architecture
### Data Flow
[Mermaid Diagram illustrating the flow of data, e.g., User -> API -> Service -> DB]

### Key Components
- **Models**: `[ModelName]`, `[ModelName]`
- **Services**: `[ServiceName]`
- **API**: `[RouterPrefix]`

## 3. Database Schema
| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `[table_name]` | [Description] | `id` (PK), `[col]` |

## 4. API Reference
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/...` | [Short desc] | Yes/No |

## 5. Key Workflows
### [Workflow Name] (e.g., Creation, Processing)
1. Step 1...
2. Step 2...
3. Step 3...

## 6. Dependencies & Configuration
- **Env Vars**: `[VAR_NAME]` (if any)
- **External Services**: [e.g. Stripe, Celery, S3]
```

## Tips
- Be concise but complete.
- For API endpoints, verify the actual `@router` decorators.
- For DB schemas, verify the `__tablename__` and column definitions.
