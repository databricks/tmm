# ZeroStream - Mobile Sensor Data Streaming Platform

Mobile sensor data collection platform that streams to Databricks Unity Catalog via ZeroBus.

**Documentation**: https://docs.databricks.com/aws/en/ingestion/zerobus-ingest

## Architecture

```
Mobile Browser → Frontend App → ZeroBus → Delta Table → Backend App → Dashboard
                                              │
                                              ├──► ZeroBus (Databricks SQL)
                                              │
                                              └──► Lakebase (PostgreSQL) [via replication]
```

- **Frontend**: Collects sensor data, pushes to ZeroBus (Service Principal auth)
- **Backend**: Two independent views with separate data access layers

### Data Access Layers

The backend has **two separate views with different data sources**:

**1. ZeroBus Streaming Data View (Blue Header) - `/zerobus`**
- **Data Source**: Unity Catalog Delta table via Databricks SQL Warehouse
- **Access Method**: ALWAYS uses Databricks SQL (`lakeflow_provider.py` / `ZerobusProvider`)
- **Use Case**: Real-time streaming data table with auto-refresh every 5 seconds
- **Table**: `demo_frank.zerostream.sensor_data` (3-level Unity Catalog)
- **Features**: Light mode design, sliding data animation, shows recent 50 records

**2. Lakebase Dashboard (Green Header) - `/lakebase`**
- **Data Source**: Replicated data via PostgreSQL-compatible interface
- **Access Method**: ALWAYS uses PostgreSQL protocol (`lakebase_provider.py`)
- **Edition**: Lakebase Autoscaling (auto-scaling Postgres instances)
- **Use Case**: Map view with all clients, click to see individual traces
- **Table**: `zerostream.sensor_data` (2-level PostgreSQL schema)
- **Note**: Data is replicated from Unity Catalog to Lakebase via Lakeflow Connect

**Navigation**: Click "View Streaming Data" button on Lakebase dashboard to access ZeroBus table view

## Quick Start

1. **Setup Database** ([ZEROBUS_SETUP_GUIDE.md](ZEROBUS_SETUP_GUIDE.md)):
   - Create Unity Catalog (catalog.schema.table)
   - Create service principal
   - Configure SQL warehouse

2. **Configure** (`config.env`):
   ```bash
   DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
   SQL_WAREHOUSE_ID=your-warehouse-id
   SERVICE_PRINCIPAL_ID=your-service-principal-uuid
   SERVICE_PRINCIPAL_SECRET=your-secret
   ZEROBUS_ENDPOINT=workspace-id.zerobus.region.cloud.databricks.com
   ZEROBUS_CATALOG=catalog_name
   ZEROBUS_SCHEMA=schema_name
   ZEROBUS_TABLE=table_name
   ```

3. **Deploy**:
   ```bash
   /deploy                # Deploy BOTH frontend and backend
   /deploy zerostream     # Deploy frontend only
   /deploy zerobackend    # Deploy backend only
   ```

## Apps

### Frontend (`zerostream`)
- **Tech**: Vue 3, FastAPI, ZeroBus Python SDK
- **Function**: Collects sensor data from mobile browsers, streams to ZeroBus
- **Deployment**: `/deploy` (both) or `/deploy zerostream` (frontend only)

### Backend (`zerobackend`)
- **Tech**: FastAPI, Databricks SQL Connector, Leaflet
- **Function**: Queries Delta table, displays dashboard with map and client list
- **Deployment**: `/deploy` (both) or `/deploy zerobackend` (backend only)

## Data Flow

1. Browser collects sensor data (1Hz)
2. POST to frontend `/api/stream`
3. Frontend transforms and pushes to ZeroBus
4. ZeroBus streams to Delta table
5. Backend queries via SQL Warehouse
6. Dashboard displays real-time data

## Table Schema

