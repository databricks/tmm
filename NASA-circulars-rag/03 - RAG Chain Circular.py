# Databricks notebook source
# MAGIC %pip install --quiet --upgrade databricks-vectorsearch mlflow langchain langchain_community
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

catalog_name = "demo_frank"
schema_name = "circulars"

# COMMAND ----------

from langchain_community.chat_models import ChatDatabricks
from langchain_community.vectorstores import DatabricksVectorSearch
from databricks.vector_search.client import VectorSearchClient
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
#from langchain_core.runnables import RunnablePassthrough
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.runnable import RunnableLambda
from operator import itemgetter
import os

# COMMAND ----------

# MAGIC %md
# MAGIC Create Vector Search in UI first to make this code work
# MAGIC

# COMMAND ----------

example_question = "explain the most interesting GRBs related to supernova or black hole events 2024, what makes them special in terms of their properties and characteristics. If you have no information say that. "


#example_question = "tell me about the afterglow of 221009A "


# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
from langchain_community.vectorstores import DatabricksVectorSearch
from langchain_community.embeddings import DatabricksEmbeddings

# Test embedding Langchain model
# NOTE: your question embedding model must match the one used in the chunk in the previous notebook 



# BAAI General Embedding (BGE) is a text embedding model that can map any text 
# to a 1024-dimension embedding vector and an embedding window of 512 tokens. 


index_name= "circular_index"
vector_index = f"{catalog_name}.{schema_name}.{index_name}"

vector_db_endpoint_name = "nasa_circulars"
k = 8

embedding_model = DatabricksEmbeddings(endpoint="databricks-bge-large-en")
host = "https://" + spark.conf.get("spark.databricks.workspaceUrl")

print(f"Test embeddings: {embedding_model.embed_query(example_question)[:20]}...")


def get_retriever(persist_dir: str = None):
    os.environ["DATABRICKS_HOST"] = host
    #Get the vector search index
    vsc = VectorSearchClient(workspace_url=host, disable_notice=True)

    #get vs index
    vs_index = vsc.get_index(
        endpoint_name= vector_db_endpoint_name,
        index_name=vector_index
    )

    # Create the retriever
    vectorstore = DatabricksVectorSearch(
        vs_index, text_column="chunked_text"
    )
    return vectorstore.as_retriever(search_kwargs={'k': k})


# test our retriever
vectorstore = get_retriever()
similar_documents = vectorstore.get_relevant_documents(example_question)
print(f"\n relevant documents: {similar_documents}")

# COMMAND ----------

# DBTITLE 1,question without context and without template
model = ChatDatabricks(
    #endpoint="databricks-dbrx-instruct",
    endpoint="databricks-meta-llama-3-70b-instruct",
    max_tokens = 4000,
)

print(model.invoke(example_question).content)

# COMMAND ----------

from langchain.chains import RetrievalQA

# Define the function to return a retriever
def loader_fn():
    return vector_search_as_retriever()

TEMPLATE = """\
You are an enthusiastic, friendly and fun science journalist with expertise in gamma-ray bursts, supernovas, and astronomical observations. Your goal is to share your knowledge in a captivating and accessible way.

Using the circulars in the context provided below, please do the following:

Write an an article that summarizes the provided circulars using the most recent 3 events from 2024. 

for GCN [number] where [number] is the number of gcn, also provide a link to 
https://gcn.nasa.gov/circulars/[number] as a source (replacing [number] with the real number)

** Don't format hyperlinks.

In a new paragraph, discuss how these events have contributed to a better understanding of science, space and life.



Context provided:
{context}

Question:
{question}

Answer:

"""

prompt = PromptTemplate(template=TEMPLATE, input_variables=["context", "question"])

chain = RetrievalQA.from_chain_type(
    llm=model,
    chain_type="stuff",
    retriever=get_retriever(),
    chain_type_kwargs={"prompt": prompt}
)


# COMMAND ----------

# DBTITLE 1,LangChain Chain with RAG context

question = {"query": example_question}
answer = chain.invoke(question)
print(answer["result"])



# COMMAND ----------

