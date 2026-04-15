# ZeroStream Complete Setup Guide

This comprehensive guide walks you through setting up ZeroStream with database streaming on a Databricks workspace, allowing you to stream mobile sensor data directly into Delta tables in Unity Catalog.

## Prerequisites

- Access to a Databricks workspace with catalog admin privileges
- Databricks SQL warehouse (create one if needed)
- Databricks CLI installed and configured
- Personal Access Token (PAT) with workspace and SQL access

## Configuration Files

### For New Users

Use the provided template files and fill in your own credentials:

```bash
cp config.env.example config.env
cp zero_frontend/app.yaml.example zero_frontend/app.yaml
cp zero_backend/app.yaml.example zero_backend/app.yaml
```

Then edit each file with your Databricks workspace credentials, service principal, and other settings.

### Encrypted Files (Original Developer Only)

The `.age` files contain the original developer's credentials encrypted with [age](https://github.com/FiloSottile/age). These are for personal backup only.

```bash
# Decrypt (requires passphrase)
age -d config.env.age > config.env
age -d zero_frontend/app.yaml.age > zero_frontend/app.yaml
age -d zero_backend/app.yaml.age > zero_backend/app.yaml

# Re-encrypt after changes
age -p -o config.env.age config.env
age -p -o zero_frontend/app.yaml.age zero_frontend/app.yaml
age -p -o zero_backend/app.yaml.age zero_backend/app.yaml
```

## Step 1: Create Unity Catalog Structure

Connect to a SQL warehouse in your Databricks workspace and run the following SQL commands. Replace the placeholders `<catalog_name>`, `<schema_name>`, and `<table_name>` with your actual values.

### 1.1 Create Catalog and Schema

```sql
-- Create catalog for sensor data
-- Replace <catalog_name> with your catalog (e.g., demo_frank, sensor_catalog)
CREATE CATALOG IF NOT EXISTS <catalog_name>
COMMENT 'ZeroStream mobile sensor data catalog';

-- Use the catalog
USE CATALOG <catalog_name>;

-- Create schema within catalog
-- Replace <schema_name> with your schema (e.g., zerostream, mobile_data)
CREATE SCHEMA IF NOT EXISTS <schema_name>
COMMENT 'Schema for mobile sensor data';

-- Use the schema
USE SCHEMA <schema_name>;

-- Verify creation
DESCRIBE CATALOG <catalog_name>;
DESCRIBE SCHEMA <catalog_name>.<schema_name>;
```

### 1.2 Create Sensor Data Table

Create the Delta table with the schema matching the mobile sensor data structure:

```sql
-- Create sensor data table with all mobile sensor fields
-- Replace placeholders with your values
CREATE TABLE IF NOT EXISTS <catalog_name>.<schema_name>.<table_name> (
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

    -- Device Orientation (from DeviceOrientationEvent)
    orientation_beta DOUBLE,                -- Device pitch angle (degrees, -180 to 180)
    orientation_gamma DOUBLE,               -- Device roll angle (degrees, -90 to 90)

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
COMMENT 'Mobile sensor data from ZeroStream app';

-- Grant permissions for users to query the data
GRANT USAGE ON CATALOG <catalog_name> TO `account users`;
GRANT USAGE ON SCHEMA <catalog_name>.<schema_name> TO `account users`;
GRANT SELECT ON TABLE <catalog_name>.<schema_name>.<table_name> TO `account users`;
```

### 1.3 Verify Table Creation

```sql
-- Verify table exists and check schema
DESCRIBE TABLE EXTENDED <catalog_name>.<schema_name>.<table_name>;

-- Check table is empty
SELECT COUNT(*) as record_count FROM <catalog_name>.<schema_name>.<table_name>;

-- Insert test record to verify write access
INSERT INTO <catalog_name>.<schema_name>.<table_name> (
    id, client_id, timestamp,
    acceleration_x, acceleration_y, acceleration_z,
    latitude, longitude,
    received_at, processing_time_ms
) VALUES (
    'test-' || uuid(),
    'test-device',
    CURRENT_TIMESTAMP(),
    0.1, 0.2, 0.3,
    37.7749, -122.4194,
    CURRENT_TIMESTAMP(),
    0
);

-- Verify test record
SELECT * FROM <catalog_name>.<schema_name>.<table_name> WHERE client_id = 'test-device';

-- Clean up test record
DELETE FROM <catalog_name>.<schema_name>.<table_name> WHERE client_id = 'test-device';
```

