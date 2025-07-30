CREATE STREAMING TABLE raw_sales_tx
TBLPROPERTIES ("quality" = "bronze")
COMMENT "streaming table for sales tx"
AS SELECT
  *
FROM STREAM (samples.bakehouse.sales_transactions)