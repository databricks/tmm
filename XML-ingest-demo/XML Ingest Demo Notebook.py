# Databricks notebook source
# MAGIC %md
# MAGIC #Ingest XML - Endangered Species Demo
# MAGIC see [README](https://github.com/databricks/tmm/blob/main/XML-ingest-demo/README.md) for more details. Run this notebook on classic single user cluster.  

# COMMAND ----------

# Adding image from misc/x.png to cell
from IPython.display import Image
Image(filename='misc/xml.png')



# COMMAND ----------

import os

# files used for this demo

# an XML list of endangered animals with XSD
endangered_f = f'file:{os.getcwd()}/endangered_species.xml'
endangered_xsd_f = f'file:{os.getcwd()}/endangered_species.xsd'

# extended XML file, with a new <POPULATION> element introduced
endangered_new_f = f'file:{os.getcwd()}/endangered_new.xml'

# apes, not matching the XSD  
endangered_apes_f = f'file:{os.getcwd()}/apes.xml'


schema_loc = '/tmp/schema_loc'
bad_rec_loc = 'file:/tmp/badrec_loc'
dbutils.fs.rm(schema_loc, True)
dbutils.fs.rm(bad_rec_loc, True)


# print(f'current working dir:{os.getcwd()}')

# COMMAND ----------

# MAGIC %md
# MAGIC This cell sets up the files and directories needed for the XML processing demo.
# MAGIC - `endangered_f` and `endangered_xsd_f` [reference XML]($./endangered_species.xml) and [XSD schema]($./endangered_species.xsd) files for endangered species data.
# MAGIC - `endangered_new_f` introduces a new XML element to test schema evolution. 
# MAGIC - `endangered_apes_f` is an XML file with a different structure that doesn't match the endangered species XSD schema.
# MAGIC - `schema_loc` is a directory where Auto Loader will store inferred schemas to enable schema evolution.

# COMMAND ----------

# DBTITLE 1,Pandas example
# pandas can load XML files too, but it's limitted to single node and not Spark

import pandas as pd
df = pd.read_xml("endangered_species.xml")
df

# COMMAND ----------

# MAGIC %md
# MAGIC For comparison, this cell shows how to read the endangered species XML into a pandas DataFrame.
# MAGIC Pandas provides a simple `read_xml` function to parse XML into a DataFrame, but Pandas doesn't scale and is limitted by memory.

# COMMAND ----------

# DBTITLE 1,Read XML list of endangered species with Spark
# `rowTag` option is required when reading files in XML format

df = (spark.read  
    .format("xml")
    .option("rowTag", "species")
    .load(endangered_f)
    )

# COMMAND ----------

# MAGIC %md
# MAGIC To read XML data into a **Spark DataFrame**, you need to specify the `"xml"` format.
# MAGIC The `"rowTag"` option is required and indicates which XML element represents a row in the DataFrame. 
# MAGIC Here, each `"species"` element will become a row.
# MAGIC The `load()` method reads the XML file specified by `endangered_f`.

# COMMAND ----------

# DBTITLE 1,XML attributes are flattened to _attribute 
display(df.select("name","_id","info"))

# COMMAND ----------

# MAGIC %md
# MAGIC When Spark reads XML, attributes are flattened into columns with a leading underscore.
# MAGIC For example, the `"id"` attribute becomes the `"_id"` column.
# MAGIC Selecting `"name"`, `"_id"`, and `"info"` columns shows the flattened structure.

# COMMAND ----------

# DBTITLE 1,Filter to only return name elements: set rowTag to "name"
df_names = (spark.read
    .format("xml") 
    .option("rowTag", "name")
    .load(endangered_f)
    )
display(df_names)

# COMMAND ----------

# MAGIC %md
# MAGIC You can use the `"rowTag"` option to control which elements are parsed as rows.
# MAGIC Setting `"rowTag"` to `"name"` will create a DataFrame with only the `"name"` elements as rows.
# MAGIC This is useful for filtering or extracting specific parts of the XML structure.

# COMMAND ----------

# DBTITLE 1,Load the movie XML with different structure and null values  
movie_df = (spark.read
    .format("xml")
    .option("rowTag", "species")
    .load(endangered_apes_f)  
    )
display(movie_df)

# COMMAND ----------

# MAGIC %md
# MAGIC This cell demonstrates reading an XML file (`endangered_apes_f`) with a different structure than the endangered species data.
# MAGIC The `"rowTag"` is set to `"Ape"` since those are the elements representing rows in this file.
# MAGIC The resulting DataFrame shows how Spark handles missing or null values in the XML.

# COMMAND ----------

# MAGIC %md
# MAGIC # XML Ingest with row validation (XML not matching)

# COMMAND ----------

# DBTITLE 1,Rejected movie XML with species XSD schema enforcement
from pyspark.sql.functions import col


movie_df = spark.read.format("xml")                     \
.option("rowTag", "species")                            \
.option("rescuedDataColumn", "_my_rescued_data")        \
.option("rowValidationXSDPath", endangered_xsd_f)       \
.load(endangered_apes_f)



if "_corrupt_record" in movie_df.columns:
    movie_df.cache()
    movie_df.select("_corrupt_record").show()

    


# COMMAND ----------

# MAGIC %md
# MAGIC Spark allows validating XML data against an XSD schema using the `"rowValidationXSDPath"` option.
# MAGIC This cell tries to load the apes XML file while enforcing the endangered species XSD schema.
# MAGIC Since the apes data does not conform to the endangered species schema, Spark will reject it.
# MAGIC tbd: check for corrupt records

# COMMAND ----------

# MAGIC
# MAGIC %md
# MAGIC # XML Ingest with row validation (happy path)

# COMMAND ----------

# DBTITLE 1,Original species XML with XSD validation  
df = spark.read.format("xml") \
        .option("rowTag", "species") \
        .option("rowValidationendangered_xsd_f", endangered_xsd_f) \
        .load(endangered_f)
        
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC To validate XML data against an [XSD schema]($./endangered_species.xsd), use the `"rowValidationXSDPath"` option.
# MAGIC Specify the path to the XSD file (`endangered_xsd_f`).
# MAGIC Spark will parse the XML and validate each row against the schema.
# MAGIC Rows that don't conform to the schema will be rejected.
# MAGIC The XSD does not impact the resulting DataFrame schema, it's only used for validation.

# COMMAND ----------

# MAGIC %md
# MAGIC # XML Ingest with Auto Loader

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

# MAGIC %md
# MAGIC Auto Loader allows streaming XML data and supports schema inference and evolution.
# MAGIC - Use `"cloudFiles.format"` to specify `"xml"` for XML data.
# MAGIC - `"rowTag"` indicates the XML elements to parse as rows.
# MAGIC - `"rowValidationXSDPath"` provides the XSD for validation.
# MAGIC - `"cloudFiles.schemaLocation"` specifies where to store the inferred schema for evolution.
# MAGIC
# MAGIC Uncomment `display(df)` to see the streaming DataFrame.

# COMMAND ----------

# DBTITLE 1,Auto Loader: old XSD, XML with NEW Element - will FAIL
# 

df = spark.readStream \
  .format("cloudFiles")  \
  .option("cloudFiles.format", "xml") \
  .option("rowTag", "species") \
  .option("rowValidationendangered_xsd_f", endangered_xsd_f) \
  .option("cloudFiles.schemaLocation", schema_loc) \
  .load(endangered_new_f)  

# COMMAND ----------

# MAGIC %md
# MAGIC This cell demonstrates a schema evolution failure.
# MAGIC - Auto Loader is set up with the original endangered species XSD.
# MAGIC - However, the XML file (`endangered_new_f`) introduces a new `<POPULATION>` element.
# MAGIC - Since the new element is not defined in the XSD, validation will fail.

# COMMAND ----------

display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC Displaying the streaming DataFrame will show the failure due to the schema mismatch.
# MAGIC Auto Loader cannot handle the new XML element because it's not defined in the original XSD schema.

# COMMAND ----------

# DBTITLE 1,SchemaEvolution for new cols ON
df = spark.readStream \
  .format("cloudFiles")  \
  .option("cloudFiles.format", "xml") \
  .option("rowTag", "species") \
  .option("rowValidationendangered_xsd_f", endangered_xsd_f) \
  .option("cloudFiles.schemaLocation", schema_loc) \
  .option("cloudFiles.schemaEvolutionMode", "addNewColumns") \
  .load(endangered_new_f)


# COMMAND ----------

# MAGIC %md
# MAGIC The default of `"cloudFiles.schemaEvolutionMode"` is `"addNewColumns"`. This allows Auto Loader to update the schema when new columns are encountered. For other settings see the [documentation for schemaEvolutionMode](https://docs.databricks.com/en/ingestion/auto-loader/schema.html#evolution). The inferred schema stored in `"cloudFiles.schemaLocation"` will be updated to include the new column.
# MAGIC Now Auto Loader can process the XML with the new `<POPULATION>` element.

# COMMAND ----------

display(df)  

# COMMAND ----------

# MAGIC %md
# MAGIC Displaying the streaming DataFrame now succeeds.
# MAGIC The DataFrame includes the new column representing the `<POPULATION>` element.
# MAGIC Auto Loader has evolved the schema to handle the change in the XML structure.

# COMMAND ----------

df.printSchema()

# COMMAND ----------

# MAGIC %md
# MAGIC Printing the DataFrame schema reveals the new column added through schema evolution.
# MAGIC Auto Loader inferred the new column and updated the schema stored in `"cloudFiles.schemaLocation"`.

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

# MAGIC %md
# MAGIC Spark SQL also supports creating tables directly from XML files.
# MAGIC - Use the `"CREATE TABLE"` statement with the `"USING XML"` clause.
# MAGIC - Specify the path to the XML file and the `"rowTag"` option to indicate the element for rows.
# MAGIC - The resulting table can be queried using standard SQL syntax.

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

# MAGIC %md
# MAGIC The `"schema_of_xml"` function in Spark SQL infers the schema of an XML string.
# MAGIC - Pass an XML string to the function, and it returns the corresponding schema.
# MAGIC - This is useful for exploring and understanding the structure of XML data.
# MAGIC - The inferred schema shows the hierarchy and data types of the XML elements and attributes.

# COMMAND ----------

# DBTITLE 1,SQL to_xml() function  
# MAGIC %sql
# MAGIC SELECT 
# MAGIC   to_xml(named_struct("species","Orangutan"))

# COMMAND ----------

# MAGIC %md
# MAGIC The `"to_xml"` function in Spark SQL converts a struct to an XML string.
# MAGIC - Use `"named_struct"` to create a struct with key-value pairs representing XML elements.
# MAGIC - Pass the struct to `"to_xml"`, and it returns the corresponding XML string.
# MAGIC - This is handy when you need to generate XML output from structured data in DataFrames or tables.
