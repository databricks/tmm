#!/usr/bin/env bash
# Build the Vocareum courseware payload for "Hands on: Agent Apps Workshop" (lab 216857).
#
# Produces dist/ with the THREE files you upload to /voc/private/courseware/:
#   - config.json            (as-is)
#   - agent_apps_setup.zip   (privileged workspace_setup notebook — runs as the init/privileged user)
#   - agent_apps_lab.zip     (per-user student content the framework copies into each home)
#
# Each .zip mirrors a Databricks "export folder as source" archive: a root manifest.mf plus the
# notebook folder (folder name == zip name, which the framework strips on import). config.json's
# `entry` points at the notebook to run inside that folder.
#
# Run:  bash vocareum/voc/private/courseware/build_zips.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
DIST="$HERE/dist"
rm -rf "$DIST"; mkdir -p "$DIST"

make_zip() {
  local folder="$1" out="$2"
  [[ -d "$folder" ]] || { echo "  ERROR: missing source folder $folder"; exit 1; }
  local stage; stage="$(mktemp -d)"
  cp -R "$folder" "$stage/"
  find "$stage" \( -name '.DS_Store' -o -name '*.pyc' \) -delete
  find "$stage" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
  # NOTE: we intentionally do NOT add a manifest.mf — the framework imports plain folder zips fine,
  # and a zip-root manifest.mf lands as a stray file inside the student's content folder (dry-run finding).
  (cd "$stage" && zip -r -q "$out" "$(basename "$folder")" -x '*.DS_Store')
  rm -rf "$stage"
  echo "  built $(basename "$out")"
}

# --- Bake the lab-guide app payload (build artifacts; gitignored) -----------------------------
# guide.html = participant guide rendered with screenshots inlined as data URIs (no binaries in
# the zip — workspace import of arbitrary binary files is unproven). deck.html = the current
# field-guide deck (single source of truth: slides-app/decks/8-bit-orbit.html).
REPO="$(cd "$HERE/../../../.." && pwd)"
echo "  baking guide_app payload..."
python3 "$HERE/render_guide.py" \
  "$REPO/docs/lab-guide/README.md" \
  "$REPO/docs/lab-guide/img" \
  "$HERE/agent_apps_setup/guide_app/guide.html"
cp "$REPO/slides-app/decks/8-bit-orbit.html" "$HERE/agent_apps_setup/guide_app/deck.html"
echo "  copied deck.html (8-bit-orbit)"

make_zip agent_apps_setup "$DIST/agent_apps_setup.zip"
make_zip agent_apps_lab   "$DIST/agent_apps_lab.zip"
cp config.json "$DIST/config.json"

echo "==> dist/ ready. Upload these 3 files to /voc/private/courseware/ in lab 216857"
echo "    (Configure Workspace > Files), replacing the cloned bricks_*.zip + config.json:"
ls -1 "$DIST"
