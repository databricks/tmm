# Lakeflow SDP — Real-Time Mode Basics

A minimal Lakeflow Spark Declarative Pipeline (SDP) running in **Real-Time Mode (RTM)** — the whole demo is a single file: [temperature_rtm.py](sdp-rtm-rate-source-stdimage/sdp-rtm-rate-source/transformations/temperature_rtm.py). It reads a synthetic `rate` stream, runs a sliding-window aggregation, and writes to a console sink so you can see RTM working without wiring up Kafka.

**This demo shows *how to enable RTM* for an SDP pipeline — the three config steps you need, deployed as a Declarative Automation Bundle.** It does not measure per-record latency; that requires a Kafka-family source/sink (see the closing note).

> **Public Preview:** RTM for Lakeflow SDP requires DBR 18.1.2 on the SDP **preview** channel.

## Why Real-Time Mode

Standard SDP runs as micro-batches. RTM is a specialization of **continuous mode** that adds three optimizations to push end-to-end latency into the millisecond range:

- **Long-running batches** — a single batch (default 5 min) processes records as they arrive, instead of restarting per micro-batch.
- **Simultaneous stage scheduling** — all query stages run concurrently, so the cluster must have task slots ≥ sum of tasks across stages.
- **Streaming shuffle** — downstream stages consume from upstream as data is produced, not after the upstream completes.

The checkpoint interval (`pipelines.trigger.interval`) controls how often state and source offsets are persisted — longer = less overhead, shorter = faster recovery and more frequent metrics reports.

## The three config steps to enable RTM

1. **Continuous mode** at the pipeline level — RTM runs *on top of* continuous, not as a replacement.
2. **`spark.databricks.streaming.realTimeMode.enabled = true`** in the pipeline's Spark config (set in [databricks.yml](sdp-rtm-rate-source-stdimage/databricks.yml)).
3. **An `@dp.update_flow`** (not `@dp.table` / `@dp.view`) with `pipelines.trigger: "RealTime"` set at the flow level via `spark_conf=`.

All three are wired into this bundle.

## The three building blocks of the flow

All defined in [temperature_rtm.py](sdp-rtm-rate-source-stdimage/sdp-rtm-rate-source/transformations/temperature_rtm.py):

### 1. Source

Any streaming `readStream`. RTM officially supports Kafka, MSK, Event Hubs (Kafka API), and Kinesis EFO. This demo uses `rate` for portability.

```python
spark.readStream.format("rate").option("rowsPerSecond", "100").load()
```

### 2. Update flow

The bridge between source and sink. RTM **requires** `@dp.update_flow` (not `@dp.table` / `@dp.view`) with `pipelines.trigger: "RealTime"` set at the flow level — in addition to the pipeline-level config in [databricks.yml](sdp-rtm-rate-source-stdimage/databricks.yml).

```python
@dp.update_flow(
    name="temperature_rtm_flow",
    target="hot_temperatures_sink",
    spark_conf={
        "pipelines.trigger": "RealTime",
        "pipelines.trigger.interval": "5 minutes",  # checkpoint interval; default
    },
)
def temperature_rtm_flow(): ...
```

> The older flow-level keys `pipelines.execution.realTimeMode` and `pipelines.realtime.trigger.duration` are deprecated. Use `pipelines.trigger: "RealTime"` and `pipelines.trigger.interval`.

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
4. Because the pipeline is `continuous: true`, the deploy auto-starts the first update — there's nothing to click. Open the deployed `sdp-rtm-rate-source` pipeline in the Lakeflow Pipelines Editor and watch windowed aggregates land in the driver console.

## Verify RTM is running

Open **Compute → Driver logs** in the Lakeflow Pipelines Editor. The console sink prints the windowed aggregates (`window_start`, `window_end`, `event_count`, `avg_temp_c`, `min_temp_c`, `max_temp_c`) as formatted tables — visual confirmation that data is flowing through the RTM flow.

## A note on latency measurement

RTM exposes per-record latency through `StreamingQueryProgress.rtmMetrics` (`processingLatencyMs`, `sourceQueuingLatencyMs`, `e2eLatencyMs`, each with `p50` and `p99`), but **only for the [officially-supported source/sink combos](https://docs.databricks.com/aws/en/dlt/realtime-mode#supported-sources-and-sinks): Kafka, MSK, Event Hubs (Kafka-compatible), and Kinesis EFO**. With the `rate` source and `console` sink used here, `rtmMetrics` is not populated — RTM optimizations run, but per-record instrumentation is gated. For real RTM SLA numbers, swap `rate` for Kafka/Kinesis and `console` for a Kafka-family sink to get the actual `rtmMetrics` values.
