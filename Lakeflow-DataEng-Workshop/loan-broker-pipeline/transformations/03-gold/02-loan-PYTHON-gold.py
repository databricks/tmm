
import dlt
from pyspark.sql.functions import sum

@dlt.table(
    comment="loan balances for consumption by different cost centers"
)
def new_loan_balances_by_cost_center():
    return (
        dlt.read("cleaned_new_txs")
        .groupBy("cost_center_code")
        .agg(sum("balance").alias("sum_balance"))
    )


"""
CREATE OR REFRESH STREAMING TABLE new_loan_balances_by_cost_center
  COMMENT "loan balances for consumption by different cost centers"
AS SELECT sum(balance) as sum_balance, cost_center_code FROM cleaned_new_txs
  GROUP BY cost_center_code
"""