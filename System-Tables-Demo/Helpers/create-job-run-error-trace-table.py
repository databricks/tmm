"""
Helper script for materializing job run errors/error traces from the RunOutput API.

It fetches the recently finished jobs from system.lakeflow.job_task_run_timeline table, 
calls the RunOutput API for FAILED/ERROR runs and materializes the results.

Prerequisites: 
1. Enable lakeflow system schema 
https://docs.databricks.com/en/admin/system-tables/jobs.html#jobs-system-table-reference
2. Get SELECT rights for the lakeflow system schema
3. Adjust the TARGET_TABLE variable for the location of your choice.

Limitations:
- RunOutput is a workspace-level API
"""
from databricks.sdk import WorkspaceClient
from pyspark.sql.types import * 
from pyspark.sql.functions import * 


BATCH_SIZE = 100
TARGET_TABLE = "jacek.default.job_run_errors"
WORKSPACE_ID = str(dbutils.notebook.entry_point.getDbutils().notebook().getContext().workspaceId().get())

SCHEMA = StructType([
    StructField('workspace_id', StringType(), True),
    StructField('job_id', StringType(), True),
    StructField('job_run_id', StringType(), True),
    StructField('run_id', StringType(), True),
    StructField('task_key', StringType(), True),
    StructField('error', StringType(), True),
    StructField('error_trace', StringType(), True),
    StructField('start_time', StringType(), True),
    StructField('end_time', StringType(), True)
])

client = WorkspaceClient()

def get_materialized_job_errors():
  if not spark.catalog.tableExists(TARGET_TABLE):
    return spark.createDataFrame([], schema=SCHEMA)
  
  return spark.sql(f"SELECT * FROM {TARGET_TABLE}")

def get_non_materialized_job_errors():
  existing_rows_df = get_materialized_job_errors()
  
  job_run_timeline_df = (
    spark.table("system.lakeflow.job_task_run_timeline").filter(
      (job_run_timeline_df.workspace_id == WORKSPACE_ID) &
      (job_run_timeline_df.result_state.isNotNull()) &
      (job_run_timeline_df.result_state.isin("FAILED", "ERROR")) &
      (job_run_timeline_df.period_end_time >= expr("current_date() - interval 7 days"))
    )
  )

  result_df = job_run_timeline_df.join(
      existing_rows_df,
      on=["workspace_id", "job_id", "run_id"],
      how="left_anti"
  )

  return result_df.select("job_id", "job_run_id", "run_id", "task_key").collect()

def insert_rows(rows):
  df = spark.createDataFrame(rows, schema=SCHEMA)
  df = (
    df.withColumn("start_time", (col("start_time") / 1000).cast("timestamp"))
      .withColumn("end_time", (col("end_time") / 1000).cast("timestamp"))
  )
  df.write.mode("append").saveAsTable(TARGET_TABLE)

def main():
  job_runs_to_process = get_non_materialized_job_errors()
  print(f"Found {len(job_runs_to_process)} job runs to process.")

  rows = []
  for i, (job_id, job_run_id, run_id, task_key) in enumerate(job_runs_to_process):
    if i and i % BATCH_SIZE == 0:
      print(f"Processed {i}/{len(job_runs_to_process)} job runs")
      print("Saving to database")
      insert_rows(rows)
      rows = []

    try:
      data = client.jobs.get_run_output(run_id)
      rows.append({
        "workspace_id": WORKSPACE_ID,
        "job_id": job_id,
        "job_run_id": job_run_id,
        "run_id": run_id,
        "task_key": task_key,
        "error": data.error,
        "error_trace": data.error_trace,
        "start_time": data.metadata.start_time,
        "end_time": data.metadata.end_time
      })
    except Exception as e:
      print(f"Failed to fetch result for job_id: {job_id}, job_run_id: {job_run_id}, run_id: {run_id}, task_key: {task_key}")
    
  if rows:
    insert_rows(rows)

main()