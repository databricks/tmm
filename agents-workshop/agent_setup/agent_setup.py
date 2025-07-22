# Databricks notebook source
# MAGIC %pip install --quiet databricks-vectorsearch mlflow-skinny[databricks] langgraph==0.3.4 databricks-langchain databricks-agents uv
# MAGIC %restart_python

# COMMAND ----------

import requests
import pandas as pd
import io
import time
from databricks.sdk import WorkspaceClient
from databricks.vector_search.client import VectorSearchClient

# Initialize clients
w = WorkspaceClient()
client = VectorSearchClient()

base_url = "https://raw.githubusercontent.com/databricks/tmm/main/agents-workshop/data"
csv_files = {
    "cust_service_data": f"{base_url}/cust_service_data.csv",
    "policies": f"{base_url}/policies.csv", 
    "product_docs": f"{base_url}/product_docs.csv"
} 

# Create catalog if not exists
spark.sql("CREATE CATALOG IF NOT EXISTS agents_lab")

# Create schema if not exists
spark.sql("CREATE SCHEMA IF NOT EXISTS agents_lab.product")

# Download and load each CSV file
for table_name, url in csv_files.items():
    # Download CSV data
    response = requests.get(url)
    response.raise_for_status()
    
    # Read CSV into pandas DataFrame
    df = pd.read_csv(io.StringIO(response.text))
    
    # Convert to Spark DataFrame and write to table
    spark_df = spark.createDataFrame(df)
    spark_df.write.mode("overwrite").saveAsTable(f"agents_lab.product.{table_name}")

print("Tables created successfully")

# Step 1: Create Vector Search Endpoint
print("Creating vector search endpoint...")
try:
    # List existing endpoints
    endpoints = client.list_endpoints()
    endpoint_names = [ep['name'] for ep in endpoints.get('endpoints', [])]
    
    if "agents_endpoint" not in endpoint_names:
        endpoint = client.create_endpoint(
            name="agents_endpoint",
            endpoint_type="STANDARD"
        )
        print(f"Vector search endpoint 'agents_endpoint' created")
        
        # Wait for endpoint to be ready
        print("Waiting for endpoint to be ready...")
        max_wait_time = 600  # 10 minutes max
        wait_interval = 10
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            endpoint_info = client.get_endpoint("agents_endpoint")
            state = endpoint_info.get('endpoint_status', {}).get('state', 'UNKNOWN')
            
            print(f"Current endpoint state: {state}")
            
            if state in ["ONLINE", "PROVISIONED", "READY"]:
                print("Endpoint is ready")
                break
            elif state in ["FAILED", "OFFLINE"]:
                print(f"Endpoint failed to provision with state: {state}")
                break
                
            time.sleep(wait_interval)
            elapsed_time += wait_interval
        else:
            print(f"Timeout waiting for endpoint after {max_wait_time} seconds")
    else:
        print("Vector search endpoint 'agents_endpoint' already exists")
        
except Exception as e:
    print(f"Error creating vector search endpoint: {e}")

# Step 2: Enable CDC on product_docs table
print("Enabling CDC on product_docs table...")
try:
    # First, we need to ensure the table has the proper properties for CDC
    # Drop and recreate the table with CDC enabled
    spark.sql("""
        CREATE OR REPLACE TABLE agents_lab.product.product_docs (
            -- Define your schema here based on the CSV structure
            -- Placeholder columns - adjust based on actual CSV structure
            {COLUMN_DEFINITIONS}
        )
        USING DELTA
        TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true'
        )
    """)
    
    # Reload the data into the CDC-enabled table
    response = requests.get(csv_files["product_docs"])
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    spark_df = spark.createDataFrame(df)
    spark_df.write.mode("overwrite").saveAsTable("agents_lab.product.product_docs")
    
    print("CDC enabled on product_docs table")
    
except Exception as e:
    # Alternative approach: try to alter existing table
    try:
        spark.sql("""
            ALTER TABLE agents_lab.product.product_docs 
            SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
        """)
        print("CDC enabled on existing product_docs table")
    except Exception as alter_error:
        print(f"Error enabling CDC: {alter_error}")

