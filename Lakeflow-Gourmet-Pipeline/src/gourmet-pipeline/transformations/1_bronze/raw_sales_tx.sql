CREATE STREAMING TABLE raw_sales_tx

--  add a data quality expectations with AI and a sloppy sentence:
--  "add data quality reasonable totalPrice less than 1000 and positive"

--- ( CONSTRAINT reasonable_totalPrice EXPECT (totalPrice > 0 AND totalPrice < 1000))

TBLPROPERTIES ("quality" = "bronze")
COMMENT "streaming table for sales tx"
AS SELECT
  *
FROM STREAM (samples.bakehouse.sales_transactions)