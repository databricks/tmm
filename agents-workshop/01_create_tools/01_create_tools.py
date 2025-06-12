# Databricks notebook source
# MAGIC %md
# MAGIC # Hands-On Lab: Building Agent Systems with Databricks
# MAGIC
# MAGIC ## Part 1 - Architect Your First Agent
# MAGIC This first agent will follow the workflow of a customer service representative to illustrate the various agent capabilites. 
# MAGIC We'll focus around processing product returns as this gives us a tangible set of steps to follow.
# MAGIC
# MAGIC ### 1.1 Build Simple Tools
# MAGIC - **SQL Functions**: Create queries that access data critical to steps in the customer service workflow for processing a return.
# MAGIC - **Simple Python Function**: Create and register a Python function to overcome some common limitations of language models.
# MAGIC
# MAGIC ### 1.2 Integrate with an LLM [AI Playground]
# MAGIC - Combine the tools you created with a Language Model (LLM) in the AI Playground.
# MAGIC
# MAGIC ### 1.3 Test the Agent [AI Playground]
# MAGIC - Ask the agent a question and observe the response.
# MAGIC - Dive deeper into the agent’s performance by exploring MLflow traces.
# MAGIC

# COMMAND ----------

# DBTITLE 1,Library Installs
# MAGIC %pip install -qqqq -U -r requirements.txt
# MAGIC # Restart to load the packages into the Python environment
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %sql
# MAGIC

# COMMAND ----------

import urllib
import os
from databricks.sdk.service import catalog

catalog_name = "marion_test"
schema_name = "agents"
volume = "data"

files = ['browsing_history', 'customers', 'email_logs', 'products_agents', 'purchases']
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog_name}.{schema_name}.{volume}")
base_url = 'https://raw.githubusercontent.com/databricks/tmm/main/agents-workshop/data/'


for d in files:
  file_name = d+'.csv'
  url = base_url+file_name
  urllib.request.urlretrieve(url, f'/Volumes/{catalog_name}/{schema_name}/{volume}/{file_name}')
  df_csv = spark.read.csv(f'/Volumes/{catalog_name}/{schema_name}/{volume}/{file_name}',
    header=True,
    sep=",")
  df_csv.write.option("mergeSchema", "true").mode("append").saveAsTable(f'{catalog_name}.{schema_name}.{d}')
  display(df_csv)


# COMMAND ----------

# DBTITLE 1,Parameter Configs
from databricks.sdk import WorkspaceClient
import yaml
import os

# Use the workspace client to retrieve information about the current user
w = WorkspaceClient()
user_email = w.current_user.me().display_name
username = user_email.split("@")[0]

# Catalog and schema have been automatically created thanks to lab environment
#catalog_name = f"{username}_vocareum_com"
catalog_name = "marion_test"
schema_name = "agents"

workspace_id = str(w.get_workspace_id())

