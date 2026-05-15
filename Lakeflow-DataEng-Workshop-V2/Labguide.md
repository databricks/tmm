# AI-Powered Data Engineering with Lakeflow

**Version 2.0**

> **Audience**: entry- to mid-level data engineers, with no or some prior Databricks knowledge. The environment is already set up for you — you have an empty workspace in an account with a pre-assigned schema `workshop.USER_ID`.

### Overview

- **Lab 1 — Manually code an SDP pipeline**: streaming table in **Python**, materialized view in **SQL** with three data-quality expectations wired in from the start. Reference files in [`lab1/`](./lab1/).
- **Lab 2 — Learn how to use Genie Code as a data engineer**: all-**SQL** pipeline (AutoCDC + Auto Loader + join gold MV), produced from a single Genie Code prompt — and verified by you before it runs. Reference files in [`lab2/`](./lab2/).
- **Lab 3 — CI/CD via Declarative Automation Bundles**: clone a public repo with a DAB, retarget two variables to `workshop.USER_ID`, and deploy it from the Workspace UI — the same bundle a CI runner would ship with `databricks bundle deploy`.
- **Lab 4 — Work with Zerobus Ingest to push IoT data** *(live instructor demo; attendees may follow along)*: one HTTP POST lands a row in `workshop.zerobus.course_temp`, with credentials fetched from a shared secret scope. Reference files in [`lab4/`](./lab4/).
- **Lab 5 — Real-Time Mode for SDP** *(optional)*: deploy a continuous pipeline running in Real-Time Mode (RTM), watch sub-second latency aggregates land in the driver console, and read the engine latency from the driver logs.
- **Lab 6 — Iceberg side-quest** *(optional)*: publish a derived bakehouse result as a managed Iceberg table and read it back with PyIceberg through the Unity Catalog Iceberg REST endpoint — no Spark session required. Reference files in [`lab6/`](./lab6/).

## Important — Your User ID

This workshop is designed so it can be run with thousands of participants in a single Databricks account sharing a number of workspaces. We therefore use your **USER_ID** (derived from your login email) to separate schemas and pipelines and avoid namespace clashes.

To get your user id, check your login email by clicking on the user avatar (e.g. **L**) at the **top right** of the workspace. Example: `labuser10148895_1745997814@vocareum.com` means your user id is `labuser10148895_1745997814`.

Throughout this guide, replace `USER_ID` with that exact value. Your pre-assigned schema is `workshop.USER_ID`.

## Prerequisites (already done by the setup notebook)

- Your catalog `workshop` / your schema `workshop.USER_ID` already exists and is writable.
- A shared volume exists at `/Volumes/workshop/shared/landing/` with a seeded subfolder `booking_fraud_flags/` containing JSON fraud markers keyed by `booking_id`. The volume is **read-only** for attendees (every attendee has `READ_VOLUME`, nobody has `WRITE_VOLUME`), so one attendee cannot disrupt another.
- This lab runs completely serverless.
- You can read `samples.bakehouse.*` and `samples.wanderbricks.*` (public sample data).

### Substitutions

Three placeholders show up throughout — resolve them once here, then paste blocks run as-is.

| Placeholder | What to use |
|---|---|
| `USER_ID` | Your user id, derived from your login email (see above). Example: `labuser10148895_1745997814`. Your schema is `workshop.USER_ID`. |
| `workshop` | The catalog. Fixed — do not change. |
| `prod_warehouse_id` (Lab 3 only) | A running SQL warehouse ID. Find it in sidebar **SQL Warehouses** → click a warehouse → copy the ID from the URL. |
| `<course_warehouse_name>` / `<course_warehouse_id>` (Lab 4 only) | The course SQL warehouse provisioned for you by the courseware. Your instructor will share the exact name and ID. |

### One-time setup — Clone this workshop repo

Clone this repo into your Workspace once at the start. You get this lab guide and all the labs locally.

1. Workspace sidebar → **Workspace** → **Create** → **Git folder**.
2. **Git repository URL**: this workshop's GitHub URL (your instructor will share it).
3. **Git provider**: GitHub.
4. Click **Create Git folder**.

The cloned `lab1/` … `lab6/` folders are read-only reference. For Labs 1 and 2 you create a new pipeline; the editor auto-creates a workspace folder named after the pipeline in your home directory, so your work stays separate from the cloned repo. Lab 5 is the exception — you deploy directly from the cloned `lab5/`.

---

## Lab 1 — Manually code an SDP pipeline

Before SDP, a pipeline was three systems wired together: a streaming job, a batch job, and a scheduler. You declared the *how*. With SDP, you declare the *target table* — the platform owns scheduling, dependencies, and incremental state.

In this lab you'll hand-code that shape end to end: one **Streaming Table** in Python over the bakehouse sample data, and one **Materialized View** in SQL with three `EXPECT` expectations baked in from the start — *log*, *drop row*, *fail update* — so you see every violation behavior in a single run. Two files. Roughly thirty lines of declarative code.

### Set up the pipeline in the Lakeflow Pipelines Editor

Before you write a single line, create the pipeline that will host Steps 1a and 1b:

1. Workspace sidebar → **New** → **ETL pipeline**. The **Lakeflow Pipelines Editor** opens with a default name `New Pipeline <date> <time>`.
2. Click the name → rename to `pipeline_USER_ID`. The editor automatically creates a workspace folder of the same name under your home (`/Workspace/Users/<your-email>/pipeline_USER_ID/`) — no manual `mkdir` needed. That folder is where your Lab 1 work lives; the cloned `lab1/` folder is the answer key.
3. **Right of the pipeline name**, click the catalog/schema selector — a **Default location** modal opens. Set:
   - **Default catalog**: `workshop`
   - **Default schema**: type `USER_ID` and click **Save**. The dropdown sometimes only offers *"Create schema"* even though your `USER_ID` schema already exists — ignore that, the typed literal is accepted.

   Unqualified table names now resolve to `workshop.USER_ID.<table>`. The full **Pipeline settings** panel may open after Save — close it with the ✕ to return to the editor.
