from pyspark.sql import SparkSession

spark = (
    SparkSession.builder.config(
        "spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5"
    )
    .appName("example")
    .getOrCreate()
)

kafka = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "kafka.gcn.nasa.gov:9092")
    .option("kafka.security.protocol", "SASL_SSL")
    .option(
        "kafka.sasl.jaas.config",
        "org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required "
        # Connect as a consumer (client "gcn_kafka")
        # Warning: don't share the client secret with others.
        'clientId="23lgm07rtt06qefioiod9el8s8" '
        'clientSecret="jqi7bmh6ca6uv4jhnd31nmf0l98h45fqp3bc905ikjqp80g886m";',
    )
    .option(
        "kafka.sasl.login.callback.handler.class",
        "org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginCallbackHandler",
    )
    .option("kafka.sasl.mechanism", "OAUTHBEARER")
    .option(
        "kafka.sasl.oauthbearer.token.endpoint.url",
        "https://auth.gcn.nasa.gov/oauth2/token",
    )
    .option("subscribe", "gcn.circulars")
    .load()
)

query = kafka.writeStream.format("console").start()
query.awaitTermination()
