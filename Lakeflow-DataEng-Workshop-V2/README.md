# Lakeflow Data Engineering Workshop (V2)

Databricks's new Data Engineering course, rebuilt around **Lakeflow Spark Declarative Pipelines (SDP)**, the new **Lakeflow Pipelines Editor**, and **Genie Code** Agent mode.

## What you'll do

Three core labs (~100 minutes total) plus three optional take-home labs:

- **Lab 1 — Bakehouse (hand-coded).** Streaming tables, materialized views, and data-quality expectations on Lakeflow SDP. Reference files in [`lab1/`](./lab1/).
- **Lab 2 — Learn how to use Genie Code.** AI-assisted pipeline authoring with Genie Code Agent mode, with human-in-the-loop verification. Reference files in [`lab2/`](./lab2/).
- **Lab 3 — Zerobus Ingest with IoT data** *(live instructor demo; attendees may follow along).* Direct ingest into Delta tables via the official `databricks-zerobus-ingest-sdk` (gRPC), with a UC config table holding the shared SP credentials. Reference file in [`lab3/`](./lab3/).
- **Lab 4 — Spark Declarative Pipelines with RTM** *(optional / take-home).* Continuous, serverless Real-Time Mode pipeline for sub-second end-to-end latency. Reference bundle in [`lab4/`](./lab4/).
- **Lab 5 — Iceberg side-quest** *(optional / take-home).* Managed Iceberg tables on Unity Catalog, read back from PyIceberg via the UC Iceberg REST Catalog. Reference files in [`lab5/`](./lab5/).
- **Lab 6 — CI/CD via Declarative Automation Bundles** *(optional / take-home).* Deploy a multi-resource bundle (pipeline + dashboard + AI Functions) from the CLI with `databricks bundle deploy` — the same path a CI runner takes. Source ships from an external repo, no local folder.

See [Labguide.md](./Labguide.md) for the step-by-step exercises.

## Prerequisites

- A Databricks workspace with Unity Catalog and Serverless enabled.
- Partner-powered AI features enabled (Genie Code dependency).
- A pre-assigned schema `workshop.<user>` per attendee.
- The [`setup_workshop.py`](./setup_workshop.py) notebook has been run once to (a) create the shared landing volume with seeded JSON fraud markers for Lab 2 and (b) provision the Zerobus target table, service principal, UC grants, and config table for Lab 3.
