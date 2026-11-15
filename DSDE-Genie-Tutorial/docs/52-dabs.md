# 7. How do I turn a pipeline and job into a Declarative Automation Bundle with Genie Code?

You built `opensky_pipeline` and `opensky_job` from prompts in the workspace. That works for one
person in one workspace, but it isn't repeatable: there's no version-controlled source of truth and
no clean way to promote the same project from dev to prod. A **Declarative Automation Bundle**
fixes that by describing both resources as YAML next to their source code, so the project deploys
the same way every time. Genie Code writes the bundle for you from the resources you already have.

## What is a Declarative Automation Bundle?

A **[Declarative Automation Bundle](https://docs.databricks.com/aws/en/dev-tools/bundles/)**
(formerly Databricks Asset Bundle) packages pipelines, jobs, notebooks, and dashboards as
declarative YAML. One `databricks.yml` defines the bundle and its **targets**, such as `dev` and
`prod`. Each resource gets its own file under `resources/`, and a deploy provisions everything the
files describe. The result: your pipeline and job live in Git, deploy identically to every
workspace, and move from dev to prod by switching the target.

You don't need a laptop or the CLI for this step.
**[Bundles in the workspace](https://docs.databricks.com/aws/en/dev-tools/bundles/workspace)** let
you create, edit, and deploy a bundle directly in the Databricks UI.

## Step-by-step guide: generate a bundle with Genie Code { #step-by-step-guide }

1. **Create a Git folder.** Bundles in the workspace live in a Git folder. In **Workspace**, click **Create** → **Git folder** and connect a repository you own, for example an empty GitHub repo.

2. **Create an empty bundle.** In the Git folder, click **Create** → **Bundle**, name it `opensky_bundle`, select **Empty project**, and click **Next**. Databricks creates a `databricks.yml` and a `.gitignore`.

3. **Prompt Genie Code to bring in your pipeline and job.** Open Genie Code in the bundle and reference both resources by name:

   ```text
   Add my existing opensky_pipeline and opensky_job to this bundle. Create
   resources/opensky_pipeline.pipeline.yml and resources/opensky_job.job.yml,
   copy the pipeline source into src/, and make the job's pipeline task reference
   the bundle's pipeline resource. In databricks.yml, add variables for catalog
   and schema, and dev and prod targets. Show me the planned YAML before writing
   any files. Do not deploy.
   ```

   *"Show me the planned YAML before writing any files"* gives you a checkpoint, the same human-in-the-loop pattern as the [EDA step](20-genie-eda.md).

4. **Review the planned YAML.** Check three things before you approve:

   - The pipeline uses **`schema:`** for its target schema. The older `target:` field is deprecated for new pipelines, and you can't set both.
   - The pipeline source is listed under **`libraries:` → `glob:` → `include:`**.
   - The job's pipeline task points at **`${resources.pipelines.opensky_pipeline.id}`**, not at a hard-coded pipeline ID. That way the job always runs the pipeline deployed by the same bundle.

5. **Deploy to dev.** Approve the plan so Genie Code writes the files. Then open the **Deployments** panel, select the **`dev`** target, and click **Deploy**. Databricks validates the bundle first and shows the results in a dialog. Fix anything it flags, then confirm **Deploy**.

   > [!IMPORTANT]
   > A `dev` deploy creates **new copies** of the pipeline and job, prefixed with `[dev <your name>]`,
   > and pauses their schedules. Your original hand-built `opensky_job` still runs every hour. Once the
   > bundle works, pause or delete the original so the two don't both refresh the same tables.

![Deploying opensky_bundle from the workspace: the Deployments panel shows Source opensky_bundle and Target dev, with [dev frank_munz] opensky_job and [dev frank_munz] opensky_pipeline under Bundle resources; the deployment output ends with "Resources: 0 created, 2 changed" and "Finished deploy on dev target successfully".](assets/52-dabs.png)

   Before it deploys, Databricks validates the bundle and lists what will change, for example **Deploying 2 resources** with the job and the pipeline. Deployments from the workspace are *source-linked*: the deployed pipeline and job reference the files in your Git folder instead of separate copies.

## Results

Genie Code generates a bundle with this layout:

```text
opensky_bundle/
├── databricks.yml                     # bundle name, variables, dev/prod targets
├── resources/
│   ├── opensky_pipeline.pipeline.yml  # the SDP pipeline as a resource
│   └── opensky_job.job.yml            # the hourly two-task job as a resource
└── src/
    └── ...                            # pipeline source and the follow-on notebook
```

**`databricks.yml`** defines the bundle, the variables, and two targets. `mode: development`
isolates your deploy by prefixing resource names and pausing schedules; `mode: production` deploys
the shared copy:

```yaml
bundle:
  name: opensky_bundle

include:
  - resources/*.yml

variables:
  catalog:
    description: Catalog for the pipeline tables (must be writable, not the Marketplace catalog)
    default: workspace
  schema:
    description: Schema for the pipeline tables
    default: default

targets:
  dev:
    default: true
    mode: development
  prod:
    mode: production
    workspace:
      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}
```

**`resources/opensky_pipeline.pipeline.yml`** is the pipeline from the
[pipeline step](40-pipeline.md), with `schema:` and a `glob` include for the source:

```yaml
resources:
  pipelines:
    opensky_pipeline:
      name: opensky_pipeline
      catalog: ${var.catalog}
      schema: ${var.schema}
      serverless: true
      root_path: ../src/opensky_pipeline
      libraries:
        - glob:
            include: ../src/opensky_pipeline/transformations/**
```

**`resources/opensky_job.job.yml`** is the job from the [job step](50-job.md): the pipeline task,
then the notebook, hourly, with a retry and a failure email:

```yaml
resources:
  jobs:
    opensky_job:
      name: opensky_job
      schedule:
        quartz_cron_expression: "0 0 * * * ?"
        timezone_id: UTC
      email_notifications:
        on_failure:
          - ${workspace.current_user.userName}
      tasks:
        - task_key: run_pipeline
          max_retries: 1
          pipeline_task:
            pipeline_id: ${resources.pipelines.opensky_pipeline.id}
        - task_key: post_process
          depends_on:
            - task_key: run_pipeline
          max_retries: 1
          notebook_task:
            notebook_path: ../src/post_process.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.schema}
```

_(This YAML matches the [reference bundle](https://github.com/databricks/tmm/tree/main/DSDE-Genie-Tutorial/code/dabs/opensky_bundle)
in the tutorial repo. Genie Code's output may differ in names and paths, so match the catalog and
schema your pipeline actually writes to.)_ On Free Edition you have a single workspace, so you
deploy the `dev` target; `prod` shows how the same code is promoted.

## Prefer a ready-made bundle?

The tutorial repo ships a tested **`opensky_bundle`** with the same pipeline and job: the pipeline
source is the code Genie Code generated in the [pipeline step](40-pipeline.md). To deploy it
without building your own:

1. In **Workspace**, click **Create** → **Git folder**, paste `https://github.com/databricks/tmm`, and under **Advanced** turn on **Sparse checkout mode** with the cone pattern `DSDE-Genie-Tutorial/code/dabs`.
2. Open `DSDE-Genie-Tutorial/code/dabs/opensky_bundle` and click **Open in editor**. In `databricks.yml`, set the `catalog` and `schema` defaults to where you want the tables (Free Edition default: `workspace.default`). Pick an empty schema if a pipeline you built earlier already owns tables with the same names.
3. Click **Deploy bundle (dev)**, review the resources in the **Deploy to dev** dialog, and confirm **Deploy**. Then click the play icon next to `opensky_job` under **Bundle resources** to run it.

On Free Edition the reference bundle's job runs in about two and a half minutes and produces the same tables as the [pipeline step](40-pipeline.md): about 6.1M bronze rows, 5.5M silver rows, and 1.7M / 2.9M / 801K rows in `gold_americas` / `gold_emea` / `gold_apac`.

## Declarative Automation Bundles — Beyond the Basics

A few things worth knowing once the basics work:

- **[Deployment modes](https://docs.databricks.com/aws/en/dev-tools/bundles/deployment-modes)** — `mode: development` prefixes resource names with your user name and pauses schedules, so your deploy never collides with a teammate's or with production; `mode: production` deploys the real, shared copy. Use it when the same bundle serves both a personal sandbox and production.
- **[Variables and target overrides](https://docs.databricks.com/aws/en/dev-tools/bundles/variables)** — declare `catalog` and `schema` once and override them per target, so one bundle reads dev data in dev and prod data in prod with no code changes. Use it when the only difference between environments is names and IDs.
- **[Generate YAML from existing resources](https://docs.databricks.com/aws/en/dev-tools/bundles/resources)** — `databricks bundle generate pipeline` (or `job`, `dashboard`, `app`) reverse-engineers YAML from a resource you built in the UI. Use it when you work from a laptop with the Databricks CLI instead of the workspace.
- **[Bundles in CI/CD](https://docs.databricks.com/aws/en/dev-tools/bundles/ci-cd/)** — run `databricks bundle validate` and `databricks bundle deploy` from GitHub Actions or Azure DevOps so every merge deploys the project. Use it when more than one person works on the project and deploys need review.

## Recap

You turned the hand-built `opensky_pipeline` and `opensky_job` into a **Declarative Automation
Bundle**: a `databricks.yml`, two resource files, and the source code, all in Git, validated and
deployed to `dev` from the workspace. The project is now reproducible code, not a one-off.

Next, you hand the cleaned data to a data scientist and [train an ML model](54-ml.md) on it.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [6. Lakeflow Job](50-job.md) | [Table of contents](index.md) | [8. ML model](54-ml.md) |

---

_Author: Te Chen & [Frank Munz](https://www.linkedin.com/in/frankmunz/) · Updated 2026-11-15_
