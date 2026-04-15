# ZeroStream Backend Documentation

## Overview

Backend processing service for ZeroStream that receives sensor data from the frontend app and streams it to Databricks Delta tables via ZeroBus.

## Status: PLANNED

This app is not yet implemented. This document describes the planned architecture.

## Purpose

- Receive batched sensor data from frontend
- Validate and transform data
- Authenticate with ZeroBus
- Stream data to Delta tables
- Monitor data quality and throughput

## Planned Architecture

### Directory Structure
```
zero_backend/
├── app.py                      # Main FastAPI application
├── app.yaml                    # Databricks Apps config
├── requirements.txt            # Python dependencies
├── services/
│   ├── zerobus_client.py      # ZeroBus integration
│   ├── data_validator.py      # Data validation logic
│   └── monitoring.py          # Metrics and logging
└── models/
    └── sensor_data.py         # Pydantic models
```

### Data Processing Pipeline

1. **Ingestion**: Receive JSON batches from frontend
2. **Validation**: Schema validation, range checks
3. **Transformation**: Format for Delta table schema
4. **Streaming**: Send to ZeroBus endpoint
5. **Monitoring**: Track success rates, latency

### API Endpoints

#### POST /ingest
Receives data from frontend app.

**Request**: Same as frontend's `/api/stream` response
**Response**: Acknowledgment with batch ID

#### GET /status
Returns service health and metrics.

**Response**:
```json
{
  "status": "healthy",
  "batches_processed": 1234,
  "records_streamed": 12340,
  "last_batch_time": "2024-02-02T10:30:00Z",
  "error_rate": 0.01
}
```

### ZeroBus Integration

#### Connection Setup
```python
# Planned implementation
client = ZeroBusClient(
    endpoint=os.getenv("ZEROBUS_ENDPOINT"),
    api_key=os.getenv("ZEROBUS_API_KEY"),
    catalog=os.getenv("ZEROBUS_CATALOG"),
    schema=os.getenv("ZEROBUS_SCHEMA"),
    table=os.getenv("ZEROBUS_TABLE")
)
```

#### Data Schema
Target Delta table in Unity Catalog: `demo_frank.zerostream.sensor_data`

```sql
CREATE TABLE sensor_data (
    -- Metadata fields
    id STRING NOT NULL,                    -- Unique record ID (UUID)
    client_id STRING NOT NULL,             -- 12-char readable client identifier
    timestamp TIMESTAMP NOT NULL,          -- When sensor reading was taken

    -- Motion sensors (from DeviceMotionEvent)
    acceleration_x DOUBLE,                  -- Linear acceleration (m/s²) excluding gravity
    acceleration_y DOUBLE,                  -- Positive: right, up, towards user
    acceleration_z DOUBLE,                  -- Device coordinate system
    rotation_alpha DOUBLE,                  -- Rotation rate (deg/s) around Z-axis
    rotation_beta DOUBLE,                   -- Rotation rate around X-axis
    rotation_gamma DOUBLE,                  -- Rotation rate around Y-axis

    -- GPS Location (from Geolocation API)
    latitude DOUBLE,                        -- GPS latitude in degrees
    longitude DOUBLE,                       -- GPS longitude in degrees
    altitude DOUBLE,                        -- Altitude in meters above sea level
    accuracy DOUBLE,                        -- Horizontal accuracy in meters
    speed DOUBLE,                           -- Speed in meters/second
    heading DOUBLE,                         -- Direction of travel (0-360 degrees)

    -- Magnetometer (from DeviceOrientationEvent)
    magnetic_x DOUBLE,                      -- Magnetic field strength (μT)
    magnetic_y DOUBLE,                      -- Device coordinate system
    magnetic_z DOUBLE,                      -- Includes Earth's field + interference

    -- Processing metadata
    received_at TIMESTAMP,                  -- When backend received the data
    processing_time_ms LONG                 -- Backend processing duration
)
USING DELTA
CLUSTER BY (client_id, timestamp)          -- Liquid clustering for efficient queries
```

#### Why Liquid Clustering?

The table uses **liquid clustering** instead of traditional partitioning for optimal streaming performance:

1. **Streaming-Optimized**: Handles continuous small writes from sensor data efficiently
2. **Multi-dimensional Queries**: Optimizes for both `client_id` and `timestamp` predicates
3. **No Small Files Problem**: Avoids issues with sparse daily partitions
4. **Automatic Optimization**: Self-tuning data organization without manual maintenance
5. **Flexible Query Patterns**: Efficient for:
   - Time-range queries across all clients
   - Single client historical analysis
   - Real-time monitoring dashboards
   - Cross-client comparisons

#### Design Decisions

- **Nullable Sensor Fields**: Accommodates devices without certain sensors
- **12-char Client IDs**: Human-readable identifiers for easier debugging
- **Comprehensive Metadata**: Tracks collection and processing times for latency analysis
- **No Column Defaults**: Explicit population by backend for better control

### Configuration

From `config.env`:
- `ZEROBUS_ENDPOINT`: Streaming endpoint URL
- `ZEROBUS_API_KEY`: Authentication token
- `ZEROBUS_CATALOG`: Unity Catalog name
- `ZEROBUS_SCHEMA`: Schema name
- `ZEROBUS_TABLE`: Table name
- `ZEROBUS_MAX_RETRIES`: Retry attempts

### Error Handling

- **Validation errors**: Return 400 with details
- **ZeroBus errors**: Retry with exponential backoff
- **Rate limiting**: Queue excess data
- **Dead letter queue**: Failed records after max retries

