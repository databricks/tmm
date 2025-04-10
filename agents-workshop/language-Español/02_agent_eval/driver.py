# Databricks notebook source
# MAGIC %md
# MAGIC # Laboratorio Práctico: Construcción de Sistemas de Agentes con Databricks
# MAGIC
# MAGIC ## Parte 2 - Evaluación del Agente
# MAGIC Ahora que hemos creado un agente, ¿cómo evaluamos su rendimiento?  
# MAGIC Para esta segunda parte, vamos a crear un agente más básico para poder enfocarnos en la evaluación.  
# MAGIC Este agente utilizará un enfoque RAG para ayudar a responder preguntas sobre productos usando la documentación del producto.
# MAGIC
# MAGIC ### 2.2 Crear Conjunto de Datos para Evaluación
# MAGIC - Hemos proporcionado un conjunto de datos de evaluación de ejemplo, aunque también puedes generarlo [sintéticamente](https://www.databricks.com/blog/streamline-ai-agent-evaluation-with-new-synthetic-data-capabilities).
# MAGIC
# MAGIC ### 2.3 Ejecutar MLflow.evaluate()
# MAGIC - MLflow tomará tu conjunto de datos de evaluación y probará las respuestas de tu agente contra él.
# MAGIC - Jueces LLM calificarán las respuestas y recopilarán todo en una interfaz agradable para su revisión.
# MAGIC
# MAGIC ### 2.4 Realiza Mejoras Necesarias y Vuelve a Ejecutar Evaluaciones
# MAGIC - Toma el feedback de la ejecución de evaluación y cambia la configuración de recuperación.
# MAGIC - Ejecuta las evaluaciones nuevamente y ¡observa la mejora!

# COMMAND ----------

# MAGIC %md
# MAGIC # Driver Notebook 
# MAGIC
# MAGIC Este es un notebook autogenerado creado por una exportación desde AI Playground. Generamos tres notebooks en la misma carpeta:
# MAGIC - [agent]($./agent): contiene el código para construir el agente.
# MAGIC - [config.yml]($./config.yml): contiene las configuraciones.
# MAGIC - [**driver**]($./driver): registra, evalúa, registra en catálogo y despliega el agente.
# MAGIC
# MAGIC Este notebook utiliza el Marco de Trabajo Mosaic AI Agent ([AWS](https://docs.databricks.com/en/generative-ai/retrieval-augmented-generation.html) | [Azure](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/retrieval-augmented-generation)) para desplegar el agente definido en el notebook [agent]($./agent). El notebook realiza lo siguiente:
# MAGIC 1. Registra el agente en MLflow  
# MAGIC 2. Evalúa el agente con Agent Evaluation  
# MAGIC 3. Registra el agente en Unity Catalog  
# MAGIC 4. Despliega el agente en un endpoint de Model Serving  
# MAGIC
# MAGIC ## Requisitos Previos
# MAGIC
# MAGIC - Completa todos los `TODO`s en este notebook.  
# MAGIC - Revisa el contenido de [config.yml]($./config.yml), ya que define las herramientas disponibles para tu agente, el endpoint del LLM y el prompt del agente.  
# MAGIC - Revisa y ejecuta el notebook [agent]($./agent) en esta carpeta para ver el código del agente, iterar sobre él y probar sus salidas.  
# MAGIC
# MAGIC ## Próximos Pasos
# MAGIC
# MAGIC Después de desplegar tu agente, puedes chatear con él en AI Playground para realizar verificaciones adicionales, compartirlo con expertos en tu organización para obtener retroalimentación, o integrarlo en una aplicación de producción. Consulta la documentación ([AWS](https://docs.databricks.com/en/generative-ai/deploy-agent.html) | [Azure](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/deploy-agent)) para más detalles.

# COMMAND ----------

# MAGIC %pip install -U -qqqq databricks-agents mlflow langchain==0.2.16 langgraph-checkpoint==1.0.12  langchain_core langchain-community==0.2.16 langgraph==0.2.16 pydantic langchain_databricks
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Registra el `agent` como un modelo de MLflow  
# MAGIC Registra el agente como código desde el notebook [agent]($./agent). Consulta [MLflow - Modelos desde Código](https://mlflow.org/docs/latest/models.html#models-from-code).

# COMMAND ----------

# Registrar el modelo en MLflow
import os
import mlflow

input_example = {
    "messages": [
        {
            "role": "user",
            "content": "Can you give me some troubleshooting steps for SoundWave X5 Pro Headphones that won't connect?"
        }
    ]
}

with mlflow.start_run():
    logged_agent_info = mlflow.langchain.log_model(
        lc_model=os.path.join(
            os.getcwd(),
            'agent',
        ),
        pip_requirements=[
            "langchain==0.2.16",
            "langchain-community==0.2.16",
            "langgraph-checkpoint==1.0.12",
            "langgraph==0.2.16",
            "pydantic",
            "langchain_databricks", # used for the retriever tool
        ],
        model_config="config.yml",
        artifact_path='agent',
        input_example=input_example,
    )

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
        "How should I clean the BlendMaster Elite 4000 after each use?",
        "How many colors is the Flexi-Comfort Office Desk available in?",
        "What sizes are available for the StormShield Pro Men's Weatherproof Jacket?",
        "What should I do if my SmartX Pro device won’t turn on?",
        "How many people can the Elegance Extendable Dining Table seat comfortably?",
        "What colors is the Urban Explorer Jacket available in?",
        "What is the water resistance rating of the BrownBox SwiftWatch X500?",
        "What colors are available for the StridePro Runner?"
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
            "The jar of the BlendMaster Elite 4000 should be rinsed.",
            "Rinse with warm water.",
            "The cleaning should take place after each use."
        ],
        [
            "The Flexi-Comfort Office Desk is available in three colors."
        ],
        [
            "The available sizes for the StormShield Pro Men's Weatherproof Jacket are Small, Medium, Large, XL, and XXL."
        ],
        [
            "Press and hold the power button for 20 seconds to reset the device.",
            "Ensure the device is charged for at least 30 minutes before attempting to turn it on again."
        ],
        [
            "The Elegance Extendable Dining Table can comfortably seat 6 people."
        ],
        [
            "The Urban Explorer Jacket is available in charcoal, navy, and olive green"
        ],
        [
            "The water resistance rating of the BrownBox SwiftWatch X500 is 5 ATM."
        ],
        [
            "The colors available for the StridePro Runner should include Midnight Blue.",
            "The colors available for the StridePro Runner should include Electric Red.",
            "The colors available for the StridePro Runner should include Forest Green."
        ]
    ]
}

eval_dataset = pd.DataFrame(data)

# COMMAND ----------

# DBTITLE 1,Run MLflow Evaluations!
import mlflow
import pandas as pd

with mlflow.start_run(run_id=logged_agent_info.run_id):
    eval_results = mlflow.evaluate(
        f"runs:/{logged_agent_info.run_id}/agent",  # replace `chain` with artifact_path that you used when calling log_model.
        data=eval_dataset,  # Your evaluation dataset
        model_type="databricks-agent",  # Enable Mosaic AI Agent Evaluation
    )

# Review the evaluation results in the MLFLow UI (see console output), or access them in place:
display(eval_results.tables['eval_results'])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Lets go back to the [agent]($./agent) notebook and change our retriever to 1.

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
#catalog_name = f"{username}_vocareum_com"
catalog_name = "retail_prod"
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
agents.deploy(UC_MODEL_NAME, uc_registered_model_info.version, tags = {"endpointSource": "playground"})