```sql
CREATE TABLE sensor_data (
    id STRING,                  -- UUID
    client_id STRING,           -- 12-char identifier
    timestamp TIMESTAMP,        -- Sensor reading time
    acceleration_x DOUBLE,      -- Linear acceleration (m/s²)
    acceleration_y DOUBLE,
    acceleration_z DOUBLE,
    rotation_alpha DOUBLE,      -- Rotation rate (deg/s)
    rotation_beta DOUBLE,
    rotation_gamma DOUBLE,
    orientation_beta DOUBLE,    -- Device pitch angle (degrees)
    orientation_gamma DOUBLE,   -- Device roll angle (degrees)
    latitude DOUBLE,            -- GPS coordinates
    longitude DOUBLE,
    altitude DOUBLE,
    accuracy DOUBLE,
    speed DOUBLE,
    heading DOUBLE,
    magnetic_x DOUBLE,          -- Magnetometer (μT)
    magnetic_y DOUBLE,
    magnetic_z DOUBLE,
    received_at TIMESTAMP,      -- Backend receipt time
    processing_time_ms BIGINT   -- Processing duration
) USING DELTA;
```

## Critical: Timestamp Format

**ZeroBus JSON Ingestion Requirements**:
- TIMESTAMP columns must be sent as **Unix timestamp in microseconds** (long integer)
- NOT as ISO 8601 strings
- Example: `1770209615552000` (not `"2026-02-04T12:59:15.552+00:00"`)

```python
# Correct format for ZeroBus
import datetime
timestamp_micros = int(dt_obj.timestamp() * 1_000_000)
```

Delta Lake automatically converts Unix microseconds to TIMESTAMP type.

## Design Principles

### No Fallbacks
- All configuration must be explicit
- Missing config = immediate error with clear message
- No default values for required settings

### Fail Fast
- Configuration validated on startup
- Clear error messages with fix instructions
- No silent failures

### Detailed Error Reports
- Always log errors with full context and stack traces
- API errors must return JSON with specific failure reasons
- Display actionable error messages in the UI
- Include relevant details: what failed, why, and how to fix it
- No generic "something went wrong" messages

### No Defensive Programming
- Don't catch exceptions just to hide them
- Don't add fallback behavior that masks problems
- Let errors surface clearly so they can be fixed
- Trust explicit configuration over implicit defaults

### Separation of Concerns
- Frontend: Write-only (ZeroBus API)
- Backend: Read-only (SQL Warehouse)
- No direct communication between apps
- Delta table is the shared data layer

## Development Tools

### Deployment Skill (`/deploy`)

Deploy apps with automatic URL display:

```bash
/deploy              # Deploy BOTH frontend and backend
/deploy zerostream   # Deploy frontend only
/deploy zerobackend  # Deploy backend only
```

**Features**:
- No args = deploys both apps sequentially
- Auto-detects source path from app name
- Generates QR code for backend (pointing to frontend)
- Shows deployment URLs after completion

## Configuration

See `config.env` for all settings. Key requirements:

**Frontend Needs**:
- `SERVICE_PRINCIPAL_ID` / `SERVICE_PRINCIPAL_SECRET` - For ZeroBus auth
- `ZEROBUS_ENDPOINT` - ZeroBus ingestion endpoint
- `ZEROBUS_CATALOG` / `ZEROBUS_SCHEMA` / `ZEROBUS_TABLE` - Target table

**Backend Needs (Zerobus)**:
- `DATABRICKS_TOKEN` - PAT token
- `SQL_WAREHOUSE_ID` / `SQL_WAREHOUSE_HTTP_PATH` - SQL warehouse
- `ZEROBUS_CATALOG` / `ZEROBUS_SCHEMA` / `ZEROBUS_TABLE` - Source table

**Backend Needs (Lakebase Autoscaling)**:
- `LAKEBASE_HOST` - Lakebase endpoint hostname (e.g., `ep-xxx.database.us-west-2.cloud.databricks.com`)
- `LAKEBASE_PROJECT` - **CRITICAL: Must be the project UUID, NOT the display name**
- `LAKEBASE_BRANCH` - Branch name (e.g., `br-proud-rain-d19jvx11`)
- `LAKEBASE_ENDPOINT` - Endpoint name (e.g., `ep-green-feather-d1ziwnzh`)
- `LAKEBASE_CATALOG` / `LAKEBASE_SCHEMA` / `LAKEBASE_TABLE` - Replicated table
- `DEFAULT_DATA_SOURCE` - Default: `zerobus` or `lakebase`
- **Edition**: Lakebase Autoscaling (uses `w.postgres.generate_database_credential()` API)
- **Authentication**: Uses OAuth with the backend app's service principal identity
- **Docs**: https://docs.databricks.com/aws/en/oltp/projects/authentication

