# Lakeflow SDP — Real-Time Mode Basics

A minimal Lakeflow Spark Declarative Pipeline (SDP) running in **Real-Time Mode (RTM)** — the whole demo is a single file: [temperature_rtm.py](sdp-rtm-rate-source-stdimage/transformations/temperature_rtm.py). It reads a synthetic `rate` stream, runs a sliding-window aggregation, and writes to a console sink so you can watch RTM work without wiring up Kafka.

> **Public Preview:** RTM for Lakeflow SDP requires DBR 18.1.2 on the SDP **preview** channel.

## Why Real-Time Mode

Standard SDP runs as micro-batches — fine for seconds-level latency, not for milliseconds. RTM is a specialization of **continuous mode** that adds three optimizations to push end-to-end latency as low as ~5 ms:

- **Long-running batches** — a single batch (default 5 min) processes records as they arrive, instead of restarting per micro-batch.
- **Simultaneous stage scheduling** — all query stages run concurrently, so the cluster must have task slots ≥ sum of tasks across stages.
- **Streaming shuffle** — downstream stages consume from upstream as data is produced, not after the upstream completes.

The checkpoint interval (`pipelines.realtime.trigger.duration`) controls how often state/offsets are persisted — longer = less overhead, shorter = faster recovery.

## The three building blocks

All defined in [temperature_rtm.py](sdp-rtm-rate-source-stdimage/transformations/temperature_rtm.py):

### 1. Source
Any streaming `readStream`. RTM officially supports Kafka, MSK, Event Hubs (Kafka API), and Kinesis EFO. This demo uses `rate` for portability.

```python
spark.readStream.format("rate").option("rowsPerSecond", "100").load()
```

### 2. Update Flow
The bridge between source and sink. RTM **requires** `@dp.update_flow` (not `@dp.table` / `@dp.view`) with `pipelines.execution.realTimeMode = true` set at the flow level — in addition to the pipeline-level config in [databricks.yml](sdp-rtm-rate-source-stdimage/databricks.yml).

```python
@dp.update_flow(
    name="temperature_rtm_flow",
    target="hot_temperatures_sink",
    spark_conf={
        "pipelines.execution.realTimeMode": "true",
        "pipelines.realtime.trigger.duration": "300 second",
    },
)
def temperature_rtm_flow(): ...
```

### 3. Sink
Declared up-front with `dp.create_sink(name, format, options)` and referenced by `target=` in the flow. Production RTM uses Kafka-family sinks; this demo writes to `console` so aggregates land in the driver log.

```python
dp.create_sink("hot_temperatures_sink", "console", {"mode": "append", "truncate": "false"})
```

## Deploy from the Databricks Workspace

The DAB is deployable entirely from the UI — no local CLI required.

1. **Workspace → Create → Git folder**, paste `https://github.com/databricks/tmm`, enable **Sparse checkout** with path `Lakeflow-SDP-RTM-Basics`.
2. Open [databricks.yml](sdp-rtm-rate-source-stdimage/databricks.yml) and set `catalog` / `schema` to values you have access to. RTM, continuous mode, and the PREVIEW channel are already configured.
3. Open the `sdp-rtm-rate-source-stdimage` folder, click the **Deployments** icon (rocket ship), pick a target, and **Deploy**.
4. Click **Run** on the `sdp-rtm-rate-source` pipeline. Because it is continuous, it keeps running — watch windowed aggregates in the driver console.
