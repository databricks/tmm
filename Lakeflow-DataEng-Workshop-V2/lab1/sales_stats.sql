CREATE OR REFRESH MATERIALIZED VIEW sales_stats (
    -- 1. LOG (default): average transaction value within a reasonable range.
    --    Violations are counted in the event log; rows are still written.
    CONSTRAINT reasonable_avg_value
        EXPECT (avg_txn_value BETWEEN 1 AND 1000),

    -- 2. DROP ROW: gross revenue must be non-negative.
    --    Violating rows are excluded from the target; pipeline continues.
    CONSTRAINT nonneg_revenue
        EXPECT (gross_revenue >= 0) ON VIOLATION DROP ROW,

    -- 3. FAIL UPDATE: product must be populated.
    --    Any violation aborts the whole pipeline update with the constraint name.
    CONSTRAINT known_product
        EXPECT (product IS NOT NULL) ON VIOLATION FAIL UPDATE
)
COMMENT 'Sales KPIs grouped by product, with data-quality expectations'
AS SELECT
    product,
    COUNT(*)                     AS txn_count,
    SUM(quantity)                AS units_sold,
    ROUND(SUM(totalPrice), 2)    AS gross_revenue,
    ROUND(AVG(totalPrice), 2)    AS avg_txn_value,
    COUNT(DISTINCT customerID)   AS unique_customers,
    COUNT(DISTINCT franchiseID)  AS franchises_selling
FROM sales_transactions
GROUP BY product;
