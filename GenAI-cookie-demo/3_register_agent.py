# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC #Part 3: Register Agent to UC
# MAGIC In this notebook, we're going to take the agent we've created and register it to UC. This will allow us to govern, track, and deploy this agent just like you would any other RAG Chain, ML model, etc.
# MAGIC

# COMMAND ----------

# DBTITLE 1,Imports and Configs
import os
import yaml
from databricks.sdk import WorkspaceClient

# Grabs the username without the full email address. 
w = WorkspaceClient()

# config file created in 1_create_tools
with open("config.yaml", "r") as file:
    config_data = yaml.safe_load(file)

# Catalog and schema have been created in 1_create_tools
catalog_name = config_data["catalog_name"]
schema_name = config_data["schema_name"]

# COMMAND ----------

# DBTITLE 1,Set to UC for Model Registry
import os
import mlflow
from databricks import agents

# Use the Unity Catalog model registry
mlflow.set_registry_uri('databricks-uc')

# COMMAND ----------

# DBTITLE 1,Establish agent config
# For this first basic demo, we'll keep the configuration as a minimum. In a real app, you can make all your RAG as a param (such as your prompt template to easily test different prompts!)
agent_config = {
    "llm_model_serving_endpoint_name": "databricks-meta-llama-3-1-70b-instruct",  # the foundation model we want to use
    "uc_function_list": f"{catalog_name}.{schema_name}.*",
}

# COMMAND ----------

# DBTITLE 1,Register Agent to Unity Catalog
import os
import mlflow
from mlflow.models.signature import ModelSignature
from mlflow.models.rag_signatures import ChatCompletionRequest, StringResponse, ChatCompletionResponse

input_example = {"messages": "Create a social media post that promotes the best selling cookie for our Chicago store while showing we listen to customer feedback."}

# Specify the full path to the chain notebook
chain_notebook_file = "2_create_agent"
chain_notebook_path = os.path.join(os.getcwd(), chain_notebook_file)

host = "https://" + spark.conf.get("spark.databricks.workspaceUrl")

print(f"Chain notebook path: {chain_notebook_path}")

with mlflow.start_run(run_name="cookie_agent"):
  logged_chain_info = mlflow.langchain.log_model(
          # Note: In classical ML, MLflow works by serializing the model object.  In generative AI, chains often include Python packages that do not serialize.  Here, we use MLflow's new code-based logging, where we saved our chain under the chain notebook and will use this code instead of trying to serialize the object.
          lc_model=chain_notebook_path,  # Chain code file e.g., /path/to/the/chain.py 
          model_config=agent_config, # Chain configuration 
          artifact_path="agent", # Required by MLflow, the chain's code/config are saved in this directory
          input_example=input_example,
          example_no_conversion=True,  # Required by MLflow to use the input_example as the chain's schema
          signature=ModelSignature(
          inputs=ChatCompletionRequest(),
          #outputs=ChatCompletionResponse(),
          outputs=StringResponse(),
          ),
          pip_requirements=["langchain", "langchain-community", "langchain-openai"],
      )

MODEL_NAME = "cookie_agent_demo"
MODEL_NAME_FQN = f"{catalog_name}.{schema_name}.{MODEL_NAME}"

# Register to UC
uc_registered_model_info = mlflow.register_model(model_uri=logged_chain_info.model_uri, name=MODEL_NAME_FQN)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC Congrats! You've now created tools, and an agent, and registered it to UC where it can be governed/deployed.
# MAGIC
# MAGIC Some next suggested next steps:
# MAGIC * Create new functions and tie them into the agent
# MAGIC * Deploy the Agent using Model Serving
# MAGIC * Deploy the Agent in the Review App (functional - but still some rough edges for retrieved-context)
