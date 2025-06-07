CREATE OR REFRESH MATERIALIZED VIEW banking_summary AS
SELECT
  customer_id,
  COUNT(*) AS num_transactions,
  MAX(amount) AS max_amount,
  AVG(amount) AS avg_amount
FROM
  finance_summit.pipeline.banking_transactions
GROUP BY
  customer_id;

