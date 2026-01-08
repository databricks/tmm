
# Getting Started with Open Source Spark Declarative Pipelines (SDP)  

This project builds a simple and fun Spark Declarative Pipeline consisting of just two powerful components: a streaming table and a materialized view. First, the streaming table uses a Custom PySpark Datasource to continuously fetch live flight data from the OpenSky API, building a permanent history of every aircraft position, altitude and velocity. Then, the materialized view reads that stream to create a "current state" board of the global airspace.

This guide outlines the steps to set up and run SDP with PySpark on a local machine. We will build a functional pipeline using Spark 4.1 Preview4, Java 17, and uv for high-performance Python package management, **relying entirely on open-source tools**.

![Aviation Data Processing Header](misc/SDP_anim.gif)

<details>
<summary><strong>Click to expand: Part 1 - Local Installation of OSS Spark Declarative Pipelines</strong></summary>

## 1. Prerequisites & System Tools for SDP

I'm describing the steps here for my MacBook Pro with MacOS with homebrew. Depending on your operating system, the commands might be slightly different for you.

Before setting up the Python environment, ensure you have the necessary system-level dependencies:

**Important Note on Java:** Spark 4.x requires **Java 17**. It is recommended to use Java 17; higher versions (such as Java 21 or newer) are known to cause compatibility issues with this preview build.

```bash
# 1. Install Java 17
brew install openjdk@17

# 2. Link Java so the system finds it (Optional but recommended, make sure JDK17 is used)
sudo ln -sfn /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk

# 3. Install uv (An extremely fast Python package installer and resolver)
brew install uv

```

## 2. Environment Setup

Create and activate a clean, isolated virtual environment using `uv`. By running the command without a name, `uv` defaults to creating a directory named `.venv`.

```bash

# install python 3.12 here
brew install python@3.12 


# Create a virtual environment (defaults to .venv)
uv venv --python 3.12 --seed

# Activate the environment
source .venv/bin/activate
```

## 3. Install PySpark (Preview Build)

Declarative Pipelines require specific development builds of Spark 4.1.

```bash
# Install Spark 4.1 
uv pip install pyspark[pipelines]
```



## 4. Verification

Verify that the installation was successful by checking the PySpark version inside your Python environment.

```bash
python -c "import pyspark; print(f'Spark Version: {pyspark.__version__}')"
```

</details>

---

## Part 2: Creating your first Spark Declarative Pipeline

To build the pipeline, you will need a code editor. You can use any editor you prefer such as vim, zed, or Sublime Text, however I recommend **Visual Studio Code** (or **Cursor**) for their Python support.

### 1. SDP Project Structure

Create a new directory for your project and organize your files according to the structure below. We will use a `transformations` subdirectory to keep our transformation logic organized.

```text
.
├── spark-pipeline.yml
└── transformations
    ├── flights_stats.sql
    └── ingest_flights.py
```

### 2. Pipeline Definition (`spark-pipeline.yml`)

This YAML file acts as the manifest for your pipeline. It defines the pipeline name, the storage location for checkpoints and data, and references the Python and SQL files with transformation logic.

**Note:** Update the `storage` path to a valid absolute path on your local machine.

```yaml
name: avionics-pl
# UPDATE THE PATH BELOW to your local absolute path
storage: file:///Users/<YOUR_USERNAME>/dev/oss_avionics/pipeline-storage
libraries:
  - glob:
      include: transformations/**
```

### 3. SDP Streaming Table: Data Ingestion (`transformations/ingest_flights.py`)

This Python file defines the ingestion logic. It utilizes the `OpenSkyDataSource` custom PySpark datasource to pull live avionics data. The **Streaming Table** is created using the `@dp.table` decorator.

```python
from pyspark.sql import SparkSession
from pyspark import pipelines as dp

# Get or create SparkSession for standalone Spark programs
spark = SparkSession.builder.appName("Avionics-Ingest").getOrCreate()

# Import and register the OpenSky datasource 
from pyspark_datasources import OpenSkyDataSource
spark.dataSource.register(OpenSkyDataSource)

# Declare a streaming table
@dp.table
def ingest_flights():
    # Read from the OpenSky source into a stream
    return spark.readStream.format("opensky").load()
```

### 4. SDP Materialized View: Analytics Logic (`transformations/flights_stats.sql`)

