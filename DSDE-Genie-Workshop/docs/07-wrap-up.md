# 7. Wrap-up & next steps

## What you did

In six steps you went from a shared Marketplace dataset to a governed app, self-service analytics, and data anyone can receive locally, mostly from plain-English prompts instead of hand-written code:

1. **[Databricks Marketplace](01-marketplace.md):** attached the OpenSky avionics data (696M rows, one full UTC day, 54,093 aircraft) as a read-only Unity Catalog table over Delta Sharing, with no copy and no ETL.
2. **[Genie Agents, EDA](02-genie-eda.md):** profiled the data in plain English and surfaced its data-quality issues across 696M records.
3. **[Genie Agents, explore & visualize](03-genie-explore.md):** answered business questions and got back charts and maps, with no dashboard to build.
4. **[Spark Declarative Pipeline](04-pipeline.md):** turned the EDA findings into enforced expectations and cleaned the data into per-region gold tables (`gold_americas`, `gold_emea`, `gold_apac`) plus an analytics summary.
5. **[Databricks App](05-app.md):** built a governed app on a gold table and visualized APAC flight routes on a zoomable map.
6. **[OpenSharing](06-opensharing.md):** received the shared data on a plain laptop with the open-source Python client, no Spark and no Java.

## Clean up

To undo everything on Free Edition:

- Delete the **Databricks App** ([Step 5](05-app.md)).
- Delete the **pipeline** and its gold tables ([Step 4](04-pipeline.md)).
- Remove the Marketplace **catalog** (`marketplace`) from Catalog Explorer ([Step 1](01-marketplace.md)).
- On your laptop, delete the `opensky.share` credential file from [Step 6](06-opensharing.md). It carries a bearer token, so treat it as a secret.

## Take it further

- **Schedule the pipeline** and add **alerts** on its data-quality expectations.
- **Enrich the Genie Agent** with your own instructions and example SQL, then share it.
- **Extend the app** to all three regions, not just APAC.
- **Go from static to streaming.** This workshop used one static day of data. The same avionics feed can run as a live stream in a Spark Declarative Pipeline: see [How to get started with Spark Declarative Pipelines](https://www.databricks.com/discover/how-to-get-started-with-spark-declarative-pipelines), which lets you track planes in the air right now. For real-time in production, watch the [air-traffic-control with Spark Structured Streaming (Real-Time Mode)](https://www.databricks.com/resources/demos/videos/air-traffic-control-with-apache-spark-structured-streaming-real-time-mode?itm_data=demo_center) demo in the Databricks Demo Center.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [6. OpenSharing](06-opensharing.md) | [Table of contents](../README.md) | — |

---

_Author: Frank Munz · Updated 2026-09-14_
