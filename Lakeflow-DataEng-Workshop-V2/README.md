# Lakeflow data engineering workshop

Welcome to Databricks's new Data Engineering course.

## Technologies covered

- **Lakeflow Spark Declarative Pipelines (SDP)** — streaming tables, materialized views, and data-quality expectations, hand-coded in Python and SQL.
- **Genie Code (Agent mode)** — AI-assisted pipeline authoring with human-in-the-loop verification.
- **Zerobus Ingest** — direct gRPC ingest into Delta tables via the official `databricks-zerobus-ingest-sdk`.
- **SDP Real-Time Mode (RTM)** — continuous, serverless pipelines with sub-second end-to-end latency.
- **Declarative Automation Bundles (DABs)** — CI/CD-style deploys from the CLI with `databricks bundle deploy`.

See [Labguide.md](./Labguide.md) for the step-by-step exercises.

## Prerequisites

- A Databricks workspace with Unity Catalog and serverless enabled.
- Partner-powered AI features enabled (Genie Code dependency).
- A pre-assigned schema `workshop.USER_ID` per attendee.
- The [`misc/setup_workshop.py`](./misc/setup_workshop.py) notebook has been run as admin once to provision shared assets (landing volume + seeded JSON fraud markers; Zerobus target table, service principal, UC grants, and config table).
