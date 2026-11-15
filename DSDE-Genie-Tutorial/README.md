# [Tutorial: Databricks Genie for Data Engineers and Data Scientists](https://community.databricks.com/t5/technical-blog/tutorial-databricks-genie-for-data-engineers-and-data-scientists/ba-p/168969)

## AI-powered Analytics of 700 Million OpenSky Network Avionics Records 


Welcome to this hands-on tutorial for data scientists and data engineers that runs start to finish on Databricks Free Edition, with real data from real planes instead of an AI generated toy dataset.

You begin with raw flight data from the **[OpenSky Network](https://opensky-network.org/)** on Databricks Marketplace: 696 million records — one full day of telemetry data in 2026, every aircraft that was in the air.

From there you track down the anomalies, explore it with natural language, publish a dashboard, build a Spark Declarative Pipeline to clean it, package it as code, train an ML model on it, and finish with a live app. Genie handles the analysis and writes the SQL, dashboard, pipeline, bundle, model and web app code as you go.

If you are interested in OSS and data sharing, you can read the same data straight from your own laptop with [open sharing](docs/70-opensharing.md) and take it from there.

<p align="center">
  <img src="docs/assets/00-intro2-anim.gif" alt="Intro animation showing the OpenSky flight-data workshop" width="75%" />
</p>

<p align="center"><em>The animation above is built from the Marketplace dataset: a space-time prism of flights over the US, followed by aircraft trajectories across Australia and holding patterns over Sydney Airport. It runs as a Databricks App</em></p>


## What you'll build

1. **[Databricks Marketplace](docs/10-marketplace.md)** — get the data as a read-only Unity Catalog table.
2. **[Genie Agents - EDA](docs/20-genie-eda.md)** — find data anomalies.
3. **[Genie Agents - explore & visualize](docs/30-genie-explore.md)** — create a Genie Agent from a prompt, then explore and visualize the data.
4. **[Genie Code - AI/BI Dashboard](docs/35-dashboard.md)** — generate a governed dashboard and link the Genie Agent in as Ask Genie.
5. **[Genie Code - Spark Declarative Pipeline](docs/40-pipeline.md)** — ingest and clean the data into per-region gold tables.
6. **[Genie Code - Lakeflow Job](docs/50-job.md)** — schedule and orchestrate the pipeline as a multi-task job.
7. **[Genie Code - Declarative Automation Bundle](docs/52-dabs.md)** — turn the pipeline and job into version-controlled code.
8. **[Genie Code - ML model](docs/54-ml.md)** — train a flight-phase classifier, track it in MLflow, and register it in Unity Catalog.
9. **[Genie One on mobile](docs/55-mobile.md)** — query the data from your phone with the Genie One mobile app.
10. **[Databricks Apps](docs/60-app.md)** — build a governed app on a gold table and visualize APAC flight routes on a zoomable map.
11. **[OpenSharing](docs/70-opensharing.md)** — receive the shared data locally with the open-source client and VSCode.
12. **[Wrap-up & next steps](docs/80-wrap-up.md)** — clean up and where to go from here.

```text
TL;DR what this tutorial shows: Marketplace → Genie Agents & Genie Code (EDA) → Genie Agents (explore & visualize)
→ Genie Code for an AI/BI Dashboard → Genie Code for Declarative Pipeline → Genie Code for a Lakeflow Job
→ Genie Code for a Declarative Automation Bundle → Genie Code for an ML model → Genie One on mobile
→ Databricks App → OpenSharing with OSS
```

## How to use this tutorial

This is a guided overview, not a click-by-click manual. Each page sketches the path and highlights the prompts that matter, rather than documenting every button and menu. It's suitable for a workshop: an instructor demos each step live while the audience follows along. Working on your own is fine too. Then treat each page as the map, explore, and let Genie do the AI-powered driving.

## Before you begin

- A **Databricks account** — the free [Databricks Free Edition](https://login.databricks.com/signup?provider=DB_FREE_TIER&dbx_source=lf_fm1)
  is enough to follow along. 
- **Unity Catalog** enabled (default on Free Edition).
- **Serverless compute** available (default on Free Edition).
- The **`USE MARKETPLACE ASSETS`** privilege on the metastore (default unless your admin revoked it).

---

_Author: [Frank Munz](https://www.linkedin.com/in/frankmunz/) · Contributor: Te Chen (AI/BI Dashboard, Declarative Automation Bundle, ML model) · Updated 2026-11-15 ·  [anchor page: "Tutorial: Databricks Genie for Data Engineers and Data Scientists"](https://community.databricks.com/t5/technical-blog/tutorial-databricks-genie-for-data-engineers-and-data-scientists/ba-p/168969)_
