-- Gold (stats): materialized view summarizing the KA file-table branch.
-- One row per metric: total events in st_for_ka (03), total in
-- classified_st_for_ka (04), and the per-event_class breakdown from 04.
CREATE OR REFRESH MATERIALIZED VIEW ka_stats
AS
  SELECT 'st_for_ka'            AS table_name, 'ALL' AS event_class, COUNT(*) AS num_events
  FROM st_for_ka
  UNION ALL
  SELECT 'classified_st_for_ka' AS table_name, 'ALL' AS event_class, COUNT(*) AS num_events
  FROM classified_st_for_ka
  UNION ALL
  SELECT 'classified_st_for_ka' AS table_name, event_class, COUNT(*) AS num_events
  FROM classified_st_for_ka
  GROUP BY event_class;