## Step 2: Create Service Principal for Streaming

### 2.1 Create Service Principal via UI (Recommended)

1. Navigate to your Databricks workspace
2. Go to **Settings** → **Identity and Access** → **Service Principals**
3. Click **Add Service Principal**
4. Enter name: `zero_streamer`
5. Click **Add**
6. Once created, click on the service principal name
7. Click **Generate Secret**
8. **Important**: Save the generated secret immediately (it won't be shown again)
9. Note the **Application ID** (UUID format like `12345678-1234-1234-1234-123456789abc`)

### 2.2 Alternative: Create via CLI

```bash
# Authenticate CLI first (use your actual workspace URL)
# AWS example:
databricks auth login --host https://dbc-34e8a5a4-09d1.cloud.databricks.com

# Azure example:
# databricks auth login --host https://adb-1234567890123456.7.azuredatabricks.net

# Create service principal
databricks service-principals create --display-name zero_streamer

# Example output:
# {
#   "active": true,
#   "application_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "display_name": "zero_streamer",
#   "id": "987654321098765432"
# }

# Generate OAuth secret (use application_id from above)
databricks service-principals create-oauthsecret \
    --service-principal-id a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Example output:
# {
#   "client_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "secret": "YOUR_GENERATED_SECRET_WILL_APPEAR_HERE",
#   "secret_hash": "SHA256:..."
# }

# IMPORTANT: Save the secret immediately - it won't be shown again
```

### 2.3 Grant Service Principal Permissions

Run these SQL commands in your SQL warehouse. Replace `<service_principal_id>` with your service principal's Application ID:

```sql
-- Grant catalog and schema access
-- Replace <catalog_name>, <schema_name>, <table_name> with your values
-- Replace <service_principal_id> with your service principal Application ID
GRANT USE CATALOG ON CATALOG <catalog_name> TO `<service_principal_id>`;
GRANT USE SCHEMA ON SCHEMA <catalog_name>.<schema_name> TO `<service_principal_id>`;

-- Grant table write permissions
GRANT MODIFY ON TABLE <catalog_name>.<schema_name>.<table_name> TO `<service_principal_id>`;

-- Verify permissions
SHOW GRANTS ON TABLE <catalog_name>.<schema_name>.<table_name>;
```

**Example with actual values:**
```sql
-- Example using actual values
GRANT USE CATALOG ON CATALOG demo_frank TO `4ec3b66b-001a-4486-8897-0ebf0ba89015`;
GRANT USE SCHEMA ON SCHEMA demo_frank.zerostream TO `4ec3b66b-001a-4486-8897-0ebf0ba89015`;
GRANT MODIFY ON TABLE demo_frank.zerostream.sensor_data TO `4ec3b66b-001a-4486-8897-0ebf0ba89015`;
SHOW GRANTS ON TABLE demo_frank.zerostream.sensor_data;
```

## Step 3: Configure SQL Warehouse

### 3.1 Find SQL Warehouse Endpoint

1. Go to **SQL Warehouses** in your workspace
2. Click on your warehouse name
3. Click **Connection Details**
4. Note the following values:

   **Server hostname examples:**
   - AWS: `dbc-34e8a5a4-09d1.cloud.databricks.com`
   - Azure: `adb-1234567890123456.7.azuredatabricks.net`
   - GCP: `1234567890123456.7.gcp.databricks.com`

   **HTTP path format:**
   - Always: `/sql/1.0/warehouses/<warehouse-id>`
   - Example: `/sql/1.0/warehouses/1234567890abcdef`

   **Warehouse ID:**
   - Format: 16 character hexadecimal string
   - Example: `1234567890abcdef`
   - Location: Last segment of the HTTP path

### 3.2 Create SQL Warehouse (if needed)

If no SQL warehouse exists:

1. Go to **SQL Warehouses**
2. Click **Create SQL Warehouse**
3. Configure:
   - Name: `zero_streamer_warehouse`
   - Cluster size: **X-Small** (for testing)
   - Auto-stop: **10 minutes**
4. Click **Create**
5. Wait for warehouse to start (green status)

## Step 4: Find ZeroBus Streaming Endpoint

The ZeroBus endpoint URL follows the Databricks Unity Catalog REST API pattern:

### Endpoint URL Format
```
https://<workspace-host>/api/2.0/unity-catalog/tables/<catalog>.<schema>.<table>/streaming/ingest
```

### Examples by Cloud Provider

**AWS Databricks:**
```
https://dbc-34e8a5a4-09d1.cloud.databricks.com/api/2.0/unity-catalog/tables/demo_frank.zerostream.sensor_data/streaming/ingest
```

**Azure Databricks:**
```
https://adb-1234567890123456.7.azuredatabricks.net/api/2.0/unity-catalog/tables/demo_frank.zerostream.sensor_data/streaming/ingest
```

**GCP Databricks:**
```
https://1234567890123456.7.gcp.databricks.com/api/2.0/unity-catalog/tables/demo_frank.zerostream.sensor_data/streaming/ingest
```

## Step 5: Update Configuration

Update the `config.env` file with your values:

```bash
# ==========================================
# DATABRICKS WORKSPACE SETTINGS
# ==========================================
# Your workspace URL
DATABRICKS_HOST=https://YOUR_WORKSPACE.cloud.databricks.com
DATABRICKS_USER=your.email@example.com
DATABRICKS_TOKEN=YOUR_DATABRICKS_TOKEN

# ==========================================
# SQL WAREHOUSE CONFIGURATION
# ==========================================
# From SQL Warehouses → Your Warehouse → Connection Details
SQL_WAREHOUSE_ID=YOUR_WAREHOUSE_ID
SQL_WAREHOUSE_HTTP_PATH=/sql/1.0/warehouses/YOUR_WAREHOUSE_ID

# ==========================================
# SERVICE PRINCIPAL CONFIGURATION
# ==========================================
# Application ID from service principal
SERVICE_PRINCIPAL_ID=YOUR_SERVICE_PRINCIPAL_UUID
# OAuth secret generated for service principal
SERVICE_PRINCIPAL_SECRET=YOUR_SERVICE_PRINCIPAL_SECRET

# ==========================================
# UNITY CATALOG CONFIGURATION
# ==========================================
ZEROBUS_CATALOG=YOUR_CATALOG
ZEROBUS_SCHEMA=YOUR_SCHEMA
ZEROBUS_TABLE=sensor_data

# ==========================================
# ZEROBUS STREAMING ENDPOINT
# ==========================================
ZEROBUS_ENDPOINT=https://YOUR_WORKSPACE.cloud.databricks.com/api/2.0/unity-catalog/tables/YOUR_CATALOG.YOUR_SCHEMA.sensor_data/streaming/ingest
ZEROBUS_API_KEY=YOUR_SERVICE_PRINCIPAL_SECRET
```

## Step 6: Deploy Applications

Deploy both frontend and backend applications:

**Using Claude Code (recommended):**
```bash
/deploy                # Deploy BOTH frontend and backend
/deploy zerostream     # Frontend only
/deploy zerobackend    # Backend only
```

**Using shell scripts (alternative):**
```bash
# Deploy frontend
./deploy-app.sh zerostream ./zero_frontend

# Deploy backend
./deploy-app.sh zerobackend ./zero_backend
```

The `/deploy` skill automatically:
- Increments version number
- Syncs `config.env` values to `app.yaml` files
- Generates QR code for mobile access (backend)
- Verifies deployment success
- Displays app URLs

## Step 7: Verify Setup

### 7.1 Test Database Connectivity

Run these SQL queries to ensure everything is configured:

```sql
-- Check catalog exists (replace <catalog_name> with your value)
SHOW CATALOGS LIKE '<catalog_name>';

-- Check schema exists
SHOW SCHEMAS IN <catalog_name> LIKE '<schema_name>';

-- Check table exists and is accessible
SELECT
    COUNT(*) as total_records,
    MIN(timestamp) as earliest_record,
    MAX(timestamp) as latest_record,
    COUNT(DISTINCT client_id) as unique_devices
FROM <catalog_name>.<schema_name>.<table_name>;
```

### 7.2 Monitor Data Ingestion

Once the app is deployed and receiving data:

```sql
-- Real-time monitoring query
SELECT
    DATE_FORMAT(timestamp, 'yyyy-MM-dd HH:mm') as minute,
    COUNT(*) as records_per_minute,
    COUNT(DISTINCT client_id) as active_devices,
    AVG(accuracy) as avg_gps_accuracy,
    SUM(processing_time_ms) / 1000.0 as total_processing_seconds
FROM <catalog_name>.<schema_name>.<table_name>
WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
GROUP BY 1
ORDER BY 1 DESC
LIMIT 60;

-- Check latest records
SELECT
    client_id,
    timestamp,
    latitude,
    longitude,
    acceleration_x,
    acceleration_y,
    acceleration_z,
    received_at,
    processing_time_ms
FROM <catalog_name>.<schema_name>.<table_name>
ORDER BY received_at DESC
LIMIT 10;

-- Data size estimation
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT client_id) as unique_devices,
    -- Estimate: ~288 bytes per row (including Delta overhead)
    ROUND(COUNT(*) * 288.0 / (1024 * 1024), 2) as estimated_size_mb,
    MIN(timestamp) as earliest_record,
    MAX(timestamp) as latest_record
FROM <catalog_name>.<schema_name>.<table_name>;
```

## Data Size Estimation

Each row in the sensor_data table uses approximately:
- **id** (UUID string): 36 bytes
- **client_id** (12 chars): 12 bytes
- **timestamp**: 8 bytes
- **15 DOUBLE fields** (8 bytes each): 120 bytes
- **received_at** timestamp: 8 bytes
- **processing_time_ms** LONG: 8 bytes
- **Total per row**: ~192 bytes
- **With Delta overhead** (~50%): ~288 bytes per row

For example:
- 1,000 records ≈ 0.27 MB
- 100,000 records ≈ 27 MB
- 1,000,000 records ≈ 275 MB

## Troubleshooting

### Issue: "Catalog not found"
- Ensure Unity Catalog is enabled on your workspace
- Verify you have CREATE CATALOG privileges
- Check: `SELECT current_user(), can_create_catalog()`

### Issue: "SQL warehouse not found"
- Check SQL_WAREHOUSE_ID in config.env matches your warehouse
- Ensure warehouse is running (green status in UI)
- Verify HTTP path format: `/sql/1.0/warehouses/<warehouse_id>`

### Issue: "Permission denied" errors
- Verify service principal has correct grants
- Check: `SHOW GRANTS ON TABLE <catalog_name>.<schema_name>.<table_name>`
- Ensure APPLICATION_ID matches exactly (case-sensitive)

### Issue: "Table not found" in backend app
- Backend app checks for catalog, schema, and table on startup
- Check logs for specific error messages
- Verify ZEROBUS_CATALOG, ZEROBUS_SCHEMA, ZEROBUS_TABLE in config.env

### Issue: "Authentication failed"
- Regenerate service principal secret if needed
- Ensure SERVICE_PRINCIPAL_SECRET is correctly copied (no extra spaces)
- Verify workspace host URL includes https:// prefix

## Next Steps

1. **Monitor streaming data**: Create dashboards in Databricks SQL
2. **Set up alerts**: Configure alerts for data quality or volume issues
3. **Optimize performance**: Consider partitioning by date if data volume grows
4. **Scale warehouse**: Increase warehouse size for production loads

## References

- [Frontend Documentation](CLAUDE.frontend.md)
- [Backend Documentation](CLAUDE.backend.md)
- [Main Project Documentation](CLAUDE.md)