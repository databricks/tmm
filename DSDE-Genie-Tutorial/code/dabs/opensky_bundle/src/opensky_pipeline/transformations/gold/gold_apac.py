from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.materialized_view(
    name="gold_apac",
    comment="Clean OpenSky flight data for APAC region (Asia-Pacific: longitude 75° to 180° and -180° to -170°)",
    cluster_by=["icao24", "callsign"]
)
def gold_apac():
    """
    Gold layer: APAC (Asia-Pacific) region flights.
    Region defined by longitude between 75° and 180°, plus -180° to -170°.
    Covers Asia, Australia, Pacific islands, and eastern Russia.
    Note: Handles International Date Line split (two longitude ranges).
    """
    return (
        spark.read.table("silver_state_vectors_clean")
        .filter(
            ((F.col("longitude") > 75) & (F.col("longitude") <= 180)) |
            ((F.col("longitude") >= -180) & (F.col("longitude") < -170))
        )
    )