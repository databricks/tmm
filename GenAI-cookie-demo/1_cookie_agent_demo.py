# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC #Part 1: Function/Tool Creation in Unity Catalog
# MAGIC V0 - First testing of GenAI Agent Demo
# MAGIC
# MAGIC You'll create two functions:
# MAGIC - A simple query to retrieve an ID based on a city name
# MAGIC - An aggregate query that returns sales data for a given ID
# MAGIC
# MAGIC Then create an Agent that can execute this.

# COMMAND ----------

# MAGIC %pip install langchain-community==0.2.16 langchain-openai==0.1.19 mlflow==2.15.1 databricks-agents==0.5.0 langchain==0.2.16
# MAGIC %restart_python

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

import mlflow
import langchain

# This is going to allow us to understand what happens during every part of the agent's execution
mlflow.langchain.autolog(disable=False)

# COMMAND ----------

from langchain_community.tools.databricks import UCFunctionToolkit
from databricks.sdk import WorkspaceClient
import pandas as pd

w = WorkspaceClient()

# Ideally grab user warehouse but fallback to anything else available
# The warehouse is going to be used in order to reference what functions are in UC
def get_shared_warehouse():
    w = WorkspaceClient()
    warehouses = w.warehouses.list()
    for wh in warehouses:
        if wh.num_clusters > 0:
            return wh 
    raise Exception("Couldn't find any Warehouse to use. Please create a wh first to run the demo and add the id here")

wh_id = get_shared_warehouse().id

# This function will use the defined warehouse to get the functions from the catalog and schema
def get_tools():
    return (
        UCFunctionToolkit(warehouse_id=wh_id)
        # Include functions as tools using their qualified names.
        # You can use "{catalog_name}.{schema_name}.*" to get all functions in a schema.
        .include(f"{catalog_name}.{schema_name}.*")
        .get_tools())

# COMMAND ----------

from langchain_community.chat_models.databricks import ChatDatabricks

# We're going to use llama 3.1 because it's tool enabled and works great. Keep temp at 0 to make it more deterministic.
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-1-70b-instruct",
    temperature=0.0,
    streaming=False)

# COMMAND ----------

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatDatabricks

# This defines our agent's system prompt. Here we can tell it what we expect it to do and guide it on using specific functions. 

def get_prompt(history = [], prompt = None):
    if not prompt:
            prompt = """You are a helpful assistant for a global company that oversees cookie stores. Your task is to help store owners understand more about their products and sales metrics. You have the ability to execute functions as follows: 

            Use the franchise_by_city function to retrieve the franchiseID for a given city name.

            Use the franchise_sales function to retrieve the cookie sales for a given franchiseID.

    Make sure to call the function for each step and provide a coherent response to the user. Don't mention tools to your users. Don't skip to the next step without ensuring the function was called and a result was retrieved. Only answer what the user is asking for."""
    return ChatPromptTemplate.from_messages([
            ("system", prompt),
            ("human", "{messages}"),
            ("placeholder", "{agent_scratchpad}"),
    ])

# COMMAND ----------

from langchain.agents import AgentExecutor, create_openai_tools_agent, Tool, load_tools

prompt = get_prompt()
tools = get_tools()
agent = create_openai_tools_agent(llm, tools, prompt)

# Here we're collecting the defined pieces and putting them together to create our Agent
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# COMMAND ----------

from operator import itemgetter
from langchain.schema.runnable import RunnableLambda
from langchain_core.output_parsers import StrOutputParser

# Very basic chain that allows us to pass the input (messages) into the Agent and collect the (output) as a string
agent_str = ({ "messages": itemgetter("messages")} | agent_executor | itemgetter("output") | StrOutputParser() )

# COMMAND ----------

# Lets ask our Compound AI Agent to generate an Instagram post. This requires it to:
#     1. Look up what stores are in Seattle
#     2. Use sales data to look up the best selling cookie at that store

answer=agent_str.invoke({"messages": "What is the best selling cookie in our Seattle stores?"})