# Step 3: Create Vector Search Index
print("Creating vector search index...")
try:
    # Create the vector search index using VectorSearchClient
    index = client.create_delta_sync_index(
        endpoint_name="agents_endpoint",
        source_table_name="agents_lab.product.product_docs",
        index_name="agents_lab.product.product_docs_index",
        pipeline_type="TRIGGERED",
        primary_key="product_id",
        embedding_source_column="indexed_doc",
        embedding_model_endpoint_name="databricks-gte-large-en"
    )
    
    print(f"Vector search index 'agents_lab.product.product_docs_index' created")
    
except Exception as e:
    print(f"Error creating vector search index: {e}")
    # If index already exists, this might fail
    print("Note: Index may already exist")

print("Setup complete!")

# Step 4: Grant all users access to the catalog
print("\nGranting all users access to agents_lab catalog...")
try:
    # Grant USE CATALOG permission to all users
    spark.sql("GRANT USE CATALOG ON CATALOG agents_lab TO `account users`")
    print("Granted USE CATALOG permission")
    
    # Grant USE SCHEMA permission on the product schema
    spark.sql("GRANT USE SCHEMA ON SCHEMA agents_lab.product TO `account users`")
    print("Granted USE SCHEMA permission")

    
    print("Successfully granted all users access to agents_lab catalog")
    
except Exception as e:
    print(f"Error granting permissions: {e}")
    # Try alternative syntax if the above fails
    try:
        spark.sql("GRANT USE CATALOG ON CATALOG agents_lab TO ALL USERS")
        spark.sql("GRANT USE SCHEMA ON SCHEMA agents_lab.product TO ALL USERS")
        print("Successfully granted permissions using alternative syntax")
    except Exception as alt_error:
        print(f"Alternative syntax also failed: {alt_error}")

# Optional: Verify the setup
print("\nVerifying setup...")
print("1. Checking tables:")
tables = spark.sql("SHOW TABLES IN agents_lab.product").collect()
for table in tables:
    print(f"   - {table.tableName}")

print("\n2. Checking CDC status on product_docs:")
try:
    properties = spark.sql("SHOW TBLPROPERTIES agents_lab.product.product_docs").collect()
    cdc_enabled = any(prop.key == 'delta.enableChangeDataFeed' and prop.value == 'true' for prop in properties)
    print(f"   CDC enabled: {cdc_enabled}")
except Exception as e:
    print(f"   Error checking CDC status: {e}")

print("\n3. Checking vector search endpoint:")
try:
    endpoint_info = client.get_endpoint("agents_endpoint")
    state = endpoint_info.get('endpoint_status', {}).get('state', 'UNKNOWN')
    print(f"   Endpoint status: {state}")
except Exception as e:
    print(f"   Error checking endpoint: {e}")

# COMMAND ----------

# MAGIC %pip install -U -qqqq mlflow-skinny[databricks] langgraph==0.3.4 databricks-langchain databricks-agents uv
# MAGIC %restart_python

# COMMAND ----------

# DBTITLE 1,Deploy Agent
from agent import AGENT

# Determine Databricks resources to specify for automatic auth passthrough at deployment time
import mlflow
from agent import tools, LLM_ENDPOINT_NAME
from databricks_langchain import VectorSearchRetrieverTool
from mlflow.models.resources import DatabricksFunction, DatabricksServingEndpoint
from unitycatalog.ai.langchain.toolkit import UnityCatalogTool

resources = [DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT_NAME)]
for tool in tools:
    if isinstance(tool, VectorSearchRetrieverTool):
        resources.extend(tool.resources)
    elif isinstance(tool, UnityCatalogTool):
        resources.append(DatabricksFunction(function_name=tool.uc_function_name))

input_example = {
    "messages": [
        {
            "role": "user",
            "content": "What color options are available for the Aria Modern Bookshelf?"
        }
    ]
}

with mlflow.start_run():
    logged_agent_info = mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model="agent.py",
        input_example=input_example,
        resources=resources,
        extra_pip_requirements=[
            "databricks-connect"
        ]
    )



# COMMAND ----------

from databricks.sdk import WorkspaceClient
import os

mlflow.set_registry_uri("databricks-uc")

# Use the workspace client to retrieve information about the current user
w = WorkspaceClient()

# Catalog and schema have been automatically created thanks to lab environment
catalog_name = "agents_lab"
schema_name = "product"

# TODO: define the catalog, schema, and model name for your UC model
model_name = "product_agent"
UC_MODEL_NAME = f"{catalog_name}.{schema_name}.{model_name}"

