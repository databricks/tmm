CREATE MATERIALIZED VIEW event_counts AS
  SELECT
    event_type,
    COUNT(*) AS count
  FROM raw_events
  GROUP BY event_type;
