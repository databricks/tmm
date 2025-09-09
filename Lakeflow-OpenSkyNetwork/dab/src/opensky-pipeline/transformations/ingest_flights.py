# use OSS pyspark package for declarative pipelines
from pyspark import pipelines as dp

# import and register the datasource
from pyspark_datasources import OpenSkyDataSource
spark.dataSource.register(OpenSkyDataSource)


REGION = "EUROPE"
INTERVAL = 5


# get your own client ID for more OpenSky Network tokens
# see: https://openskynetwork.github.io/opensky-api/rest.html
# and https://www.databricks.com/blog/processing-millions-events-thousands-aircraft-one-declarative-pipeline
CLIENT_ID = "my-api-client"

#CLIENT_SECRET = dbutils.secrets.get(scope="opensky", key="client_secret")


@dp.table
def ingest_flights():
    return (
        spark.readStream
        .format("opensky")
        .option("region", REGION) 
        .load()
    )