# register the model to UC
uc_registered_model_info = mlflow.register_model(model_uri=logged_agent_info.model_uri, name=UC_MODEL_NAME)

# COMMAND ----------

from databricks import agents

# Deploy the model to the review app and a model serving endpoint

#Disabled for the lab environment but we've deployed the agent already!
agents.deploy(UC_MODEL_NAME, uc_registered_model_info.version, tags = {"endpointSource": "Lab Admin"})

# COMMAND ----------

from mlflow.deployments import get_deploy_client

client = get_deploy_client("databricks")
endpoint = client.get_endpoint(endpoint="agents_agents_lab-product-product_agent")
print(endpoint.id)

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import iam

# Initialize the client
w = WorkspaceClient()
endpoint_id = endpoint.id  

# Method 1: Using serving_endpoints API
try:
    # Grant CAN_QUERY permission to all users
    w.serving_endpoints.set_permissions(
        serving_endpoint_id=endpoint_id,
        access_control_list=[
            iam.AccessControlRequest(
                group_name="users",
                permission_level=iam.PermissionLevel.CAN_QUERY
            )
        ]
    )
    print("Successfully set permissions!")
    
    # Verify
    perms = w.serving_endpoints.get_permissions(serving_endpoint_id=endpoint_id)
    print("\nCurrent permissions:")
    for p in perms.access_control_list:
        print(f"- {p.group_name or p.user_name}: {p.all_permissions}")
        
except Exception as e:
    print(f"Error: {str(e)}")

# Method 2: Using REST API directly (if SDK method fails)
import requests
import json

# Get your Databricks host and token
databricks_host = w.config.host
databricks_token = w.config.token  # or use your authentication method

if databricks_host and databricks_token:
    url = f"{databricks_host}/api/2.0/permissions/serving-endpoints/{endpoint_id}"
    headers = {
        "Authorization": f"Bearer {databricks_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "access_control_list": [
            {
                "group_name": "users",
                "permission_level": "CAN_QUERY"
            }
        ]
    }
    
    response = requests.patch(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 200:
        print("Successfully set permissions via REST API!")
    else:
        print(f"REST API Error: {response.status_code} - {response.text}")

# COMMAND ----------

# MAGIC %sql
# MAGIC GRANT USE CATALOG, USE SCHEMA, SELECT, EXECUTE ON CATALOG `agents_lab` TO `account users`

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION agents_lab.product.get_latest_return()
# MAGIC RETURNS TABLE(purchase_date DATE, issue_category STRING, issue_description STRING, name STRING)
# MAGIC COMMENT 'Returns the most recent customer service interaction, such as returns.'
# MAGIC RETURN (
# MAGIC   SELECT 
# MAGIC     CAST(date_time AS DATE) AS purchase_date,
# MAGIC     issue_category,
# MAGIC     issue_description,
# MAGIC     name
# MAGIC   FROM agents_lab.product.cust_service_data
# MAGIC   ORDER BY date_time DESC
# MAGIC   LIMIT 1
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION agents_lab.product.get_return_policy()
# MAGIC RETURNS TABLE (
# MAGIC   policy           STRING,
# MAGIC   policy_details   STRING,
# MAGIC   last_updated     DATE
# MAGIC )
# MAGIC COMMENT 'Returns the details of the Return Policy'
# MAGIC LANGUAGE SQL
# MAGIC RETURN (
# MAGIC   SELECT
# MAGIC     policy,
# MAGIC     policy_details,
# MAGIC     last_updated
# MAGIC   FROM agents_lab.product.policies
# MAGIC   WHERE policy = 'Return Policy'
# MAGIC   LIMIT 1
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION agents_lab.product.get_order_history(user_name STRING)
# MAGIC RETURNS TABLE (returns_last_12_months INT, issue_category STRING, todays_date DATE)
# MAGIC COMMENT 'This takes the name of a customer as an input and returns the number of returns and the issue category'
# MAGIC LANGUAGE SQL
# MAGIC RETURN 
# MAGIC SELECT count(*) as returns_last_12_months, issue_category, now() as todays_date
# MAGIC FROM agents_lab.product.cust_service_data 
# MAGIC WHERE name = user_name
# MAGIC GROUP BY issue_category;
