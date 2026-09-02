# OpenSky Avionics on Databricks

A hands-on, end-to-end tutorial on Databricks: start with a raw Marketplace dataset — a full day of flight-tracking data from the **OpenSky Network** — and finish with a live, interactive map.

## What you'll build

1. **Databricks Marketplace** - get the data as a read-only Unity Catalog table.
2. **Genie Agents** - find data anomalies (EDA).
3. **Genie Agents** - explore and visualize the data.
4. **Spark Declarative Pipeline Genie Code** — ingest and clean the data into per-region gold tables.
5. **Genie Code - Databricks App** visualize APAC flight routes on a zoomable map.
6. **Genie One** — ask questions across your data in natural language.
7. **OpenSharing** — receive the shared data locally with the fully open-source client and VSCode

```text
Marketplace → Genie Agents (EDA) → Genie Agents (explore & visualize) → Declarative Pipeline → Databricks App → Genie One → OpenSharing (local)
```

## Before you begin

- A **Databricks account** — the free [Databricks Free Edition](https://www.databricks.com/learn/free-edition)
  is enough to follow along. *(Where a step needs a feature that may not be on Free Edition, the page flags it.)*
- **Unity Catalog** enabled (default on Free Edition).
- **Serverless compute** available (default on Free Edition).
- The **`USE MARKETPLACE ASSETS`** privilege on the metastore (default unless your admin revoked it).

## Tutorial steps

1. [Databricks Marketplace — get the sample data](docs/01-marketplace.md)
2. [Genie Agents — find data anomalies with EDA](docs/02-genie-eda.md)
3. [Genie Agents — explore and visualize the data](docs/03-genie-explore.md)
4. [Spark Declarative Pipeline with Genie Code — ingest & clean](docs/04-pipeline.md)
5. [Databricks App with Genie Code — visualize APAC routes](docs/05-app.md)
6. [Genie One — ask across your data](docs/06-genie-one.md)
7. [OpenSharing — receive the data locally](docs/07-opensharing.md)
8. [Wrap-up & next steps](docs/08-wrap-up.md)
