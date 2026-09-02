# 7. OpenSharing — receive the data locally

## What we do

Everything so far ran inside Databricks. Now we go the other way: **receive** the shared OpenSky
data on your own machine with the **open-source Delta Sharing client** — no Databricks runtime,
and (because we read into pandas) **no Spark and no Java**. That's the point of open sharing: the
same data reads into any client, anywhere.

> [!NOTE]
> The receive mechanics below are verified locally with `delta-sharing` 1.4.2 / pandas 2.3.3 /
> Python 3.12. Reading your Marketplace data specifically requires a **credential file** for that
> listing ([Step 2](#step-by-step-guide)); you can try the exact same code first against the public demo profile.

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
> **Step 2: Get your credential file**
>
> On the Databricks Marketplace listing, choose **Download credential file** and save the `.share`
> profile next to your script as `opensky.share`. It's a small JSON with an `endpoint` and a
> `bearerToken` — treat it as a secret.
>
> *(To try the mechanics without Databricks, use the public demo profile instead:
> `https://raw.githubusercontent.com/delta-io/delta-sharing/main/examples/open-datasets.share`.)*
>
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

## Results

> [!NOTE]
> **Screenshot to be added:** the receive script running in VSCode, printing the shared tables and the OpenSky DataFrame (`docs/assets/07-opensharing.png`).

> [!TIP]
> **Feature spotlight — Open sharing, top 3**
>
> 1. **Cross-platform, no Databricks account** — recipients read shared data from any client (pandas, Spark, Power BI, Excel, Tableau) with just a credential file — no Databricks workspace or license required.
> 2. **Zero-copy, live data** — you read straight from the provider's cloud storage via short-lived scoped credentials, so nothing is replicated and you always see the latest committed version.
> 3. **Format-agnostic (Delta, Iceberg, Parquet)** — providers can share Delta, Iceberg, or Parquet without conversion, so open sharing isn't a single-format lock-in.

## Recap

You received Databricks-shared data on a plain laptop with ~5 lines of Python — no cluster, no
Spark, no Java. For large tables, swap `load_as_pandas` for `delta_sharing.load_as_spark(...)`,
which adds Java 17 + PySpark (the same stack as the
[OSS Spark Declarative Pipelines guide](https://github.com/databricks/tmm/tree/main/OSS-SDP-OpenSkyNetwork)).
