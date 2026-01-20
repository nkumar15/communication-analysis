# Global Coding Standards

## Scope
Applies to: **Entire Monorepo (Backend, Frontend, Infra, SQL)**

## 1. Naming Conventions

### Python (Backend)
- **Files/Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

### JavaScript/TypeScript (Frontend)
- **Files**:
    - Components: `PascalCase.js` or `PascalCase.tsx`
    - Hooks: `useCamelCase.js`
    - Utils/Services: `camelCase.js`
- **Functions/Variables**: `camelCase`
- **Constants**: `UPPER_SNAKE_CASE`

### SQL (Migrations)
- **Table/Column names**: `snake_case`
- **File naming**: `{sequence}_{description}.sql` (e.g., `001_initial_schema.sql`)

---

## 2. Monorepo Import Rules
- **Backend**: Use absolute imports from project root where possible (e.g., `from core.db.session import ...`).
- **Frontend**: Use absolute imports from `src/` (e.g., `import { Service } from 'core/api/...'`).
- **Cross-Layer**: Frontend MUST NOT import from `backend/`. Communication happens only via API.

---

## 3. Git & Commits
- **Commit Message Format**: `{type}({scope}): {description}`
    - **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
    - **Scope**: `backend`, `frontend`, `infra`, or a specific module name.
- **Rules**:
    - Never commit `.env` files.
    - **Credential Safety**: Never hardcode API keys, tokens, or secrets in the codebase. If a secret is required for a feature, check `.env.example` for the required key name and prompt the user to provide it in their local `.env`.
    - Large binary files should be handled via LFS (if configured).

---

## 4. File Headers & Metadata
- Every new Python file MUST have a docstring at the top.
- Every major React component file MUST describe its purpose and dependencies in a comment block.

---

## 5. Development Workflow
- **Linting**: Run `black` (Python) and `prettier` (JS) before committing.
- **Branching**: Use descriptive branch names (e.g., `feature/case-management`).
- **Merge Requests**: Squash commits before merging to main to maintain a clean history.
