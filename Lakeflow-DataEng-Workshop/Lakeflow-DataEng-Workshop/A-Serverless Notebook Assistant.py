# Databricks notebook source
# 1. use the Assistant (star symbol on the top right) and run the command /explain
# 2. run the code, then click on the "See performance" link that comes with serverless notebooks

display(spark.range(5).toDF("serverless"))

# COMMAND ----------

# 1. use /fix to fix the syntax error
# 2. run the code
# 3. use /doc to document the code
display(spark.createDataFrame([("Python",), ("Spark",), ("Databricks",)], ["serverless"])

# COMMAND ----------

# click on the cell header, then on the Assistant symbol to autogenerate the header.
