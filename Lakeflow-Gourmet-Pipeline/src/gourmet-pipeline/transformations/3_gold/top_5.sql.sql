CREATE MATERIALIZED VIEW top_5
AS SELECT 
  f.total_sales, f.district, f.city, f.country,
  s.ingredient

FROM live.flagship_locations f 
LEFT JOIN live.raw_suppliers s ON f.supplierId = s.supplierId
WHERE (s.ingredient IS NOT NULL)
ORDER BY total_sales DESC
LIMIT 5