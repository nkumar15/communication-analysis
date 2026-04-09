---
name: release-manager
description: Manage per-domain releases — inspect changes, generate CHANGELOG entries, cut annotated git tags, and audit past releases.
---

# Release Manager Skill

This skill handles the full release workflow for any domain or portfolio in this monorepo. Each domain has its own version history and can be released independently.

---

## Domain Registry

| Key | Scope Paths | Tag Prefix | CHANGELOG |
|-----|-------------|-----------|-----------|
| `bank` | `backend/modules/domains/b2b/bank_surveillance/`<br>`frontend/src/modules/domains/surveillance/` | `bank/` | `backend/modules/domains/b2b/bank_surveillance/CHANGELOG.md` |
| `task` | `backend/modules/domains/b2b/task_management/` | `task/` | `backend/modules/domains/b2b/task_management/CHANGELOG.md` |
| `b2b-foundation` | `backend/modules/b2b/`<br>`workers/b2b_worker/` | `b2b-foundation/` | `backend/modules/b2b/CHANGELOG.md` |
| `b2c-foundation` | `backend/modules/b2c/`<br>`workers/b2c_worker/` | `b2c-foundation/` | `backend/modules/b2c/CHANGELOG.md` |
| `platform` | `backend/modules/platform/` | `platform/` | `backend/modules/platform/CHANGELOG.md` |
| `portfolio` | entire repo | `portfolio/` | `CHANGELOG.md` (root) |

---

## Versioning Convention

**Per-domain semver tags** on `main` or `develop`:

```
bank/v1.3.0          — bank_surveillance changes only
task/v1.0.0          — task_management
b2b-foundation/v2.1.0 — B2B auth/RBAC/billing/teams
portfolio/v2026-04   — monthly cloud demo snapshot
```

**Bump rules from conventional commits** (scoped to domain paths only):

| Commits in range | Bump |
|-----------------|------|
| Only `fix:` commits | patch (x.y.Z) |
| Any `feat:` commit | minor (x.Y.0) |
| Any `feat!:` or `BREAKING CHANGE` footer | major (X.0.0) |

A domain release does **not** require bumping the foundation version unless foundation paths changed.

---

## Workflow 1 — Inspect

**Trigger phrases:** "What's changed in bank since last release?", "Inspect task changes"

### Steps

1. Find the last tag for the domain:
   ```bash
   git tag --list "{prefix}*" | sort -V | tail -1
   # e.g. git tag --list "bank/*" | sort -V | tail -1
   ```

2. List commits since that tag scoped to domain paths:
   ```bash
   git log {last_tag}..HEAD --oneline -- {scope_paths...}
   # e.g. git log bank/v1.2.0..HEAD --oneline -- \
   #   backend/modules/domains/b2b/bank_surveillance/ \
   #   frontend/src/modules/domains/surveillance/
   ```
   If no tag exists yet, use the full history: `git log --oneline -- {scope_paths...}`

3. Group commits by type:
   - `feat:` → Added / Changed
   - `fix:` → Fixed
   - `refactor:` / `chore:` → Internal (mention count only)
   - Non-conventional → flag explicitly for review

4. Suggest version bump based on rules above.

5. Report:
   ```
   Domain: bank
   Last tag: bank/v1.2.0 (2026-03-01)
   Commits since: 12
   Suggested bump: minor → bank/v1.3.0

   feat: ...
   feat: ...
   fix: ...
   ⚠ Non-conventional: "random commit message" (review needed)
   ```

---

## Workflow 2 — Generate

**Trigger phrases:** "Generate CHANGELOG entry for bank", "Write release notes for task"

### Steps

1. Run Workflow 1 (Inspect) to get the commit list.

2. Group into Keep-a-Changelog sections:
   - **Added** — new features (`feat:`)
   - **Changed** — behaviour changes (`feat:` that modify existing)
   - **Fixed** — bug fixes (`fix:`)
   - **Removed** — deleted features
   - **Security** — security fixes

