CREATE STREAMING TABLE banking_customer
AS
SELECT
  *
FROM
  STREAM finance_summit.ingestion.banking_customers
