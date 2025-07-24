# Databricks notebook source
import requests
import pandas as pd
import io
import time
from databricks.sdk import WorkspaceClient

# Initialize clients
w = WorkspaceClient()
client = VectorSearchClient()

base_url = "https://raw.githubusercontent.com/databricks/tmm/main/Governance-lab/data"
csv_files = {
    "compensation_data": f"{base_url}/compensation_data.csv",
    "employee_records": f"{base_url}/employee_records.csv", 
    "hr_cases": f"{base_url}/hr_cases.csv",
    "internal_procedures": f"{base_url}/internal_procedures.csv",
    "performance_reviews": f"{base_url}/performance_reviews.csv",
    "public_policies": f"{base_url}/public_policies.csv"
}

# Create catalog if not exists
spark.sql("CREATE CATALOG IF NOT EXISTS clientcare")

# Create schema if not exists
spark.sql("CREATE SCHEMA IF NOT EXISTS clientcare.hr_data")

# Download and load each CSV file
for table_name, url in csv_files.items():
    # Download CSV data
    response = requests.get(url)
    response.raise_for_status()
    
    # Read CSV into pandas DataFrame
    df = pd.read_csv(io.StringIO(response.text))
    
    # Convert to Spark DataFrame and write to table
    spark_df = spark.createDataFrame(df)
    spark_df.write.mode("overwrite").saveAsTable(f"clientcare.hr_data{table_name}")

print("Tables created successfully")

# COMMAND ----------

# MAGIC %sql
# MAGIC GRANT USE CATALOG, USE SCHEMA, SELECT, EXECUTE ON CATALOG `clientcare` TO `account users`

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE GROUP hr_data_analysts;
