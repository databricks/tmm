# Databricks notebook source
# MAGIC %md
# MAGIC # Read `global_sales_gold` with PyIceberg
# MAGIC Exploration notebook for Lab 5, Step 5b. Runs against the UC Iceberg REST Catalog — no Spark required.

# COMMAND ----------

# MAGIC %pip install --upgrade "pyiceberg>=0.9,<0.10" "pyarrow>=17,<20"
# MAGIC # %pip install adlfs   # uncomment on Azure workspaces

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from pyiceberg.catalog import load_catalog

WORKSPACE = spark.conf.get("spark.databricks.workspaceUrl")
CATALOG   = "workshop"
SCHEMA    = "USER_ID"
TOKEN     = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

iceberg_catalog = load_catalog(
    "uc",
    uri=f"https://{WORKSPACE}/api/2.1/unity-catalog/iceberg-rest",
    warehouse=CATALOG,
    token=TOKEN,
)

tbl = iceberg_catalog.load_table(f"{SCHEMA}.global_sales_gold")
print(tbl.current_snapshot())
tbl.scan(limit=10).to_pandas()
