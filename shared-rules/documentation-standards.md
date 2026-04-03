---
trigger: always_on
---

# Documentation Standards

## Scope
Owned by: **Technical Lead**
Applies to: **All Documentation, Feature Development, and Architecture**

## 0. The Root Index (`README.md`)
**Rule**: The Root README is the **Product Portfolio**, not just a technical index.
- **Structure**: Must follow the "SaaS Portfolio" template (Foundations vs Commercial Verticals).
- **Inclusion**: MUST list all active products (e.g., Bank Surveillance).
- **Audience**: Product Managers & New Developers (High-level value prop).

## 1. The "Code-Next-To-Doc" Principle
**Rule**: Technical documentation must live **alongside the code** it describes.

### Scenario A: Modular Architecture (Feature Folders)
*Examples: `domains/b2b/task_management`, `domains/b2b/bank_surveillance`*
- **Placement**: `README.md` inside the feature folder.
- **Example**: `backend/modules/domains/b2b/task_management/README.md`

### Scenario B: Layered Architecture (Foundation Modules)
*Examples: `modules/b2b` (Core), `modules/platform`*
- **Placement**:
  1. **Index**: `README.md` at the module root (`modules/b2b/README.md`).
  2. **Features**: Markdown files in a `docs/` subdirectory.
     - **Example**: `backend/modules/b2b/docs/invitations.md`
- **Why**: These modules lack feature-specific folders, so we group docs locally.

## 2. The Central Index (`docs/README.md`)
The `docs/` root is the **EntryPoint** and **Index** for the project.
**Rule**: Every Technical Feature Doc (`module/README.md`) must be linked from `docs/README.md`.

**Template for `docs/README.md`**:
```markdown
# Project Documentation

## 1. High-Level Architecture
- [System Overview](architecture/system_overview.md)
- [Tech Stack](architecture/tech_stack.md)

## 2. Product Index
### B2B Domain
- [Task Management (Projects/Tasks)](../../backend/modules/domains/b2b/task_management/README.md)
- [Bank Surveillance](../../backend/modules/domains/b2b/bank_surveillance/README.md)

### B2C Domain
- [Finance Trader](../../backend/modules/domains/b2c/finance_trader/README.md)

## 3. Product Guides
- [Onboarding Guide](guides/onboarding.md)
```

## 3. Product Visualization
**Rule**: Every feature **MUST** maintain the standard folder structure.
- **Structure**: `docs/wireframes/` and `docs/demos/` directories are **MANDATORY**.
- **Content**: Visual assets are **Recommended** but optional based on feature complexity.

## 4. Automation First
**Rule**: Use the **`product-doc-generator`** skill to create and maintain feature docs.
- **Skill**: `product-doc-generator`
- **Process**:
  1. Discovery: List all components.
  2. Generate: Create Feature README.
  3. Index: Update `docs/README.md`.

## 5. Documentation Lifecycle
1. **Drafting**: Brief Plan in `task.md`.
2. **Implementation**: Write Code.
3. **Documentation**: Run `product-doc-generator` skill.
4. **Verification**: Verify completeness against the "Inventory List" (did I miss any API?).
