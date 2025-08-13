

CREATE MATERIALIZED VIEW flagship_locations
(
CONSTRAINT  supplierId_set EXPECT (f.supplierId IS NOT NULL) ON VIOLATION FAIL UPDATE,
CONSTRAINT correct_city EXPECT (f.city != "Paris") 
)

COMMENT "flagship locations"
AS SELECT
  SUM(s.totalPrice) AS total_sales,
  f.district, f.city, f.country, f.supplierId
FROM
  raw_sales_tx s
  JOIN raw_franchises f ON s.franchiseID = f.franchiseID
WHERE
  DATE(s.dateTime) = (SELECT MAX(DATE(dateTime)) FROM raw_sales_tx)
GROUP BY
  ALL
ORDER BY
  total_sales DESC

