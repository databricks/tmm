![Gourmet Pipeline](https://raw.githubusercontent.com/databricks/tmm/refs/heads/main/Lakeflow-Gourmet-Pipeline/misc/gourmet_header.jpg)



# Gourmet Pipeline: End-to-End Data Engineering with Lakeflow, AI, Databricks One and Databricks Asset Bundle in the Workspace

Gourmet Pipeline is a global food company specializing in high-quality snacks. Their growth was hampered by a disconnected IT landscape and brittle data pipelines, making it difficult to analyze sales, supplier, and market data in real-time. Then their business problems got worse because they couldn't figure out how to drive new product innovation and create AI-driven, localized marketing campaigns. 

The new Lakeflow application solves all of Gourmet Pipeline's issues! It provides an automated, end-to-end data pipeline that ingests disparate data sources with Lakeflow Connect, transforms them for analysis with Lakeflow Spark Declarative Pipelines, enriches them using LLMs and AI functions, and visualizes the results on a real-time dashboard.

![Gourmet Pipeline Corp](https://raw.githubusercontent.com/databricks/tmm/refs/heads/main/Lakeflow-Gourmet-Pipeline/misc/animated.gif)

This project demonstrates a complete data engineering workflow using Databricks Asset Bundles. It covers everything from initial data ingestion to the final business intelligence dashboard served via Databricks One, providing a practical example of CI/CD and infrastructure-as-code for the Databricks Data Intelligence Platform.



### Running the Project from the Databricks Workspace

The asset bundle is designed to be deployed and run entirely from the Databricks UI, simplifying development and collaboration.

1.  **Clone the Git Repository into your Workspace**:
    *   Navigate to **Workspace** in the sidebar.
    *   Click the **Create** button and select **Git folder**.
    *   In the "Create Git folder" dialog, paste the URL `https://github.com/databricks/tmm` of the Git repository.
    *   Select your Git provider (e.g., GitHub).
    *   Enable **Sparse checkout mode** and specify the path to this specific project folder ```Lakeflow-Gourmet-Pipeline``` within the repository. This ensures you only clone the relevant project files.
    *   Click **Create Git folder**. The repository will be cloned into your workspace.


2.   **Verify/Update the configuration** 

      * Before deploying, you need to make sure you have the proper settings defined in the `databricks.yml` file.
         * `catalog_name` and `schema_name` defines the location where the pipeline tables will be created. 
         * the ID of the Databricks SQL Warehouse (`prod_warehouse_id`) that will power the dashboard
         * Update the SQL for the dashboard to match the correct catalog and schema in `src/aibi_dashboard.json`. AI/BI dashboards cannot be parametrized currently, so you have to edit this manually. 

3.  **Deploy the Asset Bundle**:
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

The core of this project is a multi-task workflow that ingests franchise, supplier, and transaction data via Lakeflow Connect from XML volumes, SFDC and MS SQL, transforms it with Spark Declarative Pipelines, enriches it through LLM and AI-based functions such as recipe generation, sentiment and translation, and finally updates AI/BI dashboards and downstream systems.


## Usage

- Run the workflow first
- Explore the dashboard, note how it blends realtime data with AI generated localized marketing campaigns
- Explore the workflow that orchestrates all the tasks without manual intervention
- Explore SDP for the data transformation with the new Lakeflow pipeline editor
- Use the asset bundle to delete and deploy again


## Requirements

- To run this you need a Datbricks account. This demo does not run on the Databricks Free Edition.


## Troubleshooting

- make sure you have the right parameters set in ```databricks.yml``` in particular DWH ID, catalog and schema name.
- if you deploy to a different catalog/schema you need to adjust the SQL in the dashboard yml file for catalog and schema since this cannot be parametrized yet. 
- Note, to keep the demo as flexible as possible and remove the requirement to have connection details for SFDC and MS SQL we use endpoint stubs for the data providers. 


---
[contact Gourmet Pipeline Corp © 2025 for reservations :-) ](https://www.linkedin.com/in/frankmunz/)

