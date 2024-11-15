# Databricks notebook source
# MAGIC %md 
# MAGIC # AI-Driven Data Intelligence for Smarter Cookie Franchises
# MAGIC
# MAGIC Welcome to this demo, where you’ll build a powerful AI agent tailored for a cookie franchise business. This agent is designed to empower franchise owners to analyze customer data, create targeted marketing campaigns, and develop data-driven sales strategies that improve their operations.
# MAGIC
# MAGIC By using data intelligence rather than generic insights, franchises can understand top-selling products and create campaigns based on actual sales data.
# MAGIC
# MAGIC This notebook will guide you through creating and registering simple functions in Unity Catalog, providing governed access to insights. You'll then build a chat-based AI using these functions, enabling franchises to develop smarter, data-driven campaigns.
# MAGIC
# MAGIC Here's what we'll cover:
# MAGIC
# MAGIC - Creating and registering SQL functions in Unity Catalog
# MAGIC - Using Langchain to integrate these functions as tools
# MAGIC - Building an AI agent to execute these tools and tackle complex questions

# COMMAND ----------

# MAGIC %pip install -q langchain-community==0.2.16 langchain-openai==0.1.19 mlflow==2.15.1 databricks-agents==0.5.0 langchain==0.2.16
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Step 1: Function/Tool Creation in Unity Catalog
# MAGIC
# MAGIC You'll create two functions:
# MAGIC - A simple query to retrieve an ID based on a city name
# MAGIC - An aggregate query that returns sales data for a given ID

# COMMAND ----------

# DBTITLE 1,Create Franchise by City Function
# MAGIC %sql
# MAGIC -- First lets make sure it doesnt already exist
# MAGIC DROP FUNCTION IF EXISTS workspace.default.franchise_by_city;
# MAGIC -- Now we create our first function. This takes in a city name and returns a table of any franchises that are in that city.
# MAGIC -- Note that we've added a comment to the input parameter to help guide the agent later on.
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC workspace.default.franchise_by_city(
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
# MAGIC SELECT * from workspace.default.franchise_by_city('Seattle')

# COMMAND ----------

# DBTITLE 1,Create Sales Function
# MAGIC %sql
# MAGIC -- Again check that it exists
# MAGIC DROP FUNCTION IF EXISTS workspace.default.franchise_sales;
# MAGIC -- This function takes an ID as input, and this time does an aggregate to return the sales for that franchise_id.
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC workspace.default.franchise_sales (
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
# MAGIC Select * from workspace.default.franchise_sales(3000038)

# COMMAND ----------

import mlflow
import langchain

# This is going to allow us to understand what happens during every part of the agent's execution
mlflow.langchain.autolog(disable=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Agent
# MAGIC
# MAGIC In this step, we're going to define three cruicial parts of our agent:
# MAGIC - Tools for the Agent to use
# MAGIC - LLM to serve as the agent's "brains"
# MAGIC - System prompt that defines guidelines for the agent's tasks

# COMMAND ----------

from langchain_community.tools.databricks import UCFunctionToolkit
from databricks.sdk import WorkspaceClient
import pandas as pd
import time

w = WorkspaceClient()

def get_shared_warehouse():
    w = WorkspaceClient()
    warehouses = w.warehouses.list()
    for wh in warehouses:
        if wh.name == "Serverless Starter Warehouse":
            if wh.num_clusters == 0:
                w.warehouses.start(wh.id)
                time.sleep(5)
                return wh
            else:
                return wh 
    raise Exception("Couldn't find any Warehouse to use. Please start the serverless SQL Warehouse for this code to run.")
    
wh_id = get_shared_warehouse().id

def get_tools():
    return (
        UCFunctionToolkit(warehouse_id=wh_id)
        .include("workspace.default.*")
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

            Use the franchise_sales function to retrieve the cookie sales for a given franchiseID. This should be run for each franchiseID. Do not ask the user if they want to see another store, just run it for ALL franchiseIDs.

    Make sure to call the function for each step and provide a coherent final response to the user. Don't mention tools to your users. Don't skip to the next step without ensuring the function was called and a result was retrieved. Only answer what the user is asking for."""
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

# COMMAND ----------

# MAGIC %md
# MAGIC ## Excited for more?
# MAGIC
# MAGIC - Catch the full demo in action [here](https://www.youtube.com/watch?v=UfbyzK488Hk&t=3501s). 
# MAGIC - Take the next step and build a [RAG-based chatbot](https://www.databricks.com/resources/demos/tutorials/data-science-and-ai/lakehouse-ai-deploy-your-llm-chatbot?itm_data=demo_center) with added contextual depth!
