# Databricks notebook source
import os

# files used for this demo

# an XML list of endangered animals with XSD
endangered_f = f'file:{os.getcwd()}/endangered_species.xml'
endangered_xsd_f = f'file:{os.getcwd()}/endangered_species.xsd'

# extended list, with a new <POPULATION> element introduced
endangered_new_f = f'file:{os.getcwd()}/endangered_new.xml'

# apes, not matching the XSD
apes_f = f'file:{os.getcwd()}/planet_of_the_apes.xml'

schema_loc = '/tmp/my-schema_loc'
dbutils.fs.rm(schema_loc, True)

spark.conf.set('apes_f', apes_f)
print(f'current working dir:{os.getcwd()}')



# COMMAND ----------

# pandas using files with absolute path
import pandas as pd
df = pd.read_xml("endangered_species.xml")
df

# COMMAND ----------

# DBTITLE 1,Read XML list of endangered species
# `rowTag` option is required for reading files in XML format

df = (spark.read
    .format("xml")
    .option("rowTag", "species")
    .load(endangered_f)
    )


# COMMAND ----------

# DBTITLE 1,XML attributes are flattened to _attribute
display(df.select("name","_id","info"))

# COMMAND ----------

# DBTITLE 1,Filter to only return name elements: set rowTag to "name"
df_names = (spark.read
    .format("xml")
    .option("rowTag", "name")
    .load(endangered_f)
    )
display(df_names)

# COMMAND ----------

# DBTITLE 1,Load whole file as single row
# 
# display(spark.read.format("xml").option("rowTag", "endangeredSpecies").load(endangered_f))

# COMMAND ----------

# DBTITLE 1,Load the movie XML with different structure and null values
movie_df = (spark.read
    .format("xml")
    .option("rowTag", "Ape")
    .load(apes_f)
    )
display(movie_df)

# COMMAND ----------

# DBTITLE 1,Rejected movie XML with species XSD schema enforcement
from pyspark.sql.functions import col


movie_df = spark.read.format("xml") \
.option("rowTag", "Ape") \
.option("rowValidationXSDPath", endangered_xsd_f) \
.load(apes_f)

# how to display corrupt records?
#display(movie_df)


# COMMAND ----------

# MAGIC %md
# MAGIC #comment header 
# MAGIC
# MAGIC comment text
# MAGIC

# COMMAND ----------

# DBTITLE 1,Original species XML with XSD validation
df = spark.read.format("xml") \
        .option("rowTag", "species") \
        .option("rowValidationendangered_xsd_f", endangered_xsd_f) \
        .load(endangered_f)
        
display(df)

# COMMAND ----------

# DBTITLE 1,Auto Loader in Python with validation
df = spark.readStream \
  .format("cloudFiles")  \
  .option("cloudFiles.format", "xml") \
  .option("rowTag", "species") \
  .option("rowValidationendangered_xsd_f", endangered_xsd_f) \
  .option("cloudFiles.schemaLocation", schema_loc) \
  .load(endangered_f)

#display(df)


# COMMAND ----------

# DBTITLE 1,Auto Loader: old XSD, new XML with new ELEMENT - will FAIL
# 

df = spark.readStream \
  .format("cloudFiles")  \
  .option("cloudFiles.format", "xml") \
  .option("rowTag", "species") \
  .option("rowValidationendangered_xsd_f", endangered_xsd_f) \
  .option("cloudFiles.schemaLocation", schema_locexp) \
  .load(endangered_new_f)


# COMMAND ----------

display(df)


# COMMAND ----------

df = spark.readStream \
  .format("cloudFiles")  \
  .option("cloudFiles.format", "xml") \
  .option("rowTag", "species") \
  .option("rowValidationendangered_xsd_f", endangered_xsd_f) \
  .option("cloudFiles.schemaLocation", schema_loc) \
  .option("cloudFiles.schemaEvolutionMode", "addNewColumns") \
  .load(endangered_new_f)

# COMMAND ----------

display(df)

# COMMAND ----------

df.printSchema()


# COMMAND ----------

# %fs head schema_loc

# COMMAND ----------

# MAGIC %md
# MAGIC # Using SQL with XML  

# COMMAND ----------

# DBTITLE 1,Ingest XML
# MAGIC %sql
# MAGIC
# MAGIC DROP TABLE IF EXISTS e_species;
# MAGIC
# MAGIC CREATE TABLE e_species USING XML
# MAGIC OPTIONS (path "file:/Workspace/Repos/frank.munz@databricks.com/tmm/XML-ingest-demo/endangered_species.xml", rowTag "species");
# MAGIC
# MAGIC SELECT * FROM e_species;

# COMMAND ----------

# DBTITLE 1,SQL with cloud_files
# MAGIC %sql
# MAGIC
# MAGIC CREATE table x_species AS
# MAGIC   SELECT * from read_files('file:/Workspace/Repos/frank.munz@databricks.com/tmm/XML-ingest-demo/endangered_species.xml',
# MAGIC     format  =>  'xml',
# MAGIC     cloudFiles.schemaEvolutionMode  'addNewColumns',
# MAGIC     cloudFiles.schemaLocation  '/Workspace/Repos/frank.munz@databricks.com/tmm/XML-ingest-demo'
# MAGIC   ) 
# MAGIC
# MAGIC
# MAGIC
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC ## SQL XML functions()

# COMMAND ----------

# DBTITLE 1,SQL schema_of_xml() function
# MAGIC %sql
# MAGIC SELECT schema_of_xml('
# MAGIC   <Ape>
# MAGIC       <Name>Koba</Name>
# MAGIC       <Species>Bonobo</Species>
# MAGIC       <Leader>false</Leader>
# MAGIC       <Intelligence>High</Intelligence>
# MAGIC       <Personality>
# MAGIC         <Trait>Aggressive</Trait>
# MAGIC         <Trait>Loyal</Trait>
# MAGIC         <Trait>Vengeful</Trait>
# MAGIC       </Personality>
# MAGIC   </Ape>
# MAGIC ');

# COMMAND ----------

# DBTITLE 1,SQL to_xml() function
# MAGIC %sql
# MAGIC SELECT
# MAGIC   to_xml(named_struct("species","Orangutan"))
