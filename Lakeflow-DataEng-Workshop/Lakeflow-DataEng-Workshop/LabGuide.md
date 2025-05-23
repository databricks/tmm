# Lab Guide: AI-Powered Data Engineering 
### (Lakeflow Edition, Summit 2025)

## 0. Background

This lab guide is part of the Databricks Foundational Workshop "AI-Powered Data Engineering". The course is designed to give you hands-on experience with the latest Databricks data engineering capabilities.

### What you will learn

You will learn how to create a DLT pipeline for streaming data, run it, and use it in a workflow. You will also learn how to use the AI-supported tool like Databricks Assistant and Genie.


### Your task

Imagine you just started a new job as a data engineer and you are asked to take over an DLT ingestion pipeline written in SQL. The pipeline ingests loan requests from an online transcation broker processing continuously. Don't worry about the transaction broker, your instructor set set this up for your (the code is provided in the repo for transparency).



## Important

* This is your main lab guide. Please **keep it open in a separate tab**. You will need it to follow the steps below and come back to them throughout the course.
* We will work with other notebooks, catalogs, and workspace settings, and this guide describes how things tie together, e.g., how to configure and run DLT pipelines.
* This lab guide is also part of the public GitHub repo, so you can easily recreate this course in your own account or share it with your colleagues.

## Super Important

This course is designed in a way that it can be run with thousands of participants on a single Databricks account sharing a number of workspaces.

We are therefore using the **USER ID** (derived from your login user email) to separate schemas and pipelines and avoid namespace clashes. Just as in your own environment, you would use your company's naming schema for resources.

To get to your user id, check your login email by clicking on the "L" on the top right of the workspace. Example: labuser10148895_1745997814@vocareum.com means your user id is: `labuser10148895_1745997814`

## 1. Add a GitHub Repo


To get access to the lab notebooks, create a repo in your workspace

### Add a Git Folder

