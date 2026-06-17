# Lakeflow + AI on NASA GCN Data

Demo from the **Data + AI Summit 2026** talk. It shows a **Lakeflow Declarative
Pipeline** (Spark Declarative Pipelines / SQL) that streams real
[NASA GCN](https://gcn.nasa.gov/) circulars — alerts about gamma-ray bursts,
gravitational waves, neutrinos, and other transient astronomical events —
straight off NASA's public Kafka feed, classifies them with AI, and shapes them
into a knowledge source for **Agent Bricks**.

> The transformation SQL in `gcn-pipeline/transformations/` is synced from the
> deployed `gcn-kafka` pipeline in the workspace, which is the **source of truth**.

## The pipeline

Five streaming tables / views under `gcn-pipeline/transformations/`:

| Order | Object | What it does |
|-------|--------|--------------|
| 01 | `raw_space_events` (ST) | Ingests GCN circulars from `kafka.gcn.nasa.gov` over OAuth as raw JSON. Kafka credentials come from the `gcn_kafka` secret scope via `secret()`. |
| 02 | `parsed_space_events` (ST) | Parses the JSON message into typed columns (event id, subject, body, submitter, timestamps). |
| 03 | `st_for_ka` (ST) | Reshapes circulars into the Agent Bricks "Files in a Table" schema (`content` + `metadata` struct); drops rows with empty content. |
| 04 | `classified_st_for_ka` (ST) | Adds an `event_class` label via `ai_classify` (neutrino / gamma-ray burst / gravitational wave / other). |
| 05 | `ka_stats` (MV) | Materialized view summarizing row counts and the per-class breakdown. |

Target: catalog `demos1`, schema `gcn_kafka`, serverless, ADVANCED edition.

## Prerequisite: Kafka secret scope

Stage 01 reads NASA GCN credentials from a Databricks secret scope named
`gcn_kafka` (keys `client_id` and `client_secret`). Create it once before the
first run:

```bash
databricks secrets create-scope gcn_kafka
databricks secrets put-secret gcn_kafka client_id     --string-value "<your-gcn-client-id>"
databricks secrets put-secret gcn_kafka client_secret --string-value "<your-gcn-client-secret>"
```

## Deploy as a Databricks Asset Bundle (DAB)

The bundle is defined in `databricks.yml` (targets `dev` / `prod`) and
`resources/gcn_pipeline.yml` (the serverless pipeline). From the workspace
terminal or any machine with the Databricks CLI authenticated:

```bash
databricks bundle validate            # check config (default target: dev)
databricks bundle deploy              # deploy pipeline to dev
databricks bundle run gcn_kafka       # trigger a pipeline update
```

Deploy to production with `-t prod` on each command. Override the destination
with `--var="catalog=my_catalog" --var="schema=my_schema"` or edit the
`variables` block in `databricks.yml`.
