# Databricks notebook source
# MAGIC %md
# MAGIC ### Welcome to the Databricks GenAI Workshop - Part Two: Retrieval Augmented Generation
# MAGIC In this section, we will explore how to augment models by using RAG (Retrieval Augmented Generation). You'll gain hands-on experience with:
# MAGIC
# MAGIC - **Concepts for Pre-processing Data:** Briefly cover how to set up tables in a medallion architecture and set your data up for RAG.
# MAGIC - **Creating a Vector Search Index:** Learn how to take a Delta table and use Databricks Vector Search and an embedding model to easily create a Vector Search index.
# MAGIC - **Understanding Similarity Search:** Explore how to retrieve relevant data using similarity search against a vector index.
# MAGIC - **Chaining Relevant Data into our Model:** See an example of using prompts and vector search to bring in relevant context and improve our model's response.
# MAGIC
# MAGIC For more advanced code and resources that are continuously updated see: https://ai-cookbook.io/index.html 

# COMMAND ----------

# DBTITLE 1,Install the needed libraries
# MAGIC %pip install -U -qqqq databricks-agents mlflow mlflow-skinny databricks-vectorsearch langchain==0.2.1 langchain_core==0.2.5 langchain_community==0.2.4 cloudpickle

# COMMAND ----------

# DBTITLE 1,Restart Python Kernel
dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Setup User-Specific Variables
#setup catalog and show widget at top
dbutils.widgets.text("catalog_name","main")
catalog_name = dbutils.widgets.get("catalog_name")

#break user in their own schema
current_user = spark.sql("SELECT current_user() as username").collect()[0].username
schema_name = f'genai_workshop_{current_user.split("@")[0].split(".")[0]}'

#create schema
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.{schema_name}")
print(f"\nUsing catalog + schema: {catalog_name}.{schema_name}")

# COMMAND ----------

# DBTITLE 1,Import Libraries
from langchain_community.chat_models import ChatDatabricks
from langchain_community.vectorstores import DatabricksVectorSearch
from langchain_community.embeddings import DatabricksEmbeddings
from databricks.vector_search.client import VectorSearchClient
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.schema.runnable import RunnableLambda
from operator import itemgetter
import os

# COMMAND ----------

# MAGIC %md
# MAGIC ### We've parsed out a couple research papers authored by Matei Zaharia (and colleagues) that represent data outside of the knowledge of our model

# COMMAND ----------

# DBTITLE 1,Lets look at the parsed data
# MAGIC %sql
# MAGIC select parsed_output.text from main.default.silver_pdf_landing_parsed

# COMMAND ----------

# MAGIC %md
# MAGIC ### This data was then broken down into chunks in preperation to be turned into vectors
# MAGIC
# MAGIC #### These chunks are going to then be turned into vectors through the use of Databricks Vector Store and a Databricks hosted embedding model
# MAGIC
# MAGIC ![Example Flow for Vector Store](https://docs.databricks.com/en/_images/calculate-embeddings.png)

# COMMAND ----------

# MAGIC %md
# MAGIC ### We've created a Vector Search Index prepared with this sample data - lets see how we can connect to it and use it to retrieve relevant contextual data

# COMMAND ----------

# DBTITLE 1,Link to Vector Store and Create Retriever
############
# Connect to the Vector Search Index
############

#provide the schema for underlying table
vector_search_schema = {
    "primary_key": "chunk_id",
    "chunk_text": "chunked_text",
    "document_source": "doc_uri"
}

#Note for the lab this has already been set up
token = dbutils.secrets.get(scope = "vs_endpoint", key = "databricks_token")

def get_retriever(persist_dir: str = None):
    #Get the vector search index
    vsc = VectorSearchClient(personal_access_token=token, disable_notice=True)
    vs_index = vsc.get_index(
        endpoint_name="vs_genai_lab",
        index_name="main.default.gold_pdf_landing_chunked_index"
    )

    # Create the retriever
    vectorstore = DatabricksVectorSearch(
        vs_index, 
        text_column="chunked_text", 
        columns=[
        vector_search_schema.get("primary_key"),
        vector_search_schema.get("chunk_text"),
        vector_search_schema.get("document_source")
    ]
    )
    return vectorstore.as_retriever(search_kwargs={'k':3}) #This defines how many of the most relevant chunks to retrieve


# COMMAND ----------

# DBTITLE 1,Test Vector Search Retrieval
#Lets test the retrieval from our vector search endpoint by asking it about specific data within our research papers

vectorstore = get_retriever()
similar_documents = vectorstore.get_relevant_documents("What is ARES?")
print(f"Relevant documents: {similar_documents}")

# COMMAND ----------

# DBTITLE 1,Test our model for knowledge
#In part 1 of this workshop, we asked our DBRX model what ARES was to test our hallucination reducing prompt

model = ChatDatabricks(
    endpoint="databricks-dbrx-instruct",
    max_tokens = 400,
)

