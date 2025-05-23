/*

For the purpose of this demo, we have a single SQL file for the silver layer to show you that a single file can contain multiple declarative pipeline data assets, such as streaming tables or materialized views.

In the silver layer where we aggregate the data from the bronze layer using JOIN operators.
Note the expectations in the SQL code. These expectations are used to enforce data quality.

With DLT using Direct Publishing Mode (DPM), it is no longer necessary to reference tables in the pipeline with the LIVE keyword.

*/

CREATE TEMPORARY STREAMING LIVE VIEW new_txs 
  COMMENT "Livestream of new transactions"
AS 
SELECT 
    txs.*
  , ref.accounting_treatment AS accounting_treatment 
FROM 
    stream(raw_txs) txs
  INNER JOIN 
    ref_accounting_treatment ref 
      ON txs.accounting_treatment_id = ref.id;

CREATE STREAMING TABLE cleaned_new_txs (
    CONSTRAINT `Payments should be this year`  EXPECT (next_payment_date > date('2020-12-31')),
    CONSTRAINT `Balance should be positive`    EXPECT (balance > 0 AND arrears_balance > 0) ON VIOLATION DROP ROW,
    CONSTRAINT `Cost center must be specified` EXPECT (cost_center_code IS NOT NULL) ON VIOLATION FAIL UPDATE
)
  COMMENT "Livestream of new transactions, cleaned and compliant"
AS 
SELECT 
    * 
FROM 
    STREAM(new_txs);

-- This is the inverse condition of the above statement to quarantine incorrect data for further analysis.
CREATE STREAMING TABLE quarantine_bad_txs (
    CONSTRAINT `Payments should be this year`  EXPECT (next_payment_date <= date('2020-12-31')),
    CONSTRAINT `Balance should be positive`    EXPECT (balance <= 0 OR arrears_balance <= 0) ON VIOLATION DROP ROW
)
  COMMENT "Incorrect transactions requiring human analysis"
AS 
SELECT 
    * 
FROM 
    STREAM(new_txs);

-- define the historical tx
CREATE MATERIALIZED VIEW historical_txs
  COMMENT "Historical loan transactions"
AS 
SELECT 
    l.*
  , ref.accounting_treatment AS accounting_treatment 
FROM 
    raw_historical_loans l
  INNER JOIN 
    ref_accounting_treatment ref 
      ON l.accounting_treatment_id = ref.id;