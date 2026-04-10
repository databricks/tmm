# SDP Example — Spark Declarative Pipelines (OSS)

A minimal, self-contained example of [Apache Spark Declarative Pipelines](https://spark.apache.org/docs/latest/declarative-pipelines-programming-guide.html) (SDP), introduced in Spark 4.1.0. No Databricks account required.

The pipeline ingests JSON events as a **streaming table** and aggregates them into a **materialized view** — two core SDP concepts in two files.

> **macOS only.** The run script uses `/usr/libexec/java_home` to pin Java 17. Linux users need to set `JAVA_HOME` manually.

Inspired by: [databricks/tmm — OSS-SDP-OpenSkyNetwork](https://github.com/databricks/tmm/tree/main/OSS-SDP-OpenSkyNetwork)

---

## Project Structure

```
OSS-SDP-HelloWorld/
├── spark-pipeline.yaml          # Pipeline spec — name, storage, file globs
├── transformations/
│   ├── ingest.py                # Streaming table: reads JSON events
│   └── aggregate.sql            # Materialized view: counts by event type
├── data/
│   └── events/
│       └── sample.json          # Sample input (6 events)
├── requirements.txt             # pyspark[pipelines]~=4.1.0
├── run_pipeline.sh              # Run the pipeline
├── show_output.sh               # Inspect results (no Spark needed)
├── show_output.py               # Python helper called by show_output.sh
└── reset.sh                     # Wipe all runtime state for a clean restart
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Java | **17** (required) | `brew install openjdk@17` |
| Python | 3.11+ | system or `brew install python@3.12` |
| uv | any | `brew install uv` |

> Java 17 is required — Java 21+ is incompatible with Hadoop security APIs used by PySpark 4.x.

---

## Quick Start

```bash
# 1. Install dependencies
uv venv --python 3.11 --seed
uv pip install -r requirements.txt

# 2. Run the pipeline
./run_pipeline.sh

# 3. Inspect the output
./show_output.sh
```

---

## Pipeline DAG

```
data/events/*.json
       │
       ▼
  raw_events          ← Streaming Table  (ingest.py)
       │
       ▼
  event_counts        ← Materialized View (aggregate.sql)
```

`raw_events` is incremental: re-running the pipeline only processes new files dropped into `data/events/`. `event_counts` is recomputed whenever `raw_events` changes.

---

## Example Output

```
=== raw_events ===
event_type  user_id  ts
click       u1       2025-01-01 09:00:00
view        u2       2025-01-01 09:01:00
click       u3       2025-01-01 09:02:00
purchase    u1       2025-01-01 09:03:00
view        u4       2025-01-01 09:04:00
click       u2       2025-01-01 09:05:00

=== event_counts ===
event_type  count
click       3
view        2
purchase    1
```

---

## Reset

To wipe all runtime state (table data, metastore, checkpoints) and start fresh:

```bash
./reset.sh
```

---

## Further Reading

- [`instructions.md`](instructions.md) — full setup, adding events, adding transformations
- [`CLAUDE.md`](CLAUDE.md) — architectural decisions and how we arrived at them
- [Spark Declarative Pipelines programming guide](https://spark.apache.org/docs/latest/declarative-pipelines-programming-guide.html)
