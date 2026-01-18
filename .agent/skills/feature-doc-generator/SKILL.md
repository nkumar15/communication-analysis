---
description: Generate comprehensive, standardized documentation for a specific feature or module.
---

# Feature Documentation Generator

This skill generates a standardized `README.md` or technical documentation file for a specific feature module.

## Usage

When asked to "document the [Feature Name] feature" or "update docs for [Path]", follow these steps **strictly**.

### Step 1: Discovery & Inventory
**CRITICAL**: Do not skip this step. You must list every component to ensure nothing is missed.
1.  **List Files**: Run `list_dir` on the module.
2.  **Identify Components**:
    *   **Routers**: Find all files in `routers/`. Record every `@router` prefix and tag.
    *   **Models**: Find all files in `models/`. Record every Class inheriting from `Base`.
    *   **Services**: Find all files in `services/`. Record public methods.
3.  **Create Inventory List**:
    *   [ ] Router: `projects.py` (Endpoints: GET /, POST /, ...)
    *   [ ] Router: `comments.py` (Endpoints: ...)
    *   [ ] Model: `Project`
    *   [ ] Model: `Comment`

### Step 2: Generate Documentation
Create/Update `README.md` using the Standard Template.
*   **Completeness Check**: refer to your Inventory List. **Every** item in the Inventory must have a corresponding section in the doc.
    *   Did you document `comments.py`?
    *   Did you document the `ScopeChecker`?

### Step 3: Link to Root Docs
*   Open `docs/README.md` (or `docs/feature_index.md`).
*   Ensure this feature is listed in the "Feature Index" with a relative link to its `README.md`.
    *   Example: `- [Task Management](../../backend/modules/domains/b2b/task_management/README.md)`

## Standard Template

```markdown
# [Feature Name]

## 1. Context
### Goal
[One sentence summary of the business value]

### User Stories
- **As a** [Role] **I want to** [Action] **so that** [Benefit].
- [Story 2]

### Key Business Rules
- [Rule 1: e.g. "Only Owners can delete"]
- [Rule 2]

## 2. Architecture
### Data Flow
[Mermaid Diagram: User -> API -> Service -> DB]

### Key Components
| Component | File | Description |
| :--- | :--- | :--- |
| **Model** | `models/project.py` | `Project` entity |
| **API** | `routers/projects.py` | Project CRUD |

## 3. Database Schema
**Schema**: `[schema_name]`

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `[table]` | [Description] | `id`, `[fk_col]` |

## 4. API Reference
**Base Path**: `/api/b2b/domain/[feature]`

### [Sub-Resource Name] (e.g. Projects)
| Method | Path | Description | Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | List items | `[resource]:read` |
| `POST` | `/` | Create item | `[resource]:write` |

*(Repeat for ALL routers found in Discovery)*

## 5. Dependencies
- **Internal**: [Modules this feature calls]
- **External**: [Stripe, Firebase, etc.]
- **Env Vars**: `[VAR_NAME]`

```

## Quality Checklist
Before finishing, ask yourself:
1. Did I include **ALL** routers found in the directory?
2. Did I include **ALL** database tables defined in models?
3. Is the Permission scope clearly stated?
