# DAIS 2025 RTM Demo

DAIS 2025 Demo of RealTime mode, shows the difference in latencies between Multibatch Mode and RealTime mode while also applying stateful operation using transformWithState.

## Real Time Mode/TransformWithState Info

* [DAIS 2025 Talk on Realtime Mode](https://youtu.be/zGJvbV80FdU?si=fSjHpF7mfnf1UZh9)
* [RealTime Mode Documentation](https://docs.databricks.com/aws/en/structured-streaming/real-time)
* [transformWithState](https://docs.databricks.com/aws/en/stateful-applications/)

## Quick Start

### Prereq
* databricks bundle cli installed
* defaults to run as is
    * access to Workspace `e2-demo-field-eng`

### Deploy
```bash
databricks bundle deploy
```

### Run
```bash
databricks bundle run dais-2025-rtm-demo
```

To specify a custom checkpoint location:
```bash
databricks bundle run dais-2025-rtm-demo --param checkpointLocation=/path/to/checkpoint
```

## Configuration

**Default Workspace:** `e2-demo-field-eng`

**Kafka Cluster:** OETRTA Kafka

**Checkpoint Location:** Update the `checkpointLocation` parameter in your streaming queries if you need to use a different path than the default.

**Rows Per Second:** The demo defaults to **200 rows/second** for data generation. You can increase this by modifying the `rowsPerSecond` widget parameter in the notebook:

```bash
databricks bundle run dais-2025-rtm-demo --param rowsPerSecond=500
```

> ⚠️ **Performance Disclaimer:** This demo is designed for small data volumes to showcase latency differences. Increasing `rowsPerSecond` beyond the default may negatively impact end-to-end (e2e) latency numbers, as the system may become resource-constrained. For accurate latency comparisons, keep the volume moderate.

> ⚠️ **Note:** If using a different Kafka cluster, update the Kafka connection configurations in the appropriate notebook/workflow settings before deployment.

## Project Structure

- `DAIS 2025 RTM Demo.ipynb` - Main demo notebook
- `resources/` - Supporting notebooks and utilities
  - `CityLocations.ipynb` - City and location data (64 cities)
  - `EnvironmentalMonitorListProcessor.ipynb`
  - `HelperFunctions.ipynb`
  - `SensorDataGenerator.ipynb`