This SQL file defines a **Materialized View**. It aggregates the raw streaming data from `ingest_flights` to calculate statistics such as unique aircraft counts, vertical rates, and observation duration.

```sql
CREATE MATERIALIZED VIEW flights_stats AS
  SELECT
    COUNT(*) AS num_events,
    COUNT(DISTINCT icao24) AS unique_aircraft,
    MAX(vertical_rate) AS max_asc_rate,
    MIN(vertical_rate) AS max_desc_rate,
    MAX(velocity) AS max_speed,
    MAX(geo_altitude) AS max_altitude,
    TIMESTAMPDIFF(SECOND, MIN(time_ingest), MAX(time_ingest)) AS observation_duration
  FROM ingest_flights;
```

### 5. Running the Pipeline

Once your files with the transformation logic and the pipeline definition are in place and your virtual environment is active (see part 1), use the `spark-pipelines` CLI to execute the pipeline.

We pass the `spark.sql.catalogImplementation=hive`. This enables Spark to persist data locally between runs, allowing you to run the pipeline repeatedly without removing the existing storage files. 

```bash
spark-pipelines run \
  --conf spark.sql.catalogImplementation=hive
```

### 6. Inspecting the Output

After the pipeline runs, you can query the streaming table and materialized view directly using PySpark to verify the data. Start a PySpark shell or create a simple Python script to inspect the results.

#### Inspecting the Streaming Table

The **Streaming Table** (`ingest_flights`) contains the raw avionics data, acting as an append-only log of all flight events received from the OpenSky Network.

```python
spark.read.table("ingest_flights").limit(3).show(truncate=False)
```

**Example Output:**

```
+-------------------+------+--------+--------------+-------------------+-------------------+---------+--------+------------+---------+--------+----------+-------------+-------+-------------+------+-----+--------+
|time_ingest        |icao24|callsign|origin_country|time_position      |last_contact       |longitude|latitude|geo_altitude|on_ground|velocity|true_track|vertical_rate|sensors|baro_altitude|squawk|spi  |category|
+-------------------+------+--------+--------------+-------------------+-------------------+---------+--------+------------+---------+--------+----------+-------------+-------+-------------+------+-----+--------+
|2025-12-15 17:36:07|a5f852|RTY484  |United States |2025-12-15 17:36:06|2025-12-15 17:36:06|-105.0557|40.4841 |1752.6      |false    |46.2    |37.76     |0.0          |NULL   |1813.56      |NULL  |false|0       |
|2025-12-15 17:36:07|ac1c12|N88G    |United States |2025-12-15 17:36:06|2025-12-15 17:36:06|-81.0734 |29.5859 |7924.8      |false    |149.2   |149.54    |0.0          |NULL   |8206.74      |1625  |false|0       |
|2025-12-15 17:36:07|ac96b8|AAL2192 |United States |2025-12-15 17:36:06|2025-12-15 17:36:06|-107.663 |36.5943 |10363.2     |false    |233.33  |293.8     |0.0          |NULL   |10713.72     |NULL  |false|0       |
+-------------------+------+--------+--------------+-------------------+-------------------+---------+--------+------------+---------+--------+----------+-------------+-------+-------------+------+-----+--------+
```

#### Inspecting the Materialized View

The **Materialized View** (`flights_stats`) provides aggregated statistics computed from the streaming table, including counts of events and aircraft, maximum speeds, altitudes, and observation duration.

```python
spark.read.table("flights_stats").limit(3).show(truncate=False)
```

**Example Output:**

```
+----------+---------------+------------+-------------+---------+------------+--------------------+
|num_events|unique_aircraft|max_asc_rate|max_desc_rate|max_speed|max_altitude|observation_duration|
+----------+---------------+------------+-------------+---------+------------+--------------------+
|39750     |9276           |101.44      |-125.5       |430.07   |38191.44    |1803                |
+----------+---------------+------------+-------------+---------+------------+--------------------+
```

## Resources

* Did you like the OSS Apache SDP example above? If you are interested, you can run the same [streaming aviation data SDP tutorial on Databricks Free Edition](https://github.com/databricks/tmm/blob/main/Lakeflow-OpenSkyNetwork/README.md) which comes with the built-in pipeline editor and includes serverless compute, dashboards, natural language queries on streaming data, and governance.
* [This blog](https://www.databricks.com/blog/processing-millions-events-thousands-aircraft-one-declarative-pipeline) provides more details about Databricks and the OpenSky Network.  
