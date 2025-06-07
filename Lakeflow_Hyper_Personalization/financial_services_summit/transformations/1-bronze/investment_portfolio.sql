CREATE STREAMING TABLE investment_portfolio 
(
CONSTRAINT valid_customer_id EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW
)
AS
SELECT
  *
FROM
  STREAM finance_summit.ingestion.investment_portfolios;


