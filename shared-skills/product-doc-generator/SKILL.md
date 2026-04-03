---
description: Generate comprehensive product documentation (product + technical) for a feature or domain at the code location.
---

# Product Documentation Generator

Generate complete feature documentation including both **product specs** (personas, pages, demos) and **technical specs** (API, schema, architecture) in a unified structure.

## When To Use

**Use this skill when asked to:**
- Create full documentation for a feature/product
- Document personas, user journeys, page specs
- **Create standard folders: `wireframes/`, `demos/` `pages/` `technical/` (MANDATORY)**
- Generate visual assets if context permits (Optional)
- Document APIs, schemas as part of a feature

**Do NOT use this skill for:**
- System-wide architecture → use `system-doc-maintainer`
- Standalone guides/runbooks → use `doc-generator`

**Trigger Phrases:**
- "Create docs for [Feature/Product]"
- "Document [Feature] with personas and API"
- "Create wireframes and demo scripts for [Feature]"

---

## Output Structure

Documentation lives at the **code location** in a `docs/` folder:

```
backend/modules/[path]/[feature]/
├── docs/
│   ├── README.md           # Overview + links
│   ├── personas.md         # User personas
│   ├── navigation.md       # Navigation IA
│   ├── features/           # Feature cards (implementation-ready)
│   │   └── [feature].md
│   ├── pages/              # Per-page specs
│   │   └── [page].md
│   ├── wireframes/         # Wireframe images
│   │   └── [page].png
│   ├── demos/              # Demo scripts
│   │   └── [persona].md
│   └── technical/          # Technical docs
│       ├── api.md
│       ├── schema.md
│       └── architecture.md
└── [code files]
```

---

## Templates

Use the template files in this skill's `templates/` folder:

| Template | Path | Purpose |
|----------|------|---------|
| README | `templates/docs/README.md` | Product overview |
| Personas | `templates/docs/personas.md` | User personas |
| Navigation | `templates/docs/navigation.md` | Navigation IA |
| **Feature Card** | `templates/docs/features/_feature_template.md` | **Implementation-ready feature spec** |
| Page Spec | `templates/docs/pages/_page_template.md` | Per-page specification |
| Demo Script | `templates/docs/demos/_demo_template.md` | Per-persona demo |
| API | `templates/docs/technical/api.md` | API reference |
| Schema | `templates/docs/technical/schema.md` | Database schema |
| Architecture | `templates/docs/technical/architecture.md` | Data flow, components |

**CRITICAL**: Copy templates to target location and fill in content. Do not modify template files.

---

## Step 1: Discovery

1. **Identify feature location**: Where does the code live?
2. **List components**:
   - Routers → for API docs
   - Models → for schema docs
   - Services → for architecture docs
3. **Identify personas**: Who uses this feature?
4. **List pages**: What UI pages exist?

## Step 2: Create Product Docs

1. **Copy templates** to `[feature]/docs/`
2. Fill in:
   - `README.md` → Overview, links, and **User Stories (Must use numbered lists)**
   - `personas.md` → User personas
   - `navigation.md` → Navigation IA
   - `pages/[page].md` → One per UI page
   - `demos/[persona].md` → One per persona

## Step 3: Create Feature Cards

**Feature cards** are implementation-ready specifications that link product and technical docs.

1. Create `features/[feature-name].md` from template
2. Fill in:
   - Status, module, priority
   - Implementation checklist (components marked `[NEW]`)
   - Workflows (trigger → processing → output)
   - Design decisions
3. **Purpose**: When you say "Implement [feature]", Claude reads this card to understand what to build.

## Step 4: Create Technical Docs

1. Fill in `technical/`:
   - `api.md` → All endpoints from routers
   - `schema.md` → All tables from models
   - `architecture.md` → Data flow, components, testing

## Step 4: Generate Wireframes

Use `generate_image` tool:
```
Clean grayscale UI wireframe for [page description].
Layout: [describe layout].
Clean enterprise wireframe style, grayscale only.
```

Save to: `docs/wireframes/[page].png`

## Step 5: Link to Root Indices

**CRITICAL**: Always link new product docs to parent indices.

### Linking Chain

```
README.md (project root)
    └── backend/modules/b2b/README.md (module index)
        └── domains/b2b/[feature]/docs/README.md (feature docs)
```

### Required Links

1. **Module Index** (REQUIRED): Add link in `backend/modules/b2b/README.md`:
   ```markdown
   ### Domain Features
   - [Feature Name](../domains/b2b/[feature]/docs/README.md)
   ```

2. **Root README** (if major product): Add in "Products" or "Domain Features" section

### Verification
```bash
# Check if feature is linked in module README
grep "[feature]" backend/modules/b2b/README.md
```

---

## Step 6: Verify Links

**CRITICAL**: Check for dead links before finishing.

1. **Internal Links**: Do `[link](./file.md)` paths exist?
2. **Anchor Links**: Does `#anchor` exist in target file?

**Quick Check**:
```bash
# Check for broken relative links
grep -r "\[.*\](.*)" [feature]/docs/
```

---

## Quality Checklist

- [ ] README links to all sections?
- [ ] All personas documented?
- [ ] All pages have specs?
- [ ] All API endpoints documented?
- [ ] All database tables documented?
- [ ] Demo scripts cover personas?
- [ ] Wireframes generated for key pages?
- [ ] **Linked from module index?**
- [ ] **Linked from docs/README.md (if major feature)?**
- [ ] **No dead links?**
