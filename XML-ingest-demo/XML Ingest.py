# Databricks notebook source
import os
c_dir = os.getcwd()    
print(c_dir)

a_file = f'file:{c_dir}/endangered_species.xml'
m_file = f'file:{c_dir}/planet_of_the_apes.xml'


xsdPath = f'file:{c_dir}/endangered_species.xsd'

# COMMAND ----------

xsdPath

# COMMAND ----------

# %fs ls "/Workspace/Repos/frank.munz@databricks.com/XML-ingest-demo/"

# COMMAND ----------

# pandas using files with absolute path
import pandas as pd
df = pd.read_xml("endangered_species.xml")
df

# COMMAND ----------

# MAGIC %md
# MAGIC #Basics

# COMMAND ----------

# DBTITLE 1,Read XML list of endangered species
# `rowTag` option is required for reading files in XML format

df = (spark.read
    .format("xml")
    .option("rowTag", "species")
    .load(a_file)
    )


# COMMAND ----------

display(df.select("name","_id","info"))

# COMMAND ----------

# DBTITLE 1,Filter to only return name elements: set rowTag to "name"
df_names = (spark.read
    .format("xml")
    .option("rowTag", "name")
    .load(a_file)
    )


# COMMAND ----------

display(df_names)

# COMMAND ----------

# DBTITLE 1,Load whole file as single row
# 
# display(spark.read.format("xml").option("rowTag", "endangeredSpeciesList").load(a_file))

# COMMAND ----------

# DBTITLE 1,Load another movie XML with more structure and null values
movie_df = (spark.read
    .format("xml")
    .option("rowTag", "Ape")
    .load(m_file)
    )
display(movie_df.select("name","personality","role"))

# COMMAND ----------

# DBTITLE 1,Rejected movie XML with species XSD schema enforcement
try:
    movie_df = spark.read.format("xml") \
        .option("rowTag", "Ape") \
        .option("rowValidationXSDPath", xsdPath) \
        .load(m_file)
except Exception as e:
    print("Error: Failed to parse XML file. Reason: {}".format(str(e)))

    corrupt_records = movie_df.filter(movie_df['_corrupt_record'].isNotNull())
    display(corrupt_records)

# COMMAND ----------

# MAGIC %md
# MAGIC #XML Ingest with row validation 

# COMMAND ----------

# DBTITLE 1,Original species XML with XSD validation
df = spark.read.format("xml") \
        .option("rowTag", "species") \
        .option("rowValidationXSDPath", xsdPath) \
        .load(a_file)
        
#display(df)

# COMMAND ----------

# DBTITLE 1,Auto Loader in Python with validation
df = spark.readStream \
  .format("cloudFiles")  \
  .option("cloudFiles.format", "xml") \
  .option("rowTag", "species") \
  .option("rowValidationXSDPath", xsdPath) \
  .option("cloudFiles.schemaLocation", "/tmp/schema") \
  .load(a_file)

display(df)


# COMMAND ----------

# DBTITLE 1,##Auto Loader in Python and validation
movie_df = spark.read.format("xml") \
        .option("rowTag", "Ape") \
        .option("rowValidationXSDPath", xsdPath) \
        .load(m_file)

# COMMAND ----------

# MAGIC %md
# MAGIC # Using SQL with XML  

# COMMAND ----------

# DBTITLE 1,Ingest XML
# MAGIC %sql
# MAGIC
# MAGIC DROP TABLE IF EXISTS e_species;
# MAGIC CREATE TABLE e_species
# MAGIC USING XML
# MAGIC OPTIONS (path "file:/Workspace/Repos/frank.munz@databricks.com/XML-ingest-demo/endangered_species.xml", rowTag "species");
# MAGIC
# MAGIC SELECT * FROM e_species;

# COMMAND ----------

# DBTITLE 1,schema_of_xml() function
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
