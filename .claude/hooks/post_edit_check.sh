#!/usr/bin/env bash
# Post-edit guardrail hook for Claude Code
# Reads tool input JSON from stdin, extracts file_path, runs targeted checks.
# Outputs warnings to stdout (visible to Claude). Always exits 0 (non-blocking).

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # PostToolUse wraps under tool_input
    fp = d.get('tool_input', d).get('file_path', '')
    print(fp)
except Exception:
    print('')
" 2>/dev/null <<< "$INPUT" || echo "")

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

WARNINGS=()

# ── Check 1: Router files must not contain direct DB queries ──────────────────
if echo "$FILE_PATH" | grep -qE "routers/[^/]+\.py$"; then
    HITS=$(grep -n \
        -e "await db\.execute" \
        -e "await db\.scalar" \
        -e "await db\.scalars" \
        -e "^[^#]*select(" \
        -e "^[^#]*insert(" \
        -e "^[^#]*update(" \
        -e "^[^#]*delete(" \
        "$FILE_PATH" 2>/dev/null | grep -v "^\s*#" || true)
    if [ -n "$HITS" ]; then
        WARNINGS+=("ROUTER VIOLATION — direct DB query found in router layer. Move to services/:
$HITS")
    fi
fi

# ── Check 2: No bare print() in non-test Python files ────────────────────────
if echo "$FILE_PATH" | grep -qE "\.py$" && ! echo "$FILE_PATH" | grep -qE "(tests?/|test_|_test\.py)"; then
    HITS=$(grep -n "^\s*print(" "$FILE_PATH" 2>/dev/null || true)
    if [ -n "$HITS" ]; then
        WARNINGS+=("PRINT STATEMENT — use get_logger() from infrastructure.logging instead:
$HITS")
    fi
fi

# ── Check 3: Celery tasks must not receive non-primitive arguments ─────────────
if echo "$FILE_PATH" | grep -qE "(tasks?/[^/]+\.py|_tasks?\.py)$"; then
    HITS=$(grep -n \
        -e "\.delay(.*\bdb\b" \
        -e "\.delay(.*session" \
        -e "apply_async.*\bdb\b" \
        "$FILE_PATH" 2>/dev/null || true)
    if [ -n "$HITS" ]; then
        WARNINGS+=("CELERY VIOLATION — only pass primitive IDs to tasks, never DB sessions or ORM objects:
$HITS")
    fi
fi

# ── Check 4: SQL migration files — schema requirements checklist ─────────────
if echo "$FILE_PATH" | grep -qE "migrations/(b2b|b2c|platform|core)/[^/]+\.sql$"; then
    # Check for non-idempotent ADD COLUMN (missing IF NOT EXISTS)
    HITS=$(grep -n "ADD COLUMN [^I]" "$FILE_PATH" 2>/dev/null | grep -v "IF NOT EXISTS" || true)
    if [ -n "$HITS" ]; then
        WARNINGS+=("MIGRATION NOT IDEMPOTENT — use 'ADD COLUMN IF NOT EXISTS':
$HITS")
    fi
    # Check for non-idempotent CREATE INDEX (missing IF NOT EXISTS)
    HITS=$(grep -n "^CREATE INDEX [^I]" "$FILE_PATH" 2>/dev/null | grep -v "IF NOT EXISTS" || true)
    if [ -n "$HITS" ]; then
        WARNINGS+=("MIGRATION NOT IDEMPOTENT — use 'CREATE INDEX IF NOT EXISTS':
$HITS")
    fi
    # Check new tables for missing RLS
    NEW_TABLES=$(grep -n "^CREATE TABLE" "$FILE_PATH" 2>/dev/null || true)
    if [ -n "$NEW_TABLES" ]; then
        HAS_RLS=$(grep -c "ENABLE ROW LEVEL SECURITY\|DISABLE ROW LEVEL SECURITY" "$FILE_PATH" 2>/dev/null || echo "0")
        if [ "$HAS_RLS" -eq 0 ]; then
            WARNINGS+=("MIGRATION — new table(s) found but no RLS policy set.
  Every new tenant-scoped table needs ENABLE ROW LEVEL SECURITY + isolation policy.
  Global/shared tables must explicitly DISABLE ROW LEVEL SECURITY.
$NEW_TABLES")
        fi
    fi
fi

# ── Check 4b: Model edits — remind to create a migration ─────────────────────
if echo "$FILE_PATH" | grep -qE "models/[^/]+\.py$" && ! echo "$FILE_PATH" | grep -qE "(test_|_test\.py)"; then
    # Look for Column( additions that suggest a schema change
    HITS=$(grep -n "Column(" "$FILE_PATH" 2>/dev/null || true)
    if [ -n "$HITS" ]; then
        # Determine product from path
        PRODUCT="b2b"
        echo "$FILE_PATH" | grep -q "b2c"      && PRODUCT="b2c"
        echo "$FILE_PATH" | grep -q "platform"  && PRODUCT="platform"
        NEXT_NUM=$(ls "$(dirname "$FILE_PATH"/../../../migrations/$PRODUCT/)"*.sql 2>/dev/null | \
            sort | tail -1 | grep -oE '[0-9]{3}' | head -1 || echo "???")
        WARNINGS+=("MODEL CHANGE DETECTED — ensure a migration file exists.
  Check: backend/migrations/$PRODUCT/ for a matching SQL file.
  Next number after current last: use 'ls backend/migrations/$PRODUCT/ | sort | tail -1'
  See: .agent/rules/db-migration-standards.md")
    fi
fi

# ── Check 5: New service files should not import from routers ────────────────
if echo "$FILE_PATH" | grep -qE "services/[^/]+\.py$"; then
    HITS=$(grep -n "from.*routers" "$FILE_PATH" 2>/dev/null || true)
    if [ -n "$HITS" ]; then
        WARNINGS+=("LAYER VIOLATION — services must not import from routers:
$HITS")
    fi
fi

# ── Output ────────────────────────────────────────────────────────────────────
if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  GUARDRAIL WARNINGS — ${FILE_PATH##*/}"
    echo "╚══════════════════════════════════════════════════════════════╝"
    for w in "${WARNINGS[@]}"; do
        echo ""
        echo "  ⚠  $w"
    done
    echo ""
fi

exit 0
