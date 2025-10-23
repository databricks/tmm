from pyspark import pipelines as dp
from pyspark.sql.functions import sum

#create a SDP streaming table for loan balances by cost center
@dp.table(
    comment="loan balances for consumption by different cost centers"
)
def new_loan_balances_by_cost_center():
    return (
        spark.read.table("cleaned_new_txs")
        .groupBy("cost_center_code")
        .agg(sum("balance").alias("sum_balance"))
    )