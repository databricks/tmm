# AI-Powered Data Engineering with Lakeflow

**Version 2.0 - May 2026**

> **Audience**: entry- to mid-level data engineers, with no or some prior Databricks knowledge. The environment is already set up for you — you have an empty workspace in an account with a pre-assigned schema `workshop.USER_ID`.

### Overview

- **Lab 1 — Manually code an SDP pipeline**: streaming table in **Python**, materialized view in **SQL** with three data-quality expectations wired in from the start. Reference files in [`labs/01-SDP/`](./labs/01-SDP/).
- **Lab 2 — Learn how to use Genie Code as a data engineer**: all-**SQL** pipeline (AutoCDC + Auto Loader + join gold MV), produced from a single Genie Code prompt — and verified by you before it runs. Reference files in [`labs/02-GenieCode/`](./labs/02-GenieCode/).
- **Lab 3 — Work with Zerobus Ingest to push IoT data** *(live instructor demo; attendees may follow along)*: one `ingest_record(...)` call via the official `databricks-zerobus-ingest-sdk` (gRPC) lands a row in `workshop.zerobus.measurements`, with credentials fetched from a shared UC config table. Reference files in [`labs/03-Zerobus/`](./labs/03-Zerobus/).
- **Lab 4 — Real-Time Mode for SDP** *(optional)*: deploy a continuous pipeline running in Real-Time Mode (RTM), watch sub-second latency aggregates land in the driver console, and read the engine latency from the driver logs. Reference bundle in [`labs/04-SDP-RTM/`](./labs/04-SDP-RTM/).
- **Lab 5 — Iceberg side-quest** *(optional)*: publish a derived bakehouse result as a managed Iceberg table and read it back with PyIceberg through the Unity Catalog Iceberg REST endpoint — no Spark session required. Reference files in [`labs/05-Iceberg/`](./labs/05-Iceberg/).
- **Lab 6 — CI/CD via Declarative Automation Bundles** *(optional)*: clone a public repo with a DAB, retarget two variables to `workshop.USER_ID`, and deploy it from the **CLI** with `databricks bundle deploy` — the same path a CI runner takes.

## Important — Your User ID

This workshop is designed so it can be run with thousands of participants in a single Databricks account sharing a number of workspaces. We therefore use your **USER_ID** (derived from your login email) to separate schemas and pipelines and avoid namespace clashes.

To get your user id, check your login email by clicking on the user avatar (e.g. **L**) at the **top right** of the workspace. Example: `labuser10148895_1745997814@vocareum.com` means your user id is `labuser10148895_1745997814`.

Throughout this guide, replace `USER_ID` with that exact value. Your pre-assigned schema is `workshop.USER_ID`.

## Prerequisites (already done by the setup notebook)

- Your catalog `workshop` / your schema `workshop.USER_ID` already exists and is writable.
- A shared volume exists at `/Volumes/workshop/shared/landing/` with a seeded subfolder `booking_fraud_flags/` containing JSON fraud markers keyed by `booking_id`. The volume is **read-only** for attendees (every attendee has `READ_VOLUME`, nobody has `WRITE_VOLUME`), so one attendee cannot disrupt another.
- The Zerobus target table `workshop.zerobus.measurements` (`id, city, temperature, comment`), the shared service principal `workshop-zerobus-sp` (with `USE CATALOG` on `workshop`, `USE SCHEMA` on `workshop.zerobus`, and `MODIFY + SELECT` on the table), and the config table `workshop.zerobus.config` (single row holding `client_id`, `client_secret`, `workspace_url`, `workspace_id`, `zerobus_endpoint`) are all pre-provisioned for Lab 3.
- This lab runs completely serverless.
- You can read `samples.bakehouse.*` and `samples.wanderbricks.*` (public sample data).

### Substitutions

Three placeholders show up throughout — resolve them once here, then paste blocks run as-is.

| Placeholder | What to use |
|---|---|
| `USER_ID` | Your user id, derived from your login email (see above). Example: `labuser10148895_1745997814`. Your schema is `workshop.USER_ID`. |
| `workshop` | The catalog used for all labs. This is fixed. No need to change this. |
| `<course_warehouse_name>` / `<course_warehouse_id>` (Lab 3 only) | The course SQL warehouse provisioned for you by the courseware. Your instructor will share the exact name and ID. |
| `prod_warehouse_id` (Lab 6 only) | A running SQL warehouse ID. Find it in sidebar **SQL Warehouses** → click a warehouse → copy the ID from the URL. |

