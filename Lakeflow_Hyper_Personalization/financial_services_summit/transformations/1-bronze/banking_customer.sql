CREATE STREAMING TABLE banking_customer AS
SELECT
  *
FROM
  STREAM banking_customer_cdf
