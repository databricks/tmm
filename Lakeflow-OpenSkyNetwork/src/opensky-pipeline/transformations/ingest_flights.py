# OpenSky Network Stream Reader Configuration
# ------------------------------------------
# OAuth2 Auth options:
# - client_id: OpenSky Network API client ID (4000+ calls/day)
# - client_secret: OpenSky Network API client secret
# - Anonymous access: 100 calls/day limit (no credentials needed)
#
# Time options:
# - interval: Seconds between API calls (min 5 recommended)
#
# Region options (bounding box):
# - EUROPE
# - NORTH_AMERICA 
# - SOUTH_AMERICA
# - ASIA
# - AUSTRALIA
# - AFRICA
# - GLOBAL

# import and register the datasource
from pyspark_datasources import OpenSkyDataSource
spark.dataSource.register(OpenSkyDataSource)


REGION = "EUROPE"
INTERVAL = 5

CLIENT_ID = "my-api-client"

# get credentials from db secrets
CLIENT_SECRET = dbutils.secrets.get(scope="opensky", key="client_secret")

# Note, you can set the secret from the command line, use the following command:
# To create the secret scope 'opensky', run the following Databricks CLI commands in a terminal:
#
# databricks secrets create-scope opensky -p PROFILE_NAME
# databricks secrets put-secret opensky client_secret --string-value CLIENT_SECRET -p PROFILE_NAME



@dlt.expect("icao24_not_null", "icao24 IS NOT NULL")
@dlt.expect("lat_long_exist", "latitude IS NOT NULL AND longitude IS NOT NULL")

@dlt.table
def ingest_flights():
    return (
        spark.readStream
        .format("opensky")
        .option("region", REGION) 
        .option("client_id", CLIENT_ID) 
        .option("client_secret", CLIENT_SECRET) 
        .option("interval", INTERVAL) 
        .load()
    )




