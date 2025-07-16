# Databricks notebook source
# MAGIC %md
# MAGIC # Hands-On Lab: Building Agent Systems with Databricks
# MAGIC
# MAGIC ## Part 2 - Agent Evaluation
# MAGIC Now that we've created an agent, how do we evaluate its performance?
# MAGIC For the second part, we're going to create a product support agent so we can focus on evaluation.
# MAGIC This agent will use a RAG approach to help answer questions about products using the product documentation.
# MAGIC
# MAGIC ### 2.1 Define our new Agent and retriever tool
# MAGIC - [**agent.py**]($./agent.py): An example Agent has been configured - first we'll explore this file and understand the building blocks
# MAGIC - **Vector Search**: We've created a Vector Search endpoint that can be queried to find related documentation about a specific product.
# MAGIC - **Create Retriever Function**: Define some properties about our retriever and package it so it can be called by our LLM.
# MAGIC
# MAGIC ### 2.2 Create Evaluation Dataset
# MAGIC - We've provided an example evaluation dataset - though you can also generate this [synthetically](https://www.databricks.com/blog/streamline-ai-agent-evaluation-with-new-synthetic-data-capabilities).
# MAGIC
# MAGIC ### 2.3 Run MLflow.evaluate() 
# MAGIC - MLflow will take your evaluation dataset and test your agent's responses against it
# MAGIC - LLM Judges will score the outputs and collect everything in a nice UI for review
# MAGIC
# MAGIC ### 2.4 Make Needed Improvements and re-run Evaluations
# MAGIC - Take feedback from our evaluation run and change the prompt
# MAGIC - Run evals again and see the improvement!

# COMMAND ----------

# MAGIC %pip install -U -qqqq mlflow-skinny[databricks] langgraph==0.3.4 databricks-langchain databricks-agents uv
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Quick test to see if Agent works
from agent import AGENT

AGENT.predict({"messages": [{"role": "user", "content": "Hello, what do you do?"}]})

# COMMAND ----------

# MAGIC %md
# MAGIC ### Log the `agent` as an MLflow model
# MAGIC Log the agent as code from the [agent]($./agent) notebook. See [MLflow - Models from Code](https://mlflow.org/docs/latest/models.html#models-from-code).

# COMMAND ----------

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

# Load the model and create a prediction function
logged_model_uri = f"runs:/{logged_agent_info.run_id}/agent"
loaded_model = mlflow.pyfunc.load_model(logged_model_uri)

def predict_wrapper(query):
    # Format for chat-style models
    
    model_input = {
        "messages": [{"role": "user", "content": query}]
    }
    response = loaded_model.predict(model_input)
    
    messages = response['messages']
    return messages[-1]['content']

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluate the agent with [Agent Evaluation](https://docs.databricks.com/generative-ai/agent-evaluation/index.html)
# MAGIC
# MAGIC You can edit the requests or expected responses in your evaluation dataset and run evaluation as you iterate your agent, leveraging mlflow to track the computed quality metrics.

# COMMAND ----------

import pandas as pd

data = {
    "request": [
        "What color options are available for the Aria Modern Bookshelf?",
        "How should I clean the Aurora Oak Coffee Table to avoid damaging it?",
        "What sizes are available for the StormShield Pro Men's Weatherproof Jacket?"
    ],
    "expected_facts": [
        [
            "The Aria Modern Bookshelf is available in natural oak finish",
            "The Aria Modern Bookshelf is available in black finish",
            "The Aria Modern Bookshelf is available in white finish"
        ],
        [
            "Use a soft, slightly damp cloth for cleaning.",
            "Avoid using abrasive cleaners."
        ],
        [
            "The available sizes for the StormShield Pro Men's Weatherproof Jacket are Small, Medium, Large, XL, and XXL."
        ]
    ]
}

eval_dataset = pd.DataFrame(data)

# COMMAND ----------

from mlflow.genai.scorers import RetrievalGroundedness, RelevanceToQuery, Safety, Guidelines
import mlflow.genai

eval_data = []
for request, facts in zip(data["request"], data["expected_facts"]):
    eval_data.append({
        "inputs": {
            "query": request  # This matches the function parameter
        },
        "expected_response": "\n".join(facts)
    })

# Define custom scorers tailored to product information evaluation
scorers = [
    #RetrievalGroundedness(),  # Pre-defined judge that checks against retrieval results
    RelevanceToQuery(),  # Checks if answer is relevant to the question
    #Safety(),  # Checks for harmful or inappropriate content
    Guidelines(
        guidelines="""Response must be clear and direct:
        - Answers the exact question asked
        - Uses lists for options, steps for instructions
        - No marketing fluff or extra background
        - Does not tell user to contact customer support
        - Concise but complete.""",
        name="clarity_and_structure",
    ),
    #Guidelines(
    #    guidelines="""Response must include ALL expected facts:
    #    - Lists ALL colors/sizes if relevant (not partial lists)
    #    - States EXACT specs if relevant (e.g., "5 ATM" not "water resistant")
    #    - Includes ALL cleaning steps if asked
    #    Fails if ANY fact is missing or wrong.""",
    #    name="completeness_and_accuracy",
    #)
]

# COMMAND ----------

print("Running evaluation...")
with mlflow.start_run():
    results = mlflow.genai.evaluate(
        data=eval_data,
        predict_fn=predict_wrapper, 
        scorers=scorers,
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Lets go back to the [agent.py]($./agent.py) file and change our prompt to reduce marketing fluff.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register the model to Unity Catalog
# MAGIC
# MAGIC Update the `catalog`, `schema`, and `model_name` below to register the MLflow model to Unity Catalog.

# COMMAND ----------

from databricks.sdk import WorkspaceClient
import os

mlflow.set_registry_uri("databricks-uc")

# Use the workspace client to retrieve information about the current user
w = WorkspaceClient()
user_email = w.current_user.me().display_name
username = user_email.split("@")[0]

# Catalog and schema have been automatically created thanks to lab environment
catalog_name = f"{username}"
schema_name = "agents"

# TODO: define the catalog, schema, and model name for your UC model
model_name = "product_agent"
UC_MODEL_NAME = f"{catalog_name}.{schema_name}.{model_name}"

# register the model to UC
uc_registered_model_info = mlflow.register_model(model_uri=logged_agent_info.model_uri, name=UC_MODEL_NAME)

# COMMAND ----------

from IPython.display import display, HTML

# Retrieve the Databricks host URL
workspace_url = spark.conf.get('spark.databricks.workspaceUrl')

# Create HTML link to created agent
html_link = f'<a href="https://{workspace_url}/explore/data/models/{catalog_name}/{schema_name}/product_agent" target="_blank">Go to Unity Catalog to see Registered Agent</a>'
display(HTML(html_link))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Deploy the agent
# MAGIC
# MAGIC ##### Note: This is disabled for lab users but will work on your own workspace

# COMMAND ----------

from databricks import agents

# Deploy the model to the review app and a model serving endpoint

#Disabled for the lab environment but we've deployed the agent already!
#agents.deploy(UC_MODEL_NAME, uc_registered_model_info.version, tags = {"endpointSource": "DI Days"})
