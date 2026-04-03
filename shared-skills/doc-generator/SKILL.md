---
description: Generate lightweight technical documentation for standalone guides, runbooks, and dev tools.
---

# Documentation Generator (Lightweight)

This skill generates standalone technical documentation that is NOT part of a product/feature.

## When To Use

**Use this skill for:**
- Developer guides (`docs/guides/`)
- Operations runbooks (`docs/operations/`)
- Dev tool READMEs (`backend/tools/`)
- Standalone technical documents

**Do NOT use this skill for:**
- Full feature documentation (product + tech) → use `product-doc-generator`
- System architecture/standards → use `system-doc-maintainer`

**Trigger Phrases:**
- "Create a guide for [workflow]"
- "Write a runbook for [operation]"
- "Document this CLI tool"

---

## Guide vs Operations

| Criteria | Guide (`docs/guides/`) | Operations (`docs/operations/`) |
|----------|------------------------|--------------------------------|
| **Audience** | Developers | DevOps / SRE / On-call |
| **Environment** | Local / Dev / Test | Staging / Production |
| **Purpose** | "How to use the system" | "How to run the system" |
| **Examples** | Local setup, testing, onboarding | Deployment, backups, incidents |

---

## Guide Template

```markdown
# [Task Name] Guide

## Prerequisites
- [Tool/Access required]

## Steps
1. [Step one]
2. [Step two]

## Troubleshooting
| Problem | Solution |
|---------|----------|
| [Issue] | [Fix] |
```

---

## Runbook Template

```markdown
# [Operation] Runbook

## Overview
[What this runbook covers]

## Prerequisites
- [Access/credentials needed]

## Procedure
1. [Step with commands]
2. [Step with commands]

## Rollback
[How to undo if needed]

## Escalation
[Who to contact if issues]
```

---

## Dev Tool Template

```markdown
# [Tool Name]

## Overview
[What the tool does]

## Setup
```bash
pip install -r requirements.txt
```

## Usage
```bash
python -m tools.[name] --config config.yaml
```

## Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `--config` | Config file path | Yes |

## Output
[What the tool produces]
```

---

## Linking

After creating documentation:
1. **Guides**: Link from `docs/guides/README.md`
2. **Runbooks**: Link from `docs/operations/README.md`
3. **Tools**: Link from `backend/tools/README.md`

---

## Checklist Before Delivery

- [ ] Correct template used (Guide / Runbook / Dev Tool)
- [ ] Placed in the right directory (`docs/guides/`, `docs/operations/`, or `backend/tools/`)
- [ ] Linked from the appropriate index README
- [ ] Prerequisites section complete
- [ ] All commands tested or marked as examples
- [ ] Runbooks include Rollback and Escalation sections
