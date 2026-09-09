# 6. How do I receive shared data locally with open sharing?

## What you'll do

Everything so far ran inside Databricks, but often it is required to share data from Databricks to other systems. 

Now you go the other way: **receive** the shared OpenSky
data on your own local machine with the **open-source Delta Sharing client** — no Databricks runtime,
and (because you simply use pandas) **no Spark and no Java**. That's the point of open sharing: the
same data reads into any client, anywhere.

## Step-by-step guide

> **Step 1: Install the tools (one time)**
>
> These commands are for macOS with [Homebrew](https://brew.sh); on another OS the equivalents
> differ slightly. You need only two tools, no Java and no Spark:
>
> ```bash
> brew install uv            # fast Python package manager + virtual-environment tool
> brew install python@3.12   # Python 3.12
> ```
>
> **Step 2: Create the Python environment in VSCode**
>
> Open the project folder in VSCode, then in the terminal create and activate an isolated
> environment with `uv` and install just two packages:
>
> ```bash
> uv venv --python 3.12 --seed
> source .venv/bin/activate
> uv pip install "delta-sharing>=1.4" "pandas>=2.2"
> ```
>
> Verify the install prints two version numbers:
>
> ```bash
> python -c "import delta_sharing, pandas; print(delta_sharing.__version__, pandas.__version__)"
> ```
>
> Then point VSCode at the new environment: open the Command Palette and run **Python: Select
> Interpreter** → `.venv/bin/python`, so the editor, integrated terminal, and Run button all use it.
>
> **Step 3: Get your credential file**
>
> On the Databricks Marketplace listing, choose **Download credential file** and save the `.share`
> profile next to your script as `opensky.share`. It's a small JSON with an `endpoint` and a
> `bearerToken` which should be treated as a secret.

> **Step 4: Write the receive script**
>
> Create `receive_opensky.py`:
>
> ```python
> import delta_sharing
>
> PROFILE = "opensky.share"
> TABLE = f"{PROFILE}#opensky_share.opensky.state_vectors"   # adjust <share> to your credential file
>
> client = delta_sharing.SharingClient(PROFILE)
> for t in client.list_all_tables():          # what the share exposes
>     print(f"{t.share}.{t.schema}.{t.name}")
>
> df = delta_sharing.load_as_pandas(TABLE, limit=1000)   # straight into pandas
> print(df.shape)
> print(df.head())
> ```
>
> **Step 5: Run it**
>
> ```bash
> python receive_opensky.py
> ```
>
> `list_all_tables()` prints the tables in the share; `load_as_pandas(url, limit=...)` pulls rows
> into a pandas DataFrame you can analyze, plot, or export — all locally.
>
> **Step 6: Ask a real question — the five fastest jets out of Japan**
>
> You don't want the whole 696M-row day on the laptop. So you **push the filter to the sharing
> server** with `jsonPredicateHints`: keep only flights out of Japan, so only the matching files
> ever cross the network. Then rank the five fastest **distinct** aircraft locally (OpenSky reports
> `velocity` in m/s and `baro_altitude` in meters, so we convert to knots and feet):
>
> ```python
> import json
>
> # Server-side predicate: only Japan → less data read & transferred
> predicate = json.dumps({"op": "equal", "children": [
>     {"op": "column", "name": "origin_country", "valueType": "string"},
>     {"op": "literal", "value": "Japan", "valueType": "string"}]})
>
> df = delta_sharing.load_as_pandas(TABLE, jsonPredicateHints=predicate)
>
> # Hints are best-effort file-skipping, so re-filter exactly in pandas
> jp = df[df["origin_country"] == "Japan"].copy()
> jp["speed_knots"] = jp["velocity"] * 1.94384       # m/s  → knots
> jp["altitude_ft"] = jp["baro_altitude"] * 3.28084  # meters → feet
>
> fastest = (
>     jp.sort_values("speed_knots", ascending=False)
>       .drop_duplicates("icao24")                   # one row per aircraft
>       .head(5)[["icao24", "callsign", "speed_knots", "altitude_ft"]]
> )
> print(fastest.round(0).to_string(index=False))
> ```
>
> Two things make this efficient and correct: `jsonPredicateHints` lets the server skip files that
> can't match — so Japan-only reads and transfers a fraction of the day instead of all 696M rows —
> and `drop_duplicates("icao24")` **after** the descending sort keeps each aircraft's single fastest
> reading, so you get five *different* planes, not five samples of one. _(The hint is best-effort
> file-skipping, which is why we still filter exactly in pandas.)_

## Results

> [!NOTE]
> **Screenshot to be added:** the receive script running in VSCode, printing the shared tables and the five fastest aircraft out of Japan (`docs/assets/06-opensharing.png`).

> [!TIP]
> **Feature spotlight — Open sharing, top 3**
>
> 1. **Cross-platform, no Databricks account** — recipients read shared data from any client (pandas, Spark, Power BI, Excel, Tableau) with just a credential file — no Databricks workspace or license required.
> 2. **Zero-copy, live data** — you read straight from the provider's cloud storage via short-lived scoped credentials, so nothing is replicated and you always see the latest committed version.
> 3. **Format-agnostic (Delta, Iceberg, Parquet)** — providers can share Delta, Iceberg, or Parquet without conversion, so open sharing isn't a single-format lock-in.

## Open Sharing — Beyond the Basics

A few things worth knowing once the basics work:

- **[Schema-level sharing](https://docs.databricks.com/aws/en/delta-sharing/)** — a provider can share a whole schema so current and future tables appear automatically. Use it when you want new tables to show up without the provider re-issuing the share.
- **[Incremental change reads](https://docs.databricks.com/aws/en/opensharing/read-data-open)** — `load_table_changes_as_pandas(...)` returns only the rows changed between table versions instead of a full snapshot (needs Change Data Feed on the shared table). Use it when repeatedly syncing a large shared table and you don't want to re-pull everything.
- **Batched reads for small machines** — page a large result set instead of loading the whole table into memory at once. Use it when consuming a big shared table on a laptop or memory-limited environment.

## Recap

You received Databricks-shared data on a plain laptop without creating a cluster, no Spark, no Java and you answered a real question over it. In the code, the filter is pushed down to the sharing server, therefore only a fraction of the day's 696M rows crossed the network. 

For large scans, change your architecture to Spark. Then swap `load_as_pandas` for
`delta_sharing.load_as_spark(...)`

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [5. Databricks App](05-app.md) | [Table of contents](../README.md) | [7. Wrap-up & next steps](07-wrap-up.md) |

---

_Author: Frank Munz · Updated 2026-09-04_
