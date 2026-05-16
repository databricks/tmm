-- Lab 5, Step 5a — Top-5 sales locations as a managed Iceberg table.
-- Runs OUTSIDE the SDP pipeline (SQL editor or a %sql notebook cell).
-- Managed Iceberg via CTAS avoids needing an external location for
-- delta.universalFormat.compatibility.location, at the cost of being
-- a snapshot (re-run or INSERT OVERWRITE to refresh).

CREATE OR REPLACE TABLE workshop.USER_ID.global_sales_gold
USING ICEBERG
AS
SELECT
    f.city,
    f.country,
    COUNT(*)                    AS txn_count,
    SUM(t.quantity)             AS units_sold,
    ROUND(SUM(t.totalPrice), 2) AS gross_revenue
FROM workshop.USER_ID.sales_transactions t
JOIN samples.bakehouse.sales_franchises f
    USING (franchiseID)
GROUP BY f.city, f.country
ORDER BY gross_revenue DESC
LIMIT 5;
