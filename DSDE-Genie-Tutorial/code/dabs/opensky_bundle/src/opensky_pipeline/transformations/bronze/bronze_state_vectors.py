from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.table(
    name="bronze_state_vectors",
    comment="Raw OpenSky state vector data ingested from marketplace (filtered to 15 minutes: 2026-03-01 12:00-12:15)"
)
def bronze_state_vectors():
    """
    Bronze layer: Ingest raw OpenSky aircraft state vectors from marketplace.
    Streaming table for incremental processing.
    Filtered to 15 minutes of data (2026-03-01 12:00:00 to 12:15:00) to reduce data volume.
    """
    return (
        spark.readStream.table("marketplace.opensky.state_vectors")
        .filter(
            (F.col("time_position") >= F.lit("2026-03-01 12:00:00").cast("timestamp")) &
            (F.col("time_position") <= F.lit("2026-03-01 12:15:00").cast("timestamp"))
        )
    )