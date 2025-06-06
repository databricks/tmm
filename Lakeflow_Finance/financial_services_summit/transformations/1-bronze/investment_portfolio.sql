CREATE STREAMING TABLE investment_portfolio AS
SELECT
  *
FROM
  STREAM finance_summit.ingestion.investment_portfolios
