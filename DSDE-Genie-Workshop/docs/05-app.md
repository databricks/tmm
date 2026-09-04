# 5. How do I build a Databricks App with Genie Code?

## What you'll do

You build an interactive **Databricks App** with **Genie Code**, a way to host web apps right next
to your data, with governed access and no separate infrastructure to manage. You describe the app
you want in plain English, and Genie Code generates, builds, and deploys it.

## What our SAs built

Genie Code generates all kinds of visualizations and full applications from a plain-English prompt, the same way coding agents such as Codex and Claude Code do. Our Solutions Architects have used this OpenSky dataset for several proofs of concept. A few are shown below.

<img src="assets/05-poc-flight-dna.png" alt="Flight DNA: a grid of radial glyphs, one per aircraft, each encoding a plane's day by time of day, altitude, and cruise level." width="100%">

*Flight DNA: each glyph is one aircraft's day. The angle is time of day (12 o'clock is midnight), the radius is altitude, and the hue is cruise level. A short hop is one arc, a long-hauler a long sweep, and a busy regional a flower of petals. Click one to expand its real track.*

<img src="assets/05-poc-spacetime-prism.png" alt="A space-time prism: aircraft positions on a map plane at 15:41 UTC, with their trajectories trailing downward through time below the map." width="100%">

*Space-time prism: aircraft sit on the map plane at a moment in time, and each flight's trajectory trails through time in the space below it.*

<img src="assets/05-poc-sydney-trajectories.png" alt="Zoomed-in flight trajectories over the Sydney sky: thousands of colored flight paths weaving over the city." width="100%">

*Zoomed-in flight trajectories over the Sydney sky.*

## Step-by-step guide

> **Step 1: Open Genie Code**
>
> Create a new **Databricks App** and open **Genie Code**.
>
> **Step 2: Generate the app**
>
> Describe the app you want in plain English: name the dataset (`marketplace.opensky.state_vectors`), say how the data should load, list the views and how to navigate between them, and ask Genie Code to build and deploy it.

## Recap

You have a live, governed Databricks App, built and deployed straight from a Genie Code prompt and running right next to your data.

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [4. Declarative Pipeline](04-pipeline.md) | [Table of contents](../README.md) | [6. OpenSharing](06-opensharing.md) |

---

_Author: Frank Munz · Updated 2026-09-04_
