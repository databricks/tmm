![Gourmet Pipe Corp](https://raw.githubusercontent.com/databricks/tmm/refs/heads/main/Lakeflow-Gourmet-Pipeline/misc/gourmet_header.jpg)

# Welcome to Gourmet Pipeline

## Overview

Gourmet Pipeline is a Databricks Asset Bundle project designed to orchestrate and manage data workflows for Gourmet Pipe Corp. This project leverages Databricks Lakehouse capabilities to ingest, transform, and analyze data efficiently.

## Features

- Automated data ingestion from multiple sources with Lakeflow Connect (demo uses endpoint stubs)
- Data transformation and cleansing with Lakeflow Declarative Pipelines
- Scheduled workflows using Lakeflow Jobs
- AI integration with Anthropic Claude and ai_functions for translation and sentiment
- Integration with Databricks Unity Catalog for data governance
- DABs in the Workspace: Modular and reusable asset bundle structure



- **src/**: Databricks artifacts (pipeline files, workflows, dashboard, etc)
- **resources/**: Lakeflow pipeline definitions

## Getting Started

1. **Create a git folder in your workspace**
   ```bash
   [use this URL] https://github.com/databricks/tmm/Lakeflow-Gourmet-Pipeline.git
   [sparse checkout]
   [cone pattern] Lakeflow-Gourmet-Pipeline
   ```

2. **Deploy the application**
   - Navigate to tmm/Lakeflow-Gourmet-Pipeline
   - Click on "Open in Editor"
   - Verify the settings in databricks.yml
   - Click on Deploy (auto approve)


## Usage

- Run the workflow first
- Explore the dashboard, note how it blends realtime data with AI generated localized marketing campaigns
- Explore the workflow to achieve this 
- Explore the pipeline for the data transformation
- Use the asset bundle to delete and deploy again


## Requirements

- Datbricks account or Databrick this demo does not run on the Databricks Free Edition


## Troubleshooting

- make sure you have the right parameters set in ```databricks.yml``` in particular DWH ID, catalog and schema name.
- if you deploy to a different catalog/schema you need to adjust the SQL in the dashboard yml file since this cannot be parametrized yet. 

---
[Gourmet Pipeline Corp © 2025](https://www.linkedin.com/in/frankmunz/)