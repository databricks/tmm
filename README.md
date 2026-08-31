# Tech Marketing Repo for Training and Tech Demos

A collection of Databricks workshops, labs, and demos.

> This is a working directory for the Databricks tech marketing team. As an entry
> point we recommend the workshops or [Databricks Demo Center](https://databricks.com/demos)
> rather than using any project here directly, unless otherwise suggested by the team.

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

## Demos & workshops

- **[agent_apps_workshop](agent_apps_workshop/)** — ~90-min hands-on workshop where participants build and deploy a custom AI customer-support agent on **Databricks Apps**, using the **OpenAI Agents SDK**, **UC Functions + Vector Search** tools (on-behalf-of-user), **Lakebase** memory, **Foundation Model APIs**, and **MLflow 3** tracing/evaluation.
- **[agents-workshop](agents-workshop/)** — Create, evaluate, and deploy AI agents with **Mosaic AI**, building tools as **Unity Catalog SQL/Python functions** and combining them with an LLM in the **AI Playground**.
- **[bricks-workshop](bricks-workshop/)** — Hands-on **Agent Bricks** lab (Vocareum-hosted Databricks environment).
- **[Cookies-DataEng-DAB](Cookies-DataEng-DAB/)** — Advanced data-engineering tutorial packaging the DAIS 2024 bakehouse app as a **Databricks Asset Bundle (DAB)**, including **AI/BI dashboard** creation and the Marketplace Cookies dataset.
- **[Genie-Code-Lakeflow](Genie-Code-Lakeflow/)** — Mini-tutorial that builds a Bronze/Silver/Gold Medallion ETL pipeline from a natural-language prompt using the AI-powered **Genie Code** assistant and **Spark Declarative Pipelines**.
- **[Genie-Speak](Genie-Speak/)** — Voice-based Q&A demo app pairing the **Databricks Conversational Genie API** with Google Cloud Speech-to-Text and ElevenLabs text-to-speech.
- **[Lakebase-101](Lakebase-101/)** — Hands-on **Lakebase** (managed Postgres / OLTP) demo — an "Order Ops Console" fed by **reverse ETL** from a Delta gold table via a **managed synced table** and fronted by a **Databricks App**, contrasting OLTP reads/writes with SQL Warehouse analytics.
- **[Lakeflow-AI-NASA](Lakeflow-AI-NASA/)** — DAIS 2026 demo: a **Lakeflow Spark Declarative Pipeline** streams NASA GCN circulars off a public **Kafka** feed, classifies them with **`ai_classify`**, and shapes them into a knowledge source for **Agent Bricks**.
- **[Lakeflow-DataEng-Workshop](Lakeflow-DataEng-Workshop/)** — Databricks data-engineering course covering **Spark Declarative Pipelines**, **Genie Code**, **Zerobus Ingest**, **Real-Time Mode**, and **Declarative Automation Bundles (DABs)**.
- **[Lakeflow-Gourmet-Pipeline](Lakeflow-Gourmet-Pipeline/)** — End-to-end, SQL-first pipeline that ingests with **Lakeflow Connect**, transforms with **Spark Declarative Pipelines**, enriches via **AI functions/LLMs**, and serves on **Databricks One** — packaged as a **Databricks Asset Bundle**.
- **[Lakeflow-OpenSkyNetwork](Lakeflow-OpenSkyNetwork/)** — Self-contained SDP example (runs on Databricks Free Edition) ingesting real-time aircraft data through a **custom PySpark data source** into **Spark Declarative Pipelines** streaming tables and materialized views, with **AI/BI Genie** analytics.
- **[Lakeflow-SDP-Kafka-Sink](Lakeflow-SDP-Kafka-Sink/)** — Lakeflow **Spark Declarative Pipeline** that reads cookie-sales Delta data and streams it to a **Confluent Cloud Kafka** topic via a Kafka sink, with credentials in Databricks secrets.
- **[Lakeflow-SDP-RTM-Basics](Lakeflow-SDP-RTM-Basics/)** — Minimal single-file **Spark Declarative Pipeline** showing the three config steps to enable **Real-Time Mode (RTM)**, deployed as a **Declarative Automation Bundle**.
- **[Lakeflow_Hyper_Personalization](Lakeflow_Hyper_Personalization/)** — Hyper-personalization for financial services with Lakeflow.
- **[NASA-circulars-rag](NASA-circulars-rag/)** — In-depth DAIS 2024 project building a compound AI (**RAG + LLM**) application over 36,000 NASA circulars, ingested with a **Lakeflow/DLT** pipeline.
- **[NASA-swift-genie](NASA-swift-genie/)** — DAIS 2024 companion project streaming NASA supernova data with **Lakeflow Declarative Pipelines**, **Genie**, **Unity Catalog**, and serverless compute.
- **[NY-Taxi-Fares](NY-Taxi-Fares/)** — **Delta Live Tables (DLT)** pipeline processing NYC taxi data through a Bronze/Silver/Gold medallion architecture with data-quality checks.
- **[Omnigent-AutoRefund-Demo](Omnigent-AutoRefund-Demo/)** — 10–15 min customer-facing demo of **Omnigent**, Databricks' agent meta-harness, told as a product-build story with multiple AI models and live collaboration.
- **[OpenSky-Marketplace-Visualization](OpenSky-Marketplace-Visualization/)** — Interactive **Databricks App** visualizing a full UTC day of OpenSky flight data sourced from a free **Databricks Marketplace** dataset, with optional live regeneration and a **Genie** exploration angle.
- **[OSS-SDP-HelloWorld](OSS-SDP-HelloWorld/)** — Minimal, self-contained example of open-source **Apache Spark Declarative Pipelines** (Spark 4.1.0) — one streaming table plus one materialized view, no Databricks account required.
- **[OSS-SDP-OpenSkyNetwork](OSS-SDP-OpenSkyNetwork/)** — Getting-started guide for running open-source **Spark Declarative Pipelines** locally (Spark 4.1.0, Java 17, uv), fetching live flight data via a **custom PySpark data source**.
- **[Spark-RTM](Spark-RTM/)** — **Databricks Asset Bundle** comparing **Real-Time Mode** vs MicroBatch latency on the same **Spark Structured Streaming** pipeline using `transformWithState` — no message bus required.
- **[Spark-RTM-Kafka](Spark-RTM-Kafka/)** — DAIS 2025 demo comparing **Real-Time Mode** vs MicroBatch latency on a **Spark Structured Streaming** + **Kafka** pipeline with `transformWithState`.
- **[XML-ingest-demo](XML-ingest-demo/)** — Databricks notebook demonstrating native **XML** processing with **Apache Spark** — reading, XSD validation, schema evolution, and **Auto Loader** ingestion.
- **[Zerostream](Zerostream/)** — Mobile sensor-data streaming demo showcasing near-real-time ingestion with **Zerobus** and **Lakebase** (PostgreSQL-compatible), served via **Databricks Apps**.

## Disclaimer

These examples are provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors, copyright holders, or contributors be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

The authors and maintainers of this repository make no guarantees about the suitability, reliability, availability, timeliness, security or accuracy of the software. It is your responsibility to determine that the software meets your needs and complies with your system requirements.

No support is provided with this software. Users are solely responsible for installation, use, and troubleshooting. While issues and pull requests may be submitted, there is no guarantee of response or resolution.

By using this software, you acknowledge that you have read this disclaimer, understand it, and agree to be bound by its terms.
