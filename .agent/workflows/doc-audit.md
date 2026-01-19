---
description: Audit existing documentation to ensure it follows the established templates and structure.
---

# Documentation Audit Workflow

Verify that feature/product documentation follows the established templates.

// turbo-all

## Step 1: Identify Target

Choose what to audit:
- **Single feature**: `backend/modules/.../[feature]/docs/`
- **All B2B features**: `backend/modules/domains/b2b/*/docs/`
- **All B2C features**: `backend/modules/domains/b2c/*/docs/`

## Step 2: Check Structure Compliance

For each `docs/` folder, verify required files exist:

```bash
# List structure
ls -la [feature]/docs/
ls -la [feature]/docs/pages/
ls -la [feature]/docs/technical/
ls -la [feature]/docs/demos/
ls -la [feature]/docs/wireframes/
```

### Required Files Checklist

| File/Folder | Required | Template |
|-------------|----------|----------|
| `docs/README.md` | ✅ Yes | Product overview |
| `docs/personas.md` | ✅ Yes | User personas |
| `docs/navigation.md` | ✅ Yes | Navigation IA |
| `docs/pages/` | ✅ Yes | Page specifications |
| `docs/technical/api.md` | ✅ Yes | API reference |
| `docs/technical/schema.md` | ✅ Yes | Database tables |
| `docs/technical/architecture.md` | ✅ Yes | Data flow |
| `docs/demos/` | ⚠️ Recommended | Demo scripts |
| `docs/wireframes/` | ⚠️ Recommended | UI wireframes |

## Step 3: Check Content Compliance

For each file, verify it follows the template structure:

### README.md
- [ ] Has "Overview" section?
- [ ] Has "Target Platform" checkboxes?
- [ ] Has "Documentation" table with links?
- [ ] Links to all sub-sections work?

### personas.md
- [ ] Has persona table at top?
- [ ] Each persona has: Profile, Goals, Pain Points, Key Pages, Workflow?

### navigation.md
- [ ] Has navigation tree/structure?
- [ ] Has permission-based visibility table?
- [ ] Has page hierarchy diagram?

### pages/*.md
- [ ] Each page has: Overview table (Goal, Persona, Permission)?
- [ ] Each page has: Features/Widgets table?
- [ ] Each page has: User Stories?
- [ ] Each page links to technical/api.md?

### technical/api.md
- [ ] Has base path defined?
- [ ] Has method/path/description/permission table?
- [ ] Has request/response examples?

### technical/schema.md
- [ ] Has schema name defined?
- [ ] Each table has columns/types/descriptions?
- [ ] Has relationships diagram?

### technical/architecture.md
- [ ] Has data flow mermaid diagram?
- [ ] Has key components table?
- [ ] Has testing section?

## Step 4: Check Root Linkage

Verify the docs are linked from parent indices:

```bash
# Check if feature is linked in module README
grep -l "[feature]" backend/modules/.../README.md

# Check if major features are in docs/README.md
grep -l "[feature]" docs/README.md
```

## Step 5: Generate Audit Report

Create a report with:

| Feature | Structure | Content | Linkage | Status |
|---------|-----------|---------|---------|--------|
| bank_surveillance | ✅ | ✅ | ⚠️ Missing | Needs update |
| billing | ❌ Missing pages/ | ❌ | ❌ | Non-compliant |

## Step 6: Fix Issues

For each non-compliant feature:
1. Copy missing template files from `.agent/skills/product-doc-generator/templates/`
2. Fill in content using discovery from code
3. Add links to root indices
4. Re-run audit to verify

---

## Quick Audit Command

```bash
# Check if all required files exist for a feature
feature="backend/modules/domains/b2b/bank_surveillance"

echo "=== Checking $feature ==="
[ -f "$feature/docs/README.md" ] && echo "✅ README.md" || echo "❌ README.md"
[ -f "$feature/docs/personas.md" ] && echo "✅ personas.md" || echo "❌ personas.md"
[ -f "$feature/docs/navigation.md" ] && echo "✅ navigation.md" || echo "❌ navigation.md"
[ -d "$feature/docs/pages" ] && echo "✅ pages/" || echo "❌ pages/"
[ -f "$feature/docs/technical/api.md" ] && echo "✅ technical/api.md" || echo "❌ technical/api.md"
[ -f "$feature/docs/technical/schema.md" ] && echo "✅ technical/schema.md" || echo "❌ technical/schema.md"
[ -f "$feature/docs/technical/architecture.md" ] && echo "✅ technical/architecture.md" || echo "❌ technical/architecture.md"
```
