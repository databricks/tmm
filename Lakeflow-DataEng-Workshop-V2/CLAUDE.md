# Lakeflow-DataEng-Workshop-V2 — Project Instructions for Claude

## Project overview
Four-core-lab Databricks training on Lakeflow Spark Declarative Pipelines (SDP) and direct ingest,
plus two optional take-home labs, delivered in the new Lakeflow Pipelines Editor. Attendees each
have a pre-assigned schema `workshop.<user>`. A shared landing volume (for Lab 2) and a shared
Zerobus target table (for Lab 4) are preseeded by a single setup notebook.

- **Lab 1 — Bakehouse, hand-coded.** Streaming table in **Python** (1a) and a materialized view
  in **SQL** (1b) over `samples.bakehouse.sales_transactions`. The MV is created with three
  `CONSTRAINT ... EXPECT` clauses wired in from the start — one per violation behavior
  (log / drop row / fail update) — so attendees paste one block and run, no replacement step.
  Source files in `lab1/`.
- **Lab 2 — Wanderbricks, SQL, Learn how to use Genie Code (verified).** AutoCDC on
  `samples.wanderbricks.booking_updates`, Auto Loader on JSON fraud markers,
  streaming table on `samples.wanderbricks.payments`, and a three-way-join gold MV.
  Reference files in `lab2/`.
- **Lab 3 — CI/CD via Declarative Automation Bundles (external Gourmet Pipeline).** Clones
  `databricks/tmm/Lakeflow-Gourmet-Pipeline` into the workspace via Git folder + sparse
  checkout, per-student overrides of `catalog_name` / `prod_warehouse_id` (and optionally
  `schema_name`) in `databricks.yml`, then deploys through the **Deployments** (🚀) pane —
  framed as the interactive entry point to the same bundle a CI runner would ship. The
  upstream demo bundle has only one target (`presenter`); production CI/CD would extend
  with `dev` and `prod` targets. Source lives in the external repo — we reference it,
  never fork it.
- **Lab 4 — Zerobus direct ingest (live instructor demo; attendees may follow along).**
  Instructor runs an Exploration notebook that pushes one `{id, city, temp}` record into the
  shared Delta table `workshop.zerobus.course_temp` via the **Zerobus REST API** (serverless-
  friendly; the gRPC SDK can't pip-install on serverless compute). Credentials come from the
  `workshop` Databricks secret scope (`zerobus_client_id`, `zerobus_client_secret`,
  `zerobus_endpoint`, `zerobus_workspace_id`, `zerobus_workspace_url`) — attendees never see
  raw SP secrets. The lab's teaching point is the governance surface (scoped OAuth via
  `authorization_details` with privilege names in **underscore form** —
  `USE_CATALOG`, `USE_SCHEMA`, `SELECT`, `MODIFY` — SP audit identity, secret scope), which
  is discussed live rather than silently typed. Reference file in `lab4/send_temperature.py`.
- **Lab 5 — Real-Time Mode for SDP (optional / take-home).** A continuous, serverless,
  PREVIEW-channel SDP pipeline using `@dp.update_flow` with `pipelines.trigger: "RealTime"`,
  enabled at the pipeline level via `spark.databricks.streaming.realTimeMode.enabled = true`
  in the bundle's `configuration:` block. A synthetic `rate` source feeds a 10-second
  windowed aggregation; the console sink emits an `engine_latency_ms` column readable from
  the driver logs. Deployed as a Declarative Automation Bundle from `lab5/`. Conform to
  the official RTM user guide for SDP — flow-level keys are `pipelines.trigger` and
  `pipelines.trigger.interval`, not the older `pipelines.execution.realTimeMode` /
  `pipelines.realtime.trigger.duration`.
- **Lab 6 — Iceberg side-quest (optional / take-home).** A managed-Iceberg CTAS
  (`global_sales_gold`, top-5 locations) run **outside** the pipeline in the SQL editor,
  read back from a small PyIceberg Exploration notebook via the UC Iceberg REST Catalog.
  Not part of the ~100-minute core arc; skip-friendly. Source files in `lab6/`.

## Language split (MUST preserve)
- Lab 1a (streaming table) — **Python** (`@dp.table` + `spark.readStream.table(...)`).
- Lab 1b (materialized view with expectations) — **SQL** (`CREATE OR REFRESH MATERIALIZED VIEW`
  with three `CONSTRAINT ... EXPECT` clauses in the same definition: one LOG/default, one
  `ON VIOLATION DROP ROW`, one `ON VIOLATION FAIL UPDATE`). One paste, not two.
- Lab 2 — every file is **SQL** (streaming tables, Auto Loader, AutoCDC flow, gold MV).
- Lab 5 (RTM) — **Python** (`@dp.update_flow` with `pipelines.trigger: "RealTime"`), in its
  own bundle and pipeline. Optional/take-home, doesn't affect the in-pipeline language split
  of the core arc.
