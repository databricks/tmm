from pyspark import pipelines as dp


@dp.table(
    name="sales_transactions",
    comment="Raw bakery transactions streamed from samples.bakehouse.sales_transactions",
)
def sales_transactions():
    # spark.readStream.table(...) inside @dp.table ⇒ streaming table
    return spark.readStream.table("samples.bakehouse.sales_transactions")
