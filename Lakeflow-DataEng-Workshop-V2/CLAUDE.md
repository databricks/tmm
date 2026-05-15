# Lakeflow-DataEng-Workshop-V2 — Project Instructions for Claude

## Project overview
Three-core-lab Databricks training on Lakeflow Spark Declarative Pipelines (SDP) and direct
ingest, plus three optional/take-home labs, delivered in the new Lakeflow Pipelines Editor.
Attendees each have a pre-assigned schema `workshop.<user>`. A shared landing volume (for
Lab 2) and a shared Zerobus target table (for Lab 3) are preseeded by a single setup notebook.

- **Lab 1 — Bakehouse, hand-coded.** Streaming table in **Python** (1a) and a materialized view
  in **SQL** (1b) over `samples.bakehouse.sales_transactions`. The MV is created with three
  `CONSTRAINT ... EXPECT` clauses wired in from the start — one per violation behavior
  (log / drop row / fail update) — so attendees paste one block and run, no replacement step.
  Source files in `lab1-SDP/`.
- **Lab 2 — Wanderbricks, SQL, Learn how to use Genie Code (verified).** AutoCDC on
  `samples.wanderbricks.booking_updates`, Auto Loader on JSON fraud markers,
  streaming table on `samples.wanderbricks.payments`, and a three-way-join gold MV.
  Reference files in `lab2-GenieCode/`.
