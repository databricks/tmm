# Databricks notebook source
# DBTITLE 1,Setup (Ensure latest libraries)
# MAGIC %pip install datasets 
# MAGIC %pip install mlflow
# MAGIC %pip install transformers

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md 
# MAGIC ## HuggingFace transformers library is supported as an MLflow model flavor
# MAGIC #### This means it's super easy to grab awesome models off the shelf and use them right away.
# MAGIC #### Lets prove this by grabbing a language model for summarization in just one cell!

# COMMAND ----------

import transformers
import mlflow

#This is the specific model we're going to use, but can grab any huggingface hosted model
summary_pipeline = transformers.pipeline(model="sshleifer/distilbart-cnn-12-6")

#Now that huggingface is supported in MLflow, we can create a new MLflow run to log our model
with mlflow.start_run() as run:
  mlflow.transformers.log_model(
    transformers_model=summary_pipeline,
    artifact_path="summary_bot",
    input_example="Some kind of long form text that mostly talks about camera lenses."
  )

# With the model now logged, we can easily load it into a simple python function!
model_uri = f"runs:/{run.info.run_id}/summary_bot"

# The end result is a chatbot object that not only responds to user prompts, but even remembers context
summarizer = mlflow.pyfunc.load_model(model_uri)

# COMMAND ----------

# MAGIC %md 
# MAGIC #### Let's use an example customer review that's rather long, and see if we can get a decent summary.

# COMMAND ----------

customer_feedback = "I've been using the Sony 24-70mm lens for a while now, and wow, it's a game changer! No matter if I'm doing portraits or capturing the great outdoors, this lens has my back. Seriously, the versatility of the zoom range is awesome. Even in tricky light, the images come out super clear and sharp - the aperture range doesn't disappoint. I was worried about distortions, but there's barely any, which is great. And can we talk about the autofocus? Super quick and quiet. Really helpful when you're trying to catch those fleeting moments. In terms of build, it's solid and feels good in the hand. All in all, the Sony 24-70mm lens is worth every penny. If you're looking to step up your photography, this lens should be on your radar. Love it!"

# COMMAND ----------

summary = summarizer.predict(customer_feedback)

# COMMAND ----------

summary

# COMMAND ----------

# MAGIC %md
# MAGIC ### Since it's so easy, why not try out a few different models from Huggingface?
# MAGIC #### This time, we'll grab a chatbot. We can use almost the same code, too.

# COMMAND ----------

import transformers
import mlflow

#This is the specific model we're going to use, but can grab any huggingface hosted model
chat_pipeline = transformers.pipeline(model="microsoft/DialoGPT-medium")

#Now that huggingface is supported in MLflow, we can create a new MLflow run to log our model
with mlflow.start_run() as run:
  mlflow.transformers.log_model(
    transformers_model=chat_pipeline,
    artifact_path="chatbot",
    input_example="Hi there!"
  )

# With the model now logged, we can easily load it into a simple python function!
model_uri = f"runs:/{run.info.run_id}/chatbot"

# The end result is a chatbot object that not only responds to user prompts, but even remembers context
chatbot = mlflow.pyfunc.load_model(model_uri)


# COMMAND ----------

# MAGIC %md
# MAGIC ### Just like that, we have a model loaded up and ready to go. Let's take it for a test drive.

# COMMAND ----------

first_response = chatbot.predict("What's the best way to get to Antarctica?")

# COMMAND ----------

display(first_response)

# COMMAND ----------

# MAGIC %md 
# MAGIC ### Okay, a solid answer. Now lets see if it can remember context...

# COMMAND ----------

second_response = chatbot.predict("What kind of boat would I need?")

# COMMAND ----------

print(second_response)

# COMMAND ----------

# MAGIC %md 
# MAGIC ### Look at that, it remembered from our first question! 
# MAGIC #### Lets reload the model and show that without context, the answer differs.

# COMMAND ----------

#reload the chatbot
chatbot = mlflow.pyfunc.load_model(model_uri) 

# COMMAND ----------

#Lets ask it the second question again, but without asking about Antarctica first
new_response = chatbot.predict("What kind of boat would I need?")

# COMMAND ----------

print(new_response)

# COMMAND ----------

# MAGIC %md 
# MAGIC ### It may have lost the context, but it definitely kept the same attitude..

# COMMAND ----------

# MAGIC %md 
# MAGIC ## We can do more than just language models, for a more visual example we can show a classifcation model as well!

# COMMAND ----------

from datasets import load_dataset
from PIL import Image
import requests

#load hugging face dataset for a picture of cats
dataset = load_dataset("huggingface/cats-image")
cats = dataset["test"]["image"][0]

#random picture of a bunch of bananas 
url = "https://i0.wp.com/post.healthline.com/wp-content/uploads/2021/10/bananas-holding-health-benefits-1296x728-header.jpg?w=1845"
bananas = Image.open(requests.get(url, stream=True).raw)

# COMMAND ----------

# MAGIC %md ### Store the pipeline in MLflow

# COMMAND ----------

from transformers import AutoImageProcessor, ViTForImageClassification, pipeline

#We'll need some image processors from the transformers library
image_processor = AutoImageProcessor.from_pretrained("google/vit-base-patch16-224")
model = ViTForImageClassification.from_pretrained("google/vit-base-patch16-224")

#Rest of the code is very similar
image_classification_pipeline = pipeline(task="image-classification", model=model, feature_extractor=image_processor)

with mlflow.start_run() as run:
  mlflow.transformers.log_model(
    transformers_model=image_classification_pipeline,
    artifact_path="image_classifier"
  )
  
model_uri = f"runs:/{run.info.run_id}/image_classifier"

classifier = mlflow.transformers.load_model(model_uri)

# COMMAND ----------

# MAGIC %md #### A picture of some cats on a couch

# COMMAND ----------

cats

# COMMAND ----------

results = classifier(cats)

# COMMAND ----------

display(results)

# COMMAND ----------

# MAGIC %md Some bananas

# COMMAND ----------

bananas

# COMMAND ----------

results = classifier(bananas)

# COMMAND ----------

display(results)

# COMMAND ----------

# MAGIC %md 
# MAGIC ### One more fun example: assemble sentences from random words

# COMMAND ----------


task = "text2text-generation"
architecture = "mrm8488/t5-base-finetuned-common_gen"
model = transformers.AutoModelForSeq2SeqLM.from_pretrained(architecture)
tokenizer = transformers.AutoTokenizer.from_pretrained(architecture)

generation_pipeline = transformers.pipeline(
    task=task,
    tokenizer=tokenizer,
    model=model,
)

with mlflow.start_run() as run:
  mlflow.transformers.log_model(
    transformers_model=generation_pipeline,
    artifact_path="sentence_builder",
    input_example="keyboard engineer model data science"
  )

# Load as interactive pyfunc
model_uri = f"runs:/{run.info.run_id}/sentence_builder"

sentence_generator = mlflow.pyfunc.load_model(model_uri)

# COMMAND ----------

sentence_generator.predict("pancakes lumberjack axe syrup")

# COMMAND ----------

sentence_generator.predict("cat bananas boat antarctica")

# COMMAND ----------

# MAGIC %md 
# MAGIC ### Remember that we can always take these models from a notebook out to the world thanks to MLflow by:
# MAGIC * Registering the model.   
# MAGIC * Deploying model through model serving + monitoring.   