## One-time setup — Clone this workshop repo

Clone this repo into your Workspace once at the start. You get this lab guide and all the labs locally. We use **sparse checkout** so you only pull the workshop subfolder, not the entire `databricks/tmm` repo.

1. Workspace sidebar → **Workspace** → **Create** → **Git folder**.
2. In the **Create Git folder** dialog:
   - **Git repository URL**: `https://github.com/databricks/tmm`
   - **Git provider**: GitHub
   - **Git folder name**: `de_workshop`
   - Enable **Sparse checkout mode**
   - **Sparse checkout path**: `Lakeflow-DataEng-Workshop-V2`
3. Click **Create Git folder**. The `Lakeflow-DataEng-Workshop-V2/` subfolder clones into `de_workshop/` in your workspace.


Most of those labs folder have reference files only. Some folders come with notebooks that you can run directly as described further below.


## Lab 1 — Manually code an SDP pipeline


In this lab you'll hand-code a SDP end to end: one **Streaming Table** in Python over the famous bakehouse sample data set, and a **Materialized View** implemented SQL with three data quality constrains. One pipeline. Two files only. 

### Set up the pipeline in the Lakeflow Pipelines Editor

Before you write a single line, create the pipeline that will host Steps 1a and 1b:

1. Workspace sidebar → **New** → **ETL pipeline**. The **Lakeflow Pipelines Editor** opens with a default name `New Pipeline <date> <time>`.
2. Click the name → rename to `pipeline_USER_ID`. The editor automatically creates a workspace folder of the same name under your home (`/Workspace/Users/<your-email>/pipeline_USER_ID/`) — no manual `mkdir` needed. That folder is where your Lab 1 work lives; the cloned `labs/01-SDP/` folder is the answer key.
3. **Right of the pipeline name**, click the catalog/schema selector — a **Default location** modal opens. Set:
   - **Default catalog**: `workshop`
   - **Default schema**: type `USER_ID` and click **Save**. The dropdown sometimes only offers *"Create schema"* even though your `USER_ID` schema already exists — ignore that, the typed literal is accepted.

   Unqualified table names now resolve to `workshop.USER_ID.<table>`. The full **Pipeline settings** panel may open after Save — close it with the ✕ to return to the editor.
4. The default file `my_transformation.py` is already Python — Step 1a uses Python. The editor opens blank with a placeholder; just start typing.
5. Confirm **⚙ Settings** shows **Serverless** ON and Unity Catalog selected.

### Step 1a — Streaming table (Python)

Paste into `my_transformation.py` and rename the file to `sales_transactions`:

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

Asset browser (the "+" symbol) → **Add → Transformation** → name `sales_stats`, language **SQL** → **Create**. Paste the block below — no replacement step later; the three expectations are already wired in:

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

Click **Run pipeline**. The DAG now shows `sales_transactions → sales_stats` (6 rows, one per product). Under Tables in the Expectations column you can see the data quality constraints and open the side panel.

SDP has **one** constraint syntax — `CONSTRAINT <name> EXPECT (<predicate>)` — and **three** violation behaviors: *log* (default), *drop row*, and *fail update*. Wiring all three into one view shows every behavior in a single round trip.

**Key teaching points**
- Python for the streaming table 
- SQL for the materialized view. The relative name `sales_transactions` resolves against the pipeline's default catalog + schema.
- You can mix Python and SQL files — no special configuration needed.
- The bakehouse sample data is clean, so all three expectations pass and row counts match a constraint-free version.

**Is this MV incrementally maintained or fully recomputed?**

A Materialized View is either *incrementally maintained* (only the rows that changed are reprocessed) or *fully recomputed* on refresh, depending on whether the SDP planner can rewrite the query as an incremental update. Simple projections, filters, and many aggregations qualify for incremental maintenance; `COUNT(DISTINCT …)` — which `sales_stats` uses twice — typically forces a **COMPLETE refresh** because distinct tracking isn't incrementally maintainable without a lot more state.

