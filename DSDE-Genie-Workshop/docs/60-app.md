# 6. How do I build a Databricks App from a gold table?

## What you'll do

You build an interactive **Databricks App**: a governed web app hosted right next to your data, with no separate infrastructure to run. It reads from Unity Catalog through a SQL warehouse, runs on serverless compute, and is available on [Databricks Free Edition](https://docs.databricks.com/getting-started/free-edition-limitations) (up to three apps, each running for 24 hours before it stops).

You build the app on top of a **gold table** from the [Spark Declarative Pipeline](40-pipeline.md). This is the common pattern: Databricks Apps sit on the gold tables an SDP pipeline produces, so it reads cleaned, query-ready data instead of raw records. If you only want to try the app quickly, you can point it at the raw table for a proof of concept, but that shortcut is not meant for anything more serious.

You describe the app you want in plain English and a coding agent writes, builds, and deploys it. Any coding agent works here: **Claude Code**, **Codex**, or Databricks **Genie Code** inside the workspace. Coding-agent support for Databricks Apps keeps improving across recent releases, so expect the in-workspace path to get smoother over time.

## What Databricks Apps can you build on the OpenSky data?

Coding agents such as **Claude Code**, **Codex**, and Databricks **Genie Code** turn a plain-English prompt into full visualizations and applications. Our Solutions Architects have used this OpenSky dataset for several proofs of concept. Each one below runs as a [Databricks App](https://www.databricks.com/blog/announcing-general-availability-databricks-apps): hosted next to the data, with governed access and no separate infrastructure. One plots Flight DNA, one an [H3](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-h3-geospatial-functions) flight-density map of Australia, and one the holding patterns over Sydney Airport.

<img src="assets/60-flights-dna.png" alt="A Databricks App showing Flight DNA: a grid of radial glyphs, one per aircraft, each encoding a plane's day by time of day, altitude, and cruise level." width="100%">

*Flight DNA: each glyph is one aircraft's day. The angle is time of day (12 o'clock is midnight), the radius is altitude, and the hue is cruise level. A short hop is one arc, a long-hauler a long sweep, and a busy regional a flower of petals. Runs as a Databricks App.*

<img src="assets/60-h3-heatmap-AUS.png" alt="A Databricks App showing an H3 hexagon flight-density map over Australia: extruded hexagons colored and raised by flight density, with 1x–12x playback controls." width="100%">

*H3 flight-density map of Australia: flights binned into H3 hexagons, extruded and colored by density, with a time scrubber to play the day forward. Runs as a Databricks App.*

<img src="assets/60-holding-patterns-SYD.png" alt="A Databricks App showing zoomed-in flight trajectories over Sydney Airport: thousands of colored flight paths weaving over the city, with orange holding-pattern loops on approach." width="100%">

*Holding patterns over Sydney Airport. The tight loops are aircraft circling as they wait to land. Runs as a Databricks App.*

## Step-by-step guide

> **Step 1: Create the Databricks App**
>
> In your workspace, create a new **Databricks App**. On Free Edition you can run up to three at once.
>
> **Step 2: Generate and deploy it from a prompt**
>
> Open **Genie Code** in the app and describe what you want in plain English: name the dataset (your pipeline's gold table, or `marketplace.opensky.state_vectors` for a quick proof of concept), say how the data should load, list the views and how to navigate between them, then ask it to build and deploy.

## Going further with Databricks Apps

A few things worth knowing once the basics work:

- **Workspace-aware discovery:** generated [Databricks App](https://docs.databricks.com/dev-tools/databricks-apps/) code resolves fully-qualified Unity Catalog names and warehouse IDs from your workspace, so the app runs without hand-editing table paths or resource IDs.
- **Pre-wired warehouse and endpoints:** name the SQL warehouse or serving endpoint once and the generated code binds to it, so the app gets governed, consistent access.
- **Smoke test before deploy:** a generated smoke test exercises the app's data path and UI before you ship, so you get early confirmation it works end to end.
- **From static data to streaming:** this workshop uses static data from Databricks Marketplace, but streaming is where Databricks leads. The same kind of feed can be ingested into an SDP pipeline from a custom PySpark data source, as shown in [Processing millions of events from thousands of aircraft in one Declarative Pipeline](https://www.databricks.com/blog/processing-millions-events-thousands-aircraft-one-declarative-pipeline).
- **Real-time in production:** Databricks works with some of the world's largest avionics organizations to build real-time streaming applications such as air-traffic-control systems. See the [air-traffic-control with Spark Structured Streaming (Real-Time Mode)](https://www.databricks.com/resources/demos/videos/air-traffic-control-with-apache-spark-structured-streaming-real-time-mode?itm_data=demo_center) demo in the Databricks Demo Center.

## Recap

You have a live, governed **Databricks App**: built on a gold table from your SDP pipeline, deployed from a plain-English prompt, and running next to your data on serverless compute.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [5. Lakeflow Job](50-job.md) | [Table of contents](index.md) | [7. OpenSharing](70-opensharing.md) |

---

_Author: Frank Munz · Updated 2026-09-15_