4. The default file `my_transformation.py` is already Python — Step 1a uses Python. The editor opens blank with a placeholder; just start typing.
5. Confirm **⚙ Settings** shows **Serverless** ON and Unity Catalog selected.

### Step 1a — Streaming table (Python)

Paste into `my_transformation.py`:

```python
from pyspark import pipelines as dp


@dp.table(
    name="sales_transactions",
    comment="Raw bakery transactions streamed from samples.bakehouse.sales_transactions",
)
def sales_transactions():
    # spark.readStream.table(...) inside @dp.table ⇒ streaming table
    return spark.readStream.table("samples.bakehouse.sales_transactions")
```

Click **Run file**. The DAG sidebar shows one node `sales_transactions` (~3,333 rows).

### Step 1b — Materialized view with data-quality expectations (SQL, copy-and-paste)

Asset browser → **Add → Transformation** → name `sales_stats`, language **SQL** → **Create**. Paste the block below — no replacement step later; the three expectations are already wired in:

```sql
CREATE OR REFRESH MATERIALIZED VIEW sales_stats (
    -- 1. LOG (default): average transaction value within a reasonable range.
    --    Violations are counted in the event log; rows are still written.
    CONSTRAINT reasonable_avg_value
        EXPECT (avg_txn_value BETWEEN 1 AND 1000),

    -- 2. DROP ROW: gross revenue must be non-negative.
    --    Violating rows are excluded from the target; pipeline continues.
    CONSTRAINT nonneg_revenue
        EXPECT (gross_revenue >= 0) ON VIOLATION DROP ROW,

    -- 3. FAIL UPDATE: product must be populated.
    --    Any violation aborts the whole pipeline update with the constraint name.
    CONSTRAINT known_product
        EXPECT (product IS NOT NULL) ON VIOLATION FAIL UPDATE
)
COMMENT 'Sales KPIs grouped by product, with data-quality expectations'
AS SELECT
    product,
    COUNT(*)                     AS txn_count,
    SUM(quantity)                AS units_sold,
    ROUND(SUM(totalPrice), 2)    AS gross_revenue,
    ROUND(AVG(totalPrice), 2)    AS avg_txn_value,
    COUNT(DISTINCT customerID)   AS unique_customers,
    COUNT(DISTINCT franchiseID)  AS franchises_selling
FROM sales_transactions
GROUP BY product;
```

Click **Run pipeline**. The DAG now shows `sales_transactions → sales_stats` (6 rows, one per product). The `sales_stats` node shows the three constraints in its sidebar. Open the event log and filter for `flow_progress` → you'll see a `data_quality.expectations` block with each constraint's `passed_records` / `failed_records` counts.

SDP has **one** constraint syntax — `CONSTRAINT <name> EXPECT (<predicate>)` — and **three** violation behaviors: *log* (default), *drop row*, and *fail update*. Wiring all three into one view shows every behavior in a single round trip.

**Key teaching points**
- Python for the streaming table (1a): `from pyspark import pipelines as dp` + `@dp.table` + `spark.readStream.table(...)` — modern SDP API. Not legacy `import dlt`.
- SQL for the materialized view (1b): `CREATE OR REFRESH MATERIALIZED VIEW` (never `CREATE OR REPLACE`). The relative name `sales_transactions` resolves against the pipeline's default catalog + schema.
- Same pipeline can mix Python and SQL files — no special configuration needed.
- The bakehouse sample data is clean, so all three expectations pass and row counts match a constraint-free version.
- Same `CONSTRAINT ... EXPECT ... [ON VIOLATION ...]` syntax works on **streaming tables**: put the block inside `CREATE OR REFRESH STREAMING TABLE <name> (...)`.

**Is this MV incrementally maintained or fully recomputed?**

A Materialized View is either *incrementally maintained* (only the rows that changed are reprocessed) or *fully recomputed* on refresh, depending on whether the SDP planner can rewrite the query as an incremental update. Simple projections, filters, and many aggregations qualify for incremental maintenance; `COUNT(DISTINCT …)` — which `sales_stats` uses twice — typically forces a **COMPLETE refresh** because distinct tracking isn't incrementally maintainable without a lot more state.

Where to see which mode ran:
- **DAG node** — click the `sales_stats` node; the right-hand flow details panel shows the refresh type (`COMPLETE` vs `INCREMENTAL`) from the most recent run.
- **Event log** — filter by `event_type = 'flow_progress'` and inspect the `details.flow_progress.status` / `planning_information` fields. The planner records the chosen execution mode and, for full recomputes, the reason it couldn't go incremental.
- **Proof by experiment** — drop the two `COUNT(DISTINCT …)` expressions from `sales_stats` and re-run. The planner can now maintain the view incrementally, and the flow details flip to `INCREMENTAL`. Attendees often find this more convincing than reading docs.

**Try a violation yourself (optional)**
- To see a *drop* in action, weaken one predicate (e.g., `EXPECT (avg_txn_value > 10000) ON VIOLATION DROP ROW`) and re-run — rows disappear and the dropped count climbs.
- To see an *abort*, flip `known_product` to `EXPECT (product = 'Cronut')` — the update fails with the constraint name in the error.

### Lab 1 take-away

In about forty lines of declarative code, you've built a streaming ingest of bakehouse transactions, a materialized view that summarises sales by product, and three different data-quality behaviours all firing in the same run. The same shape, written without SDP, would be a streaming job, a batch job, and a scheduler — three separate systems to wire together and keep in sync. Here it lives in one pipeline, expressed as the *target table* you want, and the platform owns the rest.

---

## Lab 2 — Learn how to use Genie Code as a data engineer

