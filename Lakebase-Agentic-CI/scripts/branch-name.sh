#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# branch-name.sh
#
# Normalize a Git branch name into a valid Lakebase branch id (RFC 1123):
#   - lowercase
#   - only [a-z0-9-]
#   - collapse repeats, trim leading/trailing hyphens
#   - <= 63 chars
#   - must start with a letter (prefixed with "agent-" otherwise)
#
# Shared by .claude/hooks/setup-lakebase.sh and the GitHub Actions workflows
# so the local dev branch and the CI preview branch always resolve to the
# same Lakebase branch id.
#
# Usage: scripts/branch-name.sh <git-branch-name>
# ---------------------------------------------------------------------------
set -euo pipefail

GIT_BRANCH="${1:-}"
if [[ -z "$GIT_BRANCH" ]]; then
  echo "usage: branch-name.sh <git-branch-name>" >&2
  exit 1
fi

LAKEBASE_BRANCH="$(
  printf '%s' "$GIT_BRANCH" |
    tr '[:upper:]_/' '[:lower:]--' |
    sed \
      -e 's/[^a-z0-9-]/-/g' \
      -e 's/--*/-/g' \
      -e 's/^-//' \
      -e 's/-$//' |
    cut -c1-63
)"

if [[ ! "$LAKEBASE_BRANCH" =~ ^[a-z] ]]; then
  LAKEBASE_BRANCH="agent-$LAKEBASE_BRANCH"
fi

printf '%s\n' "$LAKEBASE_BRANCH"
