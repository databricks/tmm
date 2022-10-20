# Databricks notebook source
# MAGIC %md
# MAGIC # Lab Guide Data Engineering

# COMMAND ----------

# MAGIC %md
# MAGIC # Important
# MAGIC 
# MAGIC * This is your main labguide. Please **keep it open in a separate tab** (or bookmark it). You will need it to follow the steps below and come back to them throughout the course. 
# MAGIC * We will work with other notebooks, such as DLT notebooks, but this guide here describes how thing tie together and how to run DLT notebooks. 

# COMMAND ----------

# MAGIC %md
# MAGIC ## Delta Live Tables

# COMMAND ----------

# MAGIC %md
# MAGIC ### Understand DLT Pipelines in SQL
# MAGIC 
# MAGIC * Carefully watch your instructor explaining the [DLT SQL notebook]($./01-DLT-SQL). 
# MAGIC 
# MAGIC ([core concepts are explained here](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-concepts.html))

# COMMAND ----------

# MAGIC %md
# MAGIC ```
# MAGIC After this module, you should be able to answer the following questions:
# MAGIC 
# MAGIC   * What is the difference between a streaming pipeline and a non-streaming pipeline?
# MAGIC   * What is the CTAS pattern?
# MAGIC   * Why do we use the medallion architecture?
# MAGIC ```

# COMMAND ----------

# MAGIC %md 
# MAGIC ### Run your first Data Pipeline 
# MAGIC * Watch your instructor explaining how to create a DLT pipeline, then follow the steps below. ([Detailed documentation here](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-ui.html#create-a-pipeline))
# MAGIC * Under Workflows / DLT create a new pipeline (leave all pipeline setting on default except the ones listed below)
# MAGIC   * name: 
# MAGIC   * target: 
# MAGIC   * min workers: 1, max workers: 2
# MAGIC * Run the pipeline (it might take a few mins until resources are provisioned)
# MAGIC * Note, you can change the pipeline settings for a running pipeline under "settings"
# MAGIC 
# MAGIC   

# COMMAND ----------

# MAGIC %md
# MAGIC ### Pipeline Graph
# MAGIC * Check the pipeline graph 
# MAGIC   * Identify all streaming live tables
# MAGIC   * Identify DLT views vs tables
# MAGIC   * Recap DLT development vs production mode
# MAGIC * Note 
# MAGIC 
# MAGIC   

# COMMAND ----------

# MAGIC %md
# MAGIC ### Delta Tables
# MAGIC Delta Live Tables are Delta tables
# MAGIC * Check out Delta table details
# MAGIC   * When viewing the Pipeline Graph select the table "bz_raw_txs"
# MAGIC   * on the left hand side, click on the link under "Metastore" for this table to see table details
# MAGIC   * How many files does that table consist of?
# MAGIC * Repeat the same exercise, but start with the navigation bar on the left 
# MAGIC   * Click on "Data"
# MAGIC   * Select "hive_metastore", then select your database (i.e. the DLT target setting)
# MAGIC   * Drill down to the XXX table
# MAGIC   * Check the table's meta data, how many files does it consist of?
# MAGIC   
# MAGIC   

# COMMAND ----------

# MAGIC %md
# MAGIC ### DLT Pipelines in Python
# MAGIC 
# MAGIC Listen to your instructor explaining DLT pipelines written in Python. You won't need to run this pipeline.

# COMMAND ----------

# MAGIC %md
# MAGIC ```
# MAGIC Following the explanations, make sure you can answer the following questions: 
# MAGIC * Why would you use DLT in Python? 
# MAGIC * How could you create a DLT in Python?
# MAGIC ```
# MAGIC [(some hints)](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-incremental-data.html)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Monitor DLT Events

# COMMAND ----------

# MAGIC %md
# MAGIC ## Databricks Workflows with DLT 

# COMMAND ----------

# MAGIC %md
# MAGIC * Create a Workflow
# MAGIC   * Under Workflows, create new Workflow (leave all setting on default, except the once mentioned below)
# MAGIC   * First task: DLT task, specify the notebook from above
# MAGIC   * 

# COMMAND ----------