### Monitoring

Planned metrics:
- Records per second
- Batch processing latency
- ZeroBus success rate
- Data quality scores
- Client activity patterns

### Deployment

```bash
# When ready to deploy
./deploy-app.sh zero-backend ./zero_backend
```

## Lakebase Documentation

Essential documentation for the Lakebase PostgreSQL-compatible interface:

| Topic | Link |
|-------|------|
| **Overview** - Autoscaling and Provisioned editions | https://docs.databricks.com/aws/en/oltp/ |
| **Authentication** - OAuth and native Postgres methods | https://docs.databricks.com/aws/en/oltp/instances/authentication |
| **Auth (Autoscaling)** - Token lifetime, SSL, role creation | https://docs.databricks.com/aws/en/oltp/projects/authentication |
| **Notebook Access** - Python/OAuth, connection pools, M2M token rotation | https://docs.databricks.com/aws/en/oltp/instances/query/notebook |
| **Quickstart** - psql, notebooks, SQL Editor, third-party clients | https://docs.databricks.com/aws/en/oltp/projects/connect-overview |

### Lakebase Autoscaling Setup Steps

#### 1. Create Autoscaling Lakebase Instance
- Create a new project for an autoscaling Lakebase instance in the Databricks workspace
- Note the **Project UUID** (not the display name) from the console or via SDK

#### 2. Find Your Project UUID (Critical!)
The OAuth API requires the **UUID**, not the display name:

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

for project in w.postgres.list_projects():
    print(f"Display Name: {project.status.display_name}")
    print(f"UUID: {project.uid}")  # <-- Use this for LAKEBASE_PROJECT
```

#### 3. Configure Connection
Update `config.env` and `app.yaml` with:
```bash
LAKEBASE_HOST=ep-xxx.database.us-west-2.cloud.databricks.com
LAKEBASE_PROJECT=<project-uuid>  # NOT the display name!
LAKEBASE_BRANCH=br-xxx
LAKEBASE_ENDPOINT=ep-xxx
```

#### 4. Create Lakebase Role for App Service Principal
**This step is often missed!** Before SQL GRANTs work, the service principal must be registered as a Lakebase role:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Role, RoleRoleSpec, RoleIdentityType, RoleAuthMethod

w = WorkspaceClient()

# Your app's service principal UUID (from Databricks Apps console)
app_sp = "cfe58c35-85a3-4283-bfbd-c0ab27158475"

# Full branch path
branch_name = "projects/<project-uuid>/branches/<branch-name>"

w.postgres.create_role(
    parent=branch_name,
    role=Role(
        spec=RoleRoleSpec(
            auth_method=RoleAuthMethod.LAKEBASE_OAUTH_V1,
            identity_type=RoleIdentityType.SERVICE_PRINCIPAL,
            postgres_role=app_sp
        )
    )
)
```

#### 5. Grant SQL Permissions
After the role exists, connect to Lakebase and run:

```sql
GRANT CONNECT ON DATABASE databricks_postgres TO "<service-principal-uuid>";
GRANT USAGE ON SCHEMA <schema> TO "<service-principal-uuid>";
GRANT SELECT ON ALL TABLES IN SCHEMA <schema> TO "<service-principal-uuid>";
```

#### 6. Create Sync Table
- From the Unity Catalog source table, create a sync table to replicate data to Lakebase
- This enables low-latency PostgreSQL access to the streaming data

### Lakebase Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LAKEBASE_HOST` | **Yes** | - | Lakebase endpoint hostname |
| `LAKEBASE_PROJECT` | **Yes** | - | **Project UUID** (NOT display name!) - find via `w.postgres.list_projects()` |
| `LAKEBASE_BRANCH` | **Yes** | - | Branch name (e.g., `br-proud-rain-d19jvx11`) |
| `LAKEBASE_ENDPOINT` | **Yes** | - | Endpoint name (e.g., `ep-green-feather-d1ziwnzh`) |
| `LAKEBASE_PORT` | No | `5432` | PostgreSQL port |
| `LAKEBASE_DATABASE` | No | `databricks_postgres` | Database name |
| `LAKEBASE_CATALOG` | Yes* | - | Unity Catalog catalog name |
| `LAKEBASE_SCHEMA` | Yes* | - | Schema name |
| `LAKEBASE_TABLE` | Yes* | - | Table name |

*Falls back to `ZEROBUS_CATALOG`, `ZEROBUS_SCHEMA`, `ZEROBUS_TABLE` if not set

**OAuth Endpoint Path Format**: `projects/{PROJECT_UUID}/branches/{BRANCH_NAME}/endpoints/{ENDPOINT_NAME}`

### Common Lakebase Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Endpoint 'projects/my-project/...' not found` | Using display name instead of UUID | Use project UUID from `w.postgres.list_projects()` |
| `role "xxx" does not exist` (SQLSTATE 42704) | Role not created via SDK | Run `w.postgres.create_role(...)` first |
| `password authentication failed` | Role exists but no SQL GRANTs | Run GRANT CONNECT, USAGE, SELECT statements |

### Key Implementation Notes

- **OAuth Authentication**: The backend uses OAuth with Service Principal identity for Lakebase connections
- **Connection Pooling**: See notebook documentation for connection pool examples with token rotation
- **SSL Required**: All Lakebase connections require SSL (`sslmode=require`)

## Next Steps

1. Implement ZeroBus client library
2. Create data validation rules
3. Set up monitoring dashboards
4. Configure auto-scaling
5. Add data quality checks