Lab 1 you typed every line. Lab 2 you type *one* — the prompt. Genie Code drafts four SQL files: AutoCDC on the `booking_updates` CDC feed, Auto Loader on a JSON volume of fraud markers, a plain Streaming Table on payments, and a gold Materialized View that joins all three. You prompt, you review, you approve.

The skill this lab teaches isn't typing SQL. It's catching the draft that *looks* right and isn't.

### Set up a fresh pipeline for Lab 2

1. Workspace sidebar → **New** → **ETL pipeline**. Rename to `pipeline_USER_ID_lab2`. The editor auto-creates a workspace folder of the same name under your home — Genie Code will write the four SQL files it generates there.
2. Set **Default catalog** to `workshop` and **Default schema** to `USER_ID` (same as Lab 1).

The cloned `lab2/` folder is your answer key — keep it open in another tab to verify what Genie produces.

### Open Genie Code

1. Upper-right of the workspace → click **Genie Code**. The side panel opens.
2. At the bottom of the Genie Code pane, confirm the **Agent** mode selector is set to **Agent** (not **Chat**).
3. Expect approval prompts (Allow / Decline / Allow in this thread / Always allow) whenever Genie Code wants to create a file or run code — **never** click *Always allow* in this lab; reviewing each diff is the point.

### The prompt

Paste the following into Genie Code Agent:

```text
In this Lakeflow Pipelines Editor, build a SQL-only pipeline that answers:
"For our Wanderbricks bookings, how many are fraudulent and how much gross revenue is at risk, broken down by payment method?"

Inputs:
- samples.wanderbricks.booking_updates — a CDC stream of booking-state changes (natural key booking_id, sequence column updated_at).
- samples.wanderbricks.payments — one or more payment rows per booking with amount and payment_method.
- /Volumes/workshop/shared/landing/booking_fraud_flags/ — JSON files marking fraudulent bookings (fields: booking_id, flag, reason, flagged_at, confidence).

Please:
1. Ingest the two sample tables and the JSON volume with the appropriate SDP pattern for each (AutoCDC, Auto Loader, plain stream).
2. Produce one gold materialized view aggregated by payment_method showing booking_count, gross_amount, fraud_count, fraud_amount, fraud_pct.
3. Use CREATE OR REFRESH throughout. Run the pipeline and report row counts.
```

This is deliberately higher-level — it states the *business question* and the *inputs*, and lets Genie Code plan the solution (table names, columns, join shape, aggregation form). This is the honest way to use an AI data engineering agent.

### Verify — the step that matters most

Because the prompt is high-level, Genie Code has room to make choices. Before clicking **Allow** on each proposed file, check it against the reference SQL below. Expected properties of a good generation:

- Four files: a streaming table with `AUTO CDC INTO` on `booking_updates`, a streaming table using `STREAM read_files(...)` on the JSON volume, a plain streaming table on `payments`, and one materialized view.
- `CREATE OR REFRESH` everywhere — never `CREATE OR REPLACE`.
- `SCD TYPE 1` for the AutoCDC target (TYPE 2 is also acceptable but reviewed for your use case).
- The MV groups by `payment_method` and includes `fraud_count` / `fraud_amount` / `fraud_pct`.

If a file drifts (extra staging tables, `CREATE OR REPLACE`, missing `STREAM` keyword on `read_files`, a Python file instead of SQL), **Decline** and ask Genie Code to fix it, e.g. *"Replace CREATE OR REPLACE with CREATE OR REFRESH"* or *"Remove the intermediate table — keep only the four files"*.

The reference SQL below is **one valid shape** — your generation may use different table names or column names. That is fine as long as the result answers the business question.

AutoCDC is a time-lapse, not a scrapbook. Every update collapses into one current row per `booking_id` — the latest state wins, history fades.

#### Reference — `bookings_current.sql`

```sql
CREATE OR REFRESH STREAMING TABLE bookings_current
COMMENT 'Latest state of each booking, rebuilt from booking_updates via AutoCDC';

CREATE FLOW bookings_current_flow AS AUTO CDC INTO bookings_current
FROM stream(samples.wanderbricks.booking_updates)
KEYS (booking_id)
SEQUENCE BY updated_at
COLUMNS * EXCEPT (booking_update_id)
STORED AS SCD TYPE 1;
```

Expected after run: one row per distinct `booking_id` in `booking_updates` (~48K). Booking `50928` should have status `completed`.

#### Reference — `booking_fraud_flags.sql`

```sql
CREATE OR REFRESH STREAMING TABLE booking_fraud_flags
COMMENT 'Fraud markers for bookings, ingested via Auto Loader from the shared landing volume'
AS SELECT
    booking_id,
    flag,
    reason,
    CAST(flagged_at AS TIMESTAMP)    AS flagged_at,
    confidence,
    _metadata.file_path              AS source_file,
    _metadata.file_modification_time AS source_file_ts
FROM STREAM read_files(
    '/Volumes/workshop/shared/landing/booking_fraud_flags/',
    format => 'json'
);
```

Expected after run: row count equals the number of JSON records seeded in the shared volume; `source_file` populated.

#### Reference — `payments.sql`

```sql
CREATE OR REFRESH STREAMING TABLE payments
COMMENT 'Payments stream from samples.wanderbricks.payments'
AS SELECT
    payment_id,
    booking_id,
    amount,
    payment_method,
    status,
    payment_date
FROM stream(samples.wanderbricks.payments);
```

Expected after run: ~49,638 rows.

#### Reference — `booking_fraud_summary.sql`

