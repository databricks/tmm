# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC #Part 2: Agent Creation
# MAGIC In this notebook, we're going to create an agent that can make use of the functions we created in part 1. For this, we need to define roughly the following parts:
# MAGIC
# MAGIC - Configure Langchain: Set up Langchain to work with your tools.
# MAGIC - Integrate with Foundation Model API: Use Databricks' LLMs to empower your agent.
# MAGIC - Combine Tools with LLM: Enable the LLM to access and execute your registered tools.
# MAGIC - Create Evaluation Agent: Use an Agent to call another Agent and evaluate/iterate until satisfied.

# COMMAND ----------

# MAGIC %pip install langchain-community==0.2.16 langchain-openai==0.1.19 mlflow==2.15.1 databricks-agents==0.5.0 langchain==0.2.16
# MAGIC %restart_python

# COMMAND ----------

# DBTITLE 1,Enable MLflow Tracking
import mlflow
import langchain

# This is going to allow us to understand what happens during every part of the agent's execution
mlflow.langchain.autolog(disable=False)

# COMMAND ----------

# DBTITLE 1,Grab User Configs
import os
import yaml

# config file created in 1_create_tools
with open("config.yaml", "r") as file:
    config_data = yaml.safe_load(file)
    
# Catalog and schema have been created in 1_create_tools

catalog_name = config_data["catalog_name"]
schema_name = config_data["schema_name"]

# COMMAND ----------

# DBTITLE 1,Gather Tools from Unity Catalog
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

# DBTITLE 1,Define LLM to power Agent
from langchain_community.chat_models.databricks import ChatDatabricks

# We're going to use llama 3.1 because it's tool enabled and works great. Keep temp at 0 to make it more deterministic.
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-1-70b-instruct",
    temperature=0.0,
    streaming=False)

# COMMAND ----------

# DBTITLE 1,Define System Prompt
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatDatabricks

# This defines our agent's system prompt. Here we can tell it what we expect it to do and guide it on using specific functions. 

def get_prompt(history = [], prompt = None):
    if not prompt:
            prompt = """You are a helpful assistant for a global company that oversees cookie stores. Your task is to help store owners understand more about their products and sales metrics and help create social media posts to promote stores. You have the ability to execute functions as follows: 

            Use the franchise_by_city function to retrieve the franchiseID for a given city name.

            Use the franchise_sales function to retrieve the cookie sales for a given franchiseID.

            Use the franchise_reviews function to retrieve relevant customer reviews by providing a short description. Make direct references to a product name and store location.
            
        If you don't retrieve a franchiseID, respond that the franchise or store does not exist.

    Make sure to call the function for each step and provide a coherent response to the user. Don't mention tools to your users. Don't skip to the next step without ensuring the function was called and a result was retrieved. Only answer what the user is asking for."""
    return ChatPromptTemplate.from_messages([
            ("system", prompt),
            ("human", "{messages}"),
            ("placeholder", "{agent_scratchpad}"),
    ])

# COMMAND ----------

# DBTITLE 1,Combine LLM, Tools, and System Prompt into an Agent
from langchain.agents import AgentExecutor, create_openai_tools_agent, Tool, load_tools

prompt = get_prompt()
tools = get_tools()
agent = create_openai_tools_agent(llm, tools, prompt)

# Here we're collecting the defined pieces and putting them together to create our Agent
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# COMMAND ----------

# DBTITLE 1,Define Agent Architecture
from operator import itemgetter
from langchain.schema.runnable import RunnableLambda
from langchain_core.output_parsers import StrOutputParser

# Very basic chain that allows us to pass the input (messages) into the Agent and collect the (output) as a string
agent_str = ({ "messages": itemgetter("messages")} | agent_executor | itemgetter("output") | StrOutputParser() )

# COMMAND ----------

# DBTITLE 1,Launch Agent!
# Lets ask our Compound AI Agent to generate an Instagram post. This requires it to:
#     1. Look up what stores are in Seattle
#     2. Use sales data to look up the best selling cookie at that store
#     3. Look up reviews for that specific cookie at that store
#     4. Use the retrieved reviews, summarize them, and generate a post

answer=agent_str.invoke({"messages": "Create a social media post that promotes the best selling cookie for our Seattle store while showing we listen to customer feedback. "})

# COMMAND ----------

# DBTITLE 1,Build Eval Agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatDatabricks

# This defines our agent's system prompt. Here we can tell it what we expect it to do and guide it on using specific functions. 

def get_eval_prompt(history = [], prompt = None):
    if not prompt:
            prompt = """You are a helpful AI assistant created to evaluate the work of an AI agent. Your job is to call this agent, which will retrieve information related to various metrics around a cookie franchise and use this information to craft a custom social media post. 

            You can invoke this agent by calling the cookie_agent() tool and passing it a message that includes the store details such as city. Here is an example message:
            
            "messages": "Create a social media post that promotes the best selling cookie for our Seattle store while showing we listen to customer feedback. "
            
            The final result should be a social media post that is specific to the cookie franchise and importantly also makes a reference to our new mobile app for a discount.

        Check the following social media post to see if it mentions our mobile app. If it doesn't, please call the cookie_agent() again until you get a post that does mention our mobile app.

        If the post is good, please let just respond with the final social media post.

        Return only a final social media post.

"""
    return ChatPromptTemplate.from_messages([
            ("system", prompt),
            ("human", "{messages}"),
            ("placeholder", "{agent_scratchpad}"),
    ])

# COMMAND ----------

# DBTITLE 1,Create Tool out of Agent
from langchain.tools import StructuredTool

def cookie_agent(messages: str) -> str:
    """Call cookie agent to get stuff"""
    return agent_str.invoke({"messages": messages})

def get_eval_tools():
    tool = StructuredTool.from_function(
        func=cookie_agent,
        name="cookie_agent",
        description="Useful to pull information for cookies and build a nice marketing social media post",
    )
    return [tool]

# COMMAND ----------

from langchain.agents import create_tool_calling_agent

prompt = get_eval_prompt()
tools = get_eval_tools()
agent = create_openai_tools_agent(llm, tools, prompt)

# Here we're collecting the defined pieces and putting them together to create our Agent
eval_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# COMMAND ----------

eval_executor.invoke({"messages": "Create a social media post that promotes the best selling cookie for our Seattle store while showing we listen to customer feedback. "})

# COMMAND ----------

# DBTITLE 1,MLflow Logging
# Tell MLflow logging where to find your chain. This is needed when logging a model as code. 
mlflow.models.set_model(model=eval_executor)
