# OpenSky-Marketplace-Visualization — "A Day Over" Databricks App

The **self-contained, portable** deployable for the OpenSky "A Day Over" visualization. Everything
needed to run and deploy is in this folder; the built SPA is committed in `dist/`, so no Node build
is required. (The Vite/React frontend source and the offline SQL pipeline live in the author's
separate project and are not needed here.)

For humans: see **`README.md`** (overview, screenshots, full deploy walkthrough).
For the ingest internals: see **`DESIGN.md`**.

## What's here
- `dist/` — the built SPA + bundled data snapshot (`dist/data/<region>/*.json.gz`).
- `server.py` — stdlib static server + optional ingest API (Databricks/SDK work is lazy, so the static app boots fast).
- `sql.py`, `transforms.py`, `dbx.py`, `ingest.py` — the optional "Regenerate from Marketplace" backend.
- `requirements.txt` — `databricks-sdk` (only used by the ingest path).
- `app.yaml`, `databricks.yml` — Databricks Apps + DAB config (no workspace host committed; the host comes from your CLI profile).
- `deploy.sh` — one-shot deploy; `.env(.example)` — per-environment settings (`.env` gitignored).
- `images/` — README screenshots.

## Deploy (summary)
```bash
cp .env.example .env      # edit: PROFILE, TARGET, catalog/schema, warehouse id, volume
./deploy.sh               # build (../app if present) → ensure volume → bundle deploy/run → grant SP
# flags: --no-build, --target dev|dogfood, --profile NAME
```
Full step-by-step (prerequisites, troubleshooting, manual fallback) is in `README.md`.

## Two ignore layers
- `.gitignore` → what git commits (excludes `.env`, `__pycache__/`, `*.pyc`; `.databricks/` has its own).
- `.databricksignore` → what ships to the app workspace (excludes docs, `images/`, `deploy.sh`, `.env*`, CLI state).

## Data model
Serves the **bundled snapshot** in `dist/data/` by default. When the Marketplace dataset is available
and the user opts in via the startup pop-up, the same artifacts are regenerated live into a UC volume
and served **volume-first** (bundled fallback). See `DESIGN.md`.