### Lakebase Autoscaling Setup (Critical Steps)

The OAuth credential generation API requires specific configuration. Follow these steps:

**Step 1: Find Your Project UUID**

The `LAKEBASE_PROJECT` must be the **UUID**, not the display name. Find it via SDK:

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

for project in w.postgres.list_projects():
    print(f"Display Name: {project.status.display_name}")
    print(f"UUID: {project.uid}")  # <-- Use this value
```

The endpoint path used internally is: `projects/<project-uuid>/branches/<branch>/endpoints/<endpoint>`

**Step 2: Create Lakebase Role for Service Principal**

Before SQL GRANTs work, the service principal must be registered as a **Lakebase role**.
This is NOT automatic - you must create it via the postgres API:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Role, RoleRoleSpec, RoleIdentityType, RoleAuthMethod

w = WorkspaceClient()

# Your app's service principal UUID (find via Databricks Apps UI or API)
app_service_principal = "cfe58c35-85a3-4283-bfbd-c0ab27158475"

# Your Lakebase branch path
branch_name = "projects/<project-uuid>/branches/<branch-name>"

# Create the role
w.postgres.create_role(
    parent=branch_name,
    role=Role(
        spec=RoleRoleSpec(
            auth_method=RoleAuthMethod.LAKEBASE_OAUTH_V1,
            identity_type=RoleIdentityType.SERVICE_PRINCIPAL,
            postgres_role=app_service_principal
        )
    )
)
```

**Step 3: Grant SQL Permissions**

After the role exists, grant database permissions:

```sql
-- Connect to Lakebase and run:
GRANT CONNECT ON DATABASE databricks_postgres TO "<backend-service-principal-id>";
GRANT USAGE ON SCHEMA <schema> TO "<backend-service-principal-id>";
GRANT SELECT ON ALL TABLES IN SCHEMA <schema> TO "<backend-service-principal-id>";
```

**Common Errors**:
- `Endpoint 'projects/my-project-name/...' not found` → Use project UUID, not display name
- `role "xxx" does not exist` → Create role via SDK first (Step 2)
- `password authentication failed` → Role exists but GRANTs not applied (Step 3)

## URL Routes

The backend provides distinct views:
- `/` → Landing page with QR code and setup steps
- `/lakebase` → Lakebase dashboard (green header, map view with all clients)
- `/zerobus` → ZeroBus streaming data table (blue header, real-time data table)

**Note**: The Lakebase dashboard allows clicking on any client in the list to view their full trace on the map.

## Troubleshooting

See [DEBUG_GUIDE.md](DEBUG_GUIDE.md) for common issues.

### ZeroBus Errors

**"Cannot ingest records after stream is closed"**:
- Check Service Principal has MODIFY permissions on table
- Verify `ZEROBUS_ENDPOINT` is correct

**"Invalid digit found in string"**:
- Timestamps must be Unix microseconds (integers), not strings
- Use `int(dt.timestamp() * 1_000_000)`

**Backend shows "Table not found"**:
- Run setup SQL from ZEROBUS_SETUP_GUIDE.md
- Verify catalog/schema/table names in config.env

### Lakebase Autoscaling Errors

**"Endpoint 'projects/my-project-name/...' not found"**:
- `LAKEBASE_PROJECT` must be the **UUID**, not the display name
- Find UUID via: `w.postgres.list_projects()` → use `project.uid`

**"role 'xxx' does not exist" (SQLSTATE 42704)**:
- The service principal must be registered as a Lakebase role first
- Create via SDK: `w.postgres.create_role(...)` (see Lakebase Setup above)
- SQL GRANTs only work AFTER the role is created

**"password authentication failed for user 'xxx'"**:
- Role exists but SQL GRANTs not applied
- Run: `GRANT CONNECT ON DATABASE...`, `GRANT USAGE ON SCHEMA...`, `GRANT SELECT ON ALL TABLES...`

**"Database instance 'xxx' not found"**:
- You're using the old Lakebase API (`w.database.generate_database_credential`)
- Lakebase Autoscaling uses `w.postgres.generate_database_credential(endpoint=...)`
