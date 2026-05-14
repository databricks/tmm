# transformations/temperature_rtm.py
from pyspark import pipelines as dp
from pyspark.sql.functions import (
    avg, col, count, current_timestamp, expr,
    max as max_, min as min_, unix_millis, window,
)

dp.create_sink(
    "hot_temperatures_sink",
    "console",
    {"mode": "append", "truncate": "false"},
)


@dp.update_flow(
    name="temperature_rtm_flow",
    target="hot_temperatures_sink",
    spark_conf={
        "pipelines.execution.realTimeMode": "true",
        "pipelines.realtime.trigger.duration": "60 second",
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
            max_("source_timestamp").alias("last_event_ts"),
        )
        .withColumn("sink_timestamp", current_timestamp())
        # engine_latency_ms = time from the newest event in this window
        # to the row landing in the sink. RTM ≈ a few–tens of ms,
        # MicroBatch ≈ hundreds+. Smaller = better.
        .withColumn(
            "engine_latency_ms",
            unix_millis(col("sink_timestamp")) - unix_millis(col("last_event_ts")),
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("event_count"),
            col("avg_temp_c"),
            col("min_temp_c"),
            col("max_temp_c"),
            col("engine_latency_ms"),
        )
    )
