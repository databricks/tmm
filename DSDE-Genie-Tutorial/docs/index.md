# AI-powered Analytics of 700 Million OpenSky Network Avionics Records

A hands-on tutorial for data scientists and data engineers, start to finish on **Databricks Free Edition**, with real data from real planes: 696 million records of OpenSky Network telemetry from one full day in the air.

Genie handles the analysis and writes the SQL, dashboard, pipeline, job, bundle, model, and app code as you go. Each page sketches the path and the prompts that matter, then lets Genie do the AI-powered driving.

## Table of contents

1. **[Databricks Marketplace](10-marketplace.md)** — get the data as a read-only Unity Catalog table.
2. **[Genie Agents - EDA](20-genie-eda.md)** — find data anomalies.
3. **[Genie Agents - explore & visualize](30-genie-explore.md)** — create a Genie Agent from a prompt, then explore and visualize the data.
4. **[Genie Code - AI/BI Dashboard](35-dashboard.md)** — generate a governed dashboard and link the Genie Agent in as Ask Genie.
5. **[Genie Code - Spark Declarative Pipeline](40-pipeline.md)** — ingest and clean the data into per-region gold tables.
6. **[Genie Code - Lakeflow Job](50-job.md)** — schedule and orchestrate the pipeline as a multi-task job.
7. **[Genie Code - Declarative Automation Bundle](52-dabs.md)** — turn the pipeline and job into version-controlled code.
8. **[Genie Code - ML model](54-ml.md)** — train a flight-phase classifier, track it in MLflow, and register it in Unity Catalog.
9. **[Genie One on mobile](55-mobile.md)** — query the data from your phone with the Genie One mobile app.
10. **[Databricks Apps](60-app.md)** — build a governed app on a gold table and visualize APAC flight routes on a zoomable map.
11. **[OpenSharing](70-opensharing.md)** — receive the shared data locally with the open-source client and VSCode.
12. **[Wrap-up & next steps](80-wrap-up.md)** — clean up and where to go from here.

---

_Author: [Frank Munz](https://www.linkedin.com/in/frankmunz/) · Contributor: Te Chen · Updated 2026-11-15_
