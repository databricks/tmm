# 7. OpenSharing — receive the data locally

## What we do

Everything so far ran inside Databricks. Now we go the other way: **receive** the shared OpenSky
data on your own machine with the **open-source Delta Sharing client** — no Databricks runtime,
and (because we read into pandas) **no Spark and no Java**. That's the point of open sharing: the
same data reads into any client, anywhere.

## Step-by-step guide

> **Step 1: Create the Python environment (VSCode)**
>
> Open the project folder in VSCode, then in the terminal create a virtual environment with `uv`
> (same tool as the OSS-SDP guide) and install just two packages — no Spark, no Java:
>
> ```bash
> uv venv --python 3.12 --seed
> source .venv/bin/activate
> uv pip install delta-sharing pandas
> ```
>
> Then point VSCode at the new environment: open the Command Palette and run **Python: Select
> Interpreter** → `.venv/bin/python`, so the editor, integrated terminal, and Run button all use it.
>
> **Step 2: Get your credential file**
>
> On the Databricks Marketplace listing, choose **Download credential file** and save the `.share`
> profile next to your script as `opensky.share`. It's a small JSON with an `endpoint` and a
> `bearerToken` which should be treated as a secret.

> **Step 3: Write the receive script**
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
> **Step 4: Run it**
>
> ```bash
> python receive_opensky.py
> ```
>
> `list_all_tables()` prints the tables in the share; `load_as_pandas(url, limit=...)` pulls rows
> into a pandas DataFrame you can analyze, plot, or export — all locally.
>
> **Step 5: Ask a real question — the five fastest jets out of Japan**
>
> We don't want the whole 695M-row day on the laptop. So we **push the filter to the sharing
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
> can't match — so Japan-only reads and transfers a fraction of the day instead of all 695M rows —
> and `drop_duplicates("icao24")` **after** the descending sort keeps each aircraft's single fastest
> reading, so you get five *different* planes, not five samples of one. _(The hint is best-effort
> file-skipping, which is why we still filter exactly in pandas.)_

## Results

> [!NOTE]
> **Screenshot to be added:** the receive script running in VSCode, printing the shared tables and the five fastest aircraft out of Japan (`docs/assets/07-opensharing.png`).

> [!TIP]
> **Feature spotlight — Open sharing, top 3**
>
> 1. **Cross-platform, no Databricks account** — recipients read shared data from any client (pandas, Spark, Power BI, Excel, Tableau) with just a credential file — no Databricks workspace or license required.
> 2. **Zero-copy, live data** — you read straight from the provider's cloud storage via short-lived scoped credentials, so nothing is replicated and you always see the latest committed version.
> 3. **Format-agnostic (Delta, Iceberg, Parquet)** — providers can share Delta, Iceberg, or Parquet without conversion, so open sharing isn't a single-format lock-in.

## Recap

You received Databricks-shared data on a plain laptop — no cluster, no Spark, no Java — and
answered a real question over it, letting the sharing server push the filter down so only a
fraction of the day's 695M rows crossed the network. For large scans, swap `load_as_pandas` for
`delta_sharing.load_as_spark(...)`,
which adds Java 17 + PySpark (the same stack as the
[OSS Spark Declarative Pipelines guide](https://github.com/databricks/tmm/tree/main/OSS-SDP-OpenSkyNetwork)).

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [6. Genie One](06-genie-one.md) | [Table of contents](../README.md) | [8. Wrap-up & next steps](08-wrap-up.md) |
