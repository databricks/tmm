# Real-Time Mode Latency Demo (no message bus required)

A Databricks Asset Bundle that compares **Real-Time Mode (RTM)** and **MicroBatch Mode** on the same Spark Structured Streaming pipeline, using `transformWithState` for stateful per-city aggregations over synthetic sensor data. 

## Why is no message bus needed?

The whole demo runs on a single Databricks cluster — no Kafka, Kinesis, or external data source required.

Data is generated internally by Spark's built-in `rate` source (200 rows/s across 64 cities) and written to an in-memory sink, so no Kafka/Kinesis broker or durable external storage is required. This is still a valid RTM demo because the latency gap between RTM and MicroBatch is mostly produced by the streaming engine itself, not by the source, and each rate-source record carries a timestamp — which is exactly what `e2eLatencyMs` measures against.

## What you'll see

The notebook runs the same stateful pipeline twice — once in MicroBatch Mode, once in Real-Time Mode — then prints a side-by-side **P50, P95, P99 end-to-end latency** comparison, averaged across all batches except the first two (which are skewed by warm-up). On a cluster configured as in `databricks.yml`, RTM typically lands roughly an order of magnitude below MicroBatch for this workload.

## Prerequisites

- A Databricks workspace (AWS) with Unity Catalog enabled
- Cluster runtime: **DBR 18.1** (pinned by `databricks.yml`; the bundle provisions the cluster for you)
- Databricks CLI authenticated to your workspace (`databricks auth login`)
- Write access to the target catalog — defaults to `main`, override via bundle variable if needed

The cluster config in this bundle sets `spark.databricks.streaming.realTimeMode.enabled=true`. 

## Quick Start

### Option 1 — Deploy from the workspace UI

This project is a **Databricks Asset Bundle (DAB)**. Clone or sync the repository to a Databricks Git folder and click the **Deploy** button (rocket icon) in the bundle view. The job, cluster, and Unity Catalog volume are created automatically — no CLI required.

### Option 2 — Deploy via CLI

```bash
databricks bundle deploy
databricks bundle run rtm-demo
```

You can also trigger the deployed job from the Databricks Jobs UI. Running the job (rather than attaching to an existing cluster) is what provisions a cluster with the correct RTM configuration.

## Configuration

- **Target catalog** — defaults to `main`. Override at deploy time:
  ```bash
  databricks bundle deploy --var="catalog_volume=<your_catalog>"
  ```
- **Checkpoint location** — defaults to `/Volumes/<catalog>/default/spark-rtm-demo`. Override at run time:
  ```bash
  databricks bundle run rtm-demo --param checkpointLocation=/path
  ```
- **Rows per second** — defaults to `200`. Override at run time:
  ```bash
  databricks bundle run rtm-demo --param rowsPerSecond=500
  ```

**Performance Note:** This demo is designed for small data volumes to showcase latency differences. Increasing `rowsPerSecond` beyond the default may negatively impact end-to-end latency numbers as the system becomes resource-constrained.

**Note:** The number of partitions was updated from 8 to 2; 8 was used in a previous version.

## Repo layout

| File | Purpose |
|------|---------|
| `RTM Demo.ipynb` | Main notebook: runs MBM then RTM, aggregates P99 |
| `databricks.yml` | Bundle definition: job, cluster, UC volume, parameters |
| `resources/SensorDataGenerator.ipynb` | Rate-source stream with the 64-city sensor schema |
| `resources/EnvironmentalMonitorListProcessor.ipynb` | `StatefulProcessor` using `ListState` for per-city running state |
| `resources/HelperFunctions.ipynb` | Latency extraction from `StreamingQueryProgress` and metrics helpers |
| `resources/CityLocations.ipynb` | 64 cities × 3 locations lookup data |

## References

- [DAIS 2025 talk on Real-Time Mode](https://youtu.be/zGJvbV80FdU?si=fSjHpF7mfnf1UZh9)
- [Databricks Real-Time Mode documentation](https://docs.databricks.com/aws/en/structured-streaming/real-time)
- [`transformWithState` documentation](https://docs.databricks.com/aws/en/stateful-applications/)
