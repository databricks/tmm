CREATE OR REFRESH STREAMING TABLE parsed_space_events
AS
  SELECT
    offset,
    timestamp,
    msg:['$schema']::string AS schema_url,
    msg:eventId::string AS event_id,
    msg:submitter::string AS submitter,
    msg:submittedHow::string AS submitted_how,
    msg:subject::string AS subject,
    msg:circularId::int AS circular_id,
    msg:format::string AS format,
    msg:body::string AS body,
    msg:createdOn::bigint AS created_on_epoch,
    to_timestamp(msg:createdOn::bigint / 1000) AS created_on
  FROM STREAM(raw_space_events);