```sql
CREATE OR REFRESH MATERIALIZED VIEW booking_fraud_summary
COMMENT 'Booking totals and fraud rate per payment method'
AS
WITH fraud_bookings AS (
    -- DISTINCT because the same booking can appear in multiple flag JSON files.
    SELECT DISTINCT booking_id
    FROM booking_fraud_flags
)
SELECT
    p.payment_method,
    COUNT(DISTINCT b.booking_id)                                                  AS booking_count,
    ROUND(SUM(p.amount), 2)                                                       AS gross_amount,
    COUNT(DISTINCT f.booking_id)                                                  AS fraud_count,
    ROUND(SUM(CASE WHEN f.booking_id IS NOT NULL THEN p.amount ELSE 0 END), 2)    AS fraud_amount,
    ROUND(COUNT(DISTINCT f.booking_id) * 100.0 / COUNT(DISTINCT b.booking_id), 2) AS fraud_pct
FROM bookings_current      b
JOIN payments              p ON p.booking_id = b.booking_id
LEFT JOIN fraud_bookings   f ON f.booking_id = b.booking_id
GROUP BY p.payment_method;
```

Expected after run: 5 rows (one per `payment_method`: credit_card, paypal, apple_pay, google_pay, bank_transfer). Each should have non-zero `fraud_pct` and `fraud_amount` in the same units as `payments.amount`.

### Ask Genie Code in Chat mode

Switch Genie Code to **Chat** mode and ask:

```text
Explain the data flow in this pipeline end-to-end. Which node is incrementally maintained versus fully recomputed on refresh, and why?
```

> Reference copies of the four SQL files live in [`lab2/`](./lab2/) alongside this guide — use them as the answer key when verifying Genie Code's output.

---

## Lab 3 — CI/CD via Declarative Automation Bundles (Gourmet Pipeline)

A data product lives in more than one place — a pipeline, a job, a dashboard, a connector flow. Today it probably moves between environments by runbook, screenshot, and hope. A **Declarative Automation Bundle** (DAB — formerly *Databricks Asset Bundle*; the CLI is still `databricks bundle`) collapses all of that into one folder: `databricks.yml` plus `resources/`, versioned like code. No shell recipes, no drift between envs, no screenshot-driven promotion.

Same bundle, two front doors. Interactive deploy from the Workspace **Deployments** pane — what you'll do here. Non-interactive `databricks bundle deploy -t prod` — what a GitHub Action does on merge to main. You'll sparse-clone `databricks/tmm/Lakeflow-Gourmet-Pipeline`, retarget two variables, and ship the whole data product — SQL medallion pipeline, `gourmet-workflow` job with `ai_query` enrichment, AI/BI dashboard — in a single deploy.

Source repo: `https://github.com/databricks/tmm/tree/main/Lakeflow-Gourmet-Pipeline`.

### What Gourmet Pipeline demonstrates

A global snack company's end-to-end data product: a Bronze → Silver → Gold medallion architecture authored entirely in **SQL** with Spark Declarative Pipelines, ingestion via **Lakeflow Connect** (from SFDC, MS SQL, and XML volumes — the workshop version uses stub endpoints so you don't need real creds), enrichment with **AI functions** (recipe generation, sentiment, translation), and a published **AI/BI dashboard** served via **Databricks One**. A single `gourmet-workflow` job orchestrates the whole thing. Data-quality rules are declared inline with `EXPECT` constraints.

### Step 3a — Clone the repo into your workspace

1. Workspace sidebar → click **Workspace**.
2. Top-right **Create** → **Git folder**.
3. In the **Create Git folder** dialog:
   - **Git repository URL**: `https://github.com/databricks/tmm`
   - **Git provider**: GitHub
   - Enable **Sparse checkout mode**
   - **Sparse checkout path**: `Lakeflow-Gourmet-Pipeline`
4. Click **Create Git folder**. The subfolder clones into your workspace.

### Step 3b — Adjust `databricks.yml` for your schema

Open `Lakeflow-Gourmet-Pipeline/databricks.yml`. The `variables` block you need to edit looks like this (defaults shown):

```yaml
variables:
  prod_warehouse_id:
    description: define prod warehouse id
    default: 5834a7035a11c525       # ← replace with a warehouse in YOUR workspace

  catalog_name:
    description: "Catalog name for the pipeline"
    default: daiwt_gourmet          # ← change to your workshop catalog: workshop

  schema_name:
    description: "Schema name for the pipeline"
    default: ${workspace.current_user.short_name}
                                    # ← see note below: usually leave this alone,
                                    #   override to USER_ID only if needed
```

**Per-student adjustments (do this in the file):**

1. **`catalog_name`** — change the `default:` value to the workshop catalog (replace `workshop` with the name your instructor gave you).
2. **`prod_warehouse_id`** — go to the workspace sidebar → **SQL Warehouses**, copy the ID of a running warehouse, and paste it here.
3. **`schema_name`** — the default `${workspace.current_user.short_name}` automatically resolves to your Databricks username short form. **If that already matches your pre-assigned `USER_ID` schema** (common when the workshop schema name = your username), leave it. **If your workshop schema uses a different naming convention**, override the `default:` to your literal `USER_ID` value.

Also check the `targets.presenter` block at the bottom — if it overrides `schema_name`, make sure it also points at `USER_ID`.

**4. Patch the dashboard SQL if you changed `catalog_name`** — dashboard SQL cannot be parameterized by bundle variables, so the literal catalog name is baked into the dashboard definition. If you changed `catalog_name` from `daiwt_gourmet` to `workshop` in step 1 above, you must also open `resources/dashboard_gourmet_aibi.yml` and `src/aibi_dashboard.json` and replace every occurrence of `daiwt_gourmet` with `workshop`. Skipping this leaves a dashboard that points at a catalog you don't have access to and renders empty.

### Step 3c — Verify the AI model endpoint exists on your workspace

The `new_recipe_Claude_LLM` task in `gourmet-workflow` calls `ai_query('databricks-claude-3-7-sonnet', ...)` from `src/ai_query.sql`. That older endpoint is **not** available on every workspace. Check before you deploy:

