CREATE OR REFRESH STREAMING TABLE customer_net_worth
(
  customer_id STRING,
  total_net_worth DOUBLE,
  CONSTRAINT non_null_customer_id EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW
)
AS SELECT
  customer_id,
  ROUND(SUM(portfolio_value), 2) AS total_net_worth
FROM
  STREAM (investment_portfolio)
GROUP BY
  customer_id;