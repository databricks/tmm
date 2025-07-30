

CREATE MATERIALIZED VIEW flagship_locations
(CONSTRAINT  supplierId_set EXPECT (f.supplierId IS NOT NULL) ON VIOLATION DROP ROW,
CONSTRAINT correct_city EXPECT (f.city != "test") ON VIOLATION FAIL UPDATE
)
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

