![Gourmet Pipe Corp](https://raw.githubusercontent.com/databricks/tmm/refs/heads/main/Lakeflow-Gourmet-Pipeline/misc/gourmet_header.jpg)



# Gourmet-Pipeline: An End-to-End Data Engineering Project on Databricks

Gourmet Pipeline is a global food company specializing in high-quality snacks. Their growth was hampered by a disconnected IT landscape, making it difficult to analyze sales, supplier, and market data in real-time to drive new product innovation. This Lakeflow applications solves the issue and provides an automated, end-to-end data pipeline that ingests disparate data sources, transforms them for analysis, enriches them with AI, and visualizes the results on a real-time dashboard.

This project demonstrates a complete data engineering workflow using Databricks Asset Bundles. It covers everything from initial data ingestion to the final business intelligence dashboard, providing a practical example of CI/CD and infrastructure-as-code for the Databricks Data Intelligence Platform.

## Setup

Before deploying, you need to configure the target for your data assets. This project requires you to specify the Unity Catalog `catalog` and `schema` where the tables will be created, as well as the ID of the Databricks SQL Warehouse (`databricks_sql_warehouse_id`) that will power the dashboard.


- **src/**: Databricks artifacts (pipeline files, workflows, dashboard, etc)
- **resources/**: Lakeflow pipeline definitions


### Running the Project from the Databricks Workspace

This bundle is designed to be deployed and run entirely from the Databricks UI, simplifying development and collaboration.

1.  **Clone the Git Repository into your Workspace**:
    *   Navigate to **Workspace** in the sidebar.
    *   Click the **Create** button and select **Git folder**.
    *   In the "Create Git folder" dialog, paste the URL ```https://github.com/databricks/tmm/Lakeflow-Gourmet-Pipeline.git``` of the Git repository.
    *   Select your Git provider (e.g., GitHub).
    *   Enable **Sparse checkout mode** and specify the path to this specific project folder ```Lakeflow-Gourmet-Pipeline``` within the repository. This ensures you only clone the relevant project files.
    *   Click **Create Git folder**. The repository will be cloned into your workspace.

2.  **Deploy the Asset Bundle**:
    *   Navigate to the newly cloned folder in your Workspace.
    *   The `databricks.yml` file identifies this folder as an Asset Bundle. Click the **Deployments** icon (a rocket ship) in the left-hand pane.
    *   In the Deployments pane, select your target workspace (e.g., `presenter`).
    *   Click the **Deploy** button. Databricks will validate and deploy the resources defined in the bundle, such as jobs and pipelines.

3.  **Run the Workflow**:
    *   After a successful deployment, the "Bundle resources" section will populate with the assets created by the bundle.
    *   Under "Jobs," locate the `gourmet-workflow` job.
    *   Click the **Run** (play) icon next to the job to trigger the workflow.
    *   You can monitor the job's progress in the **Job Runs** UI.


### Workflow Tasks

The core of this project is a multi-task job that orchestrates the following steps:

*   **Data Ingestion with Lakeflow Connect**:
    *   `lf-connect-franchises`: Ingests franchise data.
    *   `lf-connect-suppliers`: Ingests supplier data.
    *   `lf-connect-tx`: Ingests transaction data.
*   **Data Transformation with Lakeflow Declarative Pipelines**:
    *   `ingest-pipeline`: A Delta Live Tables pipeline that processes and transforms the raw data.
*   **AI Enrichment with LLMs and AI functions**:
    *   `new_recipe_claude_LLM`: A call to a large language model to generate new recipes based on the ingested data.
    *   `sentiment_translate_ai_funk`: A sentiment analysis and translation task.
*   **Data Visualization with AI/BI Dashboards**:
    *   `update_aibi_dashboard`: Updates a dashboard with the latest insights.
    *   `update_downstream`: A final task to update downstream systems.

The workflow is designed with conditional branching. The `is_AI_enabled` task checks if the AI enrichment steps should be executed. If true, the workflow proceeds with the AI tasks; otherwise, it follows an alternative path.



## Usage

- Run the workflow first
- Explore the dashboard, note how it blends realtime data with AI generated localized marketing campaigns
- Explore the workflow that orchestrates all the tasks without manual intervention
- Explore the Lakeflow pipeline for the data transformation with the new pipeline editor
- Use the asset bundle to delete and deploy again


## Requirements

- To run this you need a Datbricks account. This demo does not run on the Databricks Free Edition


## Troubleshooting

- make sure you have the right parameters set in ```databricks.yml``` in particular DWH ID, catalog and schema name.
- if you deploy to a different catalog/schema you need to adjust the SQL in the dashboard yml file for catalog and schema since this cannot be parametrized yet. 

---
[Gourmet Pipeline Corp © 2025 :-) ](https://www.linkedin.com/in/frankmunz/)

