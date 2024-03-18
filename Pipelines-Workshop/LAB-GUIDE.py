# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC # Lab Guide Data Engineering in the Age of AI (03/2024)

# COMMAND ----------

# MAGIC %md
# MAGIC ##0. Important
# MAGIC
# MAGIC * This is your main labguide. Please **keep it open in a separate tab**. You will need it to follow the steps below and come back to them throughout the course. 
# MAGIC * We will work with other notebooks, catalogs and workspace settings and this guide describes how things tie together, e.g. how to run DLT notebooks as a pipeline. 
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ##Super Important
# MAGIC
# MAGIC This course is designed in a way it can be run with thousands of participants on a single Databricks account. We are therefore using the **USER ID** (derived from your login user email) to separate schemas and pipelines. In your own environment you won't need that. Just use your company's naming schema for resources. 
# MAGIC
# MAGIC To get to your user id, check your login email at the to right of the workspace. Example: odl_user_1257777@databrickslabs.com means your user id is: `user_1257777`

# COMMAND ----------

# MAGIC
# MAGIC %md
# MAGIC ##1. Add a GitHub Repo
# MAGIC
# MAGIC To get access to the lab notebooks, create a repo in your workspace
# MAGIC
# MAGIC ### Add a Repo
# MAGIC
# MAGIC * Under `Workspace / Your Username` select `Repos` and click on "add repo" to add a new repo
# MAGIC * For Git Repo URL use  [`https://github.com/databricks/tmm`](https://github.com/databricks/tmm)
# MAGIC * Git provider and repo name will be filled automatically (repo name is `tmm`).
# MAGIC * Select Sparse Checkout Mode (otherwise you will clone more content than necessary)
# MAGIC   * under Cone Patter put `Pipelines-Workshop` 
# MAGIC * Click "create repo" and the resoures for this course will be cloned.
# MAGIC * Click on `Pipelines Workshop`. This is the folder we will be working with in this lab

# COMMAND ----------

# take a note of your user id (copying from top right)
#
#     USER_ID = 
#
# alternatively you can run this cell to compute your USER
import random
user = dbutils.notebook.entry_point.getDbutils().notebook().getContext().userName().get()
user = ''.join(filter(str.isdigit, user))

# make it work in non lab environments, create a 6 digit ID then
if len(user) < 3:
  user=str(random.randint(100000, 999999))

print(f"user_{user}")

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
# MAGIC In the [DLT SQL notebook]($./01-DLT-Loan-pipeline-SQL) check if the correct volumes are used for ingestion.
# MAGIC * Update the folder names and locations as described in the notebook. 
# MAGIC   * The locations used in Auto Loader must match the volumes paths as explained in the DLT SQL notebook
# MAGIC  
# MAGIC
# MAGIC ### Run your first Data Pipeline
# MAGIC 1. **Watch your instructor explaining how to create a DLT pipeline first**, then follow the steps below. ([Detailed documentation is available here](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-ui.html#create-a-pipeline))
# MAGIC 2. On your workspace, under Workflows / DLT change to "Owned by me"
# MAGIC 3. Create a new pipeline (leave all pipeline setting **on default except the ones listed below**)
# MAGIC   * `pipeline name: [use your own user_id from above as the name of the pipeline]`
# MAGIC   * Under `Source Code:` select the location of the [DLT SQL notebook]
# MAGIC   * For `Destination` select **Unity Catalog**
# MAGIC     - Catalog: demo 
# MAGIC     - Target Schema: `your user_id` (you will work with your own **schema** to separate content from others)
# MAGIC   * `Cluster mode: fixed size`
# MAGIC   * `Number Workers: 1`
# MAGIC   *  Then click "Create"
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
# MAGIC   * Understand DLT with serverless compute
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
# MAGIC (Instructor Demo)
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
# MAGIC   * `SELECT * FROM demo.USER_ID.ref_accounting_treatment` (make sure to use **your schema and table name**)
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
# MAGIC * Cluster: labcluster
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
# MAGIC Follow your instructor for cababilities still in preview. Time permitting, he will demo them on another environment. 
# MAGIC
# MAGIC ### Serverless Workflows and DLT
# MAGIC ### Databricks Assistent
# MAGIC
# MAGIC A full end to end demo of this section [**Data Engineering in the Age of AI** is available as a video in the Databricks Demo Center](https://www.databricks.com/resources/demos/videos/data-engineering/databricks-data-intelligence-platform?itm_data=demo_center)

# COMMAND ----------

# MAGIC %md 
# MAGIC
# MAGIC ##Congratulations for completing this workshop!
# MAGIC
