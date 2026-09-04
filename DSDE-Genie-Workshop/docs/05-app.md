# 5. How do I build a Databricks App with Genie Code?

## What you'll do

You build an interactive **Databricks App** with **Genie Code** — a way to host web apps right next
to your data, with governed access and no separate infrastructure to manage. Rather than plot
millions of points, you zoom in on the day's **emergency transponder codes**: out of 696M position
reports, only about 128 aircraft ever squawk an emergency. The app loads that tiny slice once and
lets you drill from the codes down to a single flight.

## Screenshot

> [!NOTE]
> **Screenshot to be added:** the running app — code overview → aircraft list → flight detail (`docs/assets/05-app.png`).

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
> Build and deploy a Databricks app (React + TypeScript, single page) on marketplace.opensky.state_vectors.
>
> Data loading: at startup run ONE query that loads every report with an emergency squawk (7500, 7600, 7700) into memory and keep it in React state. Derive all views from that in-memory data; do not query again as the user navigates.
>
> Views: (1) an overview of the three codes explaining what each means (7500 = hijack, 7600 = radio failure, 7700 = emergency) with how many aircraft are squawking each; click a code to (2) list its aircraft; click an aircraft to (3) show its flight details and altitude. Use client-side routing so the browser back button steps back up the levels.
>
> Then deploy.
> ```

## Recap

You have a live app that turns a 696M-row day into a handful of emergency squawks you can click
through — code → aircraft → flight details — all from data loaded once at startup.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [4. Declarative Pipeline](04-pipeline.md) | [Table of contents](../README.md) | [6. Genie One](06-genie-one.md) |

---

_Author: Frank Munz · Updated 2026-09-04_