1. Workspace sidebar → **Serving**. Look for `databricks-claude-3-7-sonnet` in the endpoints list.
2. **If present** — do nothing, skip to Step 3d.
3. **If missing** — pick a Claude endpoint that IS available (e.g. `databricks-claude-sonnet-4-5` or `databricks-claude-haiku-4-5`) and edit `src/ai_query.sql`, replacing **both** occurrences of `databricks-claude-3-7-sonnet` (one in the `COMMENT` docstring, one in the `ai_query(...)` call).

Alternatively, if you don't want to run the AI tasks at all, skip this step and later at Step 3e override the `ai_enabled` job parameter to `FALSE` when you trigger the run — the workflow will short-circuit after the ETL pipeline.

### Step 3d — Deploy the bundle

1. Navigate into the cloned `Lakeflow-Gourmet-Pipeline/` folder in Workspace. Because `databricks.yml` is present, the left pane shows the **Deployments** icon (🚀).
2. Click **Deployments** → select the target workspace (the bundle defaults to a target named `presenter`) → click **Deploy**.
3. Wait for validate + deploy to finish. The **Bundle resources** panel populates with the deployed assets: SDP pipelines (bronze/silver/gold transformations), a multi-task workflow `gourmet-workflow`, and an AI/BI dashboard.

### Step 3e — Run the workflow

1. In **Bundle resources**, find **Jobs → `gourmet-workflow`**. Click the **Run** (▶) icon.
2. Monitor progress in **Job Runs**. The workflow ingests franchise / supplier / transaction data, runs the SDP transformations, executes the AI enrichment steps, and refreshes the dashboard.
3. After the run finishes, open the deployed **AI/BI dashboard**.

One YAML file just deployed the medallion pipeline, the orchestration job, the AI enrichment, and the dashboard.

### The CI/CD equivalent in one snippet

You deployed interactively. A CI runner deploys the same bundle with two CLI calls:

```bash
databricks bundle validate
databricks bundle deploy -t presenter
```

`presenter` is the only target the demo bundle ships with — a single development-mode target with `source_linked_deployment: true`. In a real CI/CD setup you'd add additional `targets:` entries (e.g. `dev` and `prod`) with environment-specific overrides for `catalog_name`, `prod_warehouse_id`, `mode`, and so on, and let the workflow pick the target per branch (`-t dev` on pull-request-open, `-t prod` on push-to-main). The bundle is the deployable atom; the UI and the CLI are two entry points to the same deploy.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Bundle validate fails on warehouse ID | default `prod_warehouse_id` doesn't exist in your workspace | paste a real warehouse ID from **SQL Warehouses** |
| `new_recipe_Claude_LLM` task fails with `RESOURCE_DOES_NOT_EXIST` for endpoint `databricks-claude-3-7-sonnet` | you skipped Step 3c — the hardcoded model isn't on this workspace | go back to Step 3c: either edit `src/ai_query.sql` to a Claude endpoint that exists on your workspace, or rerun with job parameter `ai_enabled=FALSE` |
| SCHEMA_NOT_FOUND errors during run | `schema_name` resolves to something that doesn't exist in your catalog | override the `schema_name` default to your literal `USER_ID` |
| Dashboard renders empty after deploy | the dashboard's SQL still references `daiwt_gourmet` because dashboard SQL isn't parameterized | go back to Step 3b item 4: replace `daiwt_gourmet` with `workshop` in `resources/dashboard_gourmet_aibi.yml` and `src/aibi_dashboard.json`, then redeploy |
| SFDC / MS SQL connection errors | shouldn't happen — the demo uses stub endpoints | re-check you're on the demo branch of the repo, not a modified fork |

### What to take away

- **Bundles are the CI/CD primitive for data products**: `databricks.yml` + `resources/*.yml` captures an entire data product (SDP pipelines, jobs, dashboards, Lakeflow Connect flows) as versioned code. One file tree, committable, reviewable, deployable.
- **Targets are how you separate environments**: `targets:` in `databricks.yml` defines per-environment overrides. The demo bundle ships with only `presenter`; production setups extend that with `dev` and `prod` targets and let CI pick one per branch (`databricks bundle deploy -t prod` on merge to main, `-t dev` on PR open) — same bundle, different catalog and warehouse.
- **Variables + workspace placeholders**: `${workspace.current_user.short_name}` lets one bundle deploy per-user in dev with no hardcoded schemas.
- **Git folder + sparse checkout**: clone exactly the subfolder you need from a large repo without pulling everything.
- **UI deploy and CLI deploy share the same bundle**: the **Deployments** (🚀) pane and `databricks bundle deploy` read the same `databricks.yml`. Hands-on-UI for learning and one-off promotions, CLI-in-CI for production.

---

## Lab 4 — Work with Zerobus Ingest to push IoT data

> **Format: live instructor demo.** The instructor will run this end-to-end on the projector. Attendees are welcome to follow along in their own workspace — every asset is already provisioned for you — but the teaching point is the *governance surface* (scoped OAuth, SP audit identity, secret scope), which lands better when talked through than typed in silence. If you're short on time, watch and ask questions; come back to it later.

Until now, data came to you — sample tables, a JSON volume, a Delta stream. Lab 4 flips the script: **you** are the producer.

One HTTP POST lands one row in `workshop.zerobus.course_temp`. No Kafka, no Auto Loader, no pipeline. The token that authorises the POST is a *hotel keycard, not a master key* — scoped via `authorization_details` to `MODIFY` on that one table, and nothing else. Secrets come from a shared scope; the notebook never sees the raw client_secret.

Zerobus offers three interfaces — gRPC SDK, REST, OpenTelemetry. The SDK has the highest throughput but can't `pip install` on serverless, so for this workshop the demo uses the **REST API** (Beta): `requests.post`, one record, one ACK. Perfect for chatty low-frequency producers — the exact shape an external IoT device would run.

### Why Zerobus when `INSERT` is right there?

