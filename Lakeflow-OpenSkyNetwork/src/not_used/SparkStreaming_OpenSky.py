# Databricks notebook source
# MAGIC %md
# MAGIC # OpenSky live flights — streaming with the custom data source
# MAGIC
# MAGIC A minimal Structured Streaming demo of the `opensky` PySpark data source from
# MAGIC [allisonwang-db/pyspark-data-sources](https://github.com/allisonwang-db/pyspark-data-sources),
# MAGIC installed and imported exactly as in that repo's examples.
# MAGIC
# MAGIC Runs **anonymously** over Europe (~4,500 aircraft). Free Edition has open egress to
# MAGIC OpenSky, so it ingests live data. Set `client_id`/`client_secret` options for the
# MAGIC authenticated path (higher rate limits).

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install the `opensky` data source
# MAGIC
# MAGIC The released `pyspark-data-sources` package, installed and imported exactly as in
# MAGIC Allison Wang's examples. Runs **anonymously** (no `client_id`/`client_secret`).
# MAGIC Note: the released source is the pre-fix version — swap to the fixed one once
# MAGIC [PR #61](https://github.com/allisonwang-db/pyspark-data-sources/pull/61) merges.

# COMMAND ----------

# MAGIC %pip install pyspark-data-sources

# COMMAND ----------

# Restart Python so the freshly-installed package is importable.
dbutils.library.restartPython()

# COMMAND ----------

from pyspark_datasources import OpenSkyDataSource

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Register the data source and stream live flights

# COMMAND ----------

spark.dataSource.register(OpenSkyDataSource)

flights = (
    spark.readStream.format("opensky")
    .option("region", "EUROPE")
    # .option("client_id", "fmunz-api-client")            # authenticated path (optional)
    # .option("client_secret", dbutils.secrets.get("opensky", "client_secret"))
    .load()
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Stream the data and show the rows
# MAGIC
# MAGIC `display(streaming_df)` on serverless only shows a metrics dashboard (and breaks on re-run).
# MAGIC The simple, reliable way to see the **rows** is to stream one batch into an in-memory table
# MAGIC with `trigger(availableNow=True)` — it drains the current snapshot and terminates on its own
# MAGIC — then `display()` that table. Serverless requires an explicit `checkpointLocation` on a UC
# MAGIC volume; a fresh path each run avoids "cannot recover from checkpoint" on re-run.

# COMMAND ----------

import uuid

run = uuid.uuid4().hex[:8]

(flights.writeStream.format("memory").queryName("opensky_live")
    .option("checkpointLocation", f"/Volumes/workspace/opensky/checkpoints/{run}")
    .trigger(availableNow=True).start()
    .awaitTermination())

display(spark.table("opensky_live"))  # the actual aircraft rows