Check Tables / Expectations for the details. 

**Try a violation yourself (optional)**
- To see a *drop* in action, weaken one predicate (e.g., `EXPECT (avg_txn_value > 10000) ON VIOLATION DROP ROW`) and re-run — rows disappear and the dropped count climbs.
- To see an *abort*, flip `known_product` to `EXPECT (product = 'Cronut')` — the update fails with the constraint name in the error.

### Lab 1 take-away

In a few lines, you've built a streaming ingest of bakehouse transactions, a materialized view that summarises sales by product, and three different data-quality behaviours all firing in the same run. 

The same shape, written without SDP, would be a streaming job, a batch job, and a scheduler — three separate systems to wire together and keep in sync. 

Here it lives in one pipeline, expressed as the *target table* you want, and the platform owns the rest.

---

## Lab 2 — Learn how to use Genie Code as a data engineer

Lab 1 you typed every line. Lab 2 you type *one* — the prompt. Genie Code drafts four SQL files: AutoCDC on the `booking_updates` CDC feed, Auto Loader on a JSON volume of fraud markers, a plain Streaming Table on payments, and a gold Materialized View that joins all three. You prompt, you review, you approve.

The skill this lab teaches isn't typing SQL. It's catching the draft that *looks* right and isn't.

### Set up a fresh pipeline for Lab 2

1. Workspace sidebar → **New** → **ETL pipeline**. Rename to `pipeline_USER_ID_lab2`. The editor auto-creates a workspace folder of the same name under your home — Genie Code will write the four SQL files it generates there.
2. Set **Default catalog** to `workshop` and **Default schema** to `USER_ID` (same as Lab 1).

The cloned `labs/02-GenieCode/` folder is your answer key — keep it open in another tab to verify what Genie produces.

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

- `SCD TYPE 1` for the AutoCDC target (TYPE 2 is also acceptable but reviewed for your use case).
- The MV groups by `payment_method` and includes `fraud_count` / `fraud_amount` / `fraud_pct`.


AutoCDC is a time-lapse, not a scrapbook. Every update collapses into one current row per `booking_id` — the latest state wins, history fades.


### Optional

The gold MV (`booking_fraud_summary`) groups by `payment_method`. Ask Genie to extend it with `bookings_current` (the AutoCDC target) so the analysis also includes `guests_count` — for example: is the fraud rate correlated with party size? `guests_count` lives in `bookings_current` (it carries over from `samples.wanderbricks.booking_updates`).

### Ask Genie Code in Chat mode

Switch Genie Code to **Chat** mode and ask:

```text
Explain the data flow in this pipeline end-to-end. Which node is incrementally maintained versus fully recomputed on refresh, and why?
```

> Reference copies of the four SQL files live in [`labs/02-GenieCode/`](./labs/02-GenieCode/) alongside this guide — use them as the answer key when verifying Genie Code's output.

---

## Lab 3 — Work with Zerobus Ingest to push IoT data

Lab 3 flips the script: until now you processed data that came to you (sample tables, a JSON volume, a CDC stream). Now **you** are the IoT producer, emitting one IoT event data that is stored in a Delta table in the Lakebouse.

**What's already provisioned for you:**

- **Zerobus table** — a Delta table `workshop.zerobus.measurements` (`id STRING, city STRING, temperature FLOAT, comment STRING`). Every event lands here.
- **Producer identity** — a service principal `workshop-zerobus-sp` with `USE CATALOG` on `workshop`, `USE SCHEMA` on `workshop.zerobus`, and `MODIFY + SELECT` on that one table. The SDK authenticates as this SP from your notebook (the full UC chain is required for the OAuth `authorization_details` payload).
- **Config table** — `workshop.zerobus.config`, a single row holding `client_id`, `client_secret`, `workspace_url`, `workspace_id`, and `zerobus_endpoint`. The notebook reads all five values from this one place.

**Overview of what you do:** open the notebook, set three parameters (city, temperature, comment), use the official **Databricks Zerobus Ingest SDK** which opens a gRPC stream, ingests one event with a fresh UUID, flushes for durability, closes. 

Then you verify the event landed — first inside the notebook, then from a SQL warehouse as a downstream consumer.