Fair question. From inside a Databricks notebook, attendees have a Spark session and could run `INSERT INTO workshop.zerobus.course_temp VALUES(...)` in two lines — if we granted them `MODIFY` on the table. We deliberately don't. Zerobus isn't built for notebooks with a Spark session. It's built for everything without one — IoT devices, microservices, edge gateways. The attendee notebook stands in for one of those external producers. What you're actually learning here — scoped OAuth via `authorization_details`, a POST to a Databricks-managed gRPC/REST gateway, a per-record ACK — is the exact code an external system would run. Running it from inside Databricks is the teaching compromise; the pattern is for outside.

### Target

A managed Delta table provisioned by the setup notebook:

| catalog | schema | table | columns |
|---|---|---|---|
| `workshop` | `zerobus` | `course_temp` | `id STRING, city STRING, temp FLOAT` |

### Credentials model

Your notebook never sees the service principal credentials. The setup notebook created:

- One shared SP `workshop-zerobus-sp` with `MODIFY + SELECT` only on `workshop.zerobus.course_temp` (nothing else)
- A secret scope named `workshop` holding `zerobus_client_id`, `zerobus_client_secret`, `zerobus_endpoint`, `zerobus_workspace_id`, `zerobus_workspace_url`
- `READ` ACL on the scope granted to `account users`

At runtime your notebook reads the five values via `dbutils.secrets.get("workshop", ...)`. If someone leaks the client_secret, its blast radius is the single table it can write to.

### Step 4a — Open the reference notebook

Asset browser (or Workspace) → **Add → Exploration** → name `send_temperature` → language **Python** → **Create**. Paste the contents of [`lab4/send_temperature.py`](./lab4/send_temperature.py).

### Step 4b — Fill in the two widgets at the top

- **City** — your city (e.g. `Munich`)
- **Temperature (°C)** — any float (e.g. `21.5`)

### Step 4c — Run the **Submit** cell

That cell calls `submit_temperature(CITY, TEMP)`, which the notebook's plumbing cell defines. The plumbing cell is marked **⛔ DO NOT MODIFY** — it reads secrets, generates a UUID, exchanges the SP creds for an OAuth token scoped to the table via `authorization_details`, and posts a one-element JSON array to:

```
POST https://<workspace_id>.zerobus.<region>.cloud.databricks.com/zerobus/v1/tables/workshop.zerobus.course_temp/insert
```

On success you'll see:

```
✅ Sent to workshop.zerobus.course_temp: {'id': '…', 'city': 'Munich', 'temp': 21.5}
```

### Step 4d — Verify in the notebook

The last cell runs `spark.table("workshop.zerobus.course_temp").where(col("city") == "Munich")`. Your row appears within a few seconds. Zerobus REST is exactly-once at the protocol level (per-record ACK with idempotency); a client that retries on transport errors becomes at-least-once. Order isn't guaranteed across producers.

### Step 4e — Verify in Databricks SQL

The notebook read the table as a producer; now read it as a consumer. This proves the row is a real row in a real governed table, queryable by anything that can talk to a SQL warehouse — a BI dashboard, a downstream pipeline, a JDBC client, `ai_query(...)`.

1. Workspace sidebar → **SQL Editor** → **New query**.
2. In the top-right warehouse picker, select the **course warehouse** — `<course_warehouse_name>` (ID `<course_warehouse_id>`). It was provisioned for you by the courseware, so it's already running; you don't need to start a warehouse of your own.
3. Paste and run:

```sql
SELECT id, city, temp
FROM workshop.zerobus.course_temp
ORDER BY city, temp;
```

You should see every attendee's row, including your own. In a real production deployment this is the query a dashboard would run, refreshed on a schedule — same table, same grants, no separate serving tier.

### Governance surface — who wrote what, and what could they write?

This is the part of the design most workshop material skips. The SP+Zerobus model vs. a "just grant MODIFY and INSERT" model differ in ways that matter once you leave the workshop:

| Dimension | Zerobus + SP (this lab) | Direct `INSERT` (attendees granted MODIFY) |
|---|---|---|
| **Producer identity in audit** | `workshop-zerobus-sp` — one row per ingest in the audit log, trivially traceable back to the Lab 4 flow. Queryable: `SELECT * FROM system.access.audit WHERE user_identity.email = 'workshop-zerobus-sp'`. | Each attendee's own user identity, mixed in with every other query they ran that session. Forensics have to filter by action type (`writeTable`) and table name. |
| **What the credential can do** | SP token is minted per-request with `authorization_details` pinning it to `USE CATALOG` + `USE SCHEMA` + `MODIFY/SELECT` on **this one table**. A leaked token can only append rows to `course_temp`. Cannot `DELETE`, cannot `DROP`, cannot touch any other table. | Attendee holds a PAT / session token with whatever grants they have. `MODIFY` on the table allows `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `OPTIMIZE`, `VACUUM` — anything write-shaped. Harder to reason about. |
| **Revocation** | Rotate the SP's OAuth client secret in the setup notebook — old secret stops working, scope gets the new one, attendees notice nothing. No per-attendee churn. | Have to revoke/adjust grants on the group. If attendees wandered off with a PAT, the PAT keeps working until it's explicitly revoked. |
| **Credential surface** | Stored only in the `workshop` secret scope; `dbutils.secrets.get(...)` auto-redacts from notebook output; never lives in a notebook source file. | No extra credential — the attendee uses their own identity. Lower credential risk, but higher *authorization* risk because the identity is broad-purpose. |
| **Scales to 1,000 producers?** | Yes: each producer gets its own SP or they all share one; either way the path of least privilege stays the same. | Doesn't apply outside Databricks — external producers have no Databricks user identity to authenticate as. |

The TL;DR: the SP + scoped OAuth model **narrows the credential** (it can only do one thing on one table), **widens the audit trail** (you always know which producer flow wrote a row), and **scales to producers outside your workspace**. Direct `INSERT` is simpler for in-workspace use but can't express any of those properties.

### What to take away

- **Direct-to-Delta ingest** — one POST, one row, no intermediate bus. Ideal for edge devices or low-volume producers that live outside Databricks.
- **Fine-grained OAuth — a hotel keycard, not a master key.** `authorization_details` scopes the token to one table: a leaked token can append rows to `course_temp`, and nothing else. No `SELECT *`, no `DELETE`, no `DROP`.
- **Producer identity in audit** — `system.access.audit` attributes the write to `workshop-zerobus-sp`, not to the attendee. That's the right answer for "which pipeline produced this row?" queries.
- **Secret scope, not copy-paste** — attendees read creds from `dbutils.secrets.get(...)`, which the Databricks UI auto-redacts. Creds never land in notebook source, exports, or screen shares.
- **REST vs gRPC SDK trade-off** — REST is a handshake per record (higher per-record cost), gRPC holds a persistent stream (much higher throughput). For this workshop, one record per attendee, REST is the right call. At volume, use the SDK.
- **Zerobus does not create tables** — the table must exist with the exact schema before any record can land.

> Reference notebook: [`lab4/send_temperature.py`](./lab4/send_temperature.py).

---

## Lab 5 — Real-Time Mode for SDP (optional)

> **Optional.** Skip if you're short on time — nothing else in the workshop depends on it. The whole demo is a single file deployed via a Declarative Automation Bundle, ~5 minutes hands-on.

Standard SDP runs as micro-batches — fine for seconds-level latency, not for milliseconds. **Real-Time Mode (RTM)** is a specialization of SDP's continuous mode that pushes end-to-end latency as low as ~5 ms by combining three optimisations:

- **Long-running batches** — a single batch (default 5 min) processes records as they arrive, instead of restarting per micro-batch.
- **Simultaneous stage scheduling** — all query stages run concurrently, so the cluster must have task slots ≥ sum of tasks across stages.
- **Streaming shuffle** — downstream stages consume from upstream as data is produced, not after the upstream completes.

> **Public Preview:** RTM for Lakeflow SDP requires the SDP **PREVIEW** channel.

### What you'll deploy

A minimal three-piece pipeline, all in one file:

1. **Source** — a synthetic `rate` stream (RTM officially supports Kafka, MSK, Event Hubs, Kinesis EFO; `rate` is used here for portability).
2. **Update Flow** — RTM **requires** `@dp.update_flow` (not `@dp.table` / `@dp.view`) with `pipelines.execution.realTimeMode = true` set at the flow level.
3. **Sink** — declared up-front with `dp.create_sink(...)`. Production RTM uses Kafka-family sinks; this demo writes to `console` so aggregates land in the **driver log**.

The pipeline reads the rate stream, derives a synthetic `temperature_c`, runs a sliding-window aggregation (10-second window, 2-second slide), and emits an `engine_latency_ms` column on every row — the time between the newest event in the window and the row landing in the sink. RTM ≈ a few–tens of ms, MicroBatch ≈ hundreds+. Smaller = better.

### Step 5a — Open the RTM bundle

You already cloned the workshop repo at the start. Navigate to the `lab5/` subfolder — it has `databricks.yml` and `transformations/temperature_rtm.py` ready to deploy.

### Step 5b — Adjust the bundle for your schema

Open `lab5/databricks.yml`. Two variables drive the deploy — set them to your values:

```yaml
variables:
  catalog_name:
    default: workshop          # leave as-is for the workshop
  schema_name:
    default: USER_ID           # ← replace with your own USER_ID
```

`continuous: true`, `serverless: true`, `channel: PREVIEW`, and the RTM enable flag are already set — leave them as-is.

### Step 5c — Deploy and run from the Workspace UI

1. Open the `lab5/` folder in your Workspace. Because `databricks.yml` is present, the **Deployments** icon (🚀) appears in the left pane.
2. Click **Deployments** → pick a target → **Deploy**.
3. After validate + deploy finishes, open the deployed `sdp-rtm-rate-source` pipeline and click **Run**. Because it's continuous, it keeps running — no need to re-trigger.

### Step 5d — Look up the engine latency in the driver logs

The console sink writes the windowed aggregates — including `engine_latency_ms` — straight to the **driver log**. To find it:

1. In the Lakeflow Pipelines Editor, with your `sdp-rtm-rate-source` pipeline open, click **Compute** at the top.
2. In the compute pane, click **Driver logs**.
3. Scroll the log output. You'll see batch outputs from the console sink with rows like:

   ```
   +--------------------+--------------------+-----------+------------------+...+-----------------+
   |window_start        |window_end          |event_count|avg_temp_c        |   |engine_latency_ms|
   +--------------------+--------------------+-----------+------------------+...+-----------------+
   |2026-05-15 09:42:18 |2026-05-15 09:42:28 |1000       |22.51             |   |37               |
   ```

4. Read off the `engine_latency_ms` column — that's the end-to-end latency from the newest event in the window to the row landing in the sink. With RTM, expect a few tens of milliseconds. Toggle RTM off in `databricks.yml` (set `spark.databricks.streaming.realTimeMode.enabled` to `"false"`) and redeploy to see how the same pipeline behaves in micro-batch mode — the latency typically jumps to several hundred milliseconds.

> Reference files: [`lab5/databricks.yml`](./lab5/databricks.yml) and [`lab5/transformations/temperature_rtm.py`](./lab5/transformations/temperature_rtm.py). Originally based on [`Lakeflow-SDP-RTM-Basics`](https://github.com/databricks/tmm/tree/main/Lakeflow-SDP-RTM-Basics) in the public `databricks/tmm` repo.

---

## Lab 6 — Iceberg side-quest (optional)

> **Optional / take-home.** Skip if you're short on time — nothing else in the workshop depends on it. Run after Lab 1 or any time after; only the Bakehouse `sales_transactions` streaming table from Lab 1 is a prerequisite.

Publish a derived bakehouse result as a **managed Iceberg table** — then read it back with **PyIceberg** through the Unity Catalog Iceberg REST endpoint. No Spark session, no cluster, no connector JAR. That's the portability pitch of Iceberg on Unity Catalog: the same table Databricks writes is readable by Trino, Snowflake, OSS Spark, or any pure-Python client.

### Step 6a — Top-5 sales locations as a managed Iceberg table (SQL, outside the pipeline)

The streaming table from Lab 1 is Delta. To make a derived result readable by any Iceberg-compatible engine without configuring an external location for UniForm Compatibility Mode, the simplest path is a **CTAS into a managed Iceberg table** — run it *outside* the pipeline in the SQL editor or a `%sql` cell.

Open a new SQL editor tab (sidebar **SQL Editor** → **Create new query**) and run, replacing `workshop` and `USER_ID`:

```sql
CREATE OR REPLACE TABLE workshop.USER_ID.global_sales_gold
USING ICEBERG
AS
SELECT
    f.city,
    f.country,
    COUNT(*)                    AS txn_count,
    SUM(t.quantity)             AS units_sold,
    ROUND(SUM(t.totalPrice), 2) AS gross_revenue
