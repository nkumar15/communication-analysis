# Contributing to Enterprise SSO

Guide for developers working on this project.

## 🚀 Getting Started

1. **Read documentation first:**
   - [README.md](./README.md) - Project overview
   - [Roadmap](docs/planning/roadmap.md) - Current state & planned features
   - [Development Guide](docs/guides/development.md) - Setup & testing
   - [Architecture](docs/architecture/overview.md) - Technical decisions

2. **Setup local environment:**
   ```bash
   make setup    # Creates .env files
   make up       # Start services
   make migrate  # Run migrations
   cd frontend && npm start
   ```

3. **Check what's already done:**
   - Review [Completed Phases](docs/planning/completed-phases.md)
   - Check existing code in relevant service/component

---

## 📝 Before Starting Work

### 1. Check ROADMAP.md

- Is this feature already planned?
- Is someone else working on it?
- Should it be broken into smaller tasks?

### 2. Create GitHub Issue (or similar)

```markdown
Title: [Feature] Add audit logging

Description:
- What: Add audit log table tracking user actions
- Why: Security compliance requirement
- How: New AuditLog model, middleware for tracking
- References: See docs/planning/roadmap.md "Audit logging"
```

### 3. Update ROADMAP.md

Move item from "Planned" to "In Progress":

```markdown
## 🚧 In Progress
- [/] Audit logging (@yourname - Issue #42)
```

---

## 🔨 Development Workflow

### Branch Naming

```
feature/audit-logging
bugfix/activation-token-expiry
docs/update-deployment-guide
```

### Commit Messages

```
feat: add audit log table and middleware
fix: correct activation token expiry check
docs: update deployment guide with SSL setup
```

### Pull Request Template

```markdown
## What
Brief description of changes

## Why
Why this change is needed

## How
Technical approach taken

## Testing
- [ ] E2E test passes
- [ ] Unit tests added/updated
- [ ] Manual testing completed

## Documentation
- [ ] Updated docs/planning/roadmap.md
- [ ] Updated docs/guides/development.md (if architectural)
- [ ] Added comments to complex code

## Checklist
- [ ] Code follows existing patterns
- [ ] Database migration included (if schema change)
- [ ] No sensitive data in commits
- [ ] Tests pass locally
```

---

## 🏗️ Code Organization Patterns

### Backend

**Services** (`backend/app/services/`)
- Business logic goes here
- One service per domain (tenant, user, invitation, etc.)
- Services are dependency-injected

```python
# Example: user_service.py
class UserService:
    async def create_user(self, db, ...):
        # Business logic here
```

**Routers** (`backend/app/routers/`)
- API endpoints only
- Minimal logic, delegate to services
- Handle request/response

```python
# Example: users.py
@router.post("/users")
async def create_user(
    request: CreateUserRequest,
    db: AsyncSession = Depends(get_db)
):
    return await user_service.create_user(db, ...)
```

**Models** (`backend/app/db_models.py`)
- SQLAlchemy ORM models
- Database schema representation

### Frontend

**Components** (`frontend/src/components/`)
- Reusable UI components
- Keep them focused and small

**Services** (`frontend/src/services/`)
- API calls
- Firebase integration
- Business logic

---

## 🧪 Testing Requirements

### Before Committing

```bash
# Backend checks
make logs  # No errors

# Database check
make db-shell
# Verify migrations applied

# Frontend
npm start  # Compiles without errors
```

### Before PR

1. **E2E test:** Complete activation flow works
2. **Manual testing:** Test your specific feature
3. **Regression:** Existing features still work

---

## 📚 Documentation Updates

### When to Update Docs

**Always update:**
- `docs/planning/roadmap.md` - Move completed items, add discoveries
- Code comments - Explain "why", not "what"

**Sometimes update:**
- `docs/guides/development.md` - New setup steps, new patterns
- `docs/architecture/overview.md` - Architectural decisions
- `README.md` - New major features

**Example ROADMAP update:**
```markdown
## ✅ Recently Completed
- [x] Audit logging (2025-11-24) - Tracks user actions for compliance

## 💡 Discovered During Development
- Firebase has built-in audit logs, but we need custom ones for business logic
- Added middleware pattern for automatic tracking
```

---

## 🤝 Team Coordination

### Daily Standup Topics

- What you completed (update ROADMAP.md)
- What you're working on (check for conflicts)
- Blockers (database migrations, API changes)

### Before Making Breaking Changes

1. **Discuss in issue/PR**
2. **Update ARCHITECTURE.md** with decision
3. **Create migration guide** if needed
4. **Notify team** before merging

---

## 🔥 Common Pitfalls

### ❌ Don't Do This

- Start work without checking ROADMAP
- Make database changes without migration
- Skip documentation updates
- Commit secrets or credentials
- Make major changes without discussion

### ✅ Do This

- Check ROADMAP.md before starting
- Create migrations for schema changes
- Update docs as you code
- Use .env for configuration
- Discuss big changes in issues

---

## 🆘 Getting Help

1. **Check docs first** - Most answers are here
2. **Search issues** - Someone may have asked
3. **Ask in team chat** - Don't struggle alone
4. **Pair program** - Complex features benefit from collaboration

---

## 🎓 Learning Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [React Docs](https://react.dev/)

---

**Last Updated:** 2025-11-23
