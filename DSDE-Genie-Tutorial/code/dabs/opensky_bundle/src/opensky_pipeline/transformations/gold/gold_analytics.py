from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.materialized_view(
    name="gold_analytics_regional_summary",
    comment="Analytics summary providing flight statistics across all regions (Americas, EMEA, APAC)",
    cluster_by=["region"]
)
def gold_analytics_regional_summary():
    """
    Analytics layer: Regional flight statistics aggregated from gold tables.
    
    Provides summary metrics for each region:
    - Total aircraft count (unique icao24)
    - Total flight records
    - Average velocity, altitude, and vertical rate
    - Max velocity and altitude observed
    - Count of on-ground vs in-flight aircraft
    - Callsign statistics
    """
    # Americas region
    americas = (
        spark.read.table("gold_americas")
        .withColumn("region", F.lit("Americas"))
    )
    
    # EMEA region
    emea = (
        spark.read.table("gold_emea")
        .withColumn("region", F.lit("EMEA"))
    )
    
    # APAC region
    apac = (
        spark.read.table("gold_apac")
        .withColumn("region", F.lit("APAC"))
    )
    
    # Union all regions
    all_regions = americas.union(emea).union(apac)
    
    # Calculate regional statistics
    return (
        all_regions
        .groupBy("region")
        .agg(
            F.countDistinct("icao24").alias("unique_aircraft"),
            F.count("*").alias("total_records"),
            F.countDistinct("callsign").alias("unique_callsigns"),
            F.avg("velocity").alias("avg_velocity_ms"),
            F.max("velocity").alias("max_velocity_ms"),
            F.avg("baro_altitude").alias("avg_baro_altitude_m"),
            F.max("baro_altitude").alias("max_baro_altitude_m"),
            F.min("baro_altitude").alias("min_baro_altitude_m"),
            F.avg("vertical_rate").alias("avg_vertical_rate_ms"),
            F.sum(F.when(F.col("on_ground") == True, 1).otherwise(0)).alias("on_ground_count"),
            F.sum(F.when(F.col("on_ground") == False, 1).otherwise(0)).alias("in_flight_count"),
            F.min("time_position").alias("earliest_timestamp"),
            F.max("time_position").alias("latest_timestamp")
        )
        .orderBy("region")
    )