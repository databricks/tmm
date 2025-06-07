
CREATE STREAMING TABLE banking_customer_in AS
SELECT
  *
FROM
  STREAM finance_summit.ingestion.banking_customers