# Allows us to reference these values directly in the SQL/Python function creation
dbutils.widgets.text("catalog_name", defaultValue=catalog_name, label="Catalog Name")
dbutils.widgets.text("schema_name", defaultValue=schema_name, label="Schema Name")
dbutils.widgets.text("workspace_id", defaultValue=workspace_id, label="Workspace ID")

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.{schema_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC # Customer Service Return Processing Workflow
# MAGIC
# MAGIC Below is a structured outline of the **key steps** a customer service agent would typically follow when **processing a return**. This workflow ensures consistency and clarity across your support team.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 1. Get the Latest Return in the Processing Queue
# MAGIC - **Action**: Identify and retrieve the most recent return request from the ticketing or returns system.  
# MAGIC - **Why**: Ensures you’re working on the most urgent or next-in-line customer issue.
# MAGIC
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Get the Latest Return in the Processing Queue
# MAGIC %sql
# MAGIC -- Select the date of the interaction, issue category, issue description, and customer name
# MAGIC SELECT 
# MAGIC   cast(date_time as date) as case_time, 
# MAGIC   issue_category, 
# MAGIC   issue_description, 
# MAGIC   name
# MAGIC FROM ${catalog_name}.${schema_name}.cust_service_data 
# MAGIC -- Order the results by the interaction date and time in descending order
# MAGIC ORDER BY date_time DESC
# MAGIC -- Limit the results to the most recent interaction
# MAGIC LIMIT 1

# COMMAND ----------

# DBTITLE 1,Create a function registered to Unity Catalog
# MAGIC %sql
# MAGIC -- First lets make sure it doesnt already exist
# MAGIC DROP FUNCTION IF EXISTS ${catalog_name}.${schema_name}.get_latest_return;
# MAGIC -- Now we create our first function. This takes in no parameters and returns the most recent interaction.
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC ${catalog_name}.${schema_name}.get_latest_return()
# MAGIC returns table(purchase_date DATE, issue_category STRING, issue_description STRING, name STRING)
# MAGIC COMMENT 'Returns the most recent customer service interaction, such as returns.'
# MAGIC return
# MAGIC (
# MAGIC   SELECT 
# MAGIC     cast(date_time as date) as purchase_date, 
# MAGIC     issue_category, 
# MAGIC     issue_description, 
# MAGIC     name
# MAGIC   FROM ${catalog_name}.${schema_name}.cust_service_data 
# MAGIC   ORDER BY date_time DESC
# MAGIC   LIMIT 1
# MAGIC )

# COMMAND ----------

# DBTITLE 1,Test function call to retrieve latest return
# MAGIC %sql
# MAGIC select * from ${catalog_name}.${schema_name}.get_latest_return()

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 2. Retrieve Company Policies
# MAGIC - **Action**: Access the internal knowledge base or policy documents related to returns, refunds, and exchanges.  
# MAGIC - **Why**: Verifying you’re in compliance with company guidelines prevents potential errors and conflicts.
# MAGIC
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Create function to retrieve return policy
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION ${catalog_name}.${schema_name}.get_return_policy()
# MAGIC RETURNS TABLE (policy STRING, policy_details STRING, last_updated DATE)
# MAGIC COMMENT 'Returns the details of the Return Policy'
# MAGIC LANGUAGE SQL
# MAGIC RETURN 
# MAGIC SELECT policy, policy_details, last_updated 
# MAGIC FROM ${catalog_name}.${schema_name}.policies
# MAGIC WHERE policy = 'Return Policy'
# MAGIC LIMIT 1;

# COMMAND ----------

# DBTITLE 1,Test function to retrieve return policy
# MAGIC %sql
# MAGIC select * from ${catalog_name}.${schema_name}.get_return_policy()

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 3. Retrieve UserID for the Latest Return
# MAGIC - **Action**: Note the user’s unique identifier from the return request details.  
# MAGIC - **Why**: Accurately referencing the correct user’s data streamlines the process and avoids mixing up customer records.
# MAGIC
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Create function that retrieves userID based on name
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION ${catalog_name}.${schema_name}.get_user_id(user_name STRING)
# MAGIC RETURNS STRING
# MAGIC COMMENT 'This takes the name of a customer as an input and returns the corresponding user_id'
# MAGIC LANGUAGE SQL
# MAGIC RETURN 
# MAGIC SELECT customer_id 
# MAGIC FROM ${catalog_name}.${schema_name}.cust_service_data 
# MAGIC WHERE name = user_name
# MAGIC LIMIT 1
# MAGIC ;

# COMMAND ----------

# DBTITLE 1,Test function that retrieves userID based on name
# MAGIC %sql
# MAGIC select ${catalog_name}.${schema_name}.get_user_id('Nicolas Pelaez')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 4. Use the UserID to Look Up the Order History
# MAGIC - **Action**: Query your order management system or customer database using the UserID.  
# MAGIC - **Why**: Reviewing past purchases, return patterns, and any specific notes helps you determine appropriate next steps (e.g., confirm eligibility for return).
# MAGIC
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Create function that retrieves order history based on userID
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION ${catalog_name}.${schema_name}.get_order_history(user_id STRING)
# MAGIC RETURNS TABLE (returns_last_12_months INT, issue_category STRING)
# MAGIC COMMENT 'This takes the user_id of a customer as an input and returns the number of returns and the issue category'
# MAGIC LANGUAGE SQL
# MAGIC RETURN 
# MAGIC SELECT count(*) as returns_last_12_months, issue_category 
# MAGIC FROM ${catalog_name}.${schema_name}.cust_service_data 
# MAGIC WHERE customer_id = user_id 
# MAGIC GROUP BY issue_category;

# COMMAND ----------

# DBTITLE 1,Test function that retrieves order history based on userID
# MAGIC %sql
# MAGIC select * from ${catalog_name}.${schema_name}.get_order_history('453e50e0-232e-44ea-9fe3-28d550be6294')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 5. Give the LLM a Python Function to Know Today’s Date
# MAGIC - **Action**: Provide a **Python function** that can supply the Large Language Model (LLM) with the current date.  
# MAGIC - **Why**: Automating date retrieval helps in scheduling pickups, refund timelines, and communication deadlines.
# MAGIC
# MAGIC ###### Note: There is also a function registered in System.ai.python_exec that will let your LLM run generated code in a sandboxed environment
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Very simple Python function
def get_todays_date() -> str:
    """
    Returns today's date in 'YYYY-MM-DD' format.

    Returns:
        str: Today's date in 'YYYY-MM-DD' format.
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

# COMMAND ----------

# DBTITLE 1,Test python function
today = get_todays_date()
today

# COMMAND ----------

# DBTITLE 1,Register python function to Unity Catalog
from unitycatalog.ai.core.databricks import DatabricksFunctionClient

client = DatabricksFunctionClient()

# this will deploy the tool to UC, automatically setting the metadata in UC based on the tool's docstring & typing hints
python_tool_uc_info = client.create_python_function(func=get_todays_date, catalog=catalog_name, schema=schema_name, replace=True)

# the tool will deploy to a function in UC called `{catalog}.{schema}.{func}` where {func} is the name of the function
# Print the deployed Unity Catalog function name
print(f"Deployed Unity Catalog function name: {python_tool_uc_info.full_name}")

# COMMAND ----------

# DBTITLE 1,Let's take a look at our created functions
from IPython.display import display, HTML

# Retrieve the Databricks host URL
workspace_url = spark.conf.get('spark.databricks.workspaceUrl')

# Create HTML link to created functions
html_link = f'<a href="https://{workspace_url}/explore/data/functions/{catalog_name}/{schema_name}/get_todays_date" target="_blank">Go to Unity Catalog to see Registered Functions</a>'
display(HTML(html_link))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Now lets go over to the AI Playground to see how we can use these functions and assemble our first Agent!
# MAGIC
# MAGIC ### The AI Playground can be found on the left navigation bar under 'Machine Learning' or you can use the link created below

# COMMAND ----------

# DBTITLE 1,Create link to AI Playground
# Create HTML link to AI Playground
html_link = f'<a href="https://{workspace_url}/ml/playground" target="_blank">Go to AI Playground</a>'
display(HTML(html_link))
