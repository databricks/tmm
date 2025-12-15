
# Spark Declarative Pipelines: Installation & Tutorial

This guide outlines the steps to set up and run **Apache Spark Declarative Pipelines (SDP)** with PySpark on a local MacBook Pro and create a functional pipeline using only open-source tools. It utilizes `uv` for high-performance Python package management. At the time of this writing I was using the **Spark 4.0 Preview** build.

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

# install latest python e.g. python 3.14 here
brew install python@3.14 


# Create a virtual environment (defaults to .venv)
uv venv

# Activate the environment
source .venv/bin/activate
```

## 3. Install PySpark (Preview Build)

Declarative Pipelines require specific development builds of Spark 4.0.

```bash
# Install Spark 4.0 Preview (Dev build)
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
storage: file:///Users/frank/dev/oss_avionics/pipeline-storage
libraries:
  - glob:
      include: transformations/**
```

### 3. Data Ingestion (`transformations/ingest_flights.py`)

This Python file defines the ingestion logic. It utilizes the `OpenSkyDataSource` to pull data. The streaming table is created with using the `@dp.table` decorator.

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

### 4. Analytics Logic (`transformations/flights_analytics.sql`)

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

We pass the `spark.sql.catalogImplementation=hive` so the pipeline can be run repeatedly without removing existing storage files. 

```bash
spark-pipelines run \
  --spec spark-pipeline.yml \
  --conf spark.sql.catalogImplementation=hive
```

### 6. Inspecting the Output

After the pipeline runs, you can inspect the resulting Parquet files directly using `parquet-tools`. Here we look at the materialized view which provides a summary of all avionics data. 

**Note:** You will need to locate the specific Parquet file generated in your storage directory (e.g., `spark-warehouse/flights_stats/`). The filename hash (the part starting with `part-00000-...`) will differ on your machine, so use tab-completion to select the correct file.

```bash
parquet-tools cat spark-warehouse/flights_stats/part-00000-5a85e65d-ba84-478a-a29a-fa0358734899-c000.snappy.parquet | jq | head -50
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