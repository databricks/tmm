

#Step-By-Step Instructions: Lakeflow Declarative Pipelines on Databricks
This resource is provided as-is. The Lakeflow UI is being improved continuously, so expect minor deviations from the steps below. I'm actually considering replacing this step-by-step guide with a video in the future. For the best learning experience follow and [bookmark this README](README.md).

---

### Step 1: Create a New ETL Pipeline

First, we need to set up the pipeline and define a schema where our tables will be stored.

1.  In the Databricks workspace, click the **+ New** button in the left sidebar.
2.  From the menu, select **ETL pipeline**.
3.  **Name your pipeline**. For this guide, we'll use `flights`.
4.  Next, we need to create a schema (a database) to hold our tables. Click on the default schema dropdown and select **Create new schema**.
5.  Enter `flights` as the **Schema name** and click **Create**.
6.  Your pipeline is now configured to use the `workspace.flights` schema.



### Step 2: Initialize the Pipeline with an Empty File

Lakeflow provides several ways to start, but we'll build from the ground up to see how easy it is.

1.  Under "Advanced options," select **Start with an empty file**.
2.  In the dialog, ensure **Python** is selected as the language for the first file.
3.  Click **Select**. You will now be in the Lakeflow Pipelines Editor.

### Step 3: Generate Ingestion Code with the AI Assistant

Instead of writing PySpark code manually, we'll use the built-in AI assistant to generate it for us.

1.  In the editor, you'll see a prompt to "Start typing or generate with AI". Click on it or use the keyboard shortcut (`Cmd + I` or `Ctrl + I`).
2.  Enter the following prompt to define a streaming table that reads from a custom data source named `opensky`:
    ```
    create streaming table @ingest_flights reading data stream from format opensky
    ```
3.  The AI Assistant will generate the complete Python code. Click **Accept** to add it to your editor.

Your editor should now contain the following code:
```python
# use OSS pyspark package for declarative pipelines
from pyspark import pipelines as dp

# import and register the datasource
from pyspark_datasources import OpenSkyDataSource
spark.dataSource.register(OpenSkyDataSource)


@dp.table(
  name="ingest_flights",
  comment="Streaming table ingesting data from opensky format"
)
def ingest_flights():
  return (
    spark.readStream
      .format("opensky")
      .load()
  )
```

### Step 4: Add Dependencies for the Custom Data Source

The `opensky` format is a custom PySpark data source. To use it, we must add its library as a dependency to our pipeline's environment.

1.  On the left, under "Pipeline configuration," click the **Settings** icon (the gear).
2.  In the "Pipeline settings" panel, find the **Environment** section and click **Edit environment**.
3.  Click **+ Add dependency**.
4.  Enter `pyspark-data-sources` as the package name.
5.  Click **Save**. This action is equivalent to running a `pip install`, but it's fully managed by Lakeflow.

### Step 5: Run the Pipeline and View the Ingested Data

With the code and dependencies in place, you're ready to run the pipeline.

1.  Click the **Run pipeline** button in the top right.
2.  The **Pipeline graph** on the right will start building. Lakeflow automatically analyzes the code, resolves dependencies, and provisions the necessary streaming infrastructure.
3.  Once the run is complete, you can see the `ingest_flights` table in the graph. Click on it to see a preview of the live data being ingested, including columns like `icao24`, `callsign`, `origin_country`, and coordinates.

### Step 6: Create a Materialized View for Analytics

Now that we have raw data streaming in, let's pre-compute some statistics using a SQL Materialized View.

1.  In the pipeline graph, click the **+** button on the `ingest_flights` table and select **Add dataset**.
2.  Choose **Materialized view** as the dataset type.
3.  Select **SQL** as the language and name the transformation `flights_stats`.
4.  Click **Create**. A new SQL file will be added to your pipeline.
5.  Replace the boilerplate code with the following SQL query. This query calculates the total number of events, unique aircraft, and other useful flight statistics.

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
FROM ingest_flights
```

6.  **Run the pipeline again**. Lakeflow automatically detects the new materialized view and updates the graph, placing `flights_stats` downstream of the raw data. The platform handles incremental updates, ensuring efficient processing.

### Step 7: Explore Data with AI/BI Genie

Finally, let's use AI/BI Genie to ask questions about our data using plain English.

1.  Navigate to **Genie** from the left sidebar.
2.  Click **+ New** to create a new Genie space.
3.  In the "Connect your data" dialog, select the **ingest_flights** table and click **Create**.
4.  Now, you can ask questions directly. Try the following prompts:
    *   **To create a histogram:**
        ```
        give me a histogram over the speed
        ```
    *   **To create a scatter plot:**
        ```
        plot the altitude vs velocity
        ```
    *   **To refine the plot:**
        ```
        use red colors
        ```
    *   **To create a map visualization:**
        ```
        plot the coordinates of the unique planes use altitude as color
        ```

Genie will translate your natural language questions into SQL queries, execute them, and generate the appropriate visualizations instantly.

## Conclusion

Congratulations! In just a few minutes, you have successfully built a complete, production-ready streaming data pipeline on Databricks. 