- Lab 6a (managed Iceberg CTAS, **outside** the pipeline) — **SQL**
  (`CREATE OR REPLACE TABLE ... USING ICEBERG AS SELECT ...`).
- Lab 6b (Iceberg reader, **outside** the pipeline) — small **Python** Exploration notebook
  using `pyiceberg`. Client-side reader, not pipeline code — the in-pipeline language split
  is untouched.
- Net effect for **in-pipeline** code in the core arc (Labs 1–4): Python appears exactly
  once (Lab 1a); everything else in the pipeline is SQL. This is deliberate so Lab 2 aligns
  with what Genie Code generates. Do not "unify" Lab 1 to all-Python or all-SQL.

## SDP code conventions (MUST follow)
- Use **`CREATE OR REFRESH`** (never `CREATE OR REPLACE`) for streaming tables and
  materialized views. `CREATE OR REPLACE TABLE` **is** allowed for the Lab 6 managed
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

**Part B — Lab 4 Zerobus provisioning** (skipped if `zerobus_region` widget is blank):
1. Create schema `workshop.zerobus` and managed Delta table `workshop.zerobus.course_temp`
   with exactly `id STRING, city STRING, temp FLOAT`. Zerobus does not create tables.
2. Create (or reuse) a workspace service principal `workshop-zerobus-sp`. Always generate
   a fresh OAuth client secret on each run — secret_scope writes overwrite, so attendees
   always read a current value.
3. Grant the SP: `USE CATALOG` on `workshop`, `USE SCHEMA` on `workshop.zerobus`,
   `MODIFY + SELECT` on `workshop.zerobus.course_temp`. Nothing broader — this bounds
   the blast radius if the client_secret ever leaks. The OAuth `authorization_details`
   payload requires the **underscore form** of these privileges (`USE_CATALOG`,
   `USE_SCHEMA`, `SELECT`, `MODIFY`) — the spaced form is SQL-grant syntax only.
4. Create secret scope `workshop` and store five keys: `zerobus_client_id`,
   `zerobus_client_secret`, `zerobus_endpoint`, `zerobus_workspace_id`, `zerobus_workspace_url`.
5. Grant READ on the scope to `account users`. Attendees then read via
   `dbutils.secrets.get("workshop", ...)` — no credentials in notebook source.

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

## Lab 3 specifics
- Upstream source of truth: `https://github.com/databricks/tmm/tree/main/Lakeflow-Gourmet-Pipeline`.
- Per-student variables students MUST adjust in `databricks.yml`:
  - `catalog_name` — default is `daiwt_gourmet`; change to `workshop`.
  - `prod_warehouse_id` — default is an example ID that likely doesn't exist in the workshop workspace; replace with a real one from **SQL Warehouses**.
  - `schema_name` — default is `${workspace.current_user.short_name}`; leave it if that matches the attendee's `<user>` schema, otherwise override to the literal `<user>` value.
- Gotcha: dashboard SQL cannot be parameterized yet — if the attendee changes catalog/schema away from defaults, they must manually replace `daiwt_gourmet` in `resources/dashboard_gourmet_aibi.yml` and `src/aibi_dashboard.json`.
- Do NOT add a copy of the Gourmet Pipeline code to this repo. Lab 3 points to the upstream repo and students clone via Workspace **Create → Git folder** with sparse checkout path `Lakeflow-Gourmet-Pipeline`.

## Files in this repo
- `README.md` — course overview.
- `Labguide.md` — attendee-facing lab guide.
- `CLAUDE.md` — this file.
- `.gitignore` — standard Databricks/Python ignores.
- `setup_workshop.py` — instructor-run setup notebook (Part A: Lab 2 shared volume + seed; Part B: Lab 4 Zerobus target table, SP, grants, secret scope).
- `lab1/` — Lab 1 reference files: `sales_transactions.py` (streaming table) and `sales_stats.sql` (MV with three `EXPECT` constraints baked in).
- `lab2/` — Lab 2 reference SQL files (`bookings_current.sql`, `booking_fraud_flags.sql`, `payments.sql`, `booking_fraud_summary.sql`).
- `lab4/` — Lab 4 reference file: `send_temperature.py` (Databricks notebook source). Payload-construction and POST logic are in a single "DO NOT MODIFY" cell; attendees only change the two widgets.
- `lab5/` — Lab 5 (optional / take-home) Real-Time Mode bundle: `databricks.yml` (continuous, serverless, PREVIEW channel, RTM enabled at pipeline level) and `transformations/temperature_rtm.py` (`@dp.update_flow` with `pipelines.trigger: "RealTime"`, console sink with `engine_latency_ms` column).
- `lab6/` — Lab 6 (optional / take-home) Iceberg side-quest reference files: `global_sales_gold.sql` (managed-Iceberg CTAS, runs outside the pipeline) and `read_global_sales_gold.py` (PyIceberg reader, Databricks notebook source, talks to the UC Iceberg REST Catalog).
