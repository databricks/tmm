-- Create a Delta Live Tables pipeline

CREATE STREAMING TABLE raw_franchises
TBLPROPERTIES ("quality" = "bronze")
COMMENT "A materialized view for franchise data"
AS SELECT
  *
FROM STREAM(samples.bakehouse.sales_franchises)
