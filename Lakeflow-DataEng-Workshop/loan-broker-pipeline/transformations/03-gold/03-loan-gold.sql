CREATE MATERIALIZED VIEW new_loan_balances_by_country
  COMMENT "new loan balances per country"
AS 
SELECT 
  country_code,
  SUM(count) AS sum_count
FROM 
  cleaned_new_txs
GROUP BY 
  country_code
