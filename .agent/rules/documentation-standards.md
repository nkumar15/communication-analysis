
# Documentation Standards

## Scope
Owned by: **Technical Lead**
Applies to: **All Documentation, Feature Development, and Architecture**

## 1. The "Code-Next-To-Doc" Principle
**Rule**: Technical documentation must live **alongside the code** it describes.
- **Do NOT** create isolated specification files in `docs/specifications` for feature details.
- **DO** create a `README.md` inside the feature module directory.
  - Example: `backend/modules/domains/b2b/projects/README.md`

## 2. The Central Index (`docs/README.md`)
The `docs/` root is the **EntryPoint** and **Index** for the project.
**Rule**: Every Technical Feature Doc (`module/README.md`) must be linked from `docs/README.md`.

**Template for `docs/README.md`**:
```markdown
# Project Documentation

## 1. High-Level Architecture
- [System Overview](architecture/system_overview.md)
- [Tech Stack](architecture/tech_stack.md)

## 2. Feature Index
### B2B Domain
- [Task Management (Projects/Tasks)](../../backend/modules/domains/b2b/task_management/README.md)
- [Bank Surveillance](../../backend/modules/domains/b2b/bank_surveillance/README.md)

### B2C Domain
- [Finance Trader](../../backend/modules/domains/b2c/finance_trader/README.md)

## 3. Product Guides
- [Onboarding Guide](guides/onboarding.md)
```

## 3. Automation First
**Rule**: Use the **Feature Documentation Generator** skill to create and maintain feature docs.
- **Skill**: `@[feature-doc-generator]`
- **Process**:
  1. Discovery: List all components.
  2. Generate: Create Feature README.
  3. Index: Update `docs/README.md`.

## 4. Documentation Lifecycle
1. **Drafting**: Brief Plan in `task.md`.
2. **Implementation**: Write Code.
3. **Documentation**: Run `@[feature-doc-generator]`.
4. **Verification**: Verify completeness against the "Inventory List" (did I miss any API?).
