CREATE MATERIALIZED VIEW flight_stats AS
    SELECT
        COUNT(*) AS num_events,
        COUNT(DISTINCT icao24) AS unique_aircraft,
        MAX(vertical_rate) AS max_asc_rate,
        MIN(vertical_rate) AS max_desc_rate,
        MAX(velocity) AS max_speed,
        MAX(geo_altitude) AS max_altitude,
        TIMESTAMPDIFF(SECOND, MIN(time_ingest), MAX(time_ingest)) AS observation_duration
FROM ingest_flights
