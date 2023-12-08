# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC # Lab Guide Data Engineering (incl UC)

# COMMAND ----------

# MAGIC %md
# MAGIC ##1. Important
# MAGIC
# MAGIC * This is your main labguide. Please **keep it open in a separate tab**. You will need it to follow the steps below and come back to them throughout the course. 
# MAGIC * We will work with other notebooks, such as DLT notebooks, but this guide describes how things tie together, e.g. how to run DLT notebooks as a pipeline. 
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC *This course is designed in a way that it can be run with many participants on a single Databricks Workspace we are therefore using USDER_ID (derived from the login user) to separate schemas and pipelines. In your own environment you won't need that, just use your company's naming schema for resources. The course uses a single node DLT cluster. In production, we recommend to explore Enhanced Auto Scaling instead.*

# COMMAND ----------

# MAGIC
# MAGIC %md
# MAGIC ##1. Add a GitHub Repo
# MAGIC
# MAGIC ### Add a working repo
# MAGIC
# MAGIC * Under Workspace / Username select repos and click on "add repo" to add a new repo
# MAGIC * For Git Repo URL use  `https://github.com/databricks/tmm`, click on create repo
# MAGIC * Git provider and repo name will be filled automatically.
# MAGIC * Click "create repo" and the resoures for this course will be cloned.
# MAGIC
# MAGIC

# COMMAND ----------

