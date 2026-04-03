---
description: Handle requests where no existing skill matches - inform user and ask how to proceed.
---

# Skill Matching Rule

## 1. Automatic vs. Explicit Invocation

Skills are invoked in two modes. Use this decision table to resolve ambiguity:

| Condition | Mode | Action |
|-----------|------|--------|
| User names the skill explicitly ("use pytest-test-generator") | **Explicit** | Invoke immediately |
| User asks to "add tests" / "write tests" for a feature | **Auto** | Invoke `pytest-test-generator` |
| User asks to "create a new endpoint" | **Auto** | Invoke `pydantic-schema-generator` (if schemas change) + `pytest-test-generator` (after endpoint is built) |
| User asks to "add a migration" / "change the schema" | **Auto** | Invoke `db-inspector` first, then `pydantic-schema-generator` if DTOs change |
| User asks for "docs for [Feature]" without specifying type | **Auto** | See §2 to resolve which doc skill |
| User asks to "refactor" existing code | **Do not auto-invoke** | No skill unless test coverage is explicitly requested |
| User asks to "fix a bug" | **Do not auto-invoke** | No skill; add tests only if user asks |
| Request type is ambiguous | **Explicit only** | Ask user before invoking any skill |

**Rule**: When in doubt, do not auto-invoke. One missed skill is better than an unwanted skill execution changing files the user didn't ask to change.

---

## 2. Documentation Skill Selection

| Request Type | Use Skill |
|-------------|-----------|
| Full feature docs (product + tech) | `product-doc-generator` |
| Guides, runbooks, dev tools | `doc-generator` |
| System architecture, standards | `system-doc-maintainer` |

### Trigger Phrase Quick Reference

| Phrase Contains | Skill |
|-----------------|-------|
| "personas", "wireframes", "demo scripts", "page specs", "feature docs" | `product-doc-generator` |
| "guide for", "runbook for", "tool README" | `doc-generator` |
| "architecture", "standards", "policy" | `system-doc-maintainer` |

---

## 3. Multi-Skill Sequences

Some task types trigger multiple skills in a fixed order. Do not reorder:

| Task Type | Skill Sequence |
|-----------|---------------|
| New endpoint (with schema + tests) | `pydantic-schema-generator` → `pytest-test-generator` |
| DB migration (with updated DTOs) | `db-inspector` → `pydantic-schema-generator` |
| New feature (full docs + tests) | `pytest-test-generator` → `product-doc-generator` |

---

## 4. When No Skill Matches

If a documentation request doesn't fit any skill:

1. **Inform the user**:
   > "No matching documentation skill found for this request."
   >
   > Options:
   > 1. Proceed with ad-hoc documentation
   > 2. Create a new skill for this type
   > 3. Adjust request to fit an existing skill

2. **Wait for user decision** before proceeding.
