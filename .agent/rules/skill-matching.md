---
description: Handle requests where no existing skill matches - inform user and ask how to proceed.
---

# Skill Matching Rule

## Documentation Skill Selection

| Request Type | Use Skill |
|-------------|-----------|
| Full feature docs (product + tech) | `product-doc-generator` |
| Guides, runbooks, dev tools | `doc-generator` |
| System architecture, standards | `system-doc-maintainer` |

## Trigger Phrase Quick Reference

| Phrase Contains | Skill |
|-----------------|-------|
| "personas", "wireframes", "demo scripts", "page specs", "feature docs" | `product-doc-generator` |
| "guide for", "runbook for", "tool README" | `doc-generator` |
| "architecture", "standards", "policy" | `system-doc-maintainer` |

## When No Skill Matches

If a documentation request doesn't fit any skill:

1. **Inform the user**:
   > "No matching documentation skill found for this request."
   >
   > Options:
   > 1. Proceed with ad-hoc documentation
   > 2. Create a new skill for this type
   > 3. Adjust request to fit an existing skill

2. **Wait for user decision** before proceeding.
