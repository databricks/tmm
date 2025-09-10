# Databricks notebook source
import requests
import pandas as pd
import io
import time
from databricks.sdk import WorkspaceClient

# Initialize clients
w = WorkspaceClient()

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
    
    # Convert to Spark DataFrame
    spark_df = spark.createDataFrame(df)
    
    # Drop the existing table if it exists to avoid schema conflicts
    spark.sql(f"DROP TABLE IF EXISTS clientcare.hr_data.{table_name}")
    
    # Write the DataFrame to the table
    spark_df.write.mode("overwrite").saveAsTable(f"clientcare.hr_data.{table_name}")

print("Tables created successfully")

# COMMAND ----------

# MAGIC %sql
# MAGIC GRANT USE CATALOG, USE SCHEMA, SELECT, EXECUTE ON CATALOG `clientcare` TO `account users`

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE GROUP hr_data_analysts;

# COMMAND ----------

# Set our working environment

from databricks.sdk import WorkspaceClient
from pyspark.sql import SparkSession
import pandas as pd

w = WorkspaceClient()# Read-only for most operations
# Cannot set masks or row filters via SDK

catalog_name = "clientcare" 
schema_name = "hr_data"

# Verify all tables are loaded
spark.sql(f"USE CATALOG {catalog_name}")
spark.sql(f"USE SCHEMA {schema_name}")


# COMMAND ----------

# DATA ANALYST VIEW - For statistical analysis (will be assigned to agent service principal in Lab 2)
# Key features: Anonymous employee IDs, full salary access, excludes Legal dept
spark.sql("""
CREATE OR REPLACE VIEW data_analyst_view AS
SELECT 
    CONCAT('EMP_', LPAD(e.employee_id, 6, '0')) as anonymous_id,  -- EMP_000001 format
    e.department,
    YEAR(e.hire_date) as hire_year,                            -- Year only for better anonymization
    c.base_salary,                                              -- Full salary for analytics
    c.bonus,
    c.stock_options,
    YEAR(c.effective_date) as comp_year,
    pr.rating,
    QUARTER(pr.review_date) as review_quarter,
    YEAR(pr.review_date) as review_year
    -- Removed pr.comments to prevent identifying information
FROM employee_records e
LEFT JOIN compensation_data c ON e.employee_id = c.employee_id
LEFT JOIN performance_reviews pr ON e.employee_id = pr.employee_id
WHERE e.department != 'Legal'  -- Exclude Legal for compliance reasons
""")

# COMMAND ----------

# Grant permissions to the hr_data_analysts group using fully qualified names
group_name = "hr_data_analysts"

# Catalog and schema access
spark.sql(f"GRANT USAGE ON CATALOG {catalog_name} TO `{group_name}`")
spark.sql(f"GRANT USAGE ON SCHEMA {catalog_name}.{schema_name} TO `{group_name}`")

# View access with fully qualified name
spark.sql(f"GRANT SELECT ON VIEW {catalog_name}.{schema_name}.data_analyst_view TO `{group_name}`")

# COMMAND ----------

# Create column masking function for SSN
spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog_name}.{schema_name}.mask_ssn(ssn_value STRING)
RETURNS STRING
RETURN CASE 
    WHEN is_account_group_member('admins') THEN ssn_value
    WHEN is_account_group_member('hr_data_analysts') THEN 'ANALYTICS_MASKED'
    ELSE CONCAT('***-**-', RIGHT(ssn_value, 4))
END
""")

# Apply the masking function to the SSN column
spark.sql(f"""
ALTER TABLE {catalog_name}.{schema_name}.employee_records 
ALTER COLUMN ssn 
SET MASK {catalog_name}.{schema_name}.mask_ssn
""")


# COMMAND ----------

# TOOL 1: Performance & Retention Analytics
print("🔧 Creating performance analytics function...")

spark.sql(f"""
    CREATE OR REPLACE FUNCTION
    {catalog_name}.{schema_name}.analyze_performance()
    RETURNS TABLE (
        department STRING,
        avg_rating DOUBLE,
        min_rating DOUBLE,
        max_rating DOUBLE,
        employee_count INT,
        avg_tenure_years DOUBLE
    )
    COMMENT 'HR Analytics: Basic performance metrics by department'
    RETURN (
        SELECT 
            department,
            AVG(rating) as avg_rating,
            MIN(rating) as min_rating,
            MAX(rating) as max_rating,
            COUNT(DISTINCT anonymous_id) as employee_count,
            AVG(YEAR(CURRENT_DATE()) - hire_year) as avg_tenure_years
        FROM {catalog_name}.{schema_name}.data_analyst_view
        WHERE rating IS NOT NULL
        GROUP BY department
    );
""")


# COMMAND ----------

# TOOL 2: Department & Compensation Analytics
print("🔧 Creating operations analytics function...")

spark.sql(f"""
    CREATE OR REPLACE FUNCTION
    {catalog_name}.{schema_name}.analyze_operations()
    RETURNS TABLE (
        department STRING,
        employee_count INT,
        avg_salary DOUBLE,
        avg_bonus DOUBLE,
        avg_total_comp DOUBLE,
        avg_stock_options INT
    )
    COMMENT 'HR Analytics: Department compensation and operational metrics'
    RETURN (
        SELECT 
            department,
            COUNT(DISTINCT anonymous_id) as employee_count,
            AVG(base_salary) as avg_salary,
            AVG(bonus) as avg_bonus,
            AVG(base_salary + bonus) as avg_total_comp,
            AVG(stock_options) as avg_stock_options
        FROM {catalog_name}.{schema_name}.data_analyst_view
        WHERE base_salary IS NOT NULL
        GROUP BY department
    );
""")

