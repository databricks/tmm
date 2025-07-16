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

# DBTITLE 1,Parameter Configs
from databricks.sdk import WorkspaceClient
import yaml
import os

# Use the workspace client to retrieve information about the current user
w = WorkspaceClient()
user_email = w.current_user.me().display_name
username = user_email.split("@")[0]

# Catalog and schema have been automatically created thanks to lab environment
catalog_name = f"{username}"
schema_name = "agents"

# Allows us to reference these values when creating SQL/Python functions
dbutils.widgets.text("catalog_name", defaultValue=catalog_name, label="Catalog Name")
dbutils.widgets.text("schema_name", defaultValue=schema_name, label="Schema Name")

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
# MAGIC FROM agents_lab.product.cust_service_data 
# MAGIC -- Order the results by the interaction date and time in descending order
# MAGIC ORDER BY date_time DESC
# MAGIC -- Limit the results to the most recent interaction
# MAGIC LIMIT 1

# COMMAND ----------

# DBTITLE 1,Create a function registered to Unity Catalog
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION 
# MAGIC   IDENTIFIER(:catalog_name || '.' || :schema_name || '.get_latest_return')()
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

# DBTITLE 1,Test function call to retrieve latest return
# MAGIC %sql
# MAGIC select * from IDENTIFIER(:catalog_name || '.' || :schema_name || '.get_latest_return')()

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
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC   IDENTIFIER(:catalog_name || '.' || :schema_name || '.get_return_policy')()
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

# DBTITLE 1,Test function to retrieve return policy
# MAGIC %sql
# MAGIC select * from IDENTIFIER(:catalog_name || '.' || :schema_name || '.get_return_policy')()

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 3. Use the User Name to Look Up the Order History
# MAGIC - **Action**: Query your order management system or customer database using the Username.  
# MAGIC - **Why**: Reviewing past purchases, return patterns, and any specific notes helps you determine appropriate next steps (e.g., confirm eligibility for return).
# MAGIC
# MAGIC ###### Note: We've doing a little trick to give the LLM extra context into the current date by adding todays_date in the function's response
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Create function that retrieves order history based on userID
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC   IDENTIFIER(:catalog_name || '.' || :schema_name || '.get_order_history')(user_name STRING)
# MAGIC RETURNS TABLE (returns_last_12_months INT, issue_category STRING, todays_date DATE)
# MAGIC COMMENT 'This takes the user_name of a customer as an input and returns the number of returns and the issue category'
# MAGIC LANGUAGE SQL
# MAGIC RETURN 
# MAGIC SELECT count(*) as returns_last_12_months, issue_category, now() as todays_date
# MAGIC FROM agents_lab.product.cust_service_data 
# MAGIC WHERE name = user_name 
# MAGIC GROUP BY issue_category;

# COMMAND ----------

# DBTITLE 1,Test function that retrieves order history based on userID
# MAGIC %sql
# MAGIC select * from IDENTIFIER(:catalog_name || '.' || :schema_name || '.get_order_history')('Nicolas Pelaez')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 4. Python functions can be used as well! Here's an example
# MAGIC - **Action**: Provide a **Python function** that can supply the Large Language Model (LLM) with the current date.  
# MAGIC - **Why**: Automating date retrieval helps in scheduling pickups, refund timelines, and communication deadlines.
# MAGIC
# MAGIC ###### Note: For this lab we will not be using this function but leaving as example.
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
#python_tool_uc_info = client.create_python_function(func=get_todays_date, catalog=catalog_name, schema=schema_name, replace=True)

# the tool will deploy to a function in UC called `{catalog}.{schema}.{func}` where {func} is the name of the function
# Print the deployed Unity Catalog function name
#print(f"Deployed Unity Catalog function name: {python_tool_uc_info.full_name}")

# COMMAND ----------

# DBTITLE 1,Let's take a look at our created functions
from IPython.display import display, HTML

# Retrieve the Databricks host URL
workspace_url = spark.conf.get('spark.databricks.workspaceUrl')

# Create HTML link to created functions
html_link = f'<a href="https://{workspace_url}/explore/data/functions/{catalog_name}/{schema_name}/get_order_history" target="_blank">Go to Unity Catalog to see Registered Functions</a>'
display(HTML(html_link))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Now lets go over to the AI Playground to see how we can use these functions and assemble our first Agent!
# MAGIC
# MAGIC ### The AI Playground can be found on the left navigation bar under 'AI/ML' or you can use the link created below

# COMMAND ----------

# DBTITLE 1,Create link to AI Playground
# Create HTML link to AI Playground
html_link = f'<a href="https://{workspace_url}/ml/playground" target="_blank">Go to AI Playground</a>'
display(HTML(html_link))
