from pyspark import pipelines as dp

# create a SDP Streaming Table in Python
@dp.table()
@dp.expect_or_drop("supplierID needs to be set", "supplierID IS NOT NULL")
def raw_suppliers():
    return spark.readStream.table("samples.bakehouse.sales_suppliers")