**Shared Zerobus table, thousands of simultaneous producers.** This same `workshop.zerobus.measurements` table is the target for *every* attendee in the workshop. When the instructor signals go, all of you will be firing `ingest_record` all writing to the same Delta table. Zerobus is built to absorb exactly this shape of load: many concurrent streams converging on one table. 

By the end of the lab you'll see every attendee's events sitting alongside your own — a live demo of what a real fleet of IoT producers looks like on the wire.

### Target

| catalog | schema | table | columns |
|---|---|---|---|
| `workshop` | `zerobus` | `measurements` | `id STRING, city STRING, temperature FLOAT, comment STRING` |


### Step 3a — Open the notebook from the cloned repo

In the Workspace sidebar, navigate to your cloned `de_workshop/Lakeflow-DataEng-Workshop-V2/labs/03-Zerobus/send_temperature.py` and click to open it. The notebook runs directly from the Git folder. 

The notebook ships with `databricks-zerobus-ingest-sdk` already declared in its **Environment** (top-right Environment icon). On first attach, the serverless runtime builds that dependency into the notebook's cached venv — no manual click-through, no `%pip install`, no per-session install delay. 

### Step 3b — Fill in the widgets at the top

- **City** — your city (e.g. `Munich`)
- **Temperature (°C)** — any float (e.g. `21.5`)
- **Comment (optional)** — a free-form note (e.g. `Hello Zerobus`); leave the default or blank if you don't care.

### Step 3c — Run the **Submit** cell

That cell calls `submit_temperature(CITY, TEMPERATURE, COMMENT)`, which the notebook's plumbing cell defines. The plumbing cell is marked **⛔ DO NOT MODIFY** 

```python
sdk = ZerobusSdk(_SERVER_ENDPOINT, unity_catalog_url=_WORKSPACE_URL)
stream = sdk.create_stream(_CLIENT_ID, _CLIENT_SECRET, table_props, options)
stream.ingest_record(json.dumps(record))
stream.flush()
stream.close()
```

The SDK handles the OAuth token exchange and scoping internally — the attendee never sees an `authorization_details` payload or a bearer token. On success you'll see:

```
✅ Sent to workshop.zerobus.measurements: {'id': '…', 'city': 'Munich', 'temperature': 21.5, 'comment': 'Hello Zerobus'}
```

### Step 3d — Verify in the notebook

The last cell runs `spark.table("workshop.zerobus.measurements").where(col("city") == "Munich")`. Your row appears within a few seconds. Zerobus is **at-least-once** at the protocol level — durability ACKs come back per record, and a client that retries on transport errors may produce duplicates. Order isn't guaranteed across producers.

### Step 3e — Verify in Databricks SQL

The notebook read the table as a producer; now read it as a consumer. This proves the row is a real row in a real governed table, queryable by anything that can talk to a SQL warehouse — a BI dashboard, a downstream pipeline, a JDBC client, `ai_query(...)`.

1. Workspace sidebar → **SQL Editor** → **New query**.
2. In the top-right warehouse picker, select the **course warehouse** — `<course_warehouse_name>` (ID `<course_warehouse_id>`). It was provisioned for you by the courseware, so it's already running; you don't need to start a warehouse of your own.
3. Paste and run:

```sql
SELECT id, city, temperature, comment
FROM workshop.zerobus.measurements
ORDER BY city, temperature;
```

You should see every attendee's row, including your own. In a real production deployment this is the query a dashboard would run, refreshed on a schedule — same table, same grants, no separate serving tier.


### What to take away

- **Direct-to-Delta ingest** — one `ingest_record` call, one row, no intermediate bus. The SDK holds a gRPC stream with durability ACKs, so it scales from a single-record demo like this to high-throughput production producers.
- **Fine-grained OAuth — like a hotel keycard, not a master key.** The SDK mints tokens scoped via `authorization_details` to one table: even if the SP's client_secret leaked, the only thing it could do is append rows to `measurements`. No `SELECT *`, no `DELETE`, no `DROP`.
- **Producer identity in audit** — `system.access.audit` attributes the write to the service principal(s), not to the attendee. That's the right answer for "which pipeline produced this row?" queries.
- **SDK over REST** — the `databricks-zerobus-ingest-sdk` uses gRPC with a persistent stream and durability ACKs (higher throughput, simpler retries) and handles all the OAuth + `authorization_details` plumbing internally. The Zerobus REST API exists is available too.

