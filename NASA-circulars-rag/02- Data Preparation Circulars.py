# Databricks notebook source
# MAGIC %pip install --quiet tokenizers torch transformers
# MAGIC %pip install -U --quiet databricks-sdk langchain==0.1.13
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

silver_table_name = 'demo_frank.circular_pipeline.proc_circulars'
gold_table_name = 'demo_frank.circulars.circulars_chunked'

# COMMAND ----------

from pyspark.sql.functions import concat_ws, col, lit

# Load the silver table
silver_df = spark.table(silver_table_name)

silver_df = silver_df    \
    .withColumn("text",                                 \
    concat_ws(" ",lit("date: "), col("created"),     \
    lit("circularId: "), col("id"),                  \
    col("body") )) 

concatenated_df = silver_df

display(silver_df)

# COMMAND ----------

from transformers import pipeline
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transformers.utils import logging


"""
The tokenizer (AutoTokenizer from Hugging Face Transformers) prepares input text for the language model:
- Preprocesses text (lowercasing, removing punctuation, etc.)
- Splits text into tokens (words, subwords, or characters)
- Maps tokens to integer IDs based on a pre-defined vocabulary
- Handles special tokens ([CLS], [SEP], [PAD]) for model-specific purposes
- Encodes the tokenized input into a format suitable for the model (tensors)
The tokenizer is loaded from a pre-trained checkpoint to ensure compatibility with the model.
"""

# Create a tokenizer with the pre-trained model 'BAAI/bge-large-en-v1.5'
tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-large-en-v1.5')

# Define an example text for a chunk
chunk_example_text = "how far is the moon from the earth"

# Encode the chunk example text using the tokenizer
encoded_input = tokenizer(chunk_example_text, padding=True, truncation=True, return_tensors='pt')

# Print the number of tokens in the encoded input
print(f"example: '{chunk_example_text}' ")
print(f"Number of tokens: {len(encoded_input['input_ids'][0])}")
print(f"Number of words : {len(chunk_example_text.split())} ")
print(f"Number of chars : {len(chunk_example_text)}")

# COMMAND ----------

import pyspark.sql.functions as func
from pyspark.sql.types import MapType, StringType
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from pyspark.sql import Column
from pyspark.sql.types import *
from datetime import timedelta
from typing import List
import warnings

# COMMAND ----------

# Defaults
BGE_CONTEXT_WINDOW_LENGTH_TOKENS = 512
CHUNK_SIZE_TOKENS = 500         
CHUNK_OVERLAP_TOKENS = 75       
DATABRICKS_FMAPI_BGE_ENDPOINT = "databricks-bge-large-en"
FMAPI_EMBEDDINGS_TASK = "llm/v1/embeddings"

CHUNK_COLUMN_NAME = "chunked_text"
CHUNK_ID_COLUMN_NAME = "chunk_id"


# TODO: Add error handling
@func.udf(returnType=ArrayType(StringType())
          # useArrow=True, # set globally
          )


# The BAAI/bge-large-en-v1.5 model's tokenizer is trained on a large text corpus and tokenizes text while preserving semantic meaning.
# Using this tokenizer for chunking ensures semantically coherent and meaningful chunks, considering linguistic properties.
# Cutting text into fixed-length pieces may break words or sentences, leading to loss of context and meaning.

def split_char_recursive(content: str) -> List[str]:
    text_splitter = CharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer, chunk_size=CHUNK_SIZE_TOKENS, chunk_overlap=CHUNK_OVERLAP_TOKENS
    )
    chunks = text_splitter.split_text(content)
    return [doc for doc in chunks]


df_chunked = concatenated_df.select(
    "*", func.explode(split_char_recursive("text")).alias(CHUNK_COLUMN_NAME)
).drop(func.col("text"))
df_chunked = df_chunked.select(
    "*", func.md5(func.col(CHUNK_COLUMN_NAME)).alias(CHUNK_ID_COLUMN_NAME)
)

display(df_chunked)



# COMMAND ----------

df_chunked.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(gold_table_name)

# Enable CDC for Vector Search Delta Sync
spark.sql(f"ALTER TABLE {gold_table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

# COMMAND ----------

# MAGIC %md
# MAGIC
