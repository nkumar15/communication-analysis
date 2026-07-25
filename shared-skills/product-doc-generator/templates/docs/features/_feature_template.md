# Feature: [Feature Name]

> **Status**: 📝 Documented | 🚧 In Progress | ✅ Complete  
> **Module**: `[module_name]`  
> **Priority**: High | Medium | Low  

---

## Summary

[1-2 sentence description of what this feature does]

```
[Data flow or entity diagram, e.g.:]
Input → Processing → Output
```

---

## Quick Reference

| Document | Path |
|----------|------|
| Product Specs | [README.md](../README.md) |
| Personas | [personas.md](../personas.md) |
| Page Specs | [pages/](../pages/) |
| Architecture | [technical/architecture.md](../technical/architecture.md) |
| API Reference | [technical/api.md](../technical/api.md) |
| Database Schema | [technical/schema.md](../technical/schema.md) |

---

## User Stories

1. As a [persona], I want to [action] so that [benefit].
2. As a [persona], I want to [action] so that [benefit].
3. ...

---

## Workflows

### Workflow A: [Name]
- **Trigger**: `[How is it triggered - UI action, API call, scheduled]`
- **Processing**: `[Sync API | Celery Worker | Scheduled Job]`
- **Output**: `[What is produced]`

### Workflow B: [Name]
- **Trigger**: ...
- **Processing**: ...
- **Output**: ...

---

## Implementation Checklist

### New Components (Priority 1)
- [ ] `models/[new_model].py` - [Description]
- [ ] `services/[new_service].py` - [Description]

### Updates (Priority 2)
- [ ] `models/[existing].py` - [What changes]
- [ ] `routers/[existing].py` - [What changes]

### Database Migration
- [ ] Create `[schema].[table]` table
- [ ] Add columns to `[schema].[existing_table]`

### API Endpoints
- [ ] `[METHOD] /path` - [Description]

### Tests
- [ ] Unit tests in `tests/[module]/units/`
- [ ] Service tests in `tests/[module]/services/`
- [ ] API tests in `tests/[module]/api/`

---

## How to Implement

Tell Claude:

> **"Implement the [Feature Name] feature for [module]"**

Or be specific:

> **"Implement components marked [NEW] in [module]/docs/technical/architecture.md"**

---

## Design Decisions

| Topic | Decision |
|-------|----------|
| [Topic 1] | [Decision and rationale] |
| [Topic 2] | [Decision and rationale] |

---

## Related Features (Future)

- [ ] [Related feature 1] - [Brief description]
- [ ] [Related feature 2] - [Brief description]