* On the left-hand side, click on `Workspace` and `Home` and then use the button at the top right and click "Create / Git Folder" to add a new git folder
  * For Git Repo URL use  [`https://github.com/databricks/tmm`](https://github.com/databricks/tmm)
  * Git provider and repo name will be filled automatically (repo name is `tmm`).
  * Select **Sparse Checkout Mode** (otherwise, you will clone more content than necessary)
  * under Cone Pattern put `Pipelines-Workshop`
  * Click "create repo" and the resources for this course will be cloned.
* Click on `Pipelines Workshop`. This is the folder we will be working with in this lab.

## 2. Delta Live Tables

### Understand DLT Pipelines in SQL

* Watch your instructor explaining how to get started with DLT using the [DLT SQL notebook]($./01-DLT-Loan-pipeline-SQL).
* For more information, check out the [documentation: core concepts](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-concepts.html)

After this module, you should be able to answer the following questions:

* What is the difference between Streaming Tables (ST) and Materialized Views (MV)?
* What is the CTAS pattern?
* What do we use the medallion architecture for?

### Update the provided DLT pipeline for your environment

In the [DLT SQL notebook]($./01-DLT-Loan-pipeline-SQL) check if the correct volumes are used for ingestion.

* The locations used for Auto Loader must match the volumes paths as explained in the DLT SQL notebook

### Run your first Data Pipeline

1. **Watch your instructor explaining how to create a DLT pipeline first**, then follow the steps below. ([Detailed documentation is available here](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-ui.html#create-a-pipeline))
2. On your workspace, under Workflows / DLT change to "Owned by me"
3. Create a new pipeline (leave all pipeline settings **on default except the ones listed below**)
  * `pipeline name:`**[use your own user_id from above as the name of the pipeline]**
  * Select `Serverless` to run the pipeline with serverless compute
  * Under `Source Code:` select the location of the [DLT SQL notebook], that is  `YOUR_USERNAME@databrickslabs.com / tmm / Pipelines-Workshop/01-DLT-Loan-pipeline-SQL`

  * For `Destination` select **Unity Catalog**
    - Catalog: demo
    - Target Schema: `your user_id` (note, you will **work with your own schema** to separate your content from others)
  * (In older accounts **without** serverless enabled set `Cluster mode: fixed size` and `Number Workers: 1`)
  *  Then click "Create"
3. Click on "Start" (top right) to run the pipeline. Note, when you start the pipeline for the first time it might take a few minutes until resources are provisioned.

Note that the lab environment is configured so that you can access the folders for data ingestion via Unity Catalog. Make sure to use least privilege here in a production environment. (see the official [documentation for more details](https://docs.databricks.com/en/data-governance/unity-catalog/manage-external-locations-and-credentials.html))

### Pipeline Graph

You can always get to your running pipelines by clicking on "Workflows" on the left menu bar and then on "Delta Live Tables" / "Owned by me"
* Check the pipeline graph
  * Identify bronze, silver, and gold tables
  * Identify all streaming tables (ST) in the SQL code (use the link under "Paths" at the right to open the notebook)
  * Identify Materialized Views and Views

### New Developer Experience

* Once you defined the pipeline settings, the notebook is associated with the DLT code.
* On the notebook page, you will be asked if you want to attach the notebook to the pipeline. If you do so, you can see the pipeline graph and the event log in the notebook. The notebook is then like a mini IDE for DLT.

### Pipeline Settings

  * Recap DLT development vs production mode
  * Understand how to use Unity Catalog
  * Understand DLT with serverless compute

### Explore Streaming Delta Live Tables

* Take a note of the ingested records in the bronze tables
* Run the pipeline again by clicking on "Start" (top right in the Pipeline view)
  * note, only the new data is ingested
* Select "Full Refresh all" from the "Start" button
  * note that all tables will be recomputed and backfilled
* Could we convert the Materialized View (MV) used for data ingestion to a Streaming Table (ST)
* Use the button "Select Table for Refresh" and select all silver tables to be refreshed only

### UC and Lineage

Watch your instructor explaining UC lineage with DLT and the underlying Delta Tables

#### Delta Tables

(Instructor Demo)

Delta Live Tables is an abstraction for Spark Structured Streaming and built on Delta tables. Delta tables unify DWH, data engineering, streaming, and DS/ML.
* Check out Delta table details
  * When viewing the Pipeline Graph select the table "raw_txs"
    * on the right-hand side, click on the link under "Metastore" for this table to see table details
    * How many files does that table consist of?
    * Check the [generator notebook]($./00-Loan-Data-Generator) to estimate the number of generated files
* Repeat the same exercise, but start with the navigation bar on the left
  * Click on "Data"
  * Select your catalog / schema. The name of your schema is the **user_id** parameter of your pipeline setting.
  * Drill down to the `raw_tx` table
  * Check the table's schema and sample data

### DLT Pipelines in Python (Instructor only)

Listen to your instructor explaining DLT pipelines written in Python. You won't need to run this pipeline.

```
Following the explanations, make sure you can answer the following questions:
* Why would you use DLT in Python? (messaging broker[can be done in SQL now!], meta programming, Python lovers)
* How could you create a DLT in Python?
```

[(some hints)](https://docs.databricks.com/workflows/delta-live-tables/delta-live-tables-incremental-data.html)

### Direct Publishing Mode

With direct publishing mode, you can create pipeline tables under any schema name. Under "Pipeline Settings," the default schema name is set. This setting can be overwritten in the SQL code for every table.

Try using this feature and put the three gold tables into the USER_ID_dashboard schema.

### Monitor DLT Events (Optional)

Watch your instructor explaining how to retrieve DLT events, lineage, and runtime data from expectations.

[Notebook used]($./03-Log-Analysis)

## 3. Spark with Serverless Compute

You can now use Notebooks to run serverless Spark jobs

* On the left menu bar, click on +New Notebook
* Edit the name of the notebook
* Make sure next to the notebook's name `Python` is displayed for the default cell type (or change it)
* Make sure on the right-hand side you see a green dot and `connected`. Click on that button to verify you are connected to `serverless compute` (if not, connect to serverless compute)

### Use /explain and /doc

* Add the following command to a Python cell, then run it by clicking on the triangle (or using SHIFT-RETURN shortcut):

`display(spark.range(10).toDF("serverless"))`
* Click on the symbol for Databricks Assistant and document the cell. Hint: use /doc in the command line for Assistant and accept the suggestion.

### Use /fix

* Add another Python cell and copy the following command into that cell. The command contains a syntax error.
`display(spark.createDataFrame([("Python",), ("Spark",), ("Databricks",)], ["serverless"]))`
Click on the Assistant toggle (the blueish/redish star) and try to fix the problem with `/fix` and run the command.

Note that the Assistant is context-aware and knows about table names and schemas from Unity Catalog.

## 3. DWH View / SQL Persona

The Lakehouse unifies classic data lakes and DWHs. This lab will teach you how to access Delta tables generated with a DLT data pipeline from the DWH.

### Use the SQL Editor

* On the left menu bar, select the SQL persona
* Also from the left bar, open the SQL editor
* Create a simple query:
  * `SELECT * FROM demo.USER_ID.ref_accounting_treatment` (make sure to use **your schema and table name**)
  * run the query by clicking Shift-RETURN
  * Save the query using your ID as a query name

## 4. Databricks Workflows with DLT

### Create a Workflow

* In the menu bar on the left, select Workflows
* Select "Workflows owned by me"
* Click on "Create Job"
* Name the new job same as **your user_id** from above

### Add a first task

* Task name: Ingest
* Task type: DLT task
* Pipeline: your DLT pipeline name for the DLT SQL notebook from above (the pipeline should be in triggered mode for this lab.)

### Add a second task

* Task name: Update Downstream
* Task type: Notebook
* Select the `04-Update-Downstream` notebook
* Note that `Serverless` is automatically selected for compute on the right-hand side

### Run the workflow

* Run the workflow from the "Run now" button top right
  * The Workflow will fail with an error in the second task.
  * Switch to the Matrix view.
    * To explore the Matrix View, run the workflow again (it will fail again).

### Repair and Rerun (OPTIONAL)

  * In the Matrix View, click on the second task marked in red to find out what the error is
    * Click on "Highlight Error"
  * Debug the 04-Udpate-Downstream notebook (just comment out the line where the error is caused with `raise`)
  * Select the Run with the Run ID again and view the Task
  * Use the "Repair and Rerun" Feature to rerun the workflow
    * It should successfully run now.
  * You can delete the other failed run.


## 5. Instructor Demo: New DLT Pipeline Editor



### Follow the Instructor Demo

The new DLT Pipeline Editor is available in beta. It is a new way to create and manage DLT pipelines. The new editor is designed to be more user-friendly and intuitive, making it easier to create and manage DLT pipelines. One core difference is that the new editor is based on files, not notebooks.

### Setup Admin level

1. As a workspace admin, go to Previews under your user badge.
2. Enable **Pipelines multi-file developer Experience**


### Setup User level
If you want to enable the ETL Pipeline Multi-File Editor, follow these steps:

1. In the top-right corner, select your user icon
2. Right-click on Settings 
3. Select Developer.
4. Scroll to the bottom and enable **ETL Pipeline Multi-File Editor**.


## 6. Outlook (optional topics in preview)

Follow your instructor for capabilities such as Genie Data Rooms. Time permitting.


A full end-to-end demo of this section is available as a video in the [Databricks Demo Center](https://www.databricks.com/resources/demos/videos/data-engineering/databricks-data-intelligence-platform?itm_data=demo_center)

# Congratulations for completing this workshop!
