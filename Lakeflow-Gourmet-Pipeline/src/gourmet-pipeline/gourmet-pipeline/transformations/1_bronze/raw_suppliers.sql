CREATE STREAMING TABLE raw_suppliers
  COMMENT "New raw supplier data from a volume"

AS SELECT * FROM STREAM(samples.bakehouse.sales_suppliers)
