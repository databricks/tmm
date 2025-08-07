# import and register the datasource

from pyspark_datasources import OpenSkyDataSource
spark.dataSource.register(OpenSkyDataSource)


REGION = "EUROPE"
INTERVAL = 5

CLIENT_ID = "my-api-client"

#CLIENT_SECRET = dbutils.secrets.get(scope="opensky", key="client_secret")


@dlt.table
def ingest_flights():
    return (
        spark.readStream
        .format("opensky")
        .option("region", REGION) 
        .load()
    )




