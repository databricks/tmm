# cookies

![cookies](misc/bakehouse_jobs.png)



This project is not intended as a beginner tutorial (for a beginner tutorial [see here](https://www.databricks.com/discover/pages/getting-started-with-delta-live-tables)). It assumes some familiarity with Databricks, related tools and concepts. 
The project uses the bakehouse dataset from the Data+AI Summit 2024 which is available for free at the [Databricks Marketplace](https://marketplace.databricks.com/details/f8498740-31ea-49f8-9206-1bbf533f3993/Databricks_Cookies-Dataset-DAIS-2024-). 

An introduction to Databricks Workflows and Delta Live tables is [available here](https://www.youtube.com/watch?v=KVCc1Dkz7tM). This product introduction also servers as a great overview of the bakehouse application that calculates the top locations for new flagship stores based on streaming data. This repo provides the same bakehouse application as a Databricks Asset Bundle. 



![cookies](misc/bakehouse_data_eng.png)

## Getting started

1. Preparations 

* Install the Databricks CLI from https://docs.databricks.com/dev-tools/cli/databricks-cli.html
* Get the Cookies dataset from [Databricks Marketplace](https://marketplace.databricks.com/details/). Make sure to save it with the catalog name ``bakehouse`` (otherwise you have to adjust the code in the DAB accordingly).
* Since the the Cookie dataset in ``bakehouse`` is a read-only share, create another catalog with the name ``bakehouse-active`` for pipeline and result tables using either the workspace UI or SQL. 
* Install developer tools such as the Databricks extension for Visual Studio Code from [here](https://docs.databricks.com/dev-tools/vscode-ext.html). 
![Screenshot from VSCode with Databricks Extension](misc/vscode_ext.png)

2. Authenticate to your Databricks workspace, if you have not done so already:
   
   ```
    databricks auth login --host <workspace-url>
   ```

3. Make sure the CLI is configured and the bundle is valid, run the following command from the current folder:         
   ```
    databricks bundle validate [-p profileName]
   ```
   Depending on the default profile of your CLI setup you might have to add the correct profile for that environment with [-p profileName].To deploy this project, you need to reference an existing DWH. If you don't have one create it now using the Workspace UI and note its ID (here wwwww). Then run the following command:

   ```
    databricks bundle deploy -t prod --var="prod_warehouse_id=wwwww" [-p profileName]
   ```

   This deploys everything defined for this DAB project to your prod workspace: That's a Databricks Workflow with a task for DLT data ingestion and transformation, a branch task, and SQL task with ai_query() callout and two notebooks. 

   You can find those resources by opening your workpace and clicking on **Workflows** or **Delta Live Tables**


![cookies](misc/bakehouse_etl.png)

4. Note, the bundle was created by importing existing resources. Don't run this now since all the resources are added already, but here are the commands: 
   ```
   databricks bundle generate pipeline --existing-pipeline-id pppp
   databricks bundle generate job --existing-job-id jjjj 
   databricks bundle validate 

5. To run a job or pipeline, you can use the "run" command:
   ```
   $ databricks bundle run
   ```

6. The AI/BI dashboard is not part of the bundle, you can install it manually by [importing it from here](https://github.com/databricks/tmm/blob/main/Cookies-DataEng-DAB/src/Bakehouse%20Flagship%20Stores%20bundle.lvdash.json) 

7. For documentation on the Databricks asset bundles format used
   for this project, and for CI/CD configuration, see
   https://docs.databricks.com/dev-tools/bundles/index.html.



