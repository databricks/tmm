CREATE OR REFRESH STREAMING TABLE events_search
  TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
  
AS SELECT
  event_id,
  circular_id,
  
  CONCAT('https://gcn.nasa.gov/circulars/', circular_id) AS url,
  CONCAT(event_id, ' ', subject, ' ', body, ' ', submitter) AS search_content
FROM STREAM(parsed_space_events)
