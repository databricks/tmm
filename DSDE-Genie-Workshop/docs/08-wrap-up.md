# 8. Wrap-up & next steps

## What we did

In seven steps you went from a shared dataset to a live app, self-service analytics, and data anyone can receive:

1. **Databricks Marketplace** — got the OpenSky avionics data as a read-only Unity Catalog table, via Delta Sharing.
2. **Genie Agents (EDA)** — profiled the data in plain English and surfaced the data-quality issues.
3. **Genie Agents (explore & visualize)** — answered business questions and charted the results.
4. **Spark Declarative Pipeline** (with **Genie Code**) — ingested and cleaned the data into per-region gold tables.
5. **Databricks App** (with **Genie Code**) — visualized APAC routes on a zoomable map.
6. **Genie One** — asked questions across the data with no per-dataset setup.
7. **OpenSharing** — received the shared data locally with the open-source Python client, no Spark or Java.

## Clean up

To undo everything:

- Delete the **Databricks App** ([Step 5](05-app.md)).
- Delete the **pipeline** and its output tables ([Step 4](04-pipeline.md)).
- Remove the Marketplace **catalog** (`marketplace`) from Catalog Explorer ([Step 1](01-marketplace.md)).

## Take it further

- **Schedule** the pipeline and add **alerts** on its data-quality expectations.
- Enrich the **Genie Agent** with more instructions and example SQL, then share it.
- Extend the app to all regions, or add near-real-time ingestion.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [7. OpenSharing](07-opensharing.md) | [Table of contents](../README.md) | — |
