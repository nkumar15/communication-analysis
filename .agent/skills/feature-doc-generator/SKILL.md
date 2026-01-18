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

### Step 2: Standards Alignment Check
**CRITICAL**: Ensure your documentation aligns with the System Standards defined in `docs/`.
1.  **Read Standards**: Review `docs/standards/README.md` and `docs/architecture/README.md`.
2.  **Verify Patterns**: 
    *   Does the Architecture diagram match the System Architecture?
    *   Do UI requirements follow `ui-design.md`?
    *   Does Security/Auth match `security.md`?
3.  **Note Deviations**: If the feature violates a standard, you must log it in the "Standards Alignment" section.

### Step 3: Generate Documentation
Create or Update the documentation file.

**Path Selection**:
- **Modular (Feature Folder)**: Create `README.md` in the feature folder.
- **Layered (Foundation)**: Create `docs/[feature_name].md` inside the module folder (e.g., `backend/modules/b2b/docs/invitations.md`).

### Step 4: Link to Indices
1.  **Module Index** (Layered Only): If in a Layered module, ensure `[module]/README.md` links to your new doc.
2.  **Root Index**: Open `docs/README.md`. Ensure the feature (or the Module Index) is listed.

**Structure Rules**:
- **Do NOT delete sections**. The structure must be consistent across all feature docs.
- If a section (e.g., UI, Extensions) is not applicable, keep the header and write "Not Applicable" or "None".

## Standard Template

```markdown
# [Feature Name]

## 1. Context
### Goal
[One sentence summary of the business value]

### Target Platform
- [ ] Web
- [ ] Mobile (iOS/Android)
- [ ] Backend API Only
*(Check all that apply)*

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

## 5. UI Requirements
*(If Target Platform is "Backend Only", write "Not Applicable")*
*(Reference `docs/standards/ui-design.md` for components)*

### Components
- List key UI components (e.g., `UserList`, `PermissionTable`).
- Describe states (Loading, Empty, Error).

### UX Rules
- Progressive Disclosure rules.
- Error handling behavior.

## 6. Observability & Audit
*(If not applicable, write "Not Applicable")*
*(Reference `docs/architecture/observability.md` for patterns)*

### Audit Logs
- **Event**: `[EVENT_NAME]`
- **Payload**: `[actor_id, target_id, changes]`

### Metrics
- Key metrics (e.g., `signup_latency`, `active_subscriptions`).
- Tracing context (e.g., `request_id` propagation).

## 7. Extensions
*(If not applicable, write "Not Applicable")*

### Architecture
If the module supports plugins or extensions, describe the interface and lifecycle.

### Configuration
- Describe how to configure the module (YAML/JSON).
- List available plugins or use cases.

## 8. Testing
### Critical Scenarios
- List valid/invalid cases (e.g., `success`, `unauthorized`, `validation_error`).
- Reference specific edge cases.

### Test Location
- `backend/tests/e2e_api/[module]/test_[feature].py`

## 9. Dependencies
- **Internal**: [Modules this feature calls]
- **External**: [Stripe, Firebase, etc.]
- **Env Vars**: `[VAR_NAME]`

## 10. Standards Alignment
- **Architecture**: Verified against [System Architecture](../../../docs/architecture/system-architecture.md).
- **Standards**: Verified against [Standards Index](../../../docs/standards/README.md).
- **Deviations**: None.
```

## Quality Checklist
Before finishing, ask yourself:
1. Did I include **ALL** routers found in the directory?
2. Did I include **ALL** database tables defined in models?
3. **Did I include a Mermaid Diagram for the Data Flow?** (Text descriptions are not enough).
4. Is the Permission scope clearly stated?
5. Did I link to the Module Index and Root Index?
6. **Did I verify alignment with System Standards?**