# MAGIC %md
# MAGIC **Gamma-Ray Bursts: Unveiling the Secrets of the Universe**
# MAGIC
# MAGIC In the vast expanse of space, gamma-ray bursts (GRBs) are among the most powerful and enigmatic events, offering a glimpse into the universe's most extreme phenomena. As a science journalist, I'm thrilled to share with you the latest discoveries from the Gamma-Ray Coordinates Network (GCN) circulars, highlighting three recent events from 2024 that have shed new light on the connection between GRBs, supernovae, and black holes.
# MAGIC
# MAGIC **GRB 240101A: A Supernova Connection**
# MAGIC
# MAGIC On January 1, 2024, the Swift satellite detected GRB 240101A, a long-duration burst with a peculiar light curve. Spectroscopic observations revealed the emergence of a supernova (SN) associated with the GRB, similar to the iconic SN 1998bw (GCN 32800, https://gcn.nasa.gov/circulars/32800). This finding strengthens the link between GRBs and SNe, suggesting that some GRBs are triggered by the collapse of massive stars.
# MAGIC
# MAGIC **GRB 240205B: A Black Hole Candidate**
# MAGIC
# MAGIC On February 5, 2024, the Fermi Gamma-Ray Space Telescope detected GRB 240205B, a short-duration burst with an unusual energy spectrum. The burst's properties, including its high-energy emission and rapid variability, hint at the presence of a black hole (GCN 32950, https://gcn.nasa.gov/circulars/32950). This event may be one of the few GRBs powered by the merger of compact objects, such as neutron stars or black holes.
# MAGIC
# MAGIC **GRB 240315C: A High-Redshift Burst**
# MAGIC
# MAGIC On March 15, 2024, the Swift satellite detected GRB 240315C, a long-duration burst with a high-redshift signature. The burst's properties, including its long duration and low peak flux, suggest that it may be one of the most distant GRBs ever detected (GCN 33020, https://gcn.nasa.gov/circulars/33020). This event offers a unique opportunity to study the early universe and the formation of the first stars and galaxies.
# MAGIC
# MAGIC **The Bigger Picture**
# MAGIC
# MAGIC These recent GRBs have contributed significantly to our understanding of the universe. They have:
# MAGIC
# MAGIC 1. **Strengthened the GRB-SN connection**: The association between GRBs and SNe provides insight into the final stages of massive star evolution and the physics of explosive events.
# MAGIC 2. **Shed light on black hole formation**: The detection of black hole-powered GRBs offers a window into the merger of compact objects and the growth of supermassive black holes.
# MAGIC 3. **Probed the distant universe**: High-redshift GRBs allow us to study the early universe, the formation of the first stars and galaxies, and the reionization of the intergalactic medium.
# MAGIC
# MAGIC These discoveries demonstrate the power of multi-messenger astronomy, where the combination of gamma-ray, X-ray, optical, and radio observations provides a comprehensive understanding of these enigmatic events. As we continue to explore the universe, GRBs will remain a crucial tool for unraveling the secrets of the cosmos.

# COMMAND ----------

# DBTITLE 1,Test Chain with empty context
# set context to empty string for this
question = {"query": TEMPLATE.format(context="", question=example_question)}
prompt = PromptTemplate(template=TEMPLATE, input_variables=["context", "question"])

chain = RetrievalQA.from_chain_type(
    llm=model,
    chain_type="stuff",
    retriever=get_retriever(),
    chain_type_kwargs={"prompt": prompt}
)



answer = chain.invoke(question)
print(answer["result"])


# COMMAND ----------

# MAGIC %md
# MAGIC I'm excited to share with you the latest updates from the world of gamma-ray bursts (GRBs) and astronomical observations! Unfortunately, since the provided circulars only go up to 2012, I don't have any information on GRBs from 2024. However, I can summarize the most recent three events from the provided circulars and discuss their significance.
# MAGIC
# MAGIC **Summary of Recent Events**
# MAGIC
# MAGIC 1. **GCN 13308: Correction to GCN 13307 (GRB120521B)** (https://gcn.nasa.gov/circulars/13308)
# MAGIC This circular corrects an error in the title of GCN 13307, which reported observations of GRB120521B, not GRB120521A. This highlights the importance of accuracy in scientific communication.
# MAGIC 2. **GCN 8096: First GLAST Burst Monitor GRB Circulars** (https://gcn.nasa.gov/circulars/8096)
# MAGIC This circular announces the beginning of GCN circulars for triggered gamma-ray bursts detected by the GLAST Burst Monitor team. This marks a significant milestone in the detection and study of GRBs.
# MAGIC 3. **GCN 33638: New GCN Circulars Portal for Rapid Communications on Astronomical Transients is Online** (https://gcn.nasa.gov/circulars/33638)
# MAGIC This circular introduces a new GCN Circulars portal, which modernizes the way astronomers communicate and share information about GRBs and other astronomical transients. This upgrade enables faster and more efficient collaboration among researchers.
# MAGIC
# MAGIC **Contribution to a Better Understanding of Science, Space, and Life**
# MAGIC
# MAGIC These events, although not directly related to supernova or black hole events, contribute to a better understanding of GRBs and the importance of accurate communication in science. The GLAST Burst Monitor's ability to detect and report GRBs rapidly enables researchers to study these powerful events in greater detail, shedding light on the extreme physics involved. The new GCN Circulars portal facilitates the sharing of knowledge and collaboration among scientists, accelerating our understanding of the universe.
# MAGIC
# MAGIC While we don't have information on GRBs from 2024, these recent events demonstrate the ongoing efforts to improve our understanding of GRBs and the importance of accurate communication in scientific research.

# COMMAND ----------

from mlflow.models import infer_signature
import mlflow
import langchain

mlflow.set_registry_uri("databricks-uc")
my_model = "circulars_chatbot"
model_name = f"{catalog_name}.{schema_name}.{my_model}"

with mlflow.start_run(run_name= my_model) as run:
    signature = infer_signature(question, answer)
    model_info = mlflow.langchain.log_model(
        chain,
        loader_fn=get_retriever,  # Load the retriever with DATABRICKS_TOKEN env as secret (for authentication).
        artifact_path="chain",
        registered_model_name=model_name,
        pip_requirements=[
            "mlflow==" + mlflow.__version__,
            "langchain==" + langchain.__version__,
            "databricks-vectorsearch",
            "langchain_community",
        ],
        input_example=question,
        signature=signature
    )

# COMMAND ----------

# MAGIC %md
# MAGIC serve the model after it is registered...
