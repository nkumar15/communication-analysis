
# Documentation Standards

## Scope
Owned by: **Technical Lead**
Applies to: **All Documentation, Feature Development, and Architecture**

## 1. The "Code-Next-To-Doc" Principle
**Rule**: Technical documentation must live **alongside the code** it describes.
- **Do NOT** create isolated specification files in `docs/specifications` for feature details.
- **DO** create a `README.md` inside the feature module directory.
  - Example: `backend/modules/domains/b2b/projects/README.md`
- **Why**: Ensures developers see documentation while coding and updating it is part of the PR definition of done.

## 2. Structure of `docs/` Root
The `docs/` folder is reserved for **High-Level** context only.

| Directory | Purpose | Content Type |
| :--- | :--- | :--- |
| `docs/architecture/` | System-wide patterns, C4 diagrams, stack choices | Diagrams, ADRs |
| `docs/guides/` | User-facing manuals, "How-To" guides | Tutorials, Concepts |
| `docs/products/` | Product-level vision and high-level scope | PRDs, Vision Statements |

**Prohibited**: Deep technical specs (API tables, DB schemas) in `docs/`. Those belong in the module README.

## 3. Automation First
**Rule**: Use the **Feature Documentation Generator** skill to create and maintain feature docs.
- **Skill**: `@[feature-doc-generator]`
- **Command**: "Generate documentation for [module]"
- **Process**:
  1. Write Code.
  2. Run Skill to Snapshot state.
  3. Commit both.

## 4. Documentation Lifecycle
1. **Drafting**: Brief Plan in `task.md` or `implementation_plan.md`.
2. **Implementation**: Write Code.
3. **Documentation**: Run `@[feature-doc-generator]` to create/update the README.
4. **Verification**: Verify the README accurately reflects the implementation. 
