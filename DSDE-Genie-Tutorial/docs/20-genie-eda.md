# 2. Find Data Insights and Anomalies with Databricks Genie

Before you transform, visualize, or even trust any dataset, you need to understand what the raw data
actually looks like. That process is called **[exploratory data analysis (EDA)](https://en.wikipedia.org/wiki/Exploratory_data_analysis)**: profiling each column, checking
value ranges and null rates, and spotting anomalies or impossible values that would otherwise
silently corrupt everything downstream. EDA is the necessary **first step**, because the issues you
find here become the cleanup rules for your [pipeline](40-pipeline.md) and the caveats for every later
analysis. Skip it and you build on data you don't understand.

## How to run EDA with Genie Agents or Genie Code?

**Genie Code and Genie Agents** run your EDA for you. Point either one at
`marketplace.opensky.state_vectors` and ask, in plain English, to profile the columns and flag
impossible values. The agent writes and runs the SQL, summarizes the results, and explains each
anomaly in avionics context. You profile a brand-new dataset in minutes, without writing a single
query, and you stay in control: Genie pauses after profiling so you confirm which columns matter
before it runs the heavier checks.

## Step-by-step guide with Genie Code

You run the EDA in two prompts. The first profiles the data and stops. The second uses the key
columns you confirmed to hunt for anomalies. The pause in between keeps a human in the loop: you
steer the analysis instead of reviewing it after the fact.

1. **Create a notebook.** In your Databricks workspace, create a new notebook and name it **OpenSky Dataset EDA**. The notebook keeps every query and chart Genie generates, so you can rerun or share the EDA later.

2. **Open the Genie Code interface.** In the notebook, open Genie Code (for example, click the Genie lamp icon, top right).

3. **Profile the data, then stop.** Enter the first prompt. It asks for the schema, the missing values per column, and the key columns, then tells Genie to wait:

   ```text
   Profile @state_vectors: report the schema and data types, and a Markdown table
   of the count and percentage of missing values per column. Add a bar chart of
   missing-value percentage per column, then list the key columns for flight
   kinematics and identification. Stop here and wait for my go-ahead.
   ```

   Genie returns the schema, a missing-values table and chart, and its list of key columns, then waits. **Review the key columns it picked.** They drive the anomaly checks in the next prompt, so confirm they match what you care about: identifiers such as `icao24` and `callsign`, and kinematics such as `latitude`, `longitude`, `baro_altitude`, `velocity`, and `true_track`. Add or remove columns in your reply if needed.

4. **Check for anomalies.** Give the go-ahead with the second prompt. It tests the confirmed columns against real-world aviation physics and asks for the written findings your [pipeline](40-pipeline.md) builds on:

   ```text
   Now check the key kinematic and identification columns for impossible or
   out-of-range values using real-world aviation physics: malformed identifiers,
   unphysical coordinates, and extreme outliers in altitude, velocity, or heading.
   Give a breakdown of anomaly counts per rule and a box plot of velocity. Then
   list the issues with explanations in the OpenSky avionics context and
   recommend cleanup rules.
   ```

5. **Review EDA findings & reports.** Once processing is complete, scroll through the summary Genie writes in the chat. It has three parts:

   - **Anomaly counts per rule:** each physics rule, the column it checks, and how many of the 696M rows break it.
   - **Issues and causes:** what each anomaly means in avionics terms, for example a garbled-but-valid receiver decode rather than a real flight.
   - **Cleanup rules:** concrete filters, such as setting `velocity` to null when it falls outside 0 to 400 m/s, that you can pass to the [pipeline](40-pipeline.md) as data-quality expectations.

## Results

**Stage 1, profile and pause.** Genie profiles all 695,706,186 rows: the schema, a missing-values
table (`squawk` is missing in about 50% of rows, the altitude, velocity, and `vertical_rate` group in 12 to 16% (`vertical_rate`: 11.93%), and
`latitude` / `longitude` in 5.77%, always together), the key columns, and then *"Stopping here,
awaiting your go-ahead."*

![Genie Code in the OpenSky Dataset EDA notebook after the first prompt: the notebook shows the generated schema cell with 695,706,186 total rows, and the Genie Code panel shows the missing-values table per column (squawk 49.94%, geo_altitude 16.12%, baro_altitude 13.70%, velocity and true_track 11.95%, latitude and longitude 5.77%), the key identification and kinematics columns, and the message that it is stopping for the go-ahead.](assets/20-genie-eda-profile.png)

**Stage 2, anomaly check.** Genie tests ten physics rules. Coordinates, `true_track`, and `icao24`
come back clean. The kinematic extremes are rare but real: 102,259 velocities below 0 or above
400 m/s (the maximum is 2,832 m/s, about Mach 8), 150,934 barometric altitudes outside -500 to
20,000 m, and 279,268 rows flagged `on_ground` while reporting more than 500 m of altitude. Genie
explains each one and recommends a cleanup rule.

![Genie Code after the second prompt: the notebook shows the velocity box plot from a random sample (median about 197 m/s, outliers past 2,000 m/s), and the Genie Code panel shows the anomaly counts per rule (for example 102,259 velocities outside 0 to 400 m/s and 279,268 on_ground rows above 500 m) followed by the issues, causes, and cleanup rules.](assets/20-genie-eda-anomalies.png)

## Optional: EDA with Visualizations and Genie Agent

If you set up a **Genie Agent** on the dataset, you can ask
the same questions in plain English and get a **graphical report** back. Genie writes the SQL
*and* picks the right chart. Both visualizations below were generated automatically as part of EDA by a Genie Agent.

### Altitude for airborne aircraft 

Clusters at cruising altitudes of **10–12 km** (a clear peak at
11 km, ~119.7M records), with lower counts at 0–3 km for climb, descent, and regional traffic:

![A Genie Agent visualization: a histogram of barometric altitude for airborne aircraft, with a strong concentration at cruising altitudes of 10–12 km (peak at 11 km, ~119.7M state-vector records) and lower counts at 0–3 km.](assets/20-genie-eda-altitude.png)

### Hourly Pattern

State-vector volume follows a clear **diurnal pattern**: it peaks at 18:00–20:00 UTC
(~42.4M records/hour) and bottoms out around 05:00 UTC (~17.0M records/hour), pointing to
European and North American daytime airspace:

![A Genie Agent visualization: a bar chart of hourly state-vector records across the UTC day, peaking at 18:00–20:00 UTC (~42.4M records/hour) and lowest around 05:00 UTC (~17.0M records/hour).](assets/20-genie-eda-hourly.png)

## Genie Agents — Beyond the Basics

A few things worth knowing once the basics work:

- **[Create your own skills](https://docs.databricks.com/aws/en/genie-agents/best-practices)** — teach the agent reusable instructions and example-question SQL so it answers domain questions your way every time. Use it when you keep re-explaining the same metric definitions, joins, or filters and want Genie to apply them consistently.
- **Inspect the generated SQL** — every answer exposes the exact SQL Genie ran, so you can audit the logic or reuse it. Use it when an anomaly looks wrong and you need to check how Genie computed it.
- **[Conversation API](https://docs.databricks.com/aws/en/genie/conversation-api)** — query the agent programmatically (`start-conversation`, `create-message`, `get-message`) and pull back the SQL, text, and rows. Use it when you want to embed Genie answers in an app or automate repeated checks.

## Recap

You now have a set of EDA findings: the **data-quality issues Genie flagged** and what they mean in avionics terms.
Keep these: the [pipeline](40-pipeline.md) prompt turns them into data-quality constraints. The notebook keeps the full analysis, so you can rerun it when the data changes.

You can also ask Genie for a written report, then save it and reuse it to build the [SDP ETL pipeline](40-pipeline.md).

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [1. Databricks Marketplace](10-marketplace.md) | [Table of contents](index.md) | [3. Genie Agents — Explore](30-genie-explore.md) |

---

_Author: [Frank Munz](https://www.linkedin.com/in/frankmunz/) · Updated 2026-11-15_
