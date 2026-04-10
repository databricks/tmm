# CLAUDE.md

## Commands

```bash
uv venv --python 3.11 --seed
uv pip install --offline -r requirements.txt  # drop --offline if not cached

./run_pipeline.sh    # run the pipeline
./show_output.sh     # inspect results (no JVM needed)
./reset.sh           # wipe all runtime state for a clean restart
```

## What this project is

A minimal OSS Apache Spark Declarative Pipelines (SDP) example. It was built by adapting the reference project at [databricks/tmm/OSS-SDP-OpenSkyNetwork](https://github.com/databricks/tmm/tree/main/OSS-SDP-OpenSkyNetwork) to use local JSON files instead of the OpenSky live API, making it fully self-contained and runnable offline.

The pipeline has two steps:
- `transformations/ingest.py` — streaming table, reads JSON events
- `transformations/aggregate.sql` — materialized view, counts by event type

## Architectural decisions and how we got there

### Java 17 (not system Java)

Running `spark-pipelines run` on Java 25 fails immediately with `UnsupportedOperationException: getSubject is not supported`. The cause: Java 21+ removed `javax.security.auth.Subject.getSubject()`, which Hadoop's `UserGroupInformation` still calls at startup. Spark 4.x is tested against Java 17 (LTS). `run_pipeline.sh` sets `JAVA_HOME` via `/usr/libexec/java_home -v 17` and exits with a clear error if Java 17 is not installed.

> macOS only. Linux users need to set `JAVA_HOME` to a Java 17 installation manually.

### Explicit SparkSession in Python pipeline files

On Databricks, `spark` is a pre-injected global. In the OSS local runner it is not — omitting it causes `NameError: name 'spark' is not defined` at pipeline registration time. The fix, taken directly from the reference project, is:

```python
spark = SparkSession.builder.appName("...").getOrCreate()
```

The `appName` is ignored at runtime — `spark-pipelines run` starts a Spark Connect server first and `getOrCreate()` returns that existing session. The call is necessary for the name binding, not for configuration.

### No `catalog`/`database` in `spark-pipeline.yaml`

The initial pipeline spec included `catalog: spark_catalog` and `database: sdp_demo`. This caused `AnalysisException: SCHEMA_NOT_FOUND` before the pipeline even started — the Spark Connect server validates that both exist on startup, which fails on a fresh local install. Removing both fields makes the pipeline fall back to `spark_catalog.default`, which is always present. This is a workaround for a limitation of PySpark 4.1.0 local mode, not a design preference. A comment in the YAML explains this.

### Python for the streaming table, SQL for the materialized view

The reference project mixes `.py` and `.sql` files; SDP picks both up via the `transformations/**` glob. Python is used for `ingest.py` because it needs to define a `StructType` schema and pass options to the streaming reader — things that require code. SQL DDL (`CREATE MATERIALIZED VIEW … AS SELECT`) is used for `aggregate.sql` because the transformation is purely declarative. Sorting is intentionally left out of the view definition (materialized views are unordered sets) and done at read time in `show_output.py`.

### pyarrow for output inspection

The pipeline writes Parquet files to `spark-warehouse/` (the default Hive warehouse). Reading them with `pyarrow` avoids starting a second JVM and is near-instant. The path is hardcoded to `spark-warehouse/` — if `spark.sql.warehouse.dir` were ever changed, `show_output.py` would need updating. The `storage:` path in `spark-pipeline.yaml` is unrelated: it controls stream checkpoints, not table data.

### uv + compatible release pin

`uv` is used instead of `pip` for speed and for its local wheel cache (`uv pip install --offline`), which allows installation without network access once packages have been downloaded once. `requirements.txt` pins `pyspark[pipelines]~=4.1.0` (compatible release) rather than `>=4.1.0` to prevent silent breakage if 4.2.0 changes the Connect API.

### Reset story

Three separate locations hold runtime state and all must be cleared for a true reset: `spark-warehouse/` (table data), `metastore_db/` (Derby Hive metastore), and `/tmp/sdp_example/` (stream checkpoints). `reset.sh` removes all three. `spark-pipelines run --full-refresh-all` reprocesses source data but does not touch the metastore.
