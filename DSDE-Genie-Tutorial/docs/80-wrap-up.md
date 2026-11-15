# 12. How do I wrap up and take this tutorial further?

## What you did

In eleven steps you went from a shared Marketplace dataset to a governed app, self-service analytics, and data anyone can receive locally, mostly from plain-English prompts instead of hand-written code:

![Reference architecture for the tutorial: the OpenSky Marketplace listing (696M rows, one UTC day) attaches as the read-only Unity Catalog table marketplace.opensky.state_vectors; Genie Code and a Genie Agent explore it, and an AI/BI Dashboard with Ask Genie reads it through a SQL warehouse; a Declarative Automation Bundle wraps the Lakeflow Job, which orchestrates the Spark Declarative Pipeline (bronze → silver with data-quality expectations → gold_americas / gold_emea / gold_apac → gold_analytics_regional_summary) and a follow-on notebook on an hourly schedule; an ML step trains on the silver table, compares three models in MLflow, registers flight_phase_model @prod in Unity Catalog, and batch-scores gold_flight_phase_predictions; a SQL Warehouse and a Databricks App serve gold_apac; and an optional OpenSharing path filters a sample at the source into a local pandas DataFrame — all under the Unity Catalog governance plane.](assets/80-wrapup-flow.png)

1. **[Databricks Marketplace](10-marketplace.md):** attached the OpenSky avionics data (696M rows, one full UTC day, 54,093 aircraft) as a read-only Unity Catalog table over Delta Sharing, with no copy and no ETL.
2. **[Genie Agents, EDA](20-genie-eda.md):** profiled the data in plain English, confirmed the key columns, and surfaced its data-quality issues across 696M records.
3. **[Genie Agents, explore & visualize](30-genie-explore.md):** created the **OpenSky Genie** agent from a prompt, answered business questions, and got back charts and maps.
4. **[AI/BI Dashboard](35-dashboard.md):** generated the **OpenSky Flights** dashboard with Genie Code and linked the Genie Agent in as **Ask Genie**.
5. **[Spark Declarative Pipeline](40-pipeline.md):** turned the EDA findings into enforced expectations and cleaned the data into per-region gold tables (`gold_americas`, `gold_emea`, `gold_apac`) plus an analytics summary.
6. **[Lakeflow Job](50-job.md):** wrapped `opensky_pipeline` in `opensky_job`, a scheduled, multi-task job that retries on failure and notifies you when a run breaks.
7. **[Declarative Automation Bundle](52-dabs.md):** turned the pipeline and job into version-controlled YAML and deployed it to `dev` from the workspace.
8. **[ML model](54-ml.md):** trained a flight-phase classifier on the silver table, compared three models in MLflow, and registered the winner in Unity Catalog as `flight_phase_model@prod`.
9. **[Genie One on mobile](55-mobile.md):** queried the data from your phone with the Genie One mobile app, same governance as the web.
10. **[Databricks App](60-app.md):** built a governed app on a gold table and visualized APAC flight routes on a zoomable map.
11. **[OpenSharing](70-opensharing.md):** received the shared data on a plain laptop with the open-source Python client, no Spark and no Java.

## Clean up

To undo everything on Free Edition:

- Delete the **[Databricks Apps](60-app.md)** (`opensky-flights`, and `opensky-flight-dna` if you built it).
- Delete the `flight_phase_model` model, its MLflow experiment, and `gold_flight_phase_predictions` from the **[ML step](54-ml.md)**.
- Delete the `[dev]` pipeline and job deployed by the **[bundle](52-dabs.md)**, then the `opensky_bundle` Git folder.
- Delete the **[Lakeflow Job](50-job.md)** (`opensky_job`).
- Delete the **[pipeline](40-pipeline.md)** (`opensky_pipeline`) and its gold tables.
- Delete the **OpenSky Flights** [dashboard](35-dashboard.md), the **OpenSky Genie** agent, and any metric views it created in `workspace.default`.
- Remove the **[Marketplace](10-marketplace.md)** catalog (`marketplace`) from Catalog Explorer.
- On your laptop, delete the `opensky.share` credential file from [OpenSharing](70-opensharing.md). It carries a bearer token, so treat it as a secret.

## Take it further

- **Extend the Lakeflow Job:** add **alerts** on the pipeline's data-quality expectations and chain in more downstream tasks.
- **Enrich the Genie Agent** with your own instructions and example SQL, then share it.
- **Extend the app** to all three regions, not just APAC.
- **From static data to streaming:** this tutorial uses static data from Databricks Marketplace, but streaming is where Databricks leads. The same kind of feed can be ingested into an SDP pipeline from a custom PySpark data source, as shown in [Processing millions of events from thousands of aircraft in one Declarative Pipeline](https://www.databricks.com/blog/processing-millions-events-thousands-aircraft-one-declarative-pipeline).
- **Real-time in production:** Databricks works with some of the world's largest avionics organizations to build real-time streaming applications such as air-traffic-control systems. See the [air-traffic-control with Spark Structured Streaming (Real-Time Mode)](https://www.databricks.com/resources/demos/videos/air-traffic-control-with-apache-spark-structured-streaming-real-time-mode?itm_data=demo_center) demo in the Databricks Demo Center.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [11. OpenSharing](70-opensharing.md) | [Table of contents](index.md) | — |

---

_Author: [Frank Munz](https://www.linkedin.com/in/frankmunz/) · Updated 2026-11-15 ·  [anchor page: "Tutorial: Databricks Genie for Data Engineers and Data Scientists"](https://community.databricks.com/t5/technical-blog/tutorial-databricks-genie-for-data-engineers-and-data-scientists/ba-p/168969)_
