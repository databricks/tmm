# Optional "Regenerate from Marketplace" ingest — design

The app ships a frozen snapshot of one OpenSky day, baked into `dist/data/`. This add-on lets the
app **regenerate the same artifacts live** from the Marketplace dataset when it's available, so the
app works *with* the dataset instead of only carrying a copy. The static/bundled path is unchanged
and remains the fast default and the fallback.

## Principles
- **Never slow boot.** A Databricks App must pass its health check in seconds. The Databricks SDK is
  imported **lazily** (only inside `dbx.py` functions), the availability probe is **client-initiated**
  after page load, and the regenerate runs in a **background thread** — never at server start.
- **Byte-compatible output.** Regenerated `.json.gz` must be drop-in identical to the shipped
  artifacts. `transforms.py` / `sql.py` are faithful ports of the offline extraction pipeline (same
  `DAY_START`, rounding, key order, compact `json.dumps`). Verified offline against the shipped files.
- **Volume-first, bundled-fallback.** Once regenerated, `/data/*` is served from the UC volume;
  if a file isn't there (or ingest is unconfigured), the server falls back to `dist/data/`.

## Flow
1. Frontend `SourceModal` calls `GET /api/source?catalog=&schema=` on load. The server probes
   `SELECT 1 FROM <catalog>.<schema>.state_vectors LIMIT 1` on the warehouse.
2. **Reachable** → the pop-up offers *Regenerate from Marketplace* (all 3 regions, background) and
   *Use bundled snapshot* (instant/faster). **Not reachable** → says so, auto-dismisses to bundled.
3. On regenerate, `POST /api/ingest` starts a background run; the modal polls `GET /api/ingest/status`
   and shows a progress bar (12 steps = 3 regions × 4 queries). On completion it invalidates the
   frontend caches and the app reloads the region → now served from the volume.

## Backend modules (all lazy re: Databricks)
- `sql.py` — region bboxes + the 4 query templates, source table `{catalog}.{schema}.state_vectors`.
- `transforms.py` — `prism/density/anomaly` compaction + `to_gz` (gzip, `mtime=0`).
- `dbx.py` — `WorkspaceClient` (lazy). `probe()`; `run_query()` using **EXTERNAL_LINKS + JSON_ARRAY**
  (result sets exceed the 25 MiB INLINE cap), streamed chunk-by-chunk; `query_dicts()`;
  `write/read/exists` UC volume via the Files API (PUT is atomic — no half-written reads).
- `ingest.py` — `STATE` + lock, daemon thread, `source_info()`, `start()`, `_run()` looping regions
  → 4 queries → transforms → gz → volume; writes `manifest.json` (`generated_at`, day_start, …) last.
- `server.py` — `ThreadingHTTPServer`; routes `/api/source|ingest|ingest/status`; volume-first
  `/data/*`; `/data/` served `no-cache` (so a regenerate is picked up; `/assets/` stays immutable).

## Env (set by `databricks.yml` from `.env` via `deploy.sh`)
| var | meaning |
|-----|---------|
| `OPENSKY_WAREHOUSE_ID` | warehouse for the regeneration queries (app resource, CAN_USE) |
| `OPENSKY_VOLUME_ROOT`  | `/Volumes/<cat>/<schema>/<vol>` for regenerated artifacts |
| `OPENSKY_CATALOG` / `OPENSKY_SCHEMA` | default source dataset location (editable in the pop-up) |

Unset any of these → the app is bundled-only (exactly the original behavior).

## Service-principal grants (applied by `deploy.sh`)
- `USE_CATALOG`/`USE_SCHEMA` + `SELECT` on `<catalog>.<schema>.state_vectors` (the source).
- `CAN_USE` on the warehouse (via the app resource).
- `USE_CATALOG`/`USE_SCHEMA` + `READ_VOLUME`/`WRITE_VOLUME` on the artifacts volume.

## Byte-compat, measured
Offline gate (transforms over the shipped raw exports) is byte-identical for all 9 artifacts. Live
against the warehouse (Europe): **density is byte-identical**; prism/anomaly are **content-identical**
(same 1500 flights / 60 anomalies, same bbox) — they only differed by row order, so their final
SELECTs now carry `ORDER BY icao24, callsign`, making regeneration deterministic run-to-run.
Measured on the 2X-Small serverless warehouse: Europe ≈ 3.3 min, full three-region run ≈ ~8–12 min.

## Notes / risks
- `collect_list(struct(...))` (prism/anomaly tracks) arrives JSON-string-encoded via JSON_ARRAY
  (confirmed live); `transforms._pts` tolerates both a string and a pre-parsed list, so output is
  identical either way.
- `day_start` is the fixed `1772323200` (2026-03-01). Regenerating a *different* UTC day would need
  this revisited; the manifest records what was built.
- In-memory `STATE` is per-process: an app restart mid-run orphans the run (volume writes so far
  persist); the durable truth is `manifest.json`'s `generated_at`, which the pop-up reads on load.
