# Databricks notebook source
# MAGIC %md
# MAGIC Welcome to the Compound AI Systems - Tools, Chains, and Agents lab
# MAGIC
# MAGIC There will be 3 main sections:
# MAGIC 1. General Scenario and Data Prep
# MAGIC 2. Function Creation and Testing
# MAGIC 3. Agent Creation and Testing
# MAGIC
# MAGIC Lets dive in!

# COMMAND ----------

data_storage_path = "/Workspace/Repos/nicolas.pelaez@databricks.com/tmm/sample_data/reviews.parquet"
#data_storage_path = '/Volumes/bakehouse/media/sample_data/reviews.parquet'

# Query the table and save the output as parquet
reviews_chunked_gold_df = spark.sql("SELECT * FROM bakehouse.media.reviews_chunked_gold")
reviews_chunked_gold_df.write.mode("overwrite").parquet(data_storage_path)

# Display the DataFrame to confirm
#display(reviews_chunked_gold_df)

# COMMAND ----------

import requests

# Step 1: Define the URL and Unity Catalog volume path
url = "https://github.com/databricks/tmm/raw/main/reviews.zip"

root_unity_catalog_path = '/Volumes/bakehouse/media/sample_data'

# Step 2: Download the file and directly upload to Unity Catalog volume using the Databricks API
response = requests.put(url)
api_url = f"https://e2-demo-field-eng.cloud.databricks.com/api/2.0/fs/files{unity_catalog_path}"
headers = {
    "Authorization": f"Bearer {dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()}"
}
response = requests.put(api_url, headers=headers, files={"file": response.content})

print(f"File downloaded and moved to Unity Catalog volume at {unity_catalog_path}")

# COMMAND ----------

import zipfile 
import os

catalog = "bakehouse"
schema = "media"
table_name = "reviews_chunked_gold"

# Load the data from the table
reviews_df = spark.table(f"{catalog}.{schema}.{table_name}")

uc_sample_data_dir = "/Volumes/bakehouse/media/sample_data"
parquet_file_path = os.path.join(uc_sample_data_dir, f"{table_name}.parquet")
zip_file_path = os.path.join(uc_sample_data_dir, f"{table_name}.zip")

# Write the DataFrame to a Parquet file
reviews_df.write.mode("overwrite").parquet(parquet_file_path)

# Zip the Parquet file
with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(parquet_file_path, os.path.basename(parquet_file_path))

# Display the DataFrame to confirm
display(reviews_df)

# COMMAND ----------

# MAGIC
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC retail_prod.ai.franchise_by_city (
# MAGIC   city_name STRING COMMENT 'City to be searched',
# MAGIC   country_name STRING COMMENT 'Country to be searched'
# MAGIC )
# MAGIC returns table(franchiseID BIGINT, name STRING, size STRING)
# MAGIC return
# MAGIC (SELECT franchiseID, name, size from retail_prod.sales.franchises where city=city_name and country=CASE 
# MAGIC     WHEN country_name IN ('USA', 'America', 'United States') THEN 'US' 
# MAGIC     ELSE country_name 
# MAGIC     END order by size desc)
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC retail_prod.ai.franchise_sales (
# MAGIC   franchise_id BIGINT COMMENT 'ID of the franchise to be searched',
# MAGIC   start_date STRING COMMENT 'Date to start searching sales'
# MAGIC )
# MAGIC returns table(total_sales BIGINT, total_quantity BIGINT, product STRING)
# MAGIC return
# MAGIC (SELECT SUM(totalPrice) AS total_sales, SUM(quantity) AS total_quantity, product 
# MAGIC FROM retail_prod.sales.transactions 
# MAGIC WHERE franchiseID = franchise_id AND dateTime > start_date GROUP BY product)

# COMMAND ----------

# MAGIC %sql
# MAGIC DROP FUNCTION retail_prod.media.franchise_reviews

# COMMAND ----------

# DBTITLE 1,This works but not with hosted funcs
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION retail_prod.media.franchise_reviews (short_description STRING)
# MAGIC RETURNS TABLE (reviews STRING)
# MAGIC LANGUAGE SQL
# MAGIC COMMENT 'Customer reviews for each franchise rating the store, the staff, and the product'
# MAGIC RETURN
# MAGIC  SELECT chunked_text as reviews FROM VECTOR_SEARCH(index => 'retail_prod.media.gold_reviews_test', query => short_description, num_results => 3) vs

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from retail_prod.media.franchise_reviews('Seattle Cookies')

# COMMAND ----------

from databricks.sdk import WorkspaceClient

host = WorkspaceClient().config.host
spark.sql('DROP FUNCTION IF EXISTS retail_prod.ai.franchise_reviews_with_secret;')
spark.sql(f'''
CREATE OR REPLACE FUNCTION retail_prod.ai.franchise_reviews_with_secret (short_description STRING, databricks_token STRING)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Returns customer reviews for each franchise rating the store, the staff, and the product'
AS
$$
  try:
    return databricks_token + short_description
  except Exception as e:
    return f"Error calling the vs index {{e}}"
$$;''')

# COMMAND ----------

from databricks.sdk import WorkspaceClient

host = WorkspaceClient().config.host
spark.sql('DROP FUNCTION IF EXISTS retail_prod.ai.franchise_reviews_with_secret;')
spark.sql(f'''
CREATE OR REPLACE FUNCTION retail_prod.ai.franchise_reviews_with_secret (short_description STRING, databricks_token STRING)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Returns customer reviews for each franchise rating the store, the staff, and the product'
AS
$$
  try:
    import requests
    headers = {{"Authorization": "Bearer "+databricks_token}}
    #Call our vector search endpoint via simple SQL statement
    response = requests.get("{host}/api/2.0/vector-search/indexes/retail_prod.media.gold_reviews_index/query", params ={{"columns":"chunked_text","query_text":short_description, "num_results":1}}, headers=headers).json()

    chunked_texts = [entry[0] for entry in response['result']['data_array']]
    return "Relevant Reviews: " .join(chunked_texts)
  except Exception as e:
    return f"Error calling the vs index {{e}}"
$$;''')

# COMMAND ----------

databricks_token = dbutils.secrets.get('dbdemos', 'llm-agent-tools')
spark.sql(f"select retail_prod.ai.franchise_reviews_with_secret('test', '{databricks_token}') as reviews").display()

# COMMAND ----------

# MAGIC %sql
# MAGIC DROP FUNCTION IF EXISTS retail_prod.ai.franchise_reviews;
# MAGIC CREATE OR REPLACE FUNCTION retail_prod.ai.franchise_reviews (short_description STRING)
# MAGIC RETURNS TABLE (reviews STRING)
# MAGIC LANGUAGE SQL
# MAGIC COMMENT 'Returns customer reviews for each franchise rating the store, the staff, and the product'
# MAGIC RETURN SELECT retail_prod.ai.franchise_reviews_with_secret(short_description,  secret('dbdemos', 'llm-agent-tools'));

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM retail_prod.ai.franchise_reviews('test')

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION retail_prod.ai.franchise_reviews (short_description STRING)
# MAGIC RETURNS STRING
# MAGIC LANGUAGE PYTHON
# MAGIC COMMENT 'Returns customer reviews for each franchise rating the store, the staff, and the product'
# MAGIC AS
# MAGIC $$
# MAGIC   try:
# MAGIC     
# MAGIC     #get the credentials needed to pull reviews
# MAGIC     #databricks_token = dbutils.secrets.get('dbdemos', 'llm-agent-tools')
# MAGIC
# MAGIC     headers = {"Authorization": f"Bearer {databricks_token}"}
# MAGIC     
# MAGIC     #Call our vector search endpoint via simple SQL statement
# MAGIC     #reviews = spark.sql(f"SELECT chunked_text as reviews FROM VECTOR_SEARCH(index => 'retail_prod.media.gold_reviews_index', query => {short_description}, num_results => 3")
# MAGIC
# MAGIC     return short_description
# MAGIC
# MAGIC   except:
# MAGIC     return "Review: I'm obsessed with Sweet Delights in Ballard, Seattle! Their specialty cookies are a game-changer. The Outback Oatmeal is chewy perfection, and the Austin Almond Biscotti is crunchy heaven. The Orchard Oasis is a refreshing twist on a classic. The staff is always friendly and helpful, and the store is spotless. Plus, they're open till 7pm on weekdays, making it the perfect after-work treat. Can't wait to try the Tokyo Tidbits and Pearly Pies next!
# MAGIC     
# MAGIC     Review: I recently visited the specialty cookie store in Capitol Hill, Seattle, and was thoroughly impressed! The Outback Oatmeal and Austin Almond Biscotti were exceptional, with the perfect balance of flavor and texture. The store was immaculate, and the staff was friendly and helpful. I appreciated the convenient extended hours and the central location, making it easy to pop in for a treat. The Orchard Oasis and Golden Gate Ginger were also standout options, and I can't wait to try the Tokyo Tidbits and Pearly Pies on my next visit. Highly recommend this gem for cookie lovers!
# MAGIC     
# MAGIC     Review: I'm obsessed with Sweet Delights in Ballard, Seattle! Their specialty cookies are a game-changer. The Outback Oatmeal is chewy perfection, and the Austin Almond Biscotti is crunchy heaven. The Orchard Oasis is a refreshing twist on a classic. The staff is always friendly and helpful, and the store is spotless. Plus, they're open till 7pm on weekdays, making it the perfect after-work treat. Can't wait to try the Tokyo Tidbits and Pearly Pies next!
# MAGIC     "
# MAGIC $$;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION retail_prod.ai.franchise_reviews (short_description STRING)
# MAGIC RETURNS STRING
# MAGIC LANGUAGE SQL
# MAGIC COMMENT 'Returns customer reviews for each franchise rating the store, the staff, and the product'
# MAGIC RETURN
# MAGIC   SELECT chunked_text as reviews FROM VECTOR_SEARCH(index => 'retail_prod.media.gold_reviews_index', query => 'Cookies Seattle', num_results => 3)

# COMMAND ----------



# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION retail_prod.ai.franchise_reviews (short_description STRING)
# MAGIC RETURNS STRING
# MAGIC LANGUAGE PYTHON
# MAGIC COMMENT 'Returns customer reviews for each franchise rating the store, the staff, and the product'
# MAGIC AS
# MAGIC $$
# MAGIC   try:
# MAGIC     
# MAGIC     import dbutils
# MAGIC     
# MAGIC     #get the credentials needed to pull reviews
# MAGIC     
# MAGIC     #databricks_token = dbutils.secrets.get('dbdemos', 'llm-agent-tools')
# MAGIC     #headers = {"Authorization": f"Bearer {databricks_token}"}
# MAGIC
# MAGIC     #Call our vector search endpoint via simple SQL statement
# MAGIC     
# MAGIC     #reviews = spark.sql(f"SELECT chunked_text as reviews FROM VECTOR_SEARCH(index => 'retail_prod.media.gold_reviews_index', query => {short_description}, num_results => 3")
# MAGIC
# MAGIC     return short_description
# MAGIC
# MAGIC   except:
# MAGIC     return "This failed"
# MAGIC $$;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION retail_prod.media.franchise_reviews(short_description STRING)
# MAGIC RETURNS STRING
# MAGIC LANGUAGE PYTHON
# MAGIC COMMENT 'This function generate an images and returns its content as base64. It also saves the image in the demo volume.'
# MAGIC AS
# MAGIC $$
# MAGIC   try:
# MAGIC     prompt = 'A lake made of data and bytes, going around a house: the Data Lakehouse'
# MAGIC     databricks_endpoint = f"{WorkspaceClient().config.host}/serving-endpoints/databricks-shutterstock-imageai/invocations"
# MAGIC
# MAGIC     databricks_token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
# MAGIC
# MAGIC     headers = {"Authorization": f"Bearer {databricks_token}"}
# MAGIC     jdata = {"prompt": prompt}
# MAGIC
# MAGIC     response = requests.post(databricks_endpoint, json=jdata, headers=headers).json()
# MAGIC     image_data = response['data'][0]['b64_json']
# MAGIC     image_id   = response['id']
# MAGIC
# MAGIC     # Assuming base64_str is the string value without 'data:image/jpeg;base64,'
# MAGIC     file_object=io.BytesIO(base64.decodebytes(bytes(image_data, "utf-8")))
# MAGIC     img = Image.open(file_object)
# MAGIC     # Convert to JPEG and upload to volumes
# MAGIC     # this actually works in a notebook, but not yet in a DBSQL UDF, which cannot connect to a volume
# MAGIC     img.save(f'/Volumes/mimiq_retail_prod/results/images/{image_id}.jpeg', format='JPEG') 
# MAGIC   except:
# MAGIC     return {"temperature_in_celsius": 25.0, "rain_in_mm": 0.0}
# MAGIC $$;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC retail_prod.ai.franchise_reviews (
# MAGIC   search_string STRING COMMENT 'Phrase to search for similar reviews',
# MAGIC   num_results INT COMMENT 'Number of relevant reviews to retrieve'
# MAGIC )
# MAGIC RETURNS STRING
# MAGIC LANGUAGE PYTHON
# MAGIC DETERMINISTIC
# MAGIC COMMENT 'Customer reviews for each franchise rating the store, the staff, and the product'
# MAGIC AS $$
# MAGIC   import requests
# MAGIC   import os
# MAGIC
# MAGIC   databricks_url = "https://e2-demo-field-eng.cloud.databricks.com"
# MAGIC   token = dbutils.secrets.get(scope="cookie-demo", key="pat") #this causes the function call to fail
# MAGIC   headers={"Authorization": f"Bearer {token}"}
# MAGIC
# MAGIC   try:
# MAGIC       response = requests.get(databricks_url+"/api/2.0/vector-search/indexes/retail_prod.media.gold_reviews_index/query", params ={"columns":"chunked_text","query_text":search_string,"num_results":num_results}, headers=headers).json()
# MAGIC       chunked_texts = [entry[0] for entry in response['result']['data_array']]
# MAGIC       return "Relevant Reviews: ".join(chunked_texts)
# MAGIC       
# MAGIC   except requests.exceptions.RequestException as e:
# MAGIC       return f"Error: {e}"
# MAGIC $$

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC retail_prod.ai.franchise_reviews (
# MAGIC   search_string STRING COMMENT 'Phrase to search for similar reviews',
# MAGIC   num_results INT COMMENT 'Number of relevant reviews to retrieve'
# MAGIC )
# MAGIC RETURNS STRING
# MAGIC LANGUAGE PYTHON
# MAGIC DETERMINISTIC
# MAGIC COMMENT 'Customer reviews for each franchise rating the store, the staff, and the product'
# MAGIC AS $$
# MAGIC   import requests
# MAGIC   import os
# MAGIC
# MAGIC   databricks_url = "https://e2-demo-field-eng.cloud.databricks.com"
# MAGIC   
# MAGIC   ## Usage:
# MAGIC   ##  This function calls a Vector Search endpoint directly to retrieve relevant results
# MAGIC   ##
# MAGIC   ##  search_string: The phrase to search for similar reviews
# MAGIC   ##  example input: "What are people saying about the Outback Oatmeal in my Seattle stores"
# MAGIC   ##  num_results: The number of relevant reviews to retrieve
# MAGIC   ##  example input: 5
# MAGIC   ##  
# MAGIC
# MAGIC
# MAGIC   token = ####
# MAGIC   headers={"Authorization": f"Bearer {token}"}
# MAGIC
# MAGIC   try:
# MAGIC       response = requests.get(databricks_url+"/api/2.0/vector-search/indexes/retail_prod.media.gold_reviews_index/query", params ={"columns":"chunked_text","query_text":search_string,"num_results":num_results}, headers=headers).json()
# MAGIC       chunked_texts = [entry[0] for entry in response['result']['data_array']]
# MAGIC       return "Relevant Reviews: ".join(chunked_texts)
# MAGIC       
# MAGIC   except requests.exceptions.RequestException as e:
# MAGIC       return f"Error: {e}"
# MAGIC $$