# MAGIC
# MAGIC %md
# MAGIC ##2. Delta Live Tables
# MAGIC
# MAGIC
# MAGIC ### Understand DLT Pipelines in SQL
# MAGIC
# MAGIC * Watch your instructor explaining how to get started with DLT using the [DLT SQL notebook]($./01-DLT-Loan-pipeline-SQL). 
# MAGIC * For more information, check out the [documentation: core concepts](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-concepts.html)
# MAGIC
# MAGIC
# MAGIC After this module, you should be able to answer the following questions:
# MAGIC
# MAGIC * What is the difference between Streaming Table (ST) and a Materialized View (MV)
# MAGIC * What is the CTAS pattern?
# MAGIC * What do we use the medallion architecture for?
# MAGIC
# MAGIC
# MAGIC ### Update the provided DLT pipeline for your environment
# MAGIC
# MAGIC In the [DLT SQL notebook]($./01-DLT-Loan-pipeline-SQL) apply the following two changes:
# MAGIC * Update the folder name names and locations as described in the notebook.
# MAGIC  
# MAGIC
# MAGIC  
# MAGIC ### Run the Data Generator
# MAGIC The pipeline will ingest three different data sources, including a constantly produced data stream. To create the data stream you have to run the generator as described:
# MAGIC
# MAGIC 1. Watch your instructor explaining how to create the streaming updates for the lending club data.
# MAGIC 2. Use the [generator notebook]($./00-Loan-Data-Generator) and run the following steps:
# MAGIC   * Run first cell with the widget, this allows you to define the specifics of the data stream
# MAGIC   * Use the following settings in the widget:
# MAGIC     * `#recs/write (data volume): 50`
# MAGIC     * `#writes (total number of writes): 180`
# MAGIC     * `sec delay (pause between writes): 30`
# MAGIC     
# MAGIC   * Once the config values are set, run all cells
# MAGIC     * confirm that data is produced by looking at the output of CMD 5
# MAGIC     * leave the data generator running. It will run for the length of this course
# MAGIC
# MAGIC ### Run your first Data Pipeline
# MAGIC 1. Watch your instructor explaining how to create a DLT pipeline first, then follow the steps below. ([Detailed documentation is available here](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-ui.html#create-a-pipeline))
# MAGIC 2. On your workspace, under Workflows / DLT change to "Owned by me"
# MAGIC 3. Create a new pipeline (leave all pipeline setting **on default except the ones listed below**)
# MAGIC   * `pipeline name: [use your own user_id from above as the name of the pipeline]`
# MAGIC   * Under `Source Code:` select the location of the [DLT SQL notebook]
# MAGIC   * For `Destination` select **Unity Catalog**
# MAGIC     - Catalog: demos 
# MAGIC     - Target Schema: `your user_id`
# MAGIC   * `Cluster mode: fixed size`
# MAGIC   * `Number Workers: 1`
# MAGIC   *  Then click "create"
# MAGIC 3. Click on "Start" (top right) to run the pipeline. Note, when you start the pipeline for the first time it might take a few minutes until resources are provisioned.
# MAGIC
# MAGIC Note that the lab environment is configured that you can access the folders for data ingestion via Unity Catalog. Make sure to use least privilege here in a production environment. (see the official [documentation for more details](https://docs.databricks.com/en/data-governance/unity-catalog/manage-external-locations-and-credentials.html))
# MAGIC
# MAGIC
# MAGIC ### Pipeline Graph
# MAGIC You can always get to your running pipelines by clicking on "Workflows" on the left menue bar and then on "Delta Live Tables" / "Owned by me"
# MAGIC * Check the pipeline graph 
# MAGIC   * Identify bronze, silver and gold tables
# MAGIC   * Identify all streaming tables (ST) in the SQL code (use the link under "Paths" at the right to open the notebook) 
# MAGIC   * Identify Materialized Views and Views
# MAGIC
# MAGIC
# MAGIC ### Pipeline Settings
# MAGIC
# MAGIC   * Recap DLT development vs production mode
# MAGIC   * Understand how to use Unity Catalog
# MAGIC   * Understand serverless DLT
# MAGIC
# MAGIC
# MAGIC ### Explore Streaming Delta Live Tables
# MAGIC * Take a note of the ingested records in the bronze tables
# MAGIC * Run the pipeline again by clicking on "Start" (top right in the Pipeline view)
# MAGIC   * note, only the new data is ingested 
# MAGIC * Select "Full Refresh all" from the "Start" button
# MAGIC   * note that all tables will be recomputed and backfilled 
# MAGIC * Could we convert the MV used for ingestion to a ST? 
# MAGIC * Use the button "Select Table for Refresh" and select all silver tables to be refreshed only
# MAGIC
# MAGIC
# MAGIC
# MAGIC ### UC and Lineage
# MAGIC
# MAGIC Watch your instructor explaining UC lineage with DLT and the underlying Delta Tables
# MAGIC
# MAGIC #### Delta Tables
# MAGIC
# MAGIC (Instructor Demo which is part of Lineage now)
# MAGIC
# MAGIC
# MAGIC Delta Live Tables is an abstraction for Spark Structured Streaming and built on Delta tables. Delta tables unify DWH, data engineering, streaming and DS/ML. 
# MAGIC * Check out Delta table details
# MAGIC   * When viewing the Pipeline Graph select the table "raw_txs"
# MAGIC     * on the right hand side, click on the link under "Metastore" for this table to see table details
# MAGIC     * How many files does that table consist of?
# MAGIC     * Check the [generator notebook]($./00-Loan-Data-Generator) to estimate the number of generated files
# MAGIC * Repeat the same exercise, but start with the navigation bar on the left 
# MAGIC   * Click on "Data"
# MAGIC   * Select your catalog / schema. The name of your schema is the **user_id** parameter of your pipeline setting.
# MAGIC   * Drill down to the `raw_tx` table
# MAGIC   * Check the table's schema and sample data
# MAGIC   
# MAGIC   
# MAGIC
# MAGIC ### DLT Pipelines in Python (Instructor only) 
# MAGIC
# MAGIC Listen to your instructor explaining DLT pipelines written in Python. You won't need to run this pipeline.
# MAGIC
# MAGIC
# MAGIC ```
# MAGIC Following the explanations, make sure you can answer the following questions: 
# MAGIC * Why would you use DLT in Python? (messaging broker[can be done in SQL now!], meta programming, Python lovers)
# MAGIC * How could you create a DLT in Python?
# MAGIC ```
# MAGIC [(some hints)](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-incremental-data.html)
# MAGIC
# MAGIC
# MAGIC ### Monitor DLT Events (Optional) 
# MAGIC
# MAGIC Watch your instructor explaining you how to retrieve DLT events, lineage and runtime data from expectations. 
# MAGIC
# MAGIC [Notebook used]($./03-Log-Analysis)
# MAGIC
# MAGIC
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. DWH View / SQL Persona
# MAGIC
# MAGIC The Lakehouse unifies classic data lakes and DWHs. This lab will teach you how to access Delta tables generated with a DLT data pipeline from the DWH.
# MAGIC
# MAGIC ### Use the SQL Editor
# MAGIC * On the left menue bar, select the SQL persona
# MAGIC * Also from the left bar, open the SQL editor
# MAGIC * Create a simple query: 
# MAGIC   * `SELECT * FROM demos.user_455444.ref_accounting_treatment` (make sure to use **your schema and table name**)
# MAGIC   * run the query by clicking Shift-RETURN
# MAGIC   * Save the query using your ID as a query name
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Databricks Workflows with DLT
# MAGIC
# MAGIC
# MAGIC ### Create a Workflow
# MAGIC
# MAGIC * In the menue bar on the left, select Workflows
# MAGIC * Select "Workflows owned by me"
# MAGIC * Click on "Create Job"
# MAGIC * Name the new job same as **your user_id** from above
# MAGIC
# MAGIC ### Add a first task
# MAGIC
# MAGIC * Task name: Ingest
# MAGIC * Task type: DLT task
# MAGIC * Pipeline: your DLT pipeline name for the DLT SQL notebook from above (the pipeline should be in triggered mode for this lab.)
# MAGIC * Cluster: labcluster*
# MAGIC ### Add a second task
# MAGIC * Task name: Update Downstream
# MAGIC * Task type: Notebook 
# MAGIC * Select the `04-Udpate-Downstream` notebook
# MAGIC
# MAGIC
# MAGIC
# MAGIC ### Run the workflow
# MAGIC * Run the workflow from the "Run now" buttom top right
# MAGIC   * The Workflow will fail with an error in the second task.
# MAGIC   * Switch to the Matrix view.
# MAGIC     * To explore the Matrix View, run the workflow again (it will fail again).  
# MAGIC ### Repair and Rerun (OPTIONAL)
# MAGIC   * In the Matrix View, click on the second task marked in red to find out what the error is
# MAGIC     * Click on "Highlight Error"
# MAGIC   * Debug the 04-Udpate-Downstream notebook (just comment out the line where the error is caused with `raise`) 
# MAGIC   * Select the Run with the Run ID again and view the Task
# MAGIC   * Use the "Repair and Rerun" Feature to rerun the workflow   
# MAGIC     * It should successfully run now.
# MAGIC   * You can delete the other failed run. 
# MAGIC
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Outlook (optional topics in preview)
# MAGIC
# MAGIC ### Serverless Workflows and DLT
# MAGIC ### Databricks Assistent

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ##Congratulations for completing this workshop!
# MAGIC
