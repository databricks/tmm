# Instructions

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Java | **17** | `brew install openjdk@17` |
| Python | 3.11+ | system or `brew install python@3.12` |
| uv | any | `brew install uv` |

Java 17 is required — Java 21+ is incompatible with PySpark 4.x. See `CLAUDE.md`.

## Setup (once)

```bash
uv venv --python 3.11 --seed
uv pip install -r requirements.txt
```

## Run

```bash
./run_pipeline.sh
```

Both flows complete in under 15 seconds. Expected output:

```
Flow spark_catalog.default.raw_events is RUNNING.
Flow spark_catalog.default.raw_events has COMPLETED.
Flow spark_catalog.default.event_counts is RUNNING.
Flow spark_catalog.default.event_counts has COMPLETED.
Run is COMPLETED.
```

## Inspect results

```bash
./show_output.sh
```

No Spark or JVM needed — reads Parquet directly via pyarrow.

## Add more events

Drop any newline-delimited JSON file into `data/events/` and re-run. Only new files are processed (incremental streaming):

```bash
cat > data/events/batch2.json <<EOF
{"event_type": "click", "user_id": "u5", "ts": "2025-01-02T08:00:00"}
{"event_type": "signup", "user_id": "u6", "ts": "2025-01-02T08:01:00"}
EOF

./run_pipeline.sh && ./show_output.sh
```

## Add a new transformation

Create a `.py` or `.sql` file in `transformations/` — SDP picks it up automatically. Example:

```sql
-- transformations/active_users.sql
CREATE MATERIALIZED VIEW active_users AS
  SELECT user_id, COUNT(*) AS event_count
  FROM raw_events
  GROUP BY user_id;
```

## Reset

To wipe all runtime state and start completely fresh:

```bash
./reset.sh
```

This removes `spark-warehouse/`, `metastore_db/`, and the stream checkpoints under `/tmp/sdp_example/`.
