--  "add data quality reasonable totalPrice less than 1000 and positive"
CREATE STREAMING TABLE raw_sales_tx
( 
  CONSTRAINT reasonable_totalPrice EXPECT (totalPrice > 0 AND totalPrice < 1000)
)
COMMENT "streaming table for sales tx"
AS SELECT
  *
FROM STREAM (samples.bakehouse.sales_transactions)