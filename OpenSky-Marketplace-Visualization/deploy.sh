#!/usr/bin/env bash
# Self-contained deploy for the OpenSky "A Day Over" app (Databricks Apps).
#
#   1. sources deploy/.env (per-environment settings; gitignored)
#   2. rebuilds the frontend from ../app if present, else ships the committed dist/
#   3. ensures the UC volume for regenerated artifacts exists
#   4. bundle deploy + run (prints the app URL)
#   5. grants the app's service principal the access the ingest path needs
#
# Usage: ./deploy.sh [--no-build] [--target dev|dogfood] [--profile NAME]
set -euo pipefail
cd "$(dirname "$0")"

# ---- config ----
BUILD=1
CLI_TARGET=""
CLI_PROFILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-build) BUILD=0 ;;
    --target) CLI_TARGET="$2"; shift ;;
    --profile) CLI_PROFILE="$2"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ ! -f .env ]; then
  echo "ERROR: deploy/.env not found. Copy .env.example -> .env and edit it." >&2
  exit 1
fi
set -a; . ./.env; set +a
TARGET="${CLI_TARGET:-${TARGET:-dev}}"
PROFILE="${CLI_PROFILE:-${PROFILE:?set PROFILE in .env}}"
APP_NAME="opensky-europe-vis"
: "${OPENSKY_WAREHOUSE_ID:?}" "${OPENSKY_VOLUME_ROOT:?}" "${OPENSKY_CATALOG:?}" "${OPENSKY_SCHEMA:?}"
: "${VOL_CATALOG:?}" "${VOL_SCHEMA:?}" "${VOL_NAME:?}"

echo "==> target=$TARGET profile=$PROFILE  source=$OPENSKY_CATALOG.$OPENSKY_SCHEMA  volume=$OPENSKY_VOLUME_ROOT"

# ---- 1. build frontend ----
if [ "$BUILD" = "1" ] && [ -d ../app ]; then
  echo "==> building frontend (../app)"
  ( cd ../app && npm run build )
  rm -rf dist && cp -r ../app/dist dist
else
  echo "==> using committed dist/ (no build)"
fi

# ---- 2. ensure the artifacts volume exists (idempotent) ----
echo "==> ensuring volume $VOL_CATALOG.$VOL_SCHEMA.$VOL_NAME"
databricks schemas create "$VOL_SCHEMA" "$VOL_CATALOG" --profile "$PROFILE" >/dev/null 2>&1 \
  && echo "   created schema $VOL_CATALOG.$VOL_SCHEMA" || echo "   schema exists (or no create perm)"
databricks volumes create "$VOL_CATALOG" "$VOL_SCHEMA" "$VOL_NAME" MANAGED --profile "$PROFILE" >/dev/null 2>&1 \
  && echo "   created volume" || echo "   volume exists (or no create perm)"

# ---- 3. deploy + run ----
echo "==> bundle deploy"
databricks bundle deploy -t "$TARGET" --profile "$PROFILE" \
  --var="warehouse_id=$OPENSKY_WAREHOUSE_ID" \
  --var="volume_root=$OPENSKY_VOLUME_ROOT" \
  --var="catalog=$OPENSKY_CATALOG" \
  --var="schema=$OPENSKY_SCHEMA"

echo "==> bundle run"
databricks bundle run opensky_vis -t "$TARGET" --profile "$PROFILE"

# ---- 4. grant the app service principal what the ingest path needs ----
SP="$(databricks apps get "$APP_NAME" --profile "$PROFILE" -o json \
      | python3 -c "import sys,json;print(json.load(sys.stdin)['service_principal_client_id'])")"
echo "==> granting access to app SP $SP"
grant() { # SECURABLE_TYPE FULL_NAME  JSON_PRIV_LIST
  databricks grants update "$1" "$2" --profile "$PROFILE" \
    --json "{\"changes\":[{\"principal\":\"$SP\",\"add\":[$3]}]}" >/dev/null 2>&1 \
    && echo "   +$3 on $1 $2" || echo "   WARN could not grant $3 on $1 $2"
}
# read the Marketplace source
grant CATALOG "$OPENSKY_CATALOG" '"USE_CATALOG"'
grant SCHEMA  "$OPENSKY_CATALOG.$OPENSKY_SCHEMA" '"USE_SCHEMA"'
grant TABLE   "$OPENSKY_CATALOG.$OPENSKY_SCHEMA.state_vectors" '"SELECT"'
# read/write the artifacts volume
grant CATALOG "$VOL_CATALOG" '"USE_CATALOG"'
grant SCHEMA  "$VOL_CATALOG.$VOL_SCHEMA" '"USE_SCHEMA"'
grant VOLUME  "$VOL_CATALOG.$VOL_SCHEMA.$VOL_NAME" '"READ_VOLUME","WRITE_VOLUME"'

URL="$(databricks apps get "$APP_NAME" --profile "$PROFILE" -o json \
       | python3 -c "import sys,json;print(json.load(sys.stdin).get('url',''))")"
echo "==> done. App URL: $URL"
