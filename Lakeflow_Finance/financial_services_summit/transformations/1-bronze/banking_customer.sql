-- CREATE OR REFRESH STREAMING TABLE banking_customer;

-- APPLY CHANGES INTO 
--   banking_customer
-- FROM 
--   STREAM(banking_customer_cdf)
-- KEYS (customer_id)
-- APPLY AS DELETE WHEN
--   operation = "DELETE"
-- SEQUENCE BY 
--   seq
-- COLUMNS * EXCEPT (seq)
-- STORED AS SCD TYPE 1;

CREATE STREAMING TABLE banking_transactions AS
SELECT
  *
FROM
  STREAM finance_summit.ingestion.banking_transactions