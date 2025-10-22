-- SDP gold table: MV in SQL 

CREATE OR REFRESH MATERIALIZED VIEW top_5
AS
SELECT 
  f.total_sales,
  f.district,
  f.city,
  f.country,
  s.ingredient
FROM flagship_locations f
LEFT JOIN live.raw_suppliers s
  ON f.supplierId = s.supplierId
WHERE s.ingredient IS NOT NULL
ORDER BY f.total_sales DESC
LIMIT 5;