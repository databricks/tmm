-- Databricks notebook source
-- Create a Delta Live Tables pipeline

CREATE STREAMING TABLE raw_franchises
TBLPROPERTIES ("quality" = "bronze")
COMMENT "A materialized view for franchise data"
AS SELECT
  *
FROM STREAM(bakehouse.data_eng.franchises)


-- COMMAND ----------

CREATE STREAMING TABLE raw_sales_tx
TBLPROPERTIES ("quality" = "bronze")
COMMENT "streaming table for sales tx"
AS SELECT
  *
FROM STREAM (bakehouse.data_eng.transactions)

-- COMMAND ----------

CREATE STREAMING TABLE raw_suppliers
  COMMENT "New raw supplier data ingested from volume"
AS SELECT * FROM cloud_files('/Volumes/bakehouse/pipelines_dlt/suppliers_xml', 'xml', map("rowTag", "supplier"))


-- COMMAND ----------



CREATE MATERIALIZED VIEW flagship_locations
COMMENT "flagship locations"
AS SELECT
  SUM(s.totalPrice) AS total_sales,
  f.district, f.city, f.country, f.supplierId
FROM
  live.raw_sales_tx s
  JOIN live.raw_franchises f ON s.franchiseID = f.franchiseID
WHERE
  DATE(s.dateTime) = (SELECT MAX(DATE(dateTime)) FROM live.raw_sales_tx)
GROUP BY
  ALL
ORDER BY
  total_sales DESC



-- COMMAND ----------

CREATE MATERIALIZED VIEW top_5
AS SELECT 
  f.total_sales, f.district, f.city, f.country,
  s.ingredient

FROM live.flagship_locations f 
LEFT JOIN live.raw_suppliers s ON f.supplierId = s.supplierId
WHERE (s.ingredient IS NOT NULL)
ORDER BY total_sales DESC
LIMIT 5
