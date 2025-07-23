
# Billions of Avionic Events, Thousands of Aircraft, One Simple Declarative Pipeline

![Aviation Data Processing Header](misc/header.gif)




This repository is a small, self-contained example that you can easily run yourself using the Databricks Free Edition. It demonstrates how to build an IoT pipeline with Lakeflow streaming tables, materialized views, AI-powered queries, and Databricks Apps for visualization. Using real-time ADS-B aircraft data from OpenSky Network, you’ll see how to set up ingestion, aggregation, and interactive analytics—all with minimal setup.

---


### Key Features
- **IoT Streaming Data at Scale:** Ingest, process, and analyze billions of real-time avionics events from aircraft globally.
- **Declarative Simplicity:** Focus on *what* you want to build, not *how* to wire it together—Lakeflow handles orchestration, dependencies, and incremental processing.
- **AI-Driven Analytics:** Unlock natural language queries and rapid insights from streaming data.
- **Built for Databricks Free Edition:** No paid account required to get started.

---

## Prerequisites
- [Sign up for Databricks Free Edition](https://signup.databricks.com/?provider=DB_FREE_TIER&dbx_source=lf_fm1)
- [Get familiar with the Lakeflow Pipeline Editor](https://docs.databricks.com/aws/en/dlt/dlt-multi-file-editor)

---

## Show Me the Code

### Streaming Table (Live Aircraft Feed)

The Lakeflow IDE works with files. The first file will be a streaming table in Python that ingests live aircraft positions from the OpenSky Network in real-time. Use the Lakeflow Pipeline Editor to create it:

```python

# import and register the datasource
from pyspark_datasources import OpenSkyDataSource
spark.dataSource.register(OpenSkyDataSource)

# declare a streaming table 
@dlt.table
def ingest_flights():
    return spark.readStream.format("opensky").load()

```

#### Environment Setup

Next, you need to add the OpenSky data source to your environment. Note, this is the equivalent of `pip install` in a notebook (but remember, we are working with files)

1. In your pipeline, navigate to **Settings → Environment**.
2. Add the following package:
   ```
   pyspark-data-sources
   ```

---

### Materialized View (Aggregated Flight Statistics)

The materialized view summarizes and aggregates flight statistics for analytics and dashboards, making it easy to power visualizations and BI queries. We will code the materialized view on plain SQL.

```sql
-- create a materialized view in SQL
CREATE MATERIALIZED VIEW flight_stats AS
  SELECT
    COUNT(*) AS num_events,
    COUNT(DISTINCT icao24) AS unique_aircraft,
    MAX(vertical_rate) AS max_asc_rate,
    MIN(vertical_rate) AS max_desc_rate,
    MAX(velocity) AS max_speed,
    MAX(geo_altitude) AS max_altitude,
    TIMESTAMPDIFF(SECOND, MIN(time_ingest), MAX(time_ingest)) AS observation_duration
  FROM ingest_flights
```

---
## Run the Pipeline

Run the pipeline. Then explore the pipeline graph, click on the nodes of the graph, and the performance and data tabs at the bottom of the IDE. 

---
## Visualization Options

- Use AI/BI Genie for instant dashboards and natural language insights.
- Build custom visualizations with Databricks Apps using any modern web framework.
- Create interactive real-time maps with frameworks like Dash and OpenLayers.

---

## Optional Configurations

The example above is standalone and should work out of the box for most users. However, you may want to fine-tune your pipeline for specific regions, authentication, or advanced data filtering. Consider these configuration options:

### Regional Filtering

The data source provides built-in regions to limit data to your area of interest:
- AFRICA
- EUROPE
- NORTH_AMERICA
- GLOBAL (for worldwide coverage)

### Authentication

For production and higher rate limits, register for API credentials at [opensky-network.org](https://opensky-network.org):
- Anonymous: 100 calls per day
- Authenticated: 4,000 calls per day
- Data contributors: 8,000 calls per day

### Advanced Streaming Table Configuration

```python
from pyspark_datasources import OpenSkyDataSource
spark.dataSource.register(OpenSkyDataSource)

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

---

## Natural Language Queries

Query your streaming data using AI/BI Genie, just by typing questions like:

- "How many unique flights are currently tracked?"
- "Plot altitude vs. velocity for all aircraft."
- "Show the locations of all planes on a map."

![Aviation Data Processing Genie](misc/genie.png)

---

## Databricks Apps

Databricks Apps let you quickly create web front-ends and dashboards powered by your data pipeline. The example dashboard below and the animation in the header were both created using Databricks Apps and a timelapse function.

![Aviation Data Processing Stats](misc/stats.png)

---

## Learn More

- [Deep Dive Blog – coming soon!]
- [Video Guide – coming soon!]
- [OpenSky Network](https://opensky-network.org)
- [Feed your own data to OpenSky](https://opensky-network.org/feed) 
- [Spark Declarative Pipelines](https://www.databricks.com/blog/bringing-declarative-pipelines-apache-spark-open-source-project)
- [Lakeflow Documentation](https://docs.databricks.com/aws/en/dlt)
- [PySpark Custom Data Sources](https://docs.databricks.com/aws/en/pyspark/datasources)

---


## FAQ


<details>
<summary>What about Lakeflow Connect and Jobs?</summary>

**Answer:**  
This project focuses on Lakeflow Declarative Pipelines for data ingestion and transformation. In this example, the custom connector is provided for you. Lakeflow Connect can orchestrate large-scale ingestion from databases, SaaS apps, and message queues—no custom code required. Lakeflow Jobs helps you schedule, orchestrate, and manage complex workflows that combine pipelines, ML models, and business processes across your data platform. For example, you could use Jobs to integrate these pipelines into a broader logistics workflow.
</details>

<details>
<summary>Can I use Declarative Pipelines for batch processing as well as streaming?</summary>

**Answer:**  
Yes! The same code works for both batch and streaming data. You can choose to run the pipeline continuously or schedule it at specific times (for example, every Friday at 3:30 PM). Streaming tables always ingest data incrementally, so batch data is only read once when it's new.
</details>

<details>
<summary>Is it legal to access sensor data from flying planes?</summary>

**Answer:**  
Yes, it’s legal to use the OpenSky Network API. They provide public access to crowd-sourced aircraft data for private and academic use via their official REST API. Be sure to review their [terms of use](https://opensky-network.org/about/terms-of-use) for any specific limitations or attribution requirements.
</details>

<details>
<summary>Why might I stop seeing new avionic data coming in after a while?</summary>

**Answer:**  
OpenSky Network enforces a fair use policy to keep its free service sustainable. Anonymous users face stricter rate limits, which can cause data gaps during peak usage. Creating a free account increases your request allowance. For even higher limits, contribute your own ADS-B receiver data—contributors get priority access and help expand global coverage.
</details>

<details>
<summary>How can I feed my own data to the OpenSky Network?</summary>

**Answer:**  
The OpenSky Network website offers [detailed setup guides and software](https://opensky-network.org/feed) so you can get your receiver online and contribute to their global, crowd-sourced aviation tracking system. Time to dust off that old Raspberry Pi in your drawer. 
</details>
