#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup-lakebase.sh  (Claude Code SessionStart hook)
#
# Runs when a Claude session starts. Inside a Claude worktree it provisions a
# Lakebase branch (copy-on-write from production) matching the Git branch, and
# exports the branch's non-secret resource identifiers to the session so that
# subsequent tools/commands target the preview database, never production.
#
# In the main checkout (not a worktree) it does nothing.
# ---------------------------------------------------------------------------
set -euo pipefail

# ---------------------------------------------------------
# CONFIGURE THESE (env overrides win)
# ---------------------------------------------------------
LAKEBASE_PROJECT_ID="${LAKEBASE_PROJECT_ID:-appkit-lakebase-db}"
LAKEBASE_PARENT_BRANCH="${LAKEBASE_PARENT_BRANCH:-production}"
LAKEBASE_DATABASE_ID="${LAKEBASE_DATABASE_ID:-databricks-postgres}"

# ---------------------------------------------------------
# ONLY RUN INSIDE A GIT WORKTREE
# ---------------------------------------------------------
cd "$CLAUDE_PROJECT_DIR"

GIT_DIR="$(git rev-parse --git-dir)"
COMMON_DIR="$(git rev-parse --git-common-dir)"

# In the main checkout these resolve to the same git area; in a linked
# worktree they differ.
if [[ "$(cd "$GIT_DIR" && pwd)" == "$(cd "$COMMON_DIR" && pwd)" ]]; then
  echo "Main checkout detected. Lakebase preview provisioning skipped."
  exit 0
fi

GIT_BRANCH="$(git branch --show-current)"
if [[ -z "$GIT_BRANCH" ]]; then
  echo "Detached HEAD. Lakebase provisioning skipped."
  exit 0
fi

# ---------------------------------------------------------
# TURN GIT BRANCH INTO A SAFE LAKEBASE ID (shared script)
# ---------------------------------------------------------
LAKEBASE_BRANCH="$("$CLAUDE_PROJECT_DIR/scripts/branch-name.sh" "$GIT_BRANCH")"

PROJECT="projects/${LAKEBASE_PROJECT_ID}"
BRANCH="${PROJECT}/branches/${LAKEBASE_BRANCH}"
PARENT="${PROJECT}/branches/${LAKEBASE_PARENT_BRANCH}"
DATABASE="${BRANCH}/databases/${LAKEBASE_DATABASE_ID}"

# ---------------------------------------------------------
# CREATE PREVIEW BRANCH IF IT DOES NOT EXIST
#
# Cleanup is belt-and-suspenders:
#   - The `Cleanup Lakebase Branch` GitHub Action deletes this branch
#     promptly when its PR is closed (the normal path).
#   - The 30-day TTL is a safety net that reclaims branches whose PR is
#     never opened. It is a fixed deadline from creation (Lakebase does not
#     support extending a branch's TTL), so it is set well beyond the life
#     of a feature branch to avoid deleting active work.
# ---------------------------------------------------------
LAKEBASE_TTL="${LAKEBASE_TTL:-2505600s}"  # 29 days (just under Lakebase's exclusive 30-day max)

if databricks postgres get-branch "$BRANCH" >/dev/null 2>&1; then
  echo "Lakebase branch already exists: $LAKEBASE_BRANCH"
else
  echo "Creating Lakebase branch: $LAKEBASE_BRANCH (ttl: $LAKEBASE_TTL)"
  databricks postgres create-branch \
    "$PROJECT" \
    "$LAKEBASE_BRANCH" \
    --json "{
      \"spec\": {
        \"source_branch\": \"${PARENT}\",
        \"ttl\": \"${LAKEBASE_TTL}\"
      }
    }"
fi

# ---------------------------------------------------------
# EXPOSE NON-SECRET RESOURCE IDENTIFIERS TO CLAUDE
# ---------------------------------------------------------
if [[ -n "${CLAUDE_ENV_FILE:-}" ]]; then
  cat >> "$CLAUDE_ENV_FILE" <<EOF
export AGENT_ENV="lakebase-preview"
export LAKEBASE_PROJECT_ID="${LAKEBASE_PROJECT_ID}"
export LAKEBASE_PARENT_BRANCH="${LAKEBASE_PARENT_BRANCH}"
export LAKEBASE_BRANCH="${LAKEBASE_BRANCH}"
export LAKEBASE_BRANCH_RESOURCE="${BRANCH}"
export LAKEBASE_DATABASE_RESOURCE="${DATABASE}"

unset PROD_DATABASE_URL
unset PRODUCTION_DATABASE_URL
EOF
fi

echo
echo "Agent database environment:"
echo "  Git branch:      $GIT_BRANCH"
echo "  Lakebase branch: $LAKEBASE_BRANCH"
echo "  Database:        $DATABASE"
