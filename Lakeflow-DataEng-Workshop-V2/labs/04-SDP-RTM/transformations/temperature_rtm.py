# transformations/temperature_rtm.py
from pyspark import pipelines as dp
from pyspark.sql.functions import avg, col, count, expr, max as max_, min as min_, window

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
        "pipelines.trigger.interval": "2 minutes",
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
            min_("temperature_c").alias("min_temp_c"),
            max_("temperature_c").alias("max_temp_c"),
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("event_count"),
            col("avg_temp_c"),
            col("min_temp_c"),
            col("max_temp_c"),
        )
    )


# ---------------------------------------------------------------------------
# Real RTM latency: register a StreamingQueryListener that prints rtmMetrics
# (p50/p99 for processingLatencyMs, sourceQueuingLatencyMs, e2eLatencyMs)
# on every progress event. Lines are tagged [rtm] so they're easy to grep
# in the driver log alongside the console sink's batch tables.
# ---------------------------------------------------------------------------
import json
from pyspark.sql.streaming import StreamingQueryListener


class RTMLatencyLogger(StreamingQueryListener):
    """Surface latency in the driver log for RTM and micro-batch alike.

    The Python StreamingQueryProgress wrapper doesn't always expose every
    Scala-side field as a direct attribute, so we parse the underlying
    progress JSON and look for `rtmMetrics` there.

    Note: `rtmMetrics` is currently only populated for officially-supported
    RTM source/sink combos (Kafka, MSK, Event Hubs). For unsupported
    sources/sinks like the `rate` source + `console` sink in this demo,
    RTM optimizations still run, but the per-record latency instrumentation
    isn't emitted — so we fall back to `durationMs` from the progress
    object. That fallback is labelled `mode=durationMs-fallback` to make
    it clear this is **not** "RTM is off", it's "rtmMetrics unavailable
    for this source/sink".
    """

    def onQueryStarted(self, event):
        pass

    def onQueryTerminated(self, event):
        pass

    def onQueryProgress(self, event):
        prog = event.progress
        # 1. try the direct Python attribute (newer wrappers expose it)
        rtm = getattr(prog, "rtmMetrics", None)
        # 2. fall back to parsing the progress JSON
        if rtm is None and hasattr(prog, "json"):
            try:
                rtm = json.loads(prog.json).get("rtmMetrics")
            except Exception:
                rtm = None
        if rtm:
            print(
                f"[rtm] batch={prog.batchId} mode=rtm "
                f"rtmMetrics={json.dumps(rtm)}"
            )
        else:
            d = prog.durationMs or {}
            print(
                f"[rtm] batch={prog.batchId} mode=durationMs-fallback "
                f"triggerExecutionMs={d.get('triggerExecution', 'n/a')} "
                f"addBatchMs={d.get('addBatch', 'n/a')} "
                f"getBatchMs={d.get('getBatch', 'n/a')}"
            )


spark.streams.addListener(RTMLatencyLogger())
