# Tutorial: Databricks Genie for Data Engineers and Data Scientists

You inherit 696 million flight telemetry records: one UTC day, 54,093 aircraft. Your task is to understand the data, enforce quality rules, and make it useful.

This tutorial follows that workflow with Databricks Genie—from exploration to a pipeline to an app. **Genie Agents** turn natural-language questions into SQL, results, and charts. **Genie Code** generates pipeline and application code. You review the logic, validate the results, and decide what ships.

The workshop runs on [Databricks Free Edition](https://login.databricks.com/signup?provider=DB_FREE_TIER&dbx_source=lf_fm1).

## What you’ll build

- **Explore real data at scale.** Query 696 million OpenSky records through Delta Sharing, without first ingesting a copy.
- **Turn anomalies into quality rules.** Investigate missing values, outliers, and inconsistent measurements before defining pipeline constraints.
- **Deliver business and technical value.** Build regional analytics tables, deploy an app, and share data with a Python client.

## Access huge amounts of data via OpenSharing

The [OpenSky Network full-day dataset](https://opensky-network.org/) is available through [Databricks Marketplace](https://www.databricks.com/product/marketplace). [Open the listing](https://data-ai-lakehouse.cloud.databricks.com/marketplace/consumer/listings/feb64bf4-77a8-4f6a-8e21-94c51042e41f?o=2847375137997282) and add it to your workspace. In this workshop, it appears as the read-only Unity Catalog table `marketplace.opensky.state_vectors`, delivered through Delta Sharing.

The table contains approximately 696 million rows for March 1, 2026. Each row represents an aircraft state vector, with fields such as `latitude`, `longitude`, `velocity`, and `baro_altitude`.

Delta Sharing provides access to the provider’s data without requiring a persistent copy in your storage or an ingestion pipeline to maintain. Queries still transfer the data they read. Unity Catalog governs access in Databricks, while compatible clients can read shares through the open protocol.

## Profile the data before cleaning it

Exploratory data analysis (EDA) establishes what the data contains and where it needs attention. Check null rates, value ranges, and relationships between fields before deciding which records to reject.

Point [Genie](https://www.databricks.com/product/business-intelligence) at the table and ask:

~~~text
Run a comprehensive EDA for @state_vectors. Check key columns for nulls,
out-of-range values, and physically implausible values. List the issues
and explain them in the context of OpenSky aircraft telemetry.
~~~

In this walkthrough, Genie inspects the schema and runs 67 data-quality validations across the 696 million records. It groups the findings and explains potential anomalies: extreme velocities, unusual vertical rates, differences between barometric and geometric altitude, negative altitudes, and timestamp inconsistencies.

Review those explanations before turning them into constraints. An outlier is not necessarily an error: negative altitude, for example, can be valid depending on location and the altitude reference. The reviewed findings become the basis for pipeline quality rules.

![Genie's EDA on state_vectors: 67 data-quality validations across 696 million records, grouped by category.](docs/assets/02-genie-eda.png)

## Explore with SQL and charts

Once you understand the data’s limitations, investigate its patterns. [Genie Agents](https://www.databricks.com/product/business-intelligence) generate queries and visualizations from questions such as:

~~~text
For each aircraft, select its most recent position and plot it on a map.
Color each point by velocity using a red color scale.
~~~

The response includes SQL, query results, and a map. Follow-up questions retain context, so you can refine the analysis without rewriting each query.

Genie queries your Unity Catalog tables under the applicable access controls. The generated SQL makes the analysis inspectable—not automatically correct. Check how it handles timestamps, missing coordinates, and velocity units before relying on the visualization.

![A Genie Agent map: each aircraft at its most recent position across North America and the Caribbean, colored by velocity on a red scale.](docs/assets/03-genie-explore-velocity.png)

## Convert findings into a pipeline

A maintainable pipeline needs orchestration, incremental processing where supported, and data-quality enforcement. [Spark Declarative Pipelines (SDP)](https://www.databricks.com/product/data-engineering) lets you define datasets and transformations while the framework manages execution.

Ask Genie Code to generate a pipeline using the EDA findings:

~~~text
Create an SDP pipeline for the OpenSky data in marketplace.opensky.
Define data-quality expectations based on the reviewed EDA findings.
Separate rules that drop invalid rows from rules that retain and flag them.

Create one gold table for each region: Americas, EMEA, and APAC.
Add a materialized view with analytics summaries across the gold tables.
~~~

Genie Code proposes and implements a medallion architecture:

- **Bronze:** ingests the raw source records.
- **Silver:** applies quality constraints.
- **Gold:** organizes cleaned records into regional tables that feed a summary materialized view.

Strict expectations drop invalid rows; monitoring expectations record violations while retaining the data. Review the generated thresholds, regional boundaries, and null handling before running the pipeline.

The pipeline graph shows the dependencies and row counts at each stage. Compare bronze and silver counts with expectation metrics to verify that records are being dropped for the intended reasons.

![Pipeline graph: bronze flows into a cleaned silver table, which feeds three regional gold tables and a summary view.](docs/assets/04-pipeline-graph.png)

## Build an app on the gold tables

For users who do not query tables directly, an app makes the results accessible. Describe the source tables, loading behavior, and required views, then ask Genie Code to generate and deploy a [Databricks App](https://www.databricks.com/product/databricks-apps).

Databricks hosts the application, reducing the infrastructure you need to provision. Data access remains subject to the app’s configured identity and Unity Catalog permissions; review both before deployment.

The app can expose more than summary charts. Use it to explore flight trajectories, H3-based density maps, or holding patterns near an airport.

![A Databricks App: flight trajectories over Sydney, with holding-pattern loops on approach.](docs/assets/05-holding-patterns-SYD.png)

## Share data with a Python client

Cleaned data may support a model, a dashboard, or an analysis outside Databricks. Publish the required tables through [Delta Sharing](https://www.databricks.com/product/delta-sharing), then read them from a laptop using the open-source `delta-sharing` Python client. Neither Spark nor Java is required.

The workshop’s `receive_opensky.py` script lists shared tables, submits a predicate hint to help the server prune files, and loads the returned data into pandas. File pruning can reduce network transfer, but it is not equivalent to row-level filtering. Apply the required filter to the result and keep the requested subset small enough for local memory.

## What Genie automates with agentic AI, and what you own

The workflow stays the same: access, profile, explore, clean, serve, share. Genie reduces the translation work between steps—questions into SQL, findings into expectations, requirements into application code.

You still own the decisions: which anomalies indicate errors, which metrics answer the question, and which outputs are ready for production. Genie Agents generate analyses and charts; Genie Code generates implementation artifacts. Inspect the SQL, test the pipeline, and review the app before publishing.

## Try it

Follow the full workshop, [AI-powered Analytics of 700 Million OpenSky Records](README.md), on [Databricks Free Edition](https://login.databricks.com/signup?provider=DB_FREE_TIER&dbx_source=lf_fm1):

1. [Access OpenSky data through Marketplace](docs/01-marketplace.md)
2. [Profile data and investigate anomalies with Genie](docs/02-genie-eda.md)
3. [Explore and visualize with Genie Agents](docs/03-genie-explore.md)
4. [Build a pipeline with Genie Code](docs/04-pipeline.md)
5. [Build a Databricks App](docs/05-app.md)
6. [Read shared data locally](docs/06-opensharing.md)

## Further reading

- [Spark Declarative Pipelines: Getting Started](https://www.databricks.com/discover/how-to-get-started-with-spark-declarative-pipelines)
- [Databricks Apps: General Availability](https://www.databricks.com/blog/announcing-general-availability-databricks-apps)
- [Delta Sharing documentation](https://docs.databricks.com/aws/en/delta-sharing/)

---

_Author: Frank Munz · Updated 2026-09-10_