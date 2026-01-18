---
description: Maintain and organize system-level documentation (Architecture, Standards, Guides).
---

# System Documentation Maintainer

This skill helps you organize and maintain the high-level documentation in `docs/`. This is distinct from Feature Documentation (which lives in backend modules).

## 1. Taxonomy

When adding or updating documents, follow this strict taxonomy. If a document seems to fit two categories, prioritize **Standards** if it contains "Must/Should" rules, otherwise **Architecture**.

| Directory | Purpose | Content Type | Examples |
| :--- | :--- | :--- | :--- |
| `docs/architecture/` | **Design Decisions** | Diagrams, Tech Stack, System Overview, Security Models. | `security.md`, `observability.md`, `system-architecture.md` |
| `docs/standards/` | **Normative Rules** | "Must/Should" rules for Code, UX, API, Testing, AI Ethics. | `ui-design.md`, `api-standards.md`, `ai-ethics.md`, `testing-standards.md` |
| `docs/guides/` | **Operations & How-Tos** | Step-by-step instructions for humans (Deployment, Cleanup). | `deployment.md`, `celery-setup.md`, `data-lifecycle.md` |
| `docs/specifications/` | **Requirements** | PRDs, Business Logic definitions. | `spec_001_billing.md` |

### Specific Mappings
- **AI & GenAI**: 
  - Architecture (RAG pipeline) -> `docs/architecture/rag-hybridsearch.md`
  - Ethics & Usage Rules -> `docs/standards/README.md` (Placeholder)
- **Security**:
  - Auth Flow Design -> `docs/architecture/security.md`
  - Compliance Policy -> `docs/architecture/security.md`
- **Testing**:
  - Test Strategy -> `docs/standards/testing.md`
  - How to run tests -> `docs/guides/testing/workflows.md`
- **Data**:
  - Schema Design -> `backend/modules/.../README.md` (Feature Doc)
  - Retention Policy -> `docs/guides/data-lifecycle.md`
  - Deletion Guide -> `docs/guides/data-lifecycle.md`

## 2. Maintenance Workflows

### Adding a New Document
1.  **Identify Category**: Use the Reference Table above.
2.  **Place File**: Create the file in the correct subfolder.
3.  **Update Index**: Link the new file in the corresponding `README.md` (e.g., `docs/architecture/README.md`).
4.  **Root Check**: If it's a major topic, ensure it's discoverable from `docs/README.md` (System Documentation section).

### Updating Architecture Docs
*   **Must include Diagrams**: Use Mermaid.js for data flow or component interaction.
*   **Decision Record**: If changing architecture, add a "Context" section explaining *why*.

### Updating Standards
*   **Explicit Constraints**: Use keywords like **MUST**, **SHOULD**, **CONSTRAINT**.
*   **Versioning**: Increment the "Last Updated" date or Version ID at the top.

## 3. Templates

### Architecture Template
```markdown
# [System Name] Architecture

## 1. Overview
High level description of the system or subsystem.

## 2. Diagrams
[Mermaid Diagram]

## 3. Key Components
- **Component A**: Role and Responsibility.
- **Component B**: ...

## 4. Security & Scalability
- **Auth**: ...
- **Scaling Strategy**: ...
```

### Standard/Policy Template
```markdown
# [Topic] Standards

**Status**: [Draft/Active/Deprecated]
**Last Updated**: YYYY-MM-DD

## 1. Core Principles
High-level philosophy (e.g., "Secure by Design").

## 2. Rules
### 2.1. [Rule Category]
- **MUST** do X.
- **SHOULD** avoid Y.

## 3. Exceptions
When can these rules be broken?
```

### Guide Template
```markdown
# [Task Name] Guide

## Prerequisites
- Tool A
- Access B

## Steps
1. Step one...
2. Step two...

## Troubleshooting
Common errors...
```
