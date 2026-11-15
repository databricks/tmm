from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.materialized_view(
    name="gold_emea",
    comment="Clean OpenSky flight data for EMEA region (Europe, Middle East, Africa: longitude -30° to 75°)",
    cluster_by=["icao24", "callsign"]
)
def gold_emea():
    """
    Gold layer: EMEA (Europe, Middle East, Africa) region flights.
    Region defined by longitude between -30° and 75°.
    Covers Europe, Middle East, Africa, and western Russia.
    """
    return (
        spark.read.table("silver_state_vectors_clean")
        .filter(
            (F.col("longitude") > -30) & 
            (F.col("longitude") <= 75)
        )
    )