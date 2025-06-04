CREATE OR REFRESH STREAMING TABLE customer_net_worth AS
SELECT
  customer_id,
  SUM(portfolio_value) AS total_net_worth
FROM
  STREAM(investment_portfolio)
GROUP BY
  customer_id;