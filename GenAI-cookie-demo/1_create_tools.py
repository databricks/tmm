# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC #Part 1: Function/Tool Creation in Unity Catalog
# MAGIC In this notebook, we're going to create functions that query our data to accomplish some relatively basic tasks. The goal is to have some functions that we can pass along to an agent in order to help it answer questions using data stored in Databricks.
# MAGIC
# MAGIC You'll create three functions:
# MAGIC - A simple query to retrieve an ID based on a city name
# MAGIC - An aggregate query that returns sales data for a given ID
# MAGIC - A vector search function that queries a Vector Search endpoint to retrieve data similar to a given input string
# MAGIC
# MAGIC It is assumed that data lives in the agents_shared_catalog and that the 'sales' and 'media' schemas exist and can be accessed. These functions will be registered into a catalog and schema that will be unique to your username.

# COMMAND ----------

# DBTITLE 1,Define User Specific Parameters
from databricks.sdk import WorkspaceClient
import yaml
import os

# Use the workspace client to retrieve information about the current user
w = WorkspaceClient()
user_email = w.current_user.me().display_name
username = user_email.split("@")[0]

# Catalog and schema have been automatically created thanks to lab environment
catalog_name = f"{username}"
schema_name = "ai"

# Allows us to reference these values directly in the SQL/Python function creation
dbutils.widgets.text("catalog_name", defaultValue=catalog_name, label="Catalog Name")
dbutils.widgets.text("schema_name", defaultValue=schema_name, label="Schema Name")

# Save to config.yaml for use in following steps
config_data = {
    "catalog_name": catalog_name,
    "schema_name": schema_name
}

with open("config.yaml", "w") as file:
    yaml.dump(config_data, file)

# COMMAND ----------

# DBTITLE 1,Ensure Catalog and Schema Exist
# MAGIC %sql
# MAGIC --Sometimes this cell runs too fast - if it errors just try running it again
# MAGIC USE CATALOG ${catalog_name};
# MAGIC CREATE SCHEMA IF NOT EXISTS ${schema_name};

# COMMAND ----------

# DBTITLE 1,Create Franchise by City Function
# MAGIC %sql
# MAGIC -- First lets make sure it doesnt already exist
# MAGIC DROP FUNCTION IF EXISTS ${catalog_name}.${schema_name}.franchise_by_city;
# MAGIC -- Now we create our first function. This takes in a city name and returns a table of any franchises that are in that city.
# MAGIC -- Note that we've added a comment to the input parameter to help guide the agent later on.
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC ${catalog_name}.${schema_name}.franchise_by_city (
# MAGIC   city_name STRING COMMENT 'City to be searched'
# MAGIC )
# MAGIC returns table(franchiseID BIGINT, name STRING, size STRING)
# MAGIC return
# MAGIC (SELECT franchiseID, name, size from samples.bakehouse.sales_franchises where city=city_name 
# MAGIC      order by size desc)
# MAGIC

# COMMAND ----------

# DBTITLE 1,Test Franchise by City Function
# MAGIC %sql
# MAGIC -- Test the function we just created
# MAGIC SELECT * from ${catalog_name}.${schema_name}.franchise_by_city('Seattle')

# COMMAND ----------

# DBTITLE 1,Create Sales Function
# MAGIC %sql
# MAGIC -- Again check that it exists
# MAGIC DROP FUNCTION IF EXISTS ${catalog_name}.${schema_name}.franchise_sales;
# MAGIC -- This function takes an ID as input, and this time does an aggregate to return the sales for that franchise_id.
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC ${catalog_name}.${schema_name}.franchise_sales (
# MAGIC   franchise_id BIGINT COMMENT 'ID of the franchise to be searched'
# MAGIC )
# MAGIC returns table(total_sales BIGINT, total_quantity BIGINT, product STRING)
# MAGIC return
# MAGIC (SELECT SUM(totalPrice) AS total_sales, SUM(quantity) AS total_quantity, product 
# MAGIC FROM samples.bakehouse.sales_transactions 
# MAGIC WHERE franchiseID = franchise_id GROUP BY product)

# COMMAND ----------

# DBTITLE 1,Test Sales Function
# MAGIC %sql
# MAGIC -- Check the sales function works - we're going to use the franchise_id from the previous query
# MAGIC Select * from ${catalog_name}.${schema_name}.franchise_sales(3000038)

# COMMAND ----------

# DBTITLE 1,Create Python Function to call Vector Search via AI Query
# MAGIC %sql
# MAGIC
# MAGIC --IMPORTANT NOTE: You must attach to the SQL Warehouse to define this function (lab enviornment limitation)
# MAGIC
# MAGIC CREATE OR REPLACE FUNCTION ${catalog_name}.${schema_name}.franchise_reviews(query STRING)
# MAGIC RETURNS TABLE (reviews STRING)
# MAGIC LANGUAGE SQL
# MAGIC COMMENT 'Returns customer reviews for each franchise rating the store, the staff, and the product'
# MAGIC RETURN SELECT chunked_text as reviews FROM VECTOR_SEARCH(index => "agents_shared_catalog.media.vs_cookie_index", query => query, num_results => 2);

# COMMAND ----------

# DBTITLE 1,Test Vector Search Function
# MAGIC %sql
# MAGIC -- Test to see if our vector search function works. We'll use a phrase for a cookie at a specific store
# MAGIC Select * from ${catalog_name}.${schema_name}.franchise_reviews('Outback Oatmeal cookies Seattle')

# COMMAND ----------

# DBTITLE 1,Create Python Function to call Vector Search API
import os

# Get the Databricks host URL from the environment variable
host = "https://" + spark.conf.get("spark.databricks.workspaceUrl")
# Check to see if function exists - if it does drop it
spark.sql(f'DROP FUNCTION IF EXISTS {catalog_name}.{schema_name}.cookie_reviews_with_secret;')
# We often create Python functions using SQL so that we can easily pass variables in during creation time. Generally, it's easier to use SQL for all UC function creation.
# You'll notice that we have two inputs here: short_description and databricks_token.
# short_description is going to be the phrase that the Agent is going to pass in that we want to search against in our Vector Search Index 
# databricks_token is going to be passed in so that the Agent can authenticate against the API. 

# Important note: Currently an agent executing Python functions cannot reference secrets within a python function. This will likely be fixed in the fullness of time. This is why we're passing the token in as an input variable.

spark.sql(f'''
CREATE OR REPLACE FUNCTION {catalog_name}.{schema_name}.cookie_reviews_with_secret (short_description STRING, databricks_token STRING)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Returns customer reviews for cookies rating the store, the staff, and the product'
AS
$$
  try:
    import requests
    headers = {{"Authorization": "Bearer "+databricks_token}}
    # Call our vector search endpoint via API
    response = requests.get("{host}/api/2.0/vector-search/indexes/agents_shared_catalog.media.vs_cookie_index/query", params ={{"columns":"chunked_text","query_text":short_description, "num_results":1}}, headers=headers).json()

    chunked_texts = [entry[0] for entry in response['result']['data_array']]
    return "Relevant Reviews: " .join(chunked_texts)
  except Exception as e:
    return f"Error calling the vs index {{e}}"
$$;''')

# COMMAND ----------

# DBTITLE 1,Create Wrapper Function for Vector Search Function
# MAGIC %sql
# MAGIC -- Check if function exists
# MAGIC DROP FUNCTION IF EXISTS ${catalog_name}.${schema_name}.franchise_reviews_api;
# MAGIC
# MAGIC -- This SQL function simply calls that Python function (cookie_reviews_with_secret) and passes in the short_description and a token that it retrieves from a secret scope.
# MAGIC -- The secret has been created for you in the lab environment.
# MAGIC -- We only need to create this wrapper function because the agent can only call the "secret()" function from SQL, so we're making that call here and passing that as an input variable to the python function.
# MAGIC
# MAGIC CREATE OR REPLACE FUNCTION ${catalog_name}.${schema_name}.franchise_reviews_api (short_description STRING)
# MAGIC RETURNS TABLE (reviews STRING)
# MAGIC LANGUAGE SQL
# MAGIC COMMENT 'Returns customer reviews for each franchise rating the store, the staff, and the product'
# MAGIC RETURN SELECT ${catalog_name}.${schema_name}.cookie_reviews_with_secret(short_description,  secret('dbdemos', 'llm-agent-tools'));
