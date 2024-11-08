# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC ![img](misc/diag.png)

# COMMAND ----------

# DBTITLE 1,Kafka CX Details + API keys from secret scope
# kafka properties
BOOTSTRAP = "pkc-rgm37.us-west-2.aws.confluent.cloud:9092"
TOPIC = "cookie_topic"

# get api keys
confluentApiKey = dbutils.secrets.get(scope="fm-kafka-sink", key="confluentApiKey")
confluentSecret = dbutils.secrets.get(scope="fm-kafka-sink", key="confluentSecret")

# COMMAND ----------

# DBTITLE 1,Create Kafka Sink
import dlt
from pyspark.sql.functions import *
from pyspark.sql import DataFrame, Column

# ConfluentCloud is using Simple Authentication and Security Layer (SASL)

JAAS_CONFIG = f"kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username='{confluentApiKey}' password='{confluentSecret}' ;"

cx_properties = {
    "kafka.bootstrap.servers": BOOTSTRAP,
    "topic": TOPIC,
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.jaas.config": JAAS_CONFIG,
    "kafka.ssl.endpoint.identification.algorithm": "https",
    "kafka.sasl.mechanism": "PLAIN",
    "failOnDataLoss": "false",
}

# create a Kafka sink
dlt.create_sink(
    "my_kafka_sink",
    "kafka",
    cx_properties
)

# COMMAND ----------

# DBTITLE 1,Get Bakehouse Sales Transaction Stream
@dlt.table(
    name="cookie_sales",
    comment="Raw cookie sales stream",
    table_properties={"quality": "bronze"}
)
@dlt.expect_or_drop("totalPrice_non_null", "totalPrice IS NOT NULL")
def get_cookie_sales():
    # Create a temp Delta table
    return (spark.readStream 
        .format("delta") 
        .option("maxBytesPerTrigger", 500) 
        .option("maxFilesPerTrigger", 1) 
        .table("bakehouse.sales.transactions")
        .filter("totalPrice > 25")
    )

# COMMAND ----------

@dlt.append_flow(name = "cookie_sales_silver_appendflow", 
                 target = "my_kafka_sink", 
                 comment="Processed cookie sales with hourly aggregation")
def process_cookie_sales():
    df = dlt.read_stream("cookie_sales")
    return df.select(to_json(struct("dateTime", "product", "quantity","totalPrice")).alias("value"))
