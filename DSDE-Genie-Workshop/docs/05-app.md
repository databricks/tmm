# 5. Databricks App with Genie Code — visualize APAC routes

## What we do

We build an interactive visualization with **Databricks Apps** — a way to host web apps right
next to your data, with governed access and no separate infrastructure to manage. We generate the
app with **Genie Code**.

> [!IMPORTANT]
> **Free Edition:** Confirm Databricks Apps availability in your workspace before starting this step.

## Screenshot

> [!NOTE]
> **Screenshot to be added:** the running app — the zoomable APAC flight-route map (`docs/assets/05-app.png`).

## Step-by-step guide

> **Step 1: Open Genie Code**
>
> Create a new **Databricks App** and open **Genie Code**.
>
> **Step 2: Generate the app**
>
> Give it this prompt:
>
> ```text
> Create a Databricks App with a zoomable, interactive map of APAC flight
> routes from the APAC gold table. Plot each aircraft position
> (latitude/longitude) colored by altitude, draw per-callsign route polylines
> ordered by time, and let the user zoom, pan and hover a flight to see its
> callsign, origin country, altitude (ft) and speed (knots).
> ```
>
> **Step 3: Connect the data**
>
> Point the app at your **SQL warehouse** and the **APAC gold table** from [Step 4](04-pipeline.md).
>
> **Step 4: Deploy**
>
> Save a copy of the generated app in `code/app/`, then deploy and open it.

> [!TIP]
> **Feature spotlight — Generate whole assets**
>
> **Generate whole assets** — the same Genie Code capability from [Step 4](04-pipeline.md), now producing a
> *different* asset type: one prompt yields a complete, deployable Databricks App, not just a
> code snippet.

## Recap

You have a live, zoomable map of APAC flight routes built on your cleaned gold data — the payoff
of the whole workflow.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [4. Declarative Pipeline](04-pipeline.md) | [Table of contents](../README.md) | [6. Genie One](06-genie-one.md) |
