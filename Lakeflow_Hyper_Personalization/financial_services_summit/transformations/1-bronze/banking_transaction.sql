-- Streaming ingest of banking transactions

CREATE STREAMING TABLE banking_transactions AS
SELECT
  *
FROM
  STREAM finance_summit.ingestion.banking_transactions
