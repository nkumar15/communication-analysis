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

# ── Check 4: Migration files — remind about schema requirements ───────────────
if echo "$FILE_PATH" | grep -qE "migrations/versions/[^/]+\.py$"; then
    WARNINGS+=("MIGRATION REMINDER — before committing this migration verify:
  • New tenant-scoped tables have: tenant_id (UUID, indexed), created_at + updated_at (TIMESTAMPTZ), UUID primary key
  • Foreign keys are used for relations (no raw IDs stored in JSONB)
  • Run: make db-setup-auth  after applying to re-apply RLS policies")
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
