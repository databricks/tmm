# 8. Wrap-up & next steps

## What you did

In seven steps you went from a shared Marketplace dataset to a governed app, self-service analytics, and data anyone can receive locally, mostly from plain-English prompts instead of hand-written code:

1. **[Databricks Marketplace](10-marketplace.md):** attached the OpenSky avionics data (696M rows, one full UTC day, 54,093 aircraft) as a read-only Unity Catalog table over Delta Sharing, with no copy and no ETL.
2. **[Genie Agents, EDA](20-genie-eda.md):** profiled the data in plain English and surfaced its data-quality issues across 696M records.
3. **[Genie Agents, explore & visualize](30-genie-explore.md):** answered business questions and got back charts and maps, with no dashboard to build.
4. **[Spark Declarative Pipeline](40-pipeline.md):** turned the EDA findings into enforced expectations and cleaned the data into per-region gold tables (`gold_americas`, `gold_emea`, `gold_apac`) plus an analytics summary.
5. **[Lakeflow Job](50-job.md):** wrapped the pipeline in a scheduled, multi-task job that runs it, retries on failure, and notifies you when a run breaks.
6. **[Databricks App](60-app.md):** built a governed app on a gold table and visualized APAC flight routes on a zoomable map.
7. **[OpenSharing](70-opensharing.md):** received the shared data on a plain laptop with the open-source Python client, no Spark and no Java.

## Clean up

To undo everything on Free Edition:

- Delete the **[Databricks App](60-app.md)**.
- Delete the **[Lakeflow Job](50-job.md)**.
- Delete the **[pipeline](40-pipeline.md)** and its gold tables.
- Remove the **[Marketplace](10-marketplace.md)** catalog (`marketplace`) from Catalog Explorer.
- On your laptop, delete the `opensky.share` credential file from [OpenSharing](70-opensharing.md). It carries a bearer token, so treat it as a secret.

## Take it further

- **Extend the Lakeflow Job:** add **alerts** on the pipeline's data-quality expectations and chain in more downstream tasks.
- **Enrich the Genie Agent** with your own instructions and example SQL, then share it.
- **Extend the app** to all three regions, not just APAC.
- **Go from static to streaming.** This workshop used one static day of data. The same avionics feed can run as a live stream in a Spark Declarative Pipeline: see [How to get started with Spark Declarative Pipelines](https://www.databricks.com/discover/how-to-get-started-with-spark-declarative-pipelines), which lets you track planes in the air right now. For real-time in production, watch the [air-traffic-control with Spark Structured Streaming (Real-Time Mode)](https://www.databricks.com/resources/demos/videos/air-traffic-control-with-apache-spark-structured-streaming-real-time-mode?itm_data=demo_center) demo in the Databricks Demo Center.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [7. OpenSharing](70-opensharing.md) | [Table of contents](index.md) | — |

---

_Author: Frank Munz · Updated 2026-09-15_
