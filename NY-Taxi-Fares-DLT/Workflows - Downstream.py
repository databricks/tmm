# Databricks notebook source
# DBTITLE 1,Hello from a serverless world
display(spark.range(5).toDF("serverless"))

# COMMAND ----------

display(spark.createDataFrame([("Python",), ("Spark",), ("Databricks",)], ["serverless"]))

# COMMAND ----------

# MAGIC %environment
# MAGIC "client": "1"
# MAGIC "base_environment": ""
