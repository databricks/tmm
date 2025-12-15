
# Spark Declarative Pipelines: Installation & Tutorial

This guide outlines the steps to set up and run SDP with PySpark on a local machine (specifically targeting macOS/Silicon). We will build a functional pipeline using Spark 4.1 Preview4, Java 17, and uv for high-performance Python package management, **relying entirely on open-source tools**.

<details>
<summary><strong>Click to expand: Part 1 - Installation Guide</strong></summary>

## 1. Prerequisites & System Tools

Before setting up the Python environment, ensure you have the necessary system-level dependencies.

**Important Note on Java:** Spark 4.x requires **Java 17**. It is strongly recommended to use exactly Java 17; higher versions (such as Java 21 or newer) are known to cause compatibility issues with this preview build.

```bash
# 1. Install Java 17
brew install openjdk@17

# 2. Link Java so the system finds it (Optional but recommended)
sudo ln -sfn /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk

# 3. Install uv (An extremely fast Python package installer and resolver)
brew install uv

# 4. Install Parquet tools (Useful for inspecting pipeline output files later)
brew install go-parquet-tools
```

## 2. Environment Setup

Create and activate a clean, isolated virtual environment using `uv`. By running the command without a name, `uv` defaults to creating a directory named `.venv`.

```bash

# install python 3.12 here
brew install python@3.12 


# Create a virtual environment (defaults to .venv)
uv venv

# Activate the environment
source .venv/bin/activate
```

## 3. Install PySpark (Preview Build)

Declarative Pipelines require specific development builds of Spark 4.1.

```bash
# Install Spark 4.1 Preview4 (Dev build)
uv pip install pyspark==4.1.0.dev4
```

## 4. Install Pipeline Dependencies

Install the required libraries to support Spark Connect, gRPC communication, and YAML configuration parsing.

```bash
# Core dependencies for Spark Connect and Pipelines
uv pip install grpcio grpcio-status protobuf pyarrow pandas

# Configuration, compression, and data source utilities
uv pip install PyYAML zstandard pyspark_data_sources
```

## 5. Verification

Verify that the installation was successful by checking the PySpark version inside your Python environment.

```bash
python -c "import pyspark; print(f'Spark Version: {pyspark.__version__}')"
```

</details>

---

## Part 2: Creating the Pipeline

To build the pipeline, you will need a code editor. You can use any editor you prefer, though **Visual Studio Code** or **Cursor** are highly recommended for their Python support.

### 1. Project Structure

Create a new directory for your project and organize your files according to the structure below. We will use a `transformations` subdirectory to keep our logic modular.

```text
.
├── spark-pipeline.yml
└── transformations
    ├── flights_analytics.sql
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

### 3. Streaming Table: Data Ingestion (`transformations/ingest_flights.py`)

This Python file defines the ingestion logic. It utilizes the `OpenSkyDataSource` custom PySpark datasource to pull live avionics data. The **Streaming Table** is created using the `@dp.table` decorator.

```python
from pyspark.sql import SparkSession
from pyspark import pipelines as dp

# Get or create SparkSession for standalone OSS programs
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

### 4. Materialized View: Analytics Logic (`transformations/flights_analytics.sql`)

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

Once your files are in place and your virtual environment is active (from Part 1), use the `spark-pipelines` CLI to execute the pipeline.

We pass the `spark.sql.catalogImplementation=hive`. This enables Spark to persist data locally between runs, allowing you to run the pipeline repeatedly without removing the existing storage files. 

```bash
spark-pipelines run \
  --spec spark-pipeline.yml \
  --conf spark.sql.catalogImplementation=hive
```

### 6. Inspecting the Output


### Inspecting the Streaming Table

You can run another Spark program that reads the datasets and outputs them. Here I'm using a command line tool for simplicity. After the pipeline runs, you can inspect the resulting Parquet files directly using `parquet-tools`. First, let's look at the raw data flowing into the system. It's captured in the **Streaming Table** (`ingest_flights`), which acts as an append-only log of all avionics data received. 

**Note:** The filename hash (the part starting with `part-00000-...`) will differ on your machine, so use tab-completion to select the correct file. Change the ```head -n XXX``` setting to see more data. 

```bash
parquet-tools cat spark-warehouse/ingest_flights/part-00000-0f904c51-3009-4a70-8e21-7bee16afb64f-c000.snappy.parquet | jq | head -n 24
```

**Example Output:**

```json
[
  {
    "baro_altitude": 1249.68,
    "callsign": "N6545H  ",
    "category": 0,
    "geo_altitude": 1203.96,
    "icao24": "a89ea5",
    "last_contact": "2025-12-08T14:57:15.000000000Z",
    "latitude": 33.183,
    "longitude": -102.6769,
    "on_ground": false,
    "origin_country": "United States",
    "sensors": null,
    "spi": false,
    "squawk": null,
    "time_ingest": "2025-12-08T14:57:15.000000000Z",
    "time_position": "2025-12-08T14:57:15.000000000Z",
    "true_track": 203.2,
    "velocity": 35.26,
    "vertical_rate": -0.33
  },
  {
    "baro_altitude": 10957.56,
    "callsign": "VIR3N   "
    ..
  
```

### Inspecting the Materialized View

Here we look at the materialized view which provides summary stats for all avionics data. 

**Note:** You will need to locate the specific Parquet file generated in your storage directory (e.g., `spark-warehouse/flights_stats/`). The filename hash (the part starting with `part-00000-...`) will differ on your machine, so use tab-completion to select the correct file.

```bash
parquet-tools cat spark-warehouse/flights_stats/part-00000-5a85e65d-ba84-478a-a29a-fa0358734899-c000.snappy.parquet 
```

**Example Output:**

```json
[
  {
    "max_altitude": 16855.44,
    "max_asc_rate": 73.8,
    "max_desc_rate": -165.81,
    "max_speed": 320.44,
    "num_events": 20574,
    "observation_duration": 261431,
    "unique_aircraft": 8939
  }
]
```