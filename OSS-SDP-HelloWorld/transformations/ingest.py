from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, TimestampType
from pyspark import pipelines as dp

# Get or create SparkSession — required for OSS local runs
spark = SparkSession.builder.appName("SDP-Events-Ingest").getOrCreate()


_schema = StructType([
    StructField("event_type", StringType()),
    StructField("user_id", StringType()),
    StructField("ts", TimestampType()),
])


@dp.table
def raw_events():
    """Streaming table: incrementally ingests JSON events from ./data/events/.

    - Each run picks up only new files (incremental).
    - Checkpointed to the storage path defined in spark-pipeline.yaml.
    - Downstream datasets can read this as a regular table.
    """
    return (
        spark.readStream
            .format("json")
            .schema(_schema)
            .load("data/events/")
    )
