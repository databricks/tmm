-- Databricks notebook source
-- MAGIC %md 
-- MAGIC ### A cluster has been created for this demo
-- MAGIC Run this demo on the serverless DWH. 

-- COMMAND ----------

-- MAGIC %md-sandbox
-- MAGIC
-- MAGIC # DLT pipeline log analysis
-- MAGIC
-- MAGIC <img style="float:right" width="500" src="https://github.com/QuentinAmbard/databricks-demo/raw/main/retail/resources/images/retail-dlt-data-quality-dashboard.png">
-- MAGIC
-- MAGIC Each DLT Pipeline saves events and expectations metrics as Delta Tables in the Storage Location defined on the pipeline. From this table we can see what is happening and the quality of the data passing through the pipeline.
-- MAGIC
-- MAGIC You can leverage the expecations directly as a SQL table with Databricks SQL to track your expectation metrics and send alerts as required. 
-- MAGIC
-- MAGIC
-- MAGIC
-- MAGIC <!-- Collect usage data (view). Remove it to disable collection. View README for more details.  -->
-- MAGIC <img width="1px" src="https://www.google-analytics.com/collect?v=1&gtm=GTM-NKQ8TT7&tid=UA-163989034-1&aip=1&t=event&ec=dbdemos&ea=VIEW&dp=%2F_dbdemos%2Fdata-engineering%2Fdlt-loans%2F03-Log-Analysis&cid=local&uid=local">

-- COMMAND ----------

-- DBTITLE 1,Show DLT System Tables for a Pipeline
-- replace the pipeline_id with your own pipeline id 
SELECT * FROM event_log("a23cadf7-2aa3-43be-900f-c7bfa2a0a0fc")

-- COMMAND ----------

-- MAGIC %md
-- MAGIC
-- MAGIC ## System Tables
-- MAGIC
-- MAGIC For system table information check out Catalog Explorer under System and the this [Databricks blog](https://www.databricks.com/blog/improve-lakehouse-security-monitoring-using-system-tables-databricks-unity-catalog). 
-- MAGIC
-- MAGIC For more information about DLT events [check the documentation](https://docs.databricks.com/en/delta-live-tables/observability.html)
