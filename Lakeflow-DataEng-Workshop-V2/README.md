# Lakeflow Data Engineering Workshop (V2)

Databricks's new Data Engineering course, rebuilt around **Lakeflow Spark Declarative Pipelines (SDP)**, the new **Lakeflow Pipelines Editor**, and **Genie Code** Agent mode.

## What you'll do

Four core labs (~100 minutes total) plus two optional take-home labs:

- **Lab 1 — Bakehouse (hand-coded).** Build a streaming table in Python (modern `from pyspark import pipelines as dp` API) and a materialized view in SQL over `samples.bakehouse.sales_transactions`, with three data-quality expectations (log / drop / abort) wired into the MV from the start. Reference files in [`lab1/`](./lab1/).
- **Lab 2 — Learn how to use Genie Code (Wanderbricks).** Build a four-table fraud-detection pipeline from a single Genie Code prompt — AutoCDC over `samples.wanderbricks.booking_updates`, Auto Loader over JSON fraud flags in a shared volume, a join of payments, and a gold materialized view. Verify the generated SQL against the reference files in [`lab2/`](./lab2/) before letting it run.
- **Lab 3 — CI/CD via Declarative Automation Bundles.** Clone [`databricks/tmm/Lakeflow-Gourmet-Pipeline`](https://github.com/databricks/tmm/tree/main/Lakeflow-Gourmet-Pipeline) into your workspace, retarget two bundle variables (`catalog_name`, `prod_warehouse_id`) so it points at `workshop.<user>`, and deploy from the Workspace UI — the same bundle a CI runner would ship with `databricks bundle deploy`.
- **Lab 4 — Push IoT temperature reading via Zerobus Ingest** *(live instructor demo; attendees may follow along).* Push one `{id, city, temp}` reading into the shared Delta table `workshop.zerobus.course_temp` via the Zerobus REST API — no SDK, no cluster dependency, service principal credentials fetched from a secret scope. Reference file in [`lab4/`](./lab4/).
- **Lab 5 — Real-Time Mode for SDP** *(optional / take-home).* Deploy a continuous, serverless, PREVIEW-channel pipeline that uses `@dp.update_flow` with `pipelines.trigger: "RealTime"` for sub-second end-to-end latency. Read `engine_latency_ms` from the driver console sink. Reference bundle in [`lab5/`](./lab5/).
- **Lab 6 — Iceberg side-quest** *(optional / take-home).* Publish a derived bakehouse result as a managed Iceberg table (`USING ICEBERG`) and read it back from a pure-Python PyIceberg client via the Unity Catalog Iceberg REST endpoint — no Spark session required. Reference files in [`lab6/`](./lab6/).

See [Labguide.md](./Labguide.md) for the step-by-step exercises.

## Prerequisites

- A Databricks workspace with Unity Catalog and Serverless enabled.
- Partner-powered AI features enabled (Genie Code dependency).
- A pre-assigned schema `workshop.<user>` per attendee.
- The [`setup_workshop.py`](./setup_workshop.py) notebook has been run once to (a) create the shared landing volume with seeded JSON fraud markers for Lab 2 and (b) provision the Zerobus target table, service principal, and secret scope for Lab 4.

## Tech covered

- `CREATE OR REFRESH STREAMING TABLE` and `MATERIALIZED VIEW`
- `AUTO CDC INTO ... STORED AS SCD TYPE 1`
- `FROM STREAM read_files(...)` (Auto Loader)
- `from pyspark import pipelines as dp`, `@dp.table(...)`
- The new **Lakeflow Pipelines Editor** (asset browser, Run file / Run pipeline)
- **Genie Code** Agent mode for AI-assisted pipeline authoring
- **Declarative Automation Bundles** (DAB — formerly Databricks Asset Bundles) — `databricks.yml` variables/targets, Workspace UI deploy (**Deployments** 🚀 pane)
- Git folder + sparse checkout for cloning a subfolder of a public repo

## Why V2

V1 of the course used Delta Live Tables (DLT) syntax (`import dlt`, `CREATE LIVE TABLE`) and a single-notebook pipeline editor. V2 rebuilds around:

- The **modern SDP API** (`pyspark.pipelines`) — `import dlt` is legacy.
- The **new multi-file Lakeflow Pipelines Editor** with explicit transformation / exploration asset types.
- **Genie Code** as a first-class authoring tool, with mandatory human-in-the-loop verification.