> Reference notebook: [`labs/03-Zerobus/send_temperature.py`](./labs/03-Zerobus/send_temperature.py).

---

## Lab 4 — Real-Time Mode for SDP (optional)

> **Optional.** Skip if you're short on time — nothing else in the workshop depends on it. The whole demo is a single file deployed via a Declarative Automation Bundle, ~5 minutes hands-on.

Standard SDP runs as micro-batches — fine for seconds-level latency, not for milliseconds. **Real-Time Mode (RTM)** is a specialization of SDP's continuous mode that pushes end-to-end latency as low as ~5 ms by combining three optimisations:

- **Long-running batches** — a single batch (default 5 min) processes records as they arrive, instead of restarting per micro-batch.
- **Simultaneous stage scheduling** — all query stages run concurrently, so the cluster must have task slots ≥ sum of tasks across stages.
- **Streaming shuffle** — downstream stages consume from upstream as data is produced, not after the upstream completes.

> **Public Preview:** RTM for Lakeflow SDP requires the SDP **PREVIEW** channel.

### What you'll deploy

A minimal three-piece pipeline, all in one file:

1. **Source** — a synthetic `rate` stream (RTM officially supports Kafka, MSK, Event Hubs, Kinesis EFO; `rate` is used here for portability).
2. **Update Flow** — RTM **requires** `@dp.update_flow` (not `@dp.table` / `@dp.view`) with `pipelines.trigger: "RealTime"` and a `pipelines.trigger.interval` set at the flow level (via `spark_conf=`).
3. **Sink** — declared up-front with `dp.create_sink(...)`. Production RTM uses Kafka-family sinks; this demo writes to `console` so aggregates land in the **driver log**.

The pipeline reads the rate stream, derives a synthetic `temperature_c`, runs a sliding-window aggregation (10-second window, 2-second slide), and emits an `engine_latency_ms` column on every row — the time between the newest event in the window and the row landing in the sink. RTM ≈ a few–tens of ms, MicroBatch ≈ hundreds+. Smaller = better.

### Step 4a — Open the RTM bundle

You already cloned the workshop repo at the start. Navigate to the `labs/04-SDP-RTM/` subfolder — it has `databricks.yml` and `transformations/temperature_rtm.py` ready to deploy.

### Step 4b — Adjust the bundle for your schema

Open `labs/04-SDP-RTM/databricks.yml`. Two variables drive the deploy — set them to your values:

```yaml
variables:
  catalog_name:
    default: workshop          # leave as-is for the workshop
  schema_name:
    default: USER_ID           # ← replace with your own USER_ID
```

`continuous: true`, `serverless: true`, `channel: PREVIEW`, and the RTM enable flag are already set — leave them as-is.

The flow file `transformations/temperature_rtm.py` is the actual RTM pipeline — note the `@dp.update_flow` decorator with the two trigger keys, the synthetic `rate` source, the windowed aggregation, and the `engine_latency_ms` computation:

```python
from pyspark import pipelines as dp
from pyspark.sql.functions import (
    avg, col, count, current_timestamp, expr,
    max as max_, min as min_, unix_millis, window,
)

dp.create_sink(
    "hot_temperatures_sink",
    "console",
    {"mode": "append", "truncate": "false"},
)


@dp.update_flow(
    name="temperature_rtm_flow",
    target="hot_temperatures_sink",
    spark_conf={
        "pipelines.trigger": "RealTime",
        "pipelines.trigger.interval": "1 minute",
    },
)
def temperature_rtm_flow():
    return (
        spark.readStream
        .format("rate")
        .option("rowsPerSecond", "100")
        .load()
        .withColumnRenamed("timestamp", "source_timestamp")
        .withColumn("temperature_c", expr("19 + rand() * 7"))
        .withWatermark("source_timestamp", "10 seconds")
        .groupBy(window(col("source_timestamp"), "10 seconds", "2 seconds"))
        .agg(
            count("*").alias("event_count"),
            avg("temperature_c").alias("avg_temp_c"),
            max_("source_timestamp").alias("last_event_ts"),
        )
        .withColumn("sink_timestamp", current_timestamp())
        .withColumn(
            "engine_latency_ms",
            unix_millis(col("sink_timestamp")) - unix_millis(col("last_event_ts")),
        )
    )
```