FROM workshop.USER_ID.sales_transactions t
JOIN samples.bakehouse.sales_franchises f
    USING (franchiseID)
GROUP BY f.city, f.country
ORDER BY gross_revenue DESC
LIMIT 5;
```

**Why this shape:**
- `USING ICEBERG` creates a **native managed Iceberg table** — full read/write from Databricks *and* external engines via the UC Iceberg REST Catalog (IRC).
- No `delta.universalFormat.*` properties, no `compatibility.location`, no external location to pre-configure. Managed Iceberg is self-contained.
- Snapshot, not live. Re-run this CTAS (or swap to `INSERT OVERWRITE`) to refresh — acceptable for an analytics/gold table; if you need live-as-it-changes semantics, that's UniForm Compatibility Mode territory instead.
- `samples.bakehouse.sales_franchises` supplies the `city` / `country` dimensions — `sales_transactions` itself only has `franchiseID`.

Verify:

```sql
SELECT * FROM workshop.USER_ID.global_sales_gold;
```

You should see 5 rows, top (city, country) pairs by gross revenue (a city in two countries would count twice). In `DESCRIBE EXTENDED`, the `Provider` column reads `iceberg`.

### Step 6b — Read the Iceberg table with PyIceberg (Exploration notebook)

Now read the same table with a lightweight Iceberg client — no Spark required.

Asset browser → **Add → Exploration** → name `read_global_sales_gold` → language **Python** → **Create**. Paste:

```python
# MAGIC %pip install --upgrade "pyiceberg>=0.9,<0.10" "pyarrow>=17,<20"
# (Azure workspaces only) %pip install adlfs
dbutils.library.restartPython()
```

```python
from pyiceberg.catalog import load_catalog

WORKSPACE = spark.conf.get("spark.databricks.workspaceUrl")  # e.g. "dbc-xxx.cloud.databricks.com"
CATALOG   = "workshop"   # workshop UC catalog
SCHEMA    = "USER_ID"      # your pre-assigned schema
TOKEN     = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

iceberg_catalog = load_catalog(
    "uc",
    uri=f"https://{WORKSPACE}/api/2.1/unity-catalog/iceberg-rest",
    warehouse=CATALOG,     # pins the UC catalog — subsequent identifiers are <schema>.<table>
    token=TOKEN,
)

tbl = iceberg_catalog.load_table(f"{SCHEMA}.global_sales_gold")
print(tbl.current_snapshot())             # snapshot metadata proves this is Iceberg
tbl.scan(limit=10).to_pandas()            # top-5 rows as pandas
```

Expected output: a pandas DataFrame with the same 5 (city, country) pairs you saw in Step 6a, plus snapshot metadata for the Iceberg table.

**What you just demonstrated:**
- `pip install pyiceberg` — no cluster restart, no Iceberg JARs, no Spark session. A pure-Python client talks to Unity Catalog via the **Iceberg REST Catalog** endpoint at `/api/2.1/unity-catalog/iceberg-rest`.
- The `warehouse` parameter pins the UC catalog, so table identifiers collapse from three-part to two-part.
- External clients run this same code. Supply a PAT or OAuth token and the workspace URL — done. That's the portability of Iceberg on Unity Catalog.

**Requirements your admin has likely already set** (workshop attendees usually inherit these; flag with the instructor if any call fails with `403`):
- `EXTERNAL USE SCHEMA` on `workshop.USER_ID`
- External data access enabled on the workspace
- Workspace IP access list (if enabled) allows your client

> Reference copies of the CTAS and the PyIceberg reader live in [`lab6/`](./lab6/) alongside this guide.

---

## References and other demos

* [Get to know Genie Code: Lakeflow and Analytics](https://www.databricks.com/resources/demos/videos/get-know-genie-code)
* Complete [Lakeflow Demo: From messy sales data to AI insights](https://www.databricks.com/resources/demos/videos/lakeflow-action-gourmet-pipeline-demo-daiwt)
* Getting Started with [OSS Apache SDP, VSCode](https://github.com/databricks/tmm/tree/main/OSS-SDP-OpenSkyNetwork)
* [Lakeflow SDP — Real-Time Mode Basics](https://github.com/databricks/tmm/tree/main/Lakeflow-SDP-RTM-Basics) (source for Lab 5)
* RTM demo to watch: [Air Traffic Control with Apache Spark Structured Streaming — Real-Time Mode](https://www.databricks.com/resources/demos/videos/air-traffic-control-with-apache-spark-structured-streaming-real-time-mode)
* Other [Databricks workshops](https://www.databricks.com/events?event_type=workshop&region=all) for DBSQL, AI, Unity Catalog
