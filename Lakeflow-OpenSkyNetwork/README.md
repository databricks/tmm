## Billions of Events, Thousands of Aircraft, One Simple Declarative Pipeline

![Aviation Data Processing Header](misc/header.gif)


This guide demonstrates how to architect an avionics IoT system that processes billions of events per day using Lakeflow Declarative Pipelines and a PySpark data source to ingest real aircraft tracking ADS-B data from OpenSky Network.

Our mini guide assumes you're following these steps interactively. There are also other options available like Databricks Asset Bundles for more advanced automation workflows.


### Key Features
- **IoT Streaming Data Architecture**: Process billions of avionics events in real-time
- **Simplicity**: Transform complex data engineering into maintainable code using declarative pipelines
- **AI-Powered Analytics**: Enable natural language queries on streaming IoT data

## Getting Started

### Prerequisites
- [Sign up for Databricks Free Edition](https://databricks.com/try-databricks)

## Code Snippets

### Streaming Table

Use the new Lakeflow Pipeline editor and create the following streaming table:



```python
@dlt.table
def ingest_flights():
    return spark.readStream.format("opensky").load()
```

### Environment Setup

The new Lakeflow IDE is working with files. Add the OpenSky data source to your environment (this is the equivalent of running pip install in notebook):

1. Open your pipeline
2. Navigate to Settings → Environment
3. Add the following package:
```
pyspark_datasources
```


## Visualization Options

- Use AI/BI Genie for instant dashboards with natural language
- Create custom visualizations with Databricks Apps using any modern web framework
- Build interactive maps with frameworks like Dash and OpenLayers

## Optional Configurations

I recommend running your streaming table from above first. Later, you can extend it with the options below, e.g. set the region to your continent if you are not in the U.S.

### Regional Filtering

The data source includes built-in regions for geographic filtering:
- AFRICA
- EUROPE
- NORTH_AMERICA
- GLOBAL (for worldwide coverage)

### Authentication

For production deployments, register for API credentials at https://opensky-network.org to increase rate limits:
- Anonymous: 100 calls per day
- Authenticated: 4,000 calls per day
- Data contributors: 8,000 calls per day

### Advanced Streaming Table Configuration

```python
@dlt.expect("icao24_not_null", "icao24 IS NOT NULL")
@dlt.expect_or_drop("coord_exist", "latitude IS NOT NULL AND longitude IS NOT NULL")
@dlt.table
def ingest_flights():
    return (
        spark.readStream
        .format("opensky")
        .option("region", "EUROPE")
        .option("client_id", CLIENT_ID)
        .option("client_secret", CLIENT_SECRET)
        .option("interval", INTERVAL)
        .load()
    )
```
### Materialized View

Use the new Lakeflow Pipeline editor and create the following materialized view:

```sql
CREATE MATERIALIZED VIEW flight_stats AS
  SELECT
  COUNT(*) AS num_events,
  COUNT(DISTINCT icao24) AS unique_aircraft,
  MAX(vertical_rate) AS max_asc_rate,
  MIN(vertical_rate) AS max_desc_rate,
  MAX(velocity) AS max_speed,
  MAX(geo_altitude) AS max_altitude,
  TIMESTAMPDIFF(SECOND, MIN(time_ingest),
                    MAX(time_ingest))
                    AS observation_duration
FROM ingest_flights
```

## Natural Language Queries

You can analyze the streaming data with AI/BI Genie with simple English queries:

- "How many unique flights are currently tracked?"
- "Plot altitude vs velocity for all aircraft"
- "Show the locations of all planes on a map"

## Learn More

- [Deep Dive Blog - comming soon!]
- [Video Guide - comming soon!]
- [OpenSky Network](https://opensky-network.org)
- [Spark Declarative Pipelines](https://www.databricks.com/blog/bringing-declarative-pipelines-apache-spark-open-source-project)
- [Lakeflow Documentation](https://docs.databricks.com/aws/en/dlt)
- [PySpark Custom Data Sources](https://docs.databricks.com/aws/en/pyspark/datasources)

## FAQ

<details>
<summary>Question: What about Lakeflow Connect and Jobs?</summary>

**Answer:**  
This tutorial is centered around Lakeflow Declarative Pipelines for data ingestion and transformation. In this example, the custom connector was provided for you. Lakeflow Connect can handle enterprise data ingestion from hundreds of source systems, such as databases, SaaS applications, and message queues, without writing custom connectors.

Lakeflow Jobs orchestrates complex workflows that combine multiple pipelines, machine learning models, and business processes across your entire data platform. In our example, Jobs could integrate the pipeline into the logistics workflow.
</details>

<details>
<summary>Question: This is a fascinating streaming use case, but can I use Declarative Pipelines also for batch?</summary>

**Answer:**  
Yes. The same code works for batch and streaming data. You can decide whether to run the pipeline continuously or trigger it, for example, every Friday afternoon at 3:30 PM. Data ingestion with streaming tables is always incremental, which means that batch data is only read once when it is new.
</details>

<details>
<summary>Question: Is it legal to access sensor data from flying planes?</summary>

**Answer:**  
Yes, it's legal to use the OpenSky Network API. They provide public access to their crowd-sourced aircraft data through their official REST API for private and academic usage. Please review their terms of use for any usage limitations or attribution requirements.
</details>

<details>
<summary>Question: After a while, I don't see any new avionic data coming in.</summary>

**Answer:**  
OpenSky Network operates on a fair use policy to keep its free service sustainable. Anonymous users face stricter rate limits that can cause data gaps during peak usage. Creating a free account significantly increases your request allowance. For even higher limits, you can contribute your own ADS-B receiver data to their network—contributors get priority access as a thank-you for helping expand coverage.
</details>

<details>
<summary>Question: How can I feed my own data to the OpenSky network?</summary>

**Answer:**  
The OpenSky Network website provides detailed setup guides and software to help you get your receiver operational and contribute to their global crowd-sourced aviation tracking system.
</details>