### Step 4c — Deploy and run from the Workspace UI

1. Open the `labs/04-SDP-RTM/` folder in your Workspace. Because `databricks.yml` is present, the **Deployments** icon (🚀) appears in the left pane.
2. Click **Deployments** → pick a target → **Deploy**.
3. After validate + deploy finishes, open the deployed `sdp-rtm-rate-source` pipeline and click **Run**. Because it's continuous, it keeps running — no need to re-trigger.

### Step 4d — Look up the engine latency in the driver logs

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

4. Read off the `engine_latency_ms` column — that's the end-to-end latency from the newest event in the window to the row landing in the sink. With RTM, expect a few tens of milliseconds. To compare with micro-batch mode, drop the `pipelines.trigger`/`pipelines.trigger.interval` keys from the flow's `spark_conf=` in `transformations/temperature_rtm.py` (and optionally also flip the pipeline-level `spark.databricks.streaming.realTimeMode.enabled` to `"false"` in `databricks.yml`), then redeploy. The latency typically jumps to several hundred milliseconds.

> Reference files: [`labs/04-SDP-RTM/databricks.yml`](./labs/04-SDP-RTM/databricks.yml) and [`labs/04-SDP-RTM/transformations/temperature_rtm.py`](./labs/04-SDP-RTM/transformations/temperature_rtm.py). Originally based on [`Lakeflow-SDP-RTM-Basics`](https://github.com/databricks/tmm/tree/main/Lakeflow-SDP-RTM-Basics) in the public `databricks/tmm` repo.

---

## Lab 5 — Iceberg side-quest (optional)

> **Optional / take-home.** Skip if you're short on time — nothing else in the workshop depends on it. Run after Lab 1 or any time after; only the Bakehouse `sales_transactions` streaming table from Lab 1 is a prerequisite.

Publish a derived bakehouse result as a **managed Iceberg table** — then read it back with **PyIceberg** through the Unity Catalog Iceberg REST endpoint. No Spark session, no cluster, no connector JAR. That's the portability pitch of Iceberg on Unity Catalog: the same table Databricks writes is readable by Trino, Snowflake, OSS Spark, or any pure-Python client.

### Step 5a — Top-5 sales locations as a managed Iceberg table (SQL, outside the pipeline)

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

### Step 5b — Read the Iceberg table with PyIceberg (Exploration notebook)

Now read the same table with a lightweight Iceberg client — no Spark required.

Asset browser → **Add → Exploration** → name `read_global_sales_gold` → language **Python** → **Create**. Paste each of the three snippets below into its own cell (use **+ Code** to add cells).

**Cell 1 — install** (a `%pip` magic must be alone in its cell):

```python
%pip install --upgrade "pyiceberg>=0.10,<0.11" "pyarrow>=17"
# On Azure workspaces, also: %pip install adlfs
```

**Cell 2 — restart Python** so the freshly installed wheels are visible:

```python
dbutils.library.restartPython()
```

**Cell 3 — read the Iceberg table:**

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

Expected output: a pandas DataFrame with the same 5 (city, country) pairs you saw in Step 5a, plus snapshot metadata for the Iceberg table.

**What you just demonstrated:**
- `pip install pyiceberg` — no cluster restart, no Iceberg JARs, no Spark session. A pure-Python client talks to Unity Catalog via the **Iceberg REST Catalog** endpoint at `/api/2.1/unity-catalog/iceberg-rest`.
- The `warehouse` parameter pins the UC catalog, so table identifiers collapse from three-part to two-part.
- External clients run this same code. Supply a PAT or OAuth token and the workspace URL — done. That's the portability of Iceberg on Unity Catalog.

**Requirements your admin has likely already set** (workshop attendees usually inherit these; flag with the instructor if any call fails with `403`):
- `EXTERNAL USE SCHEMA` on `workshop.USER_ID`
- External data access enabled on the workspace
- Workspace IP access list (if enabled) allows your client

> Reference copies of the CTAS and the PyIceberg reader live in [`labs/05-Iceberg/`](./labs/05-Iceberg/) alongside this guide.

---

## Lab 6 — CI/CD via Declarative Automation Bundles (optional)

> **Optional / take-home.** Skip if you're short on time. The whole demo is a sparse-clone of an external repo plus four CLI commands. ~10 minutes hands-on.

A data product lives in more than one place — a pipeline, a job, a dashboard, a connector flow. A **Declarative Automation Bundle** (DAB — formerly *Databricks Asset Bundle*; the CLI is still `databricks bundle`) collapses all of that into one folder: `databricks.yml` plus `resources/`, versioned like code. No shell recipes, no drift between envs, no screenshot-driven promotion.

You'll sparse-clone `databricks/tmm/Lakeflow-Gourmet-Pipeline`, retarget two variables for your workspace, and ship the whole data product — SQL medallion pipeline, `gourmet-workflow` job with `ai_query` enrichment, AI/BI dashboard — using the **CLI**. This is the same path a CI runner takes on every commit.

Source repo: <https://github.com/databricks/tmm/tree/main/Lakeflow-Gourmet-Pipeline>
Docs: <https://docs.databricks.com/aws/en/dev-tools/bundles/>

### Prerequisites

- Databricks CLI installed and authenticated to your workspace.
  Install: <https://docs.databricks.com/aws/en/dev-tools/cli/install>
  Auth: `databricks auth login --host <your-workspace-url>` (OAuth user-to-machine).
- `git` available locally.
- A running SQL warehouse in your workspace; copy its ID from sidebar **SQL Warehouses** → click warehouse → URL.

### Step 6a — Sparse-clone the bundle

Clone only the bundle subfolder, not the whole `databricks/tmm` repo:

```bash
git clone --filter=blob:none --no-checkout https://github.com/databricks/tmm.git
cd tmm
git sparse-checkout init --cone
git sparse-checkout set Lakeflow-Gourmet-Pipeline
git checkout main
cd Lakeflow-Gourmet-Pipeline
```

### Step 6b — Retarget two variables

Open `databricks.yml` and edit the `variables` block:

```yaml
variables:
  catalog_name:
    default: workshop          # ← was daiwt_gourmet
  prod_warehouse_id:
    default: <your-warehouse-id>   # ← paste from SQL Warehouses
  schema_name:
    default: ${workspace.current_user.short_name}
                               # leave as-is unless your USER_ID schema differs
```

If your `USER_ID` schema doesn't match `${workspace.current_user.short_name}`, override `schema_name` to the literal `USER_ID` value. Also check `targets.presenter` — if it overrides `schema_name`, point it at the same value.

> **Dashboard SQL is not parameterized yet.** If you change `catalog_name` away from `workshop`, you must also manually replace `daiwt_gourmet` in `resources/dashboard_gourmet_aibi.yml` and `src/aibi_dashboard.json`. Otherwise the dashboard renders empty.

### Step 6c — Validate the bundle

```bash
databricks bundle validate
```

Validate parses `databricks.yml`, resolves variables and `${...}` substitutions, and checks the resource shapes against the workspace API. It does **not** deploy anything. A clean validate is your green light to deploy.

Docs: <https://docs.databricks.com/aws/en/dev-tools/bundles/work-tasks#validate>

### Step 6d — Deploy to the `presenter` target

```bash
databricks bundle deploy -t presenter
```

The bundle ships with a single target named `presenter`. Deploy uploads the bundle assets (notebooks, SQL files, resource definitions), creates/updates the SDP pipelines, the `gourmet-workflow` job, and the AI/BI dashboard — all in one call.

Docs: <https://docs.databricks.com/aws/en/dev-tools/bundles/deploy>

### Step 6e — Run the workflow

```bash
databricks bundle run gourmet-workflow -t presenter
```

This triggers the deployed `gourmet-workflow` job: ingest franchise/supplier/transaction data, run the SDP medallion transformations, execute the AI enrichment steps (`ai_query`, sentiment, translation), and refresh the dashboard. Stream the run to your terminal until completion.

Docs: <https://docs.databricks.com/aws/en/dev-tools/bundles/run>

### Step 6f — Tear down (recommended after the workshop)

```bash
databricks bundle destroy -t presenter
```

Removes everything the deploy created: pipelines, job, dashboard. Source data and the cloned repo are untouched. Use this to clean up after the workshop instead of deleting resources by hand in the UI.

Docs: <https://docs.databricks.com/aws/en/dev-tools/bundles/destroy>

### The basic command set

These five are the core commands you'll use day-to-day:

| Command | Purpose |
|---|---|
| `databricks bundle validate` | Parse + check resource shapes; no side effects. |
| `databricks bundle deploy -t <target>` | Upload bundle assets and create/update resources for a target. |
| `databricks bundle run <resource> -t <target>` | Trigger a deployed job/pipeline. |
| `databricks bundle summary -t <target>` | Show what's deployed under this target (URLs, IDs). |
| `databricks bundle destroy -t <target>` | Remove all resources the bundle created in that target. |

In a real CI/CD setup you'd add `dev` and `prod` targets to `databricks.yml`, give them environment-specific overrides for `catalog_name` / `prod_warehouse_id` / `mode`, and run `databricks bundle deploy -t dev` on PR open and `databricks bundle deploy -t prod` on merge to main — same bundle, different target.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `bundle validate` fails on warehouse ID | `prod_warehouse_id` doesn't exist in your workspace | paste a real warehouse ID from **SQL Warehouses** |
| `new_recipe_Claude_LLM` task fails with `RESOURCE_DOES_NOT_EXIST` for `databricks-claude-3-7-sonnet` | the hardcoded model isn't available on your workspace | edit `src/ai_query.sql`, replacing **both** occurrences of `databricks-claude-3-7-sonnet` with one that is available (e.g. `databricks-claude-sonnet-4-5` or `databricks-claude-haiku-4-5`); or run with `--params ai_enabled=FALSE` to skip AI tasks |
| `SCHEMA_NOT_FOUND` during run | `schema_name` resolved to something that doesn't exist in your catalog | override the `schema_name` default in `databricks.yml` to your literal `USER_ID` value |
| Dashboard renders empty after deploy | dashboard SQL still references `daiwt_gourmet` (not parameterizable yet) | replace `daiwt_gourmet` with `workshop` in `resources/dashboard_gourmet_aibi.yml` and `src/aibi_dashboard.json`, then redeploy |

### What to take away

- **Bundles are the CI/CD primitive for data products.** `databricks.yml` + `resources/*.yml` captures an entire data product (SDP pipelines, jobs, dashboards, Lakeflow Connect flows) as versioned code. One file tree, committable, reviewable, deployable.
- **Five basic commands cover the full lifecycle.** `validate`, `deploy`, `run`, `summary`, `destroy` — locally, in a script, or in a CI runner. Same commands, same bundle.
- **Targets separate environments.** Add `dev` and `prod` targets with per-environment overrides; route them via branch (`-t dev` on PR, `-t prod` on merge).
- **The CLI is the source of truth.** The Workspace UI's **Deployments** pane runs the same `bundle deploy` against the same `databricks.yml`. Pick the entry point that fits the moment; the result is identical.

---

## References and other demos

* [Get to know Genie Code: Lakeflow and Analytics](https://www.databricks.com/resources/demos/videos/get-know-genie-code)
* Complete [Lakeflow Demo: From messy sales data to AI insights](https://www.databricks.com/resources/demos/videos/lakeflow-action-gourmet-pipeline-demo-daiwt)
* Getting Started with [OSS Apache SDP, VSCode](https://github.com/databricks/tmm/tree/main/OSS-SDP-OpenSkyNetwork)
* [Lakeflow SDP — Real-Time Mode Basics](https://github.com/databricks/tmm/tree/main/Lakeflow-SDP-RTM-Basics) (source for Lab 4)
* RTM demo to watch: [Air Traffic Control with Apache Spark Structured Streaming — Real-Time Mode](https://www.databricks.com/resources/demos/videos/air-traffic-control-with-apache-spark-structured-streaming-real-time-mode)
* Other [Databricks workshops](https://www.databricks.com/events?event_type=workshop&region=all) for DBSQL, AI, Unity Catalog
