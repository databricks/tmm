# Lakebase 101 — Order Ops Console

A hands-on demo of **[Lakebase](https://docs.databricks.com/lakebase/index.html)**: managed Postgres (OLTP) on Databricks, fed by **reverse ETL** from the lakehouse, fronted by a **Databricks App**.

It builds one story around a fictional "Order Ops Console":

1. **Reverse ETL** — a Delta *gold* table (`customer_360`) is continuously synced into Lakebase Postgres via a **managed synced table** (no pipeline code to write).
2. **OLTP speed** — the same point lookup runs against Lakebase vs. a SQL Warehouse, side by side, so you can watch millisecond operational reads beat lakehouse scans.
3. **Real transactions** — the app places orders against Lakebase (`INSERT` order + `UPDATE` stock, atomically) — genuine OLTP writes, not analytics.
4. **Right tool for the job** — a 5M-row aggregate join shows the lakehouse (SQL Warehouse) winning heavy analytics, reinforcing *when* to use each engine.

---

## Architecture

```mermaid
flowchart LR
    subgraph Lakehouse["Lakehouse (Unity Catalog)"]
        D1[products / customers_directory]
        D2[customer_360_gold<br/>50k rows]
        D3[sales_events<br/>5M rows]
    end

    subgraph Lakebase["Lakebase — Managed Postgres"]
        S1[(customer_360_synced)]
        S2[(customers_directory_synced)]
        S3[(sales_events_synced)]
        O1[(orders — OLTP)]
        O2[(inventory — OLTP)]
    end

    WH[SQL Warehouse]
    APP[Databricks App<br/>FastAPI · Order Ops Console]

    D2 -- managed synced table --> S1
    D1 -- managed synced table --> S2
    D3 -- managed synced table --> S3

    APP -- fast reads / writes --> Lakebase
    APP -- heavy analytics --> WH
    WH --- Lakehouse
```

Reverse ETL uses **native managed synced tables** (`SNAPSHOT` policy), so there is no pipeline code in this repo — the sync is declared in `resources/synced_tables.yml`. The app's `orders` / `inventory` tables are OLTP-native, created and owned in Postgres by the post-deploy step.

---

## Prerequisites

- A Databricks workspace with **Lakebase** and **Databricks Apps** enabled.
- The **[Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html)** (v0.230+), authenticated:
  ```bash
  databricks configure   # or: databricks auth login --host <workspace-url>
  ```
- A **SQL Warehouse** you can use (for the speed comparison and analytics panes).
- Permission to create a catalog, a Lakebase project, and a Databricks App.

### Configure before deploying

Edit `databricks.yml` and set these for **your** workspace — the defaults are environment-specific and will not work elsewhere:

| Variable | Where | What to change |
|---|---|---|
| `workspace.host` | `targets.dev` / `targets.prod` | Your workspace URL |
| `warehouse_id` | `variables` | Your SQL Warehouse ID |
| `catalog` / `schema` | `variables` | Optional — rename if `lakebase_101_catalog` is taken |

> **App source note:** the app deploys from GitHub (`resources/apps.yml` → `git_repository` on branch `main`). If you fork this repo, point that `url`/`branch` at your fork, and remember that **local edits to `src/app/` take effect only after you commit and push** them — `databricks bundle deploy` pulls the app code from Git, not from your local working copy.

---

## Quick start

The setup is three steps: bootstrap the Delta source data, deploy the bundle, then wire up grants and OLTP tables.

```bash
# 1. Bootstrap the lakehouse source tables (catalog, schema, 4 Delta tables incl. 5M-row fact)
#    Run src/00_Setup.ipynb in the workspace (needs a cluster; generates ~5M rows).

# 2. Deploy Lakebase infra + synced tables + the app
databricks bundle deploy

# 3. Grant the app's service principal access + create/seed the Postgres OLTP tables
#    Run src/01_Post_Deploy.ipynb in the workspace.
```

Then open the app URL:

```bash
databricks apps list        # find "lakebase-101-app"
```

> **Order matters.** `00_Setup` must run *before* `bundle deploy` (synced tables reference the Delta sources), and `01_Post_Deploy` must run *after* (it needs the app's service principal, which only exists once the app is deployed).

---

## Using the app

The console (a FastAPI backend + static frontend) exposes:

| Pane | Endpoint | Shows |
|---|---|---|
| Customer search | `GET /api/customers?q=` | Search the 50k synced directory |
| Speed test | `GET /api/speed/{customer_id}` | Same lookup: Lakebase vs. SQL Warehouse (with speedup) |
| Analytics showdown | `GET /api/aggregate` | 5M-row join: warehouse wins (the "right tool" point) |
| Customer 360 | `GET /api/customer/{customer_id}` | Fast profile read + recent orders |
| Place order | `POST /api/order` | Atomic OLTP write (insert order, decrement stock) |
| Inventory | `GET /api/inventory` | Live stock levels |
| Sync now | `POST /api/sync` | Trigger the managed reverse-ETL pipeline |
| Health / debug | `GET /api/health`, `GET /api/debug` | Connection diagnostics — **hit `/api/debug` first if Lakebase access looks broken** |

---

## Repository layout

```
Lakebase-101/
├── databricks.yml              # Bundle definition + variables + dev/prod targets
├── resources/
│   ├── lakebase.yml            # Lakebase project, branch, endpoint, role, database
│   ├── synced_tables.yml       # Managed reverse-ETL synced tables (Delta → Postgres)
│   └── apps.yml                # Databricks App resource (deploys from GitHub)
└── src/
    ├── 00_Setup.ipynb          # (before deploy) catalog + schema + Delta source tables
    ├── 01_Post_Deploy.ipynb    # (after deploy)  grants + Postgres OLTP tables + seed
    ├── 99_Cleanup.ipynb        # teardown (Delta tables, schema/catalog, sync pipelines)
    └── app/                    # FastAPI app (server/, static/) — source of truth on GitHub
```

---

## Cleanup

`src/99_Cleanup.ipynb` drops the Delta tables, the schema/catalog, and the synced-table pipelines (which `bundle destroy` does not remove). To also remove the Lakebase project, endpoint, and the app itself, run:

```bash
databricks bundle destroy --auto-approve
```

> Run the cleanup notebook first (to catch the auto-created sync pipelines), then `bundle destroy` for the declared infrastructure.

---

## How it works (a bit more detail)

- **Auth to Lakebase.** The app mints a short-lived Lakebase-scoped credential with `w.postgres.generate_database_credential(...)` (requires `databricks-sdk>=0.80.0`) and connects over standard Postgres/psycopg2. Tokens are refreshed before their ~1h expiry (`src/app/server/db.py`).
- **Synced tables** use `SNAPSHOT` scheduling with `create_database_objects_if_missing: true`, so the target Postgres tables are created and populated by the managed pipeline. The app reads them by their Postgres names (e.g. `lakebase_101_schema.customer_360_synced`).
- **OLTP tables** (`public.orders`, `public.inventory`) are created and owned in Postgres by `01_Post_Deploy`, which also grants the app's service principal read access to the synced schema and read/write on the OLTP tables.
- **App configuration** is injected via `src/app/app.yaml` env vars and resource bindings (SQL Warehouse, Lakebase database) — no secrets in code.
