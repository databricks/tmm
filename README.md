# Tech Marketing Repo for Training and Tech Demos

A collection of Databricks workshops, labs, and demos.

## Tech covered

- **Lakeflow Spark Declarative Pipelines (SDP / LDP)** — streaming tables, materialized views, expectations, AutoCDC (SCD 1/2), Auto Loader (`read_files`), Lakeflow Pipelines Editor
- **Real-Time Mode (RTM)** — sub-second latency pipelines with `@dp.update_flow` and `pipelines.trigger: "RealTime"`
- **OSS Spark Declarative Pipelines** — self-contained Apache Spark SDP examples
- **Spark Structured Streaming + Kafka** — sources, sinks, RTM vs MicroBatch
- **Declarative Automation Bundles (DAB)** — multi-target CI/CD via `databricks.yml`
- **Zerobus Ingest** — direct gRPC/REST ingest into Delta tables
- **Lakebase** — managed Postgres for OLTP and app state
- **Apache Iceberg** — managed Iceberg tables, UC Iceberg REST Catalog, PyIceberg
- **Genie & Genie Code** — natural-language SQL, AI-assisted pipeline authoring
- **Agent Bricks & Mosaic AI Agents** — Knowledge Assistants, Multi-Agent Supervisors, agent eval
- **GenAI / RAG** — retrieval pipelines, Vector Search, MLflow evaluation
- **Unity Catalog & Governance** — system tables, lineage, audit, fine-grained access
- **AI/BI Dashboards** — Lakeview dashboards bundled with pipelines
- **Databricks Apps** — Streamlit/Flask front-ends with OAuth and SQL warehouse access
- **Data formats & ingestion** — XML, JSON, CDC, Auto Loader

See each subdirectory's README for details.

## Disclaimer

These examples are provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors, copyright holders, or contributors be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

The authors and maintainers of this repository make no guarantees about the suitability, reliability, availability, timeliness, security or accuracy of the software. It is your responsibility to determine that the software meets your needs and complies with your system requirements.

No support is provided with this software. Users are solely responsible for installation, use, and troubleshooting. While issues and pull requests may be submitted, there is no guarantee of response or resolution.

By using this software, you acknowledge that you have read this disclaimer, understand it, and agree to be bound by its terms.
