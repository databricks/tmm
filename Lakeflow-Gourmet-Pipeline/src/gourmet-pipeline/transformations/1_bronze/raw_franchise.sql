-- Create a SDP Streamin Table in SQL

CREATE STREAMING TABLE raw_franchises
TBLPROPERTIES ("quality" = "bronze")
COMMENT "A materialized view for franchise data"
AS SELECT
  *
FROM STREAM(samples.bakehouse.sales_franchises)
