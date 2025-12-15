from pyspark.sql import SparkSession
from pyspark import pipelines as dp

# Get or create SparkSession for standalone OSS programs
spark = SparkSession.builder.appName("Avionics-Ingest").getOrCreate()

# import and register the OpenSky datasource 
from pyspark_datasources import OpenSkyDataSource
spark.dataSource.register(OpenSkyDataSource)

# declare a streaming table
@dp.table
def ingest_flights():
    return spark.readStream.format("opensky").load()