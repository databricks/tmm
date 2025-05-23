-- Databricks notebook source
-- MAGIC %md-sandbox
-- MAGIC # AI-Powered Data Engineering with Lakeflow
-- MAGIC
-- MAGIC Declerative Pipelines make Data Engineering accessible for all. 
-- MAGIC
-- MAGIC <img style="float:right" src="https://upload.wikimedia.org/wikipedia/commons/6/63/Databricks_Logo.png" width="700"/>
-- MAGIC
-- MAGIC **Accelerate ETL development** <br/>
-- MAGIC Enable analysts and data engineers to innovate rapidly with simple pipeline development and maintenance 
-- MAGIC
-- MAGIC **Remove operational complexity** <br/>
-- MAGIC By automating complex administrative tasks and gaining broader visibility into pipeline operations
-- MAGIC
-- MAGIC **Trust your data** <br/>
-- MAGIC With built-in quality controls and quality monitoring to ensure accurate and useful BI, Data Science, and ML 
-- MAGIC
-- MAGIC **Simplify batch and streaming** <br/>
-- MAGIC With self-optimization and auto-scaling data pipelines for batch or streaming processing 
-- MAGIC
-- MAGIC ## Our declarative pipeline
-- MAGIC
-- MAGIC We'll be using as input a raw dataset containing information on our customers Loan and historical transactions. 
-- MAGIC
-- MAGIC Our goal is to ingest this data in near real time and build table for our Analyst team while ensuring data quality.
-- MAGIC
-- MAGIC <!-- Collect usage data (view). Remove it to disable collection. View README for more details.  -->
-- MAGIC <img width="1px" src="https://www.google-analytics.com/collect?v=1&gtm=GTM-NKQ8TT7&tid=UA-163989034-1&aip=1&t=event&ec=dbdemos&ea=VIEW&dp=%2F_dbdemos%2Fdata-engineering%2Fdlt-loans%2F01-DLT-Loan-pipeline-SQL&cid=local&uid=local">

-- COMMAND ----------

-- MAGIC %md 
-- MAGIC
-- MAGIC Our datasets are coming from 3 different systems and saved in UC governed volumes. You can see these volumes under `Catalog / demo / loan_io`:
-- MAGIC
-- MAGIC * `raw_transactions` (loans - streaming data)
-- MAGIC * `ref_accounting` (reference table, mostly static)
-- MAGIC * `historical_loans` (loan from legacy system, new data added every week)
-- MAGIC
-- MAGIC We will ingest this data incrementally, and then compute a couple of aggregates that we'll need for our final Dashboard to report our KPI.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC
-- MAGIC ### Adjust the Pipeline definiton for Ingestion
-- MAGIC
-- MAGIC make sure to verify the ingestion location for Auto Loader in the first three SQL statement below: 
-- MAGIC

-- COMMAND ----------

-- MAGIC %md-sandbox 
-- MAGIC
-- MAGIC ## Bronze layer: incrementally ingest data leveraging Databricks Auto Loader
-- MAGIC
-- MAGIC <img style="float: right; padding-left: 10px" src="https://github.com/QuentinAmbard/databricks-demo/raw/main/product_demos/dlt-golden-demo-loan-2.png" width="600"/>
-- MAGIC
-- MAGIC Our raw data is being sent to a blob storage. 
-- MAGIC
-- MAGIC Auto Loader simplify this ingestion, including schema inference, schema evolution while being able to scale to millions of incoming files. 
-- MAGIC
-- MAGIC Auto Loader is available in SQL using the `cloud_files` function and can be used with a variety of format (json, csv, avro...):
-- MAGIC
-- MAGIC For more detail on Auto Loader, you can see `dbdemos.install('auto-loader')`
-- MAGIC
-- MAGIC #### STREAMING TABLE 
-- MAGIC Defining tables as `STREAMING` will guarantee that you only consume new incoming data. Without `STREAMING`, you will scan and ingest all the data available at once. See the [documentation](https://docs.databricks.com/data-engineering/delta-live-tables/delta-live-tables-incremental-data.html) for more details

-- COMMAND ----------

-- DBTITLE 1,Capture new incoming transactions
CREATE STREAMING TABLE raw_txs
  COMMENT "New raw loan data incrementally ingested from cloud object storage landing zone"
AS 
SELECT *
FROM cloud_files(
  '/Volumes/demo/loan_io/raw_transactions', 
  'json', 
  map("cloudFiles.inferColumnTypes", "true")
)

-- COMMAND ----------

-- DBTITLE 1,Historical transaction from legacy system
CREATE STREAMING TABLE raw_historical_loans
  TBLPROPERTIES ("pipelines.trigger.interval" = "6 hour")
  COMMENT "Raw historical transactions"
AS 
SELECT 
  * 
FROM 
  cloud_files(
    '/Volumes/demo/loan_io/historical_loans', 
    'csv', 
    map("cloudFiles.inferColumnTypes", "true")
  )

-- COMMAND ----------

-- DBTITLE 1,Reference table - metadata (small & almost static)
CREATE MATERIALIZED VIEW ref_accounting_treatment
  COMMENT "Lookup mapping for accounting codes"
AS 
SELECT 
  * 
FROM 
  delta.`/Volumes/demo/loan_io/ref_accounting`