- **Lab 3 — Zerobus direct ingest (live instructor demo; attendees may follow along).**
  Instructor runs an Exploration notebook that pushes one `{id, city, temperature, comment}`
  record into the shared Delta table `workshop.zerobus.measurements` via the
  **Zerobus REST API** (serverless-friendly; the gRPC SDK can't pip-install on serverless
  compute). Credentials come from the UC config table `workshop.zerobus.config` (single
  row, columns: `client_id`, `client_secret`, `workspace_url`, `workspace_id`,
  `zerobus_endpoint`) — attendees read all five values from one place. The shared SP
  `client_secret` lives in the table in cleartext; this is intentional given the 1:1000
  shared-credential model (every attendee needs the secret to mint OAuth tokens, and the
  SP's UC grants are tightly scoped to `measurements`). The lab's teaching point is
  the governance surface (scoped OAuth via `authorization_details` carrying the **full
  UC chain** — `USE CATALOG`, `USE SCHEMA`, `SELECT`, `MODIFY` — with **spaced**
  privilege names matching `SHOW GRANTS`. SP audit identity, table-level GRANT, no
  broader scope than required.) Discussed live rather than silently typed. REST variant
  in `lab3-Zerobus-Ingest/send_temperature.py`; gRPC variant (uses the official
  `databricks-zerobus-ingest-sdk` via a serverless notebook **Environment**) in
  `lab3-Zerobus-Ingest/send_temperature_grpc.py`.
- **Lab 4 — Real-Time Mode for SDP (optional / take-home).** A continuous, serverless,
  PREVIEW-channel SDP pipeline using `@dp.update_flow` with `pipelines.trigger: "RealTime"`,
  enabled at the pipeline level via `spark.databricks.streaming.realTimeMode.enabled = true`
  in the bundle's `configuration:` block. A synthetic `rate` source feeds a 10-second
  windowed aggregation; the console sink emits an `engine_latency_ms` column readable from
  the driver logs. Deployed as a Declarative Automation Bundle from `lab4-SDP-RTM/`. Conform to
  the official RTM user guide for SDP — flow-level keys are `pipelines.trigger` and
  `pipelines.trigger.interval`, not the older `pipelines.execution.realTimeMode` /
  `pipelines.realtime.trigger.duration`.
- **Lab 5 — Iceberg side-quest (optional / take-home).** A managed-Iceberg CTAS
  (`global_sales_gold`, top-5 locations) run **outside** the pipeline in the SQL editor,
  read back from a small PyIceberg Exploration notebook via the UC Iceberg REST Catalog.
  Not part of the ~100-minute core arc; skip-friendly. Source files in `lab5-Iceberg/`.
- **Lab 6 — CI/CD via Declarative Automation Bundles (external Gourmet Pipeline).** Clones
  `databricks/tmm/Lakeflow-Gourmet-Pipeline` into the workspace via Git folder + sparse
  checkout, per-student overrides of `catalog_name` / `prod_warehouse_id` (and optionally
  `schema_name`) in `databricks.yml`, then deploys via `databricks bundle deploy` from the
  CLI — the same path a CI runner would take. The upstream demo bundle has only one target
  (`presenter`); production CI/CD would extend with `dev` and `prod` targets. Source lives
  in the external repo — we reference it, never fork it. No local folder for this lab.

## Language split (MUST preserve)
- Lab 1a (streaming table) — **Python** (`@dp.table` + `spark.readStream.table(...)`).
- Lab 1b (materialized view with expectations) — **SQL** (`CREATE OR REFRESH MATERIALIZED VIEW`
  with three `CONSTRAINT ... EXPECT` clauses in the same definition: one LOG/default, one
  `ON VIOLATION DROP ROW`, one `ON VIOLATION FAIL UPDATE`). One paste, not two.
- Lab 2 — every file is **SQL** (streaming tables, Auto Loader, AutoCDC flow, gold MV).
- Lab 4 (RTM) — **Python** (`@dp.update_flow` with `pipelines.trigger: "RealTime"`), in its
  own bundle and pipeline. Optional/take-home, doesn't affect the in-pipeline language split
  of the core arc.
- Lab 5a (managed Iceberg CTAS, **outside** the pipeline) — **SQL**
  (`CREATE OR REPLACE TABLE ... USING ICEBERG AS SELECT ...`).
- Lab 5b (Iceberg reader, **outside** the pipeline) — small **Python** Exploration notebook
  using `pyiceberg`. Client-side reader, not pipeline code — the in-pipeline language split
  is untouched.
- Net effect for **in-pipeline** code in the core arc (Labs 1–3): Python appears exactly
  once (Lab 1a); everything else in the pipeline is SQL. This is deliberate so Lab 2 aligns
  with what Genie Code generates. Do not "unify" Lab 1 to all-Python or all-SQL.

## SDP code conventions (MUST follow)
- Use **`CREATE OR REFRESH`** (never `CREATE OR REPLACE`) for streaming tables and
  materialized views. `CREATE OR REPLACE TABLE` **is** allowed for the Lab 5 managed
  Iceberg CTAS, because that runs outside SDP in the SQL editor — plain Spark SQL semantics apply.
- Python: `from pyspark import pipelines as dp`. Never use legacy `import dlt`,
  `dlt.read`, `dlt.read_stream`, or `dlt.apply_changes`.
- Inside `@dp.table`, use `spark.read.table(...)` for MV / batch reads and
  `spark.readStream.table(...)` for streaming reads.
- Auto Loader in SQL streaming tables: `FROM STREAM read_files('/Volumes/...', format => 'json')`.
  `STREAM` is required; plain `read_files(...)` is batch and will fail in a streaming table.
- AutoCDC: `CREATE FLOW ... AS AUTO CDC INTO ... KEYS (...) SEQUENCE BY ... STORED AS SCD TYPE 1|2`.
- Serverless pipelines only (no classic clusters).
- Unity Catalog only.

## Source data (read-only)
- `samples.bakehouse.sales_transactions` — 3,333 rows, 6 products, 3 payment methods.
- `samples.wanderbricks.booking_updates` — the only native CDC feed in the dataset
  (keys `booking_id`, sequence `updated_at`, per-event `booking_update_id`).
- `samples.wanderbricks.payments` — joined with bookings via `booking_id`.

## Destination conventions
- Catalog: `workshop` (fixed — do not replace with a placeholder).
- Per-attendee schema: `workshop.<user>` (exists; setup notebook never creates/mutates it).
- Shared landing volume: `/Volumes/workshop/shared/landing/booking_fraud_flags/`
  — JSON fraud markers keyed by `booking_id`.

## Setup-notebook responsibilities (MUST include)
The setup notebook (`setup_workshop.py`, run once per workshop) is split into two parts.

**Part A — Lab 2 shared assets:**
1. Create schema `workshop.shared` if it does not exist.
2. Create volume `workshop.shared.landing` if it does not exist.
3. Create folder `booking_fraud_flags/` in the volume and seed JSON fraud markers
   for **3%** of distinct `booking_id`s from `samples.wanderbricks.booking_updates`.
4. **Grant `USE_SCHEMA` on `workshop.shared` to group `account users`**
   (so attendees can see the volume).
5. **Grant `READ_VOLUME` on `workshop.shared.landing` to group `account users`**
   (read-only — no `WRITE_VOLUME`).

**Part B — Lab 3 Zerobus provisioning** (skipped if `zerobus_region` widget is blank):
0. **Storage preflight.** Create schema `workshop.zerobus`, then check via the SDK that
   the catalog/schema has a managed storage location AND that the location is not workspace
   default storage. The check pattern-matches the effective `storage_root` against known
   default-storage bucket prefixes (`s3://dbstorage-`, `s3://databricks-`,
   `abfss://unity-catalog@`, `abfss://dbstorage`, `gs://databricks-`); a customer-owned
   UC managed location won't match any of them. If the location is missing OR matches a
   default-storage prefix, raise `RuntimeError` with remediation guidance (set
   `MANAGED LOCATION` on the catalog or schema, or use a different catalog). Zerobus
   rejects writes to default-storage tables with HTTP 403 at insert time — failing here
   at setup is much cheaper than failing in 1000 attendee notebooks later.
1. Create the managed Delta table `workshop.zerobus.measurements` with exactly
   `id STRING, city STRING, temperature FLOAT, comment STRING`. Zerobus does not create
   tables.
2. Create (or reuse) a workspace service principal `workshop-zerobus-sp`. Always generate
   a fresh OAuth client secret on each run — config-table writes overwrite, so attendees
   always read a current value.
3. Grant the SP: `USE CATALOG` on `workshop`, `USE SCHEMA` on `workshop.zerobus`,
   `MODIFY + SELECT` on the data table. Nothing broader — this bounds the blast radius.
   The Zerobus OAuth scoped-token endpoint (`zerobusDirectWriteApi` resource) requires the
   token's `authorization_details` to carry the **full UC chain** — `USE CATALOG` on the
   catalog, `USE SCHEMA` on the schema, and `SELECT` + `MODIFY` on the table — using the
   **spaced** privilege names exactly as `SHOW GRANTS` reports them. Underscore form
   (`USE_CATALOG`, `USE_SCHEMA`) is rejected with `invalid_authorization_details`. A token
   minted *without* the catalog/schema entries (table-only) is accepted by `/oidc/v1/token`
   with HTTP 200 but rejected by `/zerobus/v1/tables/.../insert` with HTTP 403 at write
   time — that's the failure mode to watch for.
4. Create the config table `workshop.zerobus.config` (single row, columns: `client_id`,
   `client_secret`, `workspace_url`, `workspace_id`, `zerobus_endpoint`) and `GRANT SELECT`
   on it to `account users` (with fallback to workspace `users`). Cleartext storage of
   `client_secret` is intentional: every attendee needs the secret to mint OAuth tokens
   anyway, and the SP's UC grants are tightly bounded — the table simplifies the read
   path at the cost of secret-scope redaction. Attendees then read via
   `spark.table("workshop.zerobus.config").first()`.

**Global rules:**
6. Never grant anything on the individual per-attendee schemas.
7. Be idempotent — safe to re-run.

## UI conventions (new Lakeflow Pipelines Editor)
- Create: sidebar **New → ETL Pipeline**.
- Default catalog + schema: selector right of the pipeline name.
- Add source files: asset browser **Add → Transformation** (or **Add → Exploration** for
  non-pipeline notebooks).
- Run: **Run file** (single file) or **Run pipeline** (whole DAG).
- Genie Code: **Genie Code** button upper-right of workspace, **Agent** toggle lower-right
  of the pane. Never click *Always allow* in teaching material — verification each step is the pedagogy.

## When editing lab content
- Preserve the Lab 1 (Bakehouse, Python + SQL, hand-coded) vs Lab 2 (Wanderbricks, SQL, Genie-Code) split.
- If a new table is added, update both tables in the lab guide (wrap-up + course arc) and the
  verification plan in the instructor section.
- Keep Lab 2's single Genie Code prompt self-contained. If you change any of the four target
  files, update the prompt and all four reference code blocks in the same commit.
- Any doc references should link to `docs.databricks.com/aws/en/ldp/...` or
  `docs.databricks.com/aws/en/genie-code/...` and include the doc's "last updated" date.

## Lab 6 specifics (CI/CD via Asset Bundles)
- Upstream source of truth: `https://github.com/databricks/tmm/tree/main/Lakeflow-Gourmet-Pipeline`.
- Per-student variables students MUST adjust in `databricks.yml`:
  - `catalog_name` — default is `daiwt_gourmet`; change to `workshop`.
  - `prod_warehouse_id` — default is an example ID that likely doesn't exist in the workshop workspace; replace with a real one from **SQL Warehouses**.
  - `schema_name` — default is `${workspace.current_user.short_name}`; leave it if that matches the attendee's `<user>` schema, otherwise override to the literal `<user>` value.
- Gotcha: dashboard SQL cannot be parameterized yet — if the attendee changes catalog/schema away from defaults, they must manually replace `daiwt_gourmet` in `resources/dashboard_gourmet_aibi.yml` and `src/aibi_dashboard.json`.
- Do NOT add a copy of the Gourmet Pipeline code to this repo. Lab 6 points to the upstream repo and students clone via Workspace **Create → Git folder** with sparse checkout path `Lakeflow-Gourmet-Pipeline`.
- The lab is taught from the **CLI**: `databricks bundle validate`, `databricks bundle deploy -t presenter`, `databricks bundle run`, `databricks bundle destroy`. Link to the docs:
  `https://docs.databricks.com/aws/en/dev-tools/bundles/`. These are the basic commands;
  production CI runners use the same `databricks bundle deploy` against `dev` / `prod` targets.

## Files in this repo
- `README.md` — course overview.
- `Labguide.md` — attendee-facing lab guide.
- `CLAUDE.md` — this file.
- `.gitignore` — standard Databricks/Python ignores.
- `setup_workshop.py` — instructor-run setup notebook (Part A: Lab 2 shared volume + seed; Part B: Lab 3 Zerobus target table, SP, grants, config table).
- `lab1-SDP/` — Lab 1 reference files: `sales_transactions.py` (streaming table) and `sales_stats.sql` (MV with three `EXPECT` constraints baked in).
- `lab2-GenieCode/` — Lab 2 reference SQL files (`bookings_current.sql`, `booking_fraud_flags.sql`, `payments.sql`, `booking_fraud_summary.sql`).
- `lab3-Zerobus-Ingest/` — Lab 3 reference file: `send_temperature.py` (Databricks notebook source). Payload-construction and POST logic are in a single "DO NOT MODIFY" cell; attendees only change the three widgets (city, temperature, comment).
- `lab4-SDP-RTM/` — Lab 4 (optional / take-home) Real-Time Mode bundle: `databricks.yml` (continuous, serverless, PREVIEW channel, RTM enabled at pipeline level) and `transformations/temperature_rtm.py` (`@dp.update_flow` with `pipelines.trigger: "RealTime"`, console sink with `engine_latency_ms` column).
- `lab5-Iceberg/` — Lab 5 (optional / take-home) Iceberg side-quest reference files: `global_sales_gold.sql` (managed-Iceberg CTAS, runs outside the pipeline) and `read_global_sales_gold.py` (PyIceberg reader, Databricks notebook source, talks to the UC Iceberg REST Catalog).
- (no `lab6/` folder) — Lab 6 (CI/CD via Asset Bundles) ships from the external repo `databricks/tmm/Lakeflow-Gourmet-Pipeline`; nothing is forked into this repo.
