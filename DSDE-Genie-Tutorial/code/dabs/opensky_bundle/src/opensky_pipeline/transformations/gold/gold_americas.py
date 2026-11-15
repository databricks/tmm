from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.materialized_view(
    name="gold_americas",
    comment="Clean OpenSky flight data for Americas region (longitude -170° to -30°)",
    cluster_by=["icao24", "callsign"]
)
def gold_americas():
    """
    Gold layer: Americas region flights.
    Region defined by longitude between -170° and -30°.
    Includes North America, Central America, South America, and Caribbean.
    """
    return (
        spark.read.table("silver_state_vectors_clean")
        .filter(
            (F.col("longitude") >= -170) & 
            (F.col("longitude") <= -30)
        )
    )