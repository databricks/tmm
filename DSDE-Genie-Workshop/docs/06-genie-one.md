# 6. Genie One — ask across your data

## What we do

We ask questions across our data with **Genie (Genie One)** — the workspace-wide,
natural-language experience that finds and answers questions across your catalogs and tables,
with no per-dataset agent to set up. Where the **Genie Agent** in [Step 2](02-genie-eda.md) was curated and scoped
to one table, **Genie One** lets anyone open a chat and query whatever data they can access —
including the raw `state_vectors` table and the per-region gold tables you built in [Step 4](04-pipeline.md).

> [!NOTE]
> **Screenshot to be added:** Genie One answering a question across the OpenSky data (`docs/assets/06-genie-one.png`).

## Step-by-step guide

> **Step 1: Open Genie**
>
> From the sidebar, open **Genie** (the workspace-level assistant — no setup or scoping required).
>
> **Step 2: Ask a question across your data**
>
> Enter a question in plain English, for example:
>
> ```text
> Using the OpenSky gold tables, which origin countries had the most flights
> in the APAC region, and how many aircraft were airborne versus on the ground?
> ```
>
> **Step 3: Review and follow up**
>
> Review the answer and the SQL Genie generated, then ask a follow-up to drill deeper.

> [!TIP]
> **Feature spotlight — No-setup data discovery**
>
> **No-setup data discovery** — Genie One answers natural-language questions across everything
> you can access in the workspace without building a curated agent first, which makes it the
> fastest way for anyone on the team to explore new data.

## Recap

You've now queried the OpenSky data through **Genie One** without any per-dataset setup — a quick,
governed way for the whole team to explore the raw and cleaned tables in plain English.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [5. Databricks App](05-app.md) | [Table of contents](../README.md) | [7. OpenSharing](07-opensharing.md) |
