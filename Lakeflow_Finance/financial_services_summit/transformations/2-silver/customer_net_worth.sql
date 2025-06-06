CREATE OR REFRESH STREAMING TABLE customer_net_worth
(
   CONSTRAINT valid_portfolio_value EXPECT (total_net_worth >= 0) ON VIOLATION DROP ROW
)
AS 
SELECT
  customer_id,
  SUM(portfolio_value) AS total_net_worth
FROM
  STREAM (investment_portfolio)
GROUP BY
  customer_id;