# Databricks notebook source
from pyspark.sql.functions import col

# Retrieve client_id and client_secret from Databricks secret scope
client_id = dbutils.secrets.get(scope="nasa-gcn", key="client_id")
client_secret = dbutils.secrets.get(scope="nasa-gcn", key="client_secret")


jaas_config =   f'kafkashaded.org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required \
                clientId="{client_id}" \
                clientSecret="{client_secret}" ;'

kafka_config = {
    'kafka.bootstrap.servers': 'kafka.gcn.nasa.gov:9092',
    'kafka.security.protocol': 'SASL_SSL',
    'kafka.sasl.mechanism': 'OAUTHBEARER',
    'kafka.sasl.oauthbearer.token.endpoint.url': 'https://auth.gcn.nasa.gov/oauth2/token',
    'kafka.sasl.jaas.config': jaas_config,
    'kafka.sasl.login.callback.handler.class': 'kafkashaded.org.apache.kafka.common.security.oauthbearer.secured.OAuthBearerLoginCallbackHandler',
    'startingOffsets': 'earliest'
}

topic = "gcn.classic.text.SWIFT_POINTDIR"

df = spark \
    .readStream \
    .format("kafka") \
    .options(**kafka_config) \
    .option("subscribe", topic) \
    .load()

df = df.withColumn("value", col("value").cast("string"))

result_df = df.select("topic", "offset", "timestamp", "value")


display(result_df)
