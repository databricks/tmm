# 4. How do I build an AI/BI Dashboard with Genie Code?

The [explore step](30-genie-explore.md) answered one-off questions. But the questions your team asks
every day, such as how many aircraft are in the air, at what altitudes, and at which hours, deserve a
page they can open without typing anything. That page is an **AI/BI Dashboard**, and you don't build
it by hand: you describe it to Genie Code, then link the **OpenSky Genie** agent from the explore step
so viewers can still ask follow-up questions in plain English.

## How do AI/BI Dashboards and Genie Agents fit together?

**[AI/BI Dashboards](https://docs.databricks.com/aws/en/dashboards/)** are governed dashboards that
read live from Unity Catalog through a SQL warehouse. **Genie Code** plans and generates them from
plain-English prompts: it proposes the datasets, writes the SQL, picks the chart types, and lays out
the page. When you publish, the dashboard can carry a **[Genie Agent](https://docs.databricks.com/aws/en/dashboards/genie-spaces)**:
viewers click **Ask Genie** to question the data behind the charts.

Together: the dashboard shows the metrics you know matter, and the Genie Agent handles the questions
you didn't think to chart.

## Step-by-step guide: dashboard with Genie Code

1. **Create the dashboard.** In your workspace, click **Dashboards** in the left-hand navigation, then **Create dashboard**. The empty canvas opens on *"Create a dashboard with Genie"*, with a Genie Code prompt box in the middle.

2. **Generate the overview from a prompt.** Describe the page you want in that box:

   ```text
   Build a dashboard named OpenSky Flights on marketplace.opensky.state_vectors. Put three KPI tiles
   across the top: total state vectors, distinct aircraft (distinct icao24), and
   average velocity. Below them, add a histogram of baro_altitude and a bar chart
   of record count by hour of time_position. Add a filter on on_ground.
   ```

   Genie Code creates the datasets, builds the widgets, and checks the numbers against the live table before it reports back. Check the SQL behind each dataset in the **Data** tab: every widget shows the query it runs.

3. **Add a map and refine.** Follow up in plain English. Genie Code edits the dashboard in place:

   ```text
   Add a point map of the most recent position per aircraft, colored by velocity.
   Format the KPI tiles with compact numbers, and order the hourly bar chart by hour.
   ```

4. **Teach the agent the flight phases.** Open the **OpenSky Genie** agent you created in the [explore step](30-genie-explore.md) and add this to its instructions, so it answers phase questions with the same rule you used in the altitude-vs-speed chart:

   ```text
   "Flight phase" is Ground when on_ground, Climb when vertical_rate > 1.5,
   Descent when vertical_rate < -1.5, otherwise Cruise.
   ```

5. **Link the agent and publish.** In the dashboard's **⋮** menu, open **Settings and themes** → **General**. Keep **Enable Genie** on, select **Link existing Genie agent**, and paste the URL of **OpenSky Genie**. Then click **Publish** and choose **Individual data permission**.

   > [!NOTE]
   > The OpenSky table arrives over OpenSharing, and Genie doesn't support OpenSharing datasets on a
   > dashboard published with embedded credentials (**Share data permission**, the default). With
   > **Individual data permission**, every viewer queries with their own permissions. A linked agent
   > uses its own credential settings either way.

## Results

A published **OpenSky Flights** dashboard reading live from `marketplace.opensky.state_vectors`:
KPI tiles for 696M state vectors (695.7M on the tile), 54.1K distinct aircraft, and an unfiltered average velocity of 168.6 m/s;
the barometric altitude histogram with its cruise peak around 10 km; records by hour of day, with
the same diurnal pattern you found in the [EDA step](20-genie-eda.md); and a velocity-colored map
of each aircraft's latest position.

Click **Ask Genie** and the **OpenSky Genie** agent answers from the dashboard. Asked *"Which 5
airline operators had the most tracked flights?"*, it uses the operator code and the tracked-flights measure it set up in the
explore step and returns a chart: Southwest (3,730 tracked flights), American, United, Ryanair, and Delta.

![The published OpenSky Flights AI/BI Dashboard: KPI tiles for 695.7M total state vectors, 54.1K distinct aircraft, and 168.6 m/s average velocity; a barometric altitude histogram; a bar chart of records by UTC hour; and a map of the latest known position per aircraft colored by velocity. The Ask Genie panel on the right answers "Which 5 airline operators had the most tracked flights?" with a bar chart led by SWA with 3,730 flights, then AAL, UAL, RYR, and DAL.](assets/35-dashboard.png)

## AI/BI Dashboards — Beyond the Basics

A few things worth knowing once the basics work:

- **[Choose the right visualization](https://docs.databricks.com/aws/en/dashboards/manage/visualizations/types)** — AI/BI offers ~20 chart types (point and choropleth maps, heatmaps, histograms, combo charts, funnels, Sankey). Use it when a default chart doesn't tell the story; ask Genie Code to switch it.
- **Cross-filtering** — clicking a bar or map point filters every other widget built on the same dataset. Use it when you want to drill from the overview into a slice without adding more filters.
- **[Autogenerated vs. linked Genie Agent](https://docs.databricks.com/aws/en/dashboards/genie-spaces)** — if you don't link an agent, publishing generates one from the dashboard's datasets, but you can't edit its instructions. Use a linked agent when the answers depend on your own definitions, like the flight-phase rule.
- **Scheduled refresh and subscriptions** — refresh the published dashboard on a schedule and email a snapshot to subscribers. Use it when stakeholders should see fresh numbers without opening the workspace.

## Recap

You built a governed **AI/BI Dashboard** on `marketplace.opensky.state_vectors` from two prompts and
linked the **OpenSky Genie** agent into it, so the dashboard shows the key metrics and answers
open-ended questions. You'll open the same dashboard from your phone in
[Genie One on mobile](55-mobile.md).

Next, you clean the raw data with a [Spark Declarative Pipeline](40-pipeline.md).

---

### Tutorial navigation

| ← Previous | Overview | Next → |
|:---|:---:|---:|
| [3. Genie Agents — Explore](30-genie-explore.md) | [Table of contents](index.md) | [5. Declarative Pipeline](40-pipeline.md) |

---

_Author: Te Chen & [Frank Munz](https://www.linkedin.com/in/frankmunz/) · Updated 2026-11-15_
