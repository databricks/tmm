-- Please edit the sample below
CREATE STREAMING TABLE campaign AS
SELECT
  *
FROM
  STREAM finance_summit.ingestion.campaign