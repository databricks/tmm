# Databricks notebook source
# 1. use the Assistant (star symbol on the top right) and run the command /explain
# 2. run the code, then click on the "See performance" link that comes with serverless notebooks

display(spark.range(5).toDF("serverless"))

# COMMAND ----------

# 1. use /fix to fix the syntax error
# 2. run the code
# 3. use /doc to document the code
display(spark.createDataFrame([("Python",), ("Spark",), ("Databricks",)], ["serverless"]))

# COMMAND ----------

# DBTITLE 1,Implement Modul A from Requirement 2805
# this cell implements modul A from requirement 2805 in the version 2 spec
# TODO: implementation :-)

# click on the cell header, then on the Assistant symbol to autogenerate the header.

# COMMAND ----------

# DBTITLE 1,Create Lakeflow Streaming Table with Assistant
# MAGIC %sql
# MAGIC -- now let's create a declarative pipeline, run the following command in Assistant  
# MAGIC -- run the following command in Assistant
# MAGIC -- create streaming table reading from @raw_txs  in SQL

# COMMAND ----------

# DBTITLE 1,Generate Materialized View from Streaming Table
# MAGIC %sql
# MAGIC -- run the following command in Assistant
# MAGIC -- create materialized view reading from @my_streaming_table  in SQL
