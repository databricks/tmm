# AI-powered Analytics of 700 Million OpenSky Avionics Records on Databricks Free Edition

## How to get started with Databricks Genie as a Data Scientist or Data Engineer


A hands-on, end-to-end tutorial on Databricks Free Edition with a real data set. Start with publicly available, raw Marketplace flight data from every single plane in the air on a particular day in 2026 from the **[OpenSky Network](https://opensky-network.org/)**, run EDA, analytics, ingest pipelines and finish with a live, interactive map.

## What you'll build

1. **[Databricks Marketplace](docs/01-marketplace.md)** — get the data as a read-only Unity Catalog table.
2. **[Genie Agents - EDA](docs/02-genie-eda.md)** — find data anomalies.
3. **[Genie Agents - explore & visualize](docs/03-genie-explore.md)** — explore and visualize the data.
4. **[Genie Code - Spark Declarative Pipeline](docs/04-pipeline.md)** — ingest and clean the data into per-region gold tables.
5. **[Genie Code - create a Databricks App](docs/05-app.md)** — visualize APAC flight routes on a zoomable map.
6. **[Genie One](docs/06-genie-one.md)** — ask questions across your data in natural language.
7. **[OpenSharing](docs/07-opensharing.md)** — receive the shared data locally with the open-source client and VSCode.
8. **[Wrap-up & next steps](docs/08-wrap-up.md)** — clean up and where to go from here.

```text
Marketplace → Genie Agents (EDA) → Genie Agents (explore & visualize) → Declarative Pipeline → Databricks App → Genie One → OpenSharing (local)
```

## Before you begin

- A **Databricks account** — the free [Databricks Free Edition](https://www.databricks.com/learn/free-edition)
  is enough to follow along. *(Where a step needs a feature that may not be on Free Edition, the page flags it.)*
- **Unity Catalog** enabled (default on Free Edition).
- **Serverless compute** available (default on Free Edition).
- The **`USE MARKETPLACE ASSETS`** privilege on the metastore (default unless your admin revoked it).
