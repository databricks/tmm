# DAIS 2025 RTM Demo

A demonstration of **Real-Time Mode (RTM)** in Databricks Structured Streaming, comparing latencies between MicroBatch Mode and Real-Time Mode while applying stateful operations using `transformWithState`.

## What is Real-Time Mode?

**Real-Time Mode (RTM)** is a streaming execution mode in Databricks that enables sub-second end-to-end latency by continuously processing records as they arrive, rather than waiting for micro-batches to accumulate.

## What is transformWithState?

**transformWithState** is a stateful streaming operator that allows you to maintain and update custom state across streaming records, enabling complex event processing like aggregations, sessionization, and pattern detection.

## What This Demo Does

1. Uses Spark's rate source to generate synthetic environmental sensor data (temperature, humidity, CO2, PM2.5) for 64 cities at 200 rows/second
2. Applies `transformWithState` to calculate running averages, detect temperature trends, and generate threshold-based alerts
3. Writes output to a memory sink using both MicroBatch Mode (20 batches) and Real-Time Mode (5 batches with 60-second checkpoint intervals), resulting in comparable total runtime for fair latency comparison
4. Compares P99 latency metrics to demonstrate RTM's sub-second latency advantage

## Resources

- [DAIS 2025 Talk on Real-Time Mode](https://youtu.be/zGJvbV80FdU?si=fSjHpF7mfnf1UZh9)
- [Real-Time Mode Documentation](https://docs.databricks.com/aws/en/structured-streaming/real-time)
- [transformWithState Documentation](https://docs.databricks.com/aws/en/stateful-applications/)

## Quick Start

### Prerequisites

- Access to workspace `e2-demo-field-eng` (default configuration)
- For CLI deployment: Databricks Bundle CLI installed

### Option 1: Deploy from Workspace UI

This project is a **Declarative Automation Bundle (DAB)** and can be deployed directly from the workspace. Clone or sync the repository to a Databricks Git folder, then click the **Deploy** button (rocket icon) in the workspace UI to deploy the bundle without needing the CLI.

### Option 2: Deploy via CLI

```bash
databricks bundle deploy
```

### Run

```bash
databricks bundle run dais-2025-rtm-demo
```

Or run the deployed job directly from the Databricks Jobs UI.

## Configuration

### Catalog and Schema

The demo uses Unity Catalog for checkpoint storage with the following defaults:

- **Catalog:** `main`
- **Schema:** `default`

```bash
databricks bundle deploy [-var="catalog_volume=your_catalog"]
```

**Note:** If you do not have write access to `main.default`, use the command above to specify a catalog you can write to.

### Checkpoint Location

Specify a custom checkpoint location:

```bash
databricks bundle run dais-2025-rtm-demo --param checkpointLocation=/path/to/checkpoint
```

### Rows Per Second

The demo defaults to **200 rows/second**. You can adjust this:

```bash
databricks bundle run dais-2025-rtm-demo --param rowsPerSecond=500
```

**Performance Note:** This demo is designed for small data volumes to showcase latency differences. Increasing `rowsPerSecond` beyond the default may negatively impact end-to-end latency numbers as the system becomes resource-constrained.

## Project Structure

| File | Description |
|------|-------------|
| `DAIS 2025 RTM Demo.ipynb` | Main demo notebook |
| `resources/SensorDataGenerator.ipynb` | Generates synthetic sensor data using Spark rate source |
| `resources/EnvironmentalMonitorListProcessor.ipynb` | transformWithState processor for alerts and aggregations |
| `resources/HelperFunctions.ipynb` | Utility functions for latency calculation and metrics |
| `resources/CityLocations.ipynb` | City and location data (64 cities, 3 locations each) |