3. Draft the entry and **present it to the user for review** before writing:
   ```markdown
   ## [bank/v1.3.0] — 2026-04-06

   ### Added
   - Alert ego-network visualization on alert detail page
   - Hybrid search with highlighting in intelligence archive

   ### Fixed
   - RBAC sidebar visibility for surveillance_chief role
   - tenant.domain_type not set during demo onboarding
   ```

4. On user confirmation:
   - Prepend the entry to the domain's CHANGELOG.md (create if missing)
   - Update the root `CHANGELOG.md` index with the new version reference

### CHANGELOG File Format

```markdown
# Changelog — {Domain Name}

All notable changes to this domain are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/)

## [bank/v1.3.0] — 2026-04-06

### Added
- ...

### Fixed
- ...

## [bank/v1.2.0] — 2026-03-01
...
```

### Root CHANGELOG.md Format

```markdown
# Changelog

## Portfolio snapshot: portfolio/v2026-04 — 2026-04-06
| Component | Version |
|-----------|---------|
| bank_surveillance | bank/v1.3.0 |
| b2b-foundation | b2b-foundation/v2.1.0 |

## Component Changelogs
- [Bank Surveillance](backend/modules/domains/b2b/bank_surveillance/CHANGELOG.md)
- [Task Management](backend/modules/domains/b2b/task_management/CHANGELOG.md)
- [B2B Foundation](backend/modules/b2b/CHANGELOG.md)
- [B2C Foundation](backend/modules/b2c/CHANGELOG.md)
- [Platform](backend/modules/platform/CHANGELOG.md)
```

---

## Workflow 3 — Tag

**Trigger phrases:** "Cut a release for bank", "Tag bank as v1.3.0", "Release bank/v1.3.0"

### Pre-flight Checks (all must pass)

1. Working tree is clean: `git status --porcelain` returns empty
2. On `develop` or `main` branch
3. CHANGELOG entry exists for this version in the domain CHANGELOG
4. Tag does not already exist: `git tag --list "{tag}"` returns empty

If any check fails, report the blocker and stop.

### Tag Creation

```bash
git tag -a bank/v1.3.0 -m "Bank Surveillance v1.3.0 — {one-line summary from CHANGELOG}"
```

### Push Offer

After creating the tag, ask the user:
> Tag `bank/v1.3.0` created locally. Push to origin?

If confirmed:
```bash
git push origin bank/v1.3.0
```

For portfolio releases, also offer to create a GitHub release:
```bash
gh release create portfolio/v2026-04 --title "Portfolio v2026-04" --notes-file CHANGELOG.md
```

---

## Workflow 4 — Audit

**Trigger phrases:** "What's in release bank/v1.2.0?", "Audit bank/v1.2.0"

### Steps

1. Find the previous tag for the domain:
   ```bash
   git tag --list "bank/*" | sort -V | grep -B1 "^bank/v1.2.0$" | head -1
   ```

2. Show commits in the release range scoped to domain paths:
   ```bash
   git log {prev_tag}..bank/v1.2.0 --oneline -- {scope_paths...}
   ```

3. Highlight any DB migrations in the range:
   ```bash
   git log {prev_tag}..bank/v1.2.0 --oneline -- backend/migrations/
   ```

4. Report summary:
   ```
   Release: bank/v1.2.0
   Date: 2026-03-01
   Range: bank/v1.1.0..bank/v1.2.0
   Commits: 8 (4 feat, 3 fix, 1 chore)
   DB migrations: 2 files changed
     - backend/migrations/b2b/028_add_region_sensitivity_to_alerts.sql
     - backend/migrations/b2b/029_add_clearance_level_to_team_role_definitions.sql
   ```

---

## General Rules

- **Never tag on a feature branch.** Tags go on `develop` or `main` only.
- **Never auto-push.** Always offer and wait for user confirmation before `git push`.
- **Never modify history.** If a tag was created incorrectly, create a new one with a patch bump — do not delete and recreate published tags.
- **Scope strictly.** When inspecting commits, only count commits that touch the domain's registered paths. A commit that touches `backend/modules/b2b/` does not count as a `bank` change.