#Lets remind ourselves that it does not know what ARES is - this time without the anti-hallicunation prompt
#Note: ARES is NOT the Atmospheric Remote-Sensing Infrared Exoplanet Large-survey - this is a hallucination
print(model.invoke("What is ARES?").content)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Now lets tie our model and retriever together, along with some prompts needed as glue. Here's a breakdown of how this looks in action.
# MAGIC
# MAGIC ![Example Flow for RAG](https://github.com/databricks-demos/dbdemos-resources/blob/main/images/product/chatbot-rag/rag-basic.png?raw=true)

# COMMAND ----------

# DBTITLE 1,RAG Chain Creation
#Helper function to take retrieved docs and join them together
def format_context(docs):
    chunk_template = "`{chunk_text}`\n"
    chunk_contents = [chunk_template.format(chunk_text=d.page_content) for d in docs]
    return "".join(chunk_contents)

#First prompt to bring in context and set the model's behavior
prompt_template = "You are a trusted assistant that helps answer questions about academic research based only on the provided information. If you do not know the answer to a question, you truthfully say you do not know.  Here is some context which might or might not help you answer: {context}.  Answer directly, do not repeat the question, do not start with something like: the answer to the question, do not add AI in front of your answer, do not say: here is the answer, do not mention the context or the question. Based on this history and context, answer this question: {question}."

#Define the variables for first prompt
chat_prompt_template_variables=["context","question"]

#Similar to part 1 - we're creating prompt templates
prompt = PromptTemplate(
    template= prompt_template,
    input_variables=chat_prompt_template_variables,
)

#Second prompt used to write a query for the retrieved context based on the user's question
query_rewriter_prompt_template = "Based on the chat history below, we want you to generate a query for an external data source to retrieve relevant documents so that we can better answer the question. The query should be in natual language. The external data source uses similarity search to search for relevant documents in a vector space. So the query should be similar to the relevant documents semantically. Answer with only the query. Do not add explanation. Question: {messages}"
query_rewriter_prompt_template_variables= ["messages"]

#Similar to part 1 - we're creating prompt templates
query_rewrite_prompt = PromptTemplate(
    template=query_rewriter_prompt_template,
    input_variables=query_rewriter_prompt_template_variables,
)

#Tie them together to create a RAG chain. Components are chained together in order they appear
rag_chain = (
    {
            "context": query_rewrite_prompt     #assemble rewriter prompt to add user's question
            | model                             #define the model to be used
            | StrOutputParser()                 #parses the string output generated by the model
            | get_retriever        #performs similarity search and returns context
            | RunnableLambda(format_context),   #formats the returned results
            "question": itemgetter("messages"), #adds the original user's question
        }
    | prompt                                    #main prompt that now has both the context variable as well as question
    | model                                     #model to be used
    | StrOutputParser()                         #final output
)



# COMMAND ----------

# DBTITLE 1,Run RAG Chain
#Create out sample prompt - lets set up our question from earlier and see if it's learned
input_sample = {
    "messages": [
        {
            "role": "user",
            "content": "What is ARES?",
        }]}
        
#Run the chain!
print(rag_chain.invoke(input_sample))

# COMMAND ----------

# DBTITLE 1,Create MLflow Experiment for RAG Chain
import mlflow
import cloudpickle
import langchain
import langchain_community


# Create a new mlflow experiment or get the existing one if already exists.
current_user = spark.sql("SELECT current_user() as username").collect()[0].username
experiment_name = f"/Users/{current_user}/genai-prompt-engineering-workshop"
mlflow.set_experiment(experiment_name)

# set the name of our model
model_name = "dbrx_chain_rag"

# get experiment id to pass to the run
experiment_id = mlflow.get_experiment_by_name(experiment_name).experiment_id
with mlflow.start_run(experiment_id=experiment_id):
    mlflow.langchain.log_model(
        rag_chain,
        model_name,
        loader_fn = get_retriever(),
        input_example=input_sample,
        pip_requirements=[
            "mlflow==" + mlflow.__version__,
            "langchain==" + langchain.__version__,
            "langchain-community==" + langchain_community.__version__,
            "databricks-vectorsearch",
            "pydantic==2.5.2 --no-binary pydantic",
            "cloudpickle==" + cloudpickle.__version__
        ]
    )

# COMMAND ----------

# DBTITLE 1,Register our Model in Unity Catalog
import mlflow

#grab our most recent run (which logged the model) using our experiment ID
runs = mlflow.search_runs([experiment_id])
last_run_id = runs.sort_values('start_time', ascending=False).iloc[0].run_id

#grab the model URI that's generated from the run
model_uri = f"runs:/{last_run_id}/{model_name}"

#log the model to catalog.schema.model. The schema name referenced below is generated for you in the init script
catalog = dbutils.widgets.get("catalog_name")
schema = schema_name

#set our registry location to Unity Catalog
mlflow.set_registry_uri("databricks-uc")
mlflow.register_model(
    model_uri=model_uri,
    name=f"{catalog}.{schema}.{model_name}"
)
