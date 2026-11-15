# Databricks notebook source
# MAGIC %md
# MAGIC # Post-process (task 2 of opensky_job)
# MAGIC
# MAGIC Runs after the pipeline task. A placeholder for downstream work such as a report or an
# MAGIC export: here it prints row counts of the gold tables and the regional summary.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "default")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# COMMAND ----------

for t in ["gold_americas", "gold_emea", "gold_apac"]:
    n = spark.table(f"{catalog}.{schema}.{t}").count()
    print(f"{t}: {n:,} rows")

display(spark.table(f"{catalog}.{schema}.gold_analytics_regional_summary"))
