# Lakeflow + AI on NASA GCN Data

Demo from the **Data + AI Summit 2026** talk. It shows a **Lakeflow Declarative
Pipeline** (Spark Declarative Pipelines / SQL) that streams real
[NASA GCN](https://gcn.nasa.gov/) circulars — alerts about gamma-ray bursts,
gravitational waves, and other transient astronomical events — straight off
NASA's public Kafka feed and prepares them for AI / RAG search.

## The pipeline

Three streaming tables form a medallion flow under `gcn-pipeline/transformations/`:

| Order | Table | What it does |
|-------|-------|--------------|
| 01 | `raw_space_events` | Ingests GCN circulars from `kafka.gcn.nasa.gov` (OAuth) as raw JSON. |
| 02 | `parsed_space_events` | Parses the JSON message into typed columns (event id, subject, body, submitter, timestamps). |
| 03 | `events_search` | Builds a RAG-ready search table (URL + concatenated content), Change Data Feed enabled. |

## Deploy as a Databricks Asset Bundle (DAB)

The bundle is defined in `databricks.yml` (targets `dev` / `prod`) and
`resources/gcn_pipeline.yml` (the serverless pipeline). From the workspace
terminal or any machine with the Databricks CLI authenticated:

```bash
databricks bundle validate            # check config (default target: dev)
databricks bundle deploy              # deploy pipeline to dev
databricks bundle run gcn_pipeline    # trigger a pipeline update
```

Deploy to production with `-t prod` on each command. Override the destination
with `--var="catalog=my_catalog" --var="schema=my_schema"` or edit the
`variables` block in `databricks.yml`.

> **Note:** `gcn-pipeline/transformations/01_raw_space_events.sql` currently
> contains a hardcoded Kafka `clientSecret`. For anything beyond a throwaway
> demo, move it to a [Databricks secret scope](https://docs.databricks.com/security/secrets/).
