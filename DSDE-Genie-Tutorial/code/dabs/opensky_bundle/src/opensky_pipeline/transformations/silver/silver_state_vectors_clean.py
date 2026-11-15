from pyspark import pipelines as dp

@dp.table(
    name="silver_state_vectors_clean",
    comment="Cleaned OpenSky state vectors with data quality constraints",
    cluster_by=["icao24"]
)
@dp.expect_all_or_drop({
    "valid_position": "latitude IS NOT NULL AND longitude IS NOT NULL",
    "valid_latitude_range": "latitude BETWEEN -90 AND 90",
    "valid_longitude_range": "longitude BETWEEN -180 AND 180",
    "valid_icao24": "icao24 IS NOT NULL AND length(icao24) = 6",
    "valid_altitude": "baro_altitude IS NULL OR (baro_altitude >= -500 AND baro_altitude <= 50000)",
    "valid_velocity": "velocity IS NULL OR velocity >= 0",
    "valid_timestamps": "time_position IS NOT NULL AND last_contact IS NOT NULL"
})
@dp.expect("reasonable_geo_altitude", "geo_altitude IS NULL OR (geo_altitude >= -500 AND geo_altitude <= 50000)")
@dp.expect("valid_track", "true_track IS NULL OR (true_track >= 0 AND true_track < 360)")
def silver_state_vectors_clean():
    """
    Silver layer: Apply data quality constraints to filter invalid records.
    
    Quality checks:
    - Drop records with null or invalid position (lat/lon)
    - Drop records with invalid coordinate ranges
    - Drop records with missing aircraft identifier (icao24)
    - Drop records with unreasonable altitude or negative velocity
    - Drop records with missing timestamps
    - Warn on geo_altitude and track outliers
    """
    return spark.readStream.table("bronze_state_vectors")