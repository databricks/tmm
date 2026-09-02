# 3. Genie Agents — explore and visualize the data

## What we do

With the data profiled in [Step 2](02-genie-eda.md), we now use a **Genie Agent** to answer questions on the data and
**visualize** the answers. 


Where [the EDA step](02-genie-eda.md) focused on data quality and finding anomalies, this step is
about *insight*: ask a question and Genie returns the SQL, the result table, and
an appropriate **chart or map**. You never have to write a query or build a dashboard manually. This is what Genie Agents does for you. 

## Step-by-step guide

> **Step 1: Open your Genie Agent**
>
> Create a
> new Genie agent on `marketplace.opensky.state_vectors`
>
> **Step 2: Ask for a visualization**
>
> Enter one of the prompts below in the chat box. Genie returns the generated SQL, the result set,
> and a chart or map — then ask follow-ups to refine it (change the chart type, add a filter, split
> by another column).

## Prompts to try

**1. Air-traffic volume across the day**

How busy is the airspace hour by hour?

```text
Plot the number of records in @state_vectors per hour of the UTC day as a bar chart, so I can see how air-traffic volume rises and falls across the 24 hours.
```

**2. Last known position of every aircraft, by country**

Where is each plane, and who operates it?

```text
For each aircraft (icao24) in @state_vectors, take its most recent position (latitude, longitude) and plot it on a map, coloring each point by origin_country.
```

**3. Altitude vs. speed**

Do faster aircraft fly higher?

```text
Create a scatter plot of altitude versus speed for @state_vectors — use baro_altitude in feet and velocity in knots — to show how speed relates to altitude.
```

**4. Busiest airspace corridors**

Where does traffic concentrate?

```text
Create a density heatmap of aircraft positions (latitude, longitude) in @state_vectors to reveal the busiest airspace corridors and hub regions.
```

**5. Flight-phase mix over time**

When are aircraft climbing, cruising, or descending?

```text
Classify each record in @state_vectors into a flight phase from vertical_rate (climbing above +1 m/s, level between -1 and +1 m/s, descending below -1 m/s) and show the share of each phase by hour of day as a stacked bar chart.
```

## Results

> [!NOTE]
> **Screenshot to be added:** the Genie Agent answering one of the prompts above with a chart / map (`docs/assets/03-genie-explore.png`).

> [!TIP]
> **Feature spotlight — Auto-generated visualizations**
>
> **Auto-generated visualizations** — Genie turns a natural-language question into the right chart
> (bar, scatter, map, or heatmap) automatically, so you get a visual answer without building a
> dashboard first.

## Recap

You've explored the OpenSky data and produced visualizations with Genie Agents — no query writing,
no dashboard setup. These views tell you what's worth operationalizing, which is exactly what the
pipeline in [Step 4](04-pipeline.md) and the app in [Step 5](05-app.md) build on.
