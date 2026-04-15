-- Databricks notebook source
-- MAGIC %md
-- MAGIC # ZeroStream Unity Catalog Setup
-- MAGIC
-- MAGIC This notebook creates the Unity Catalog infrastructure for ZeroStream sensor data streaming.
-- MAGIC
-- MAGIC **Instructions:**
-- MAGIC 1. Update the variables below with your catalog and schema names
-- MAGIC 2. Run all cells in order
-- MAGIC 3. Verify the setup with the test queries at the end
-- MAGIC
-- MAGIC **Prerequisites:**
-- MAGIC - Unity Catalog enabled on workspace
-- MAGIC - CREATE CATALOG and CREATE SCHEMA privileges
-- MAGIC - Connected to a SQL warehouse

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Configuration
-- MAGIC
-- MAGIC Update these variables for your setup:

-- COMMAND ----------

-- Set your catalog and schema names here
SET VAR catalog_name = 'sensor_catalog';
SET VAR schema_name = 'mobile_data';
SET VAR table_name = 'sensor_data';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Create Catalog
-- MAGIC
-- MAGIC Creates the Unity Catalog catalog if it doesn't already exist.

-- COMMAND ----------

CREATE CATALOG IF NOT EXISTS ${catalog_name}
COMMENT 'ZeroStream mobile sensor data catalog';

-- Verify catalog creation
DESCRIBE CATALOG ${catalog_name};

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Create Schema
-- MAGIC
-- MAGIC Creates the schema within the catalog.

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS ${catalog_name}.${schema_name}
COMMENT 'Mobile sensor telemetry data from ZeroStream app';

-- Verify schema creation
DESCRIBE SCHEMA ${catalog_name}.${schema_name};

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Create Sensor Data Table
-- MAGIC
-- MAGIC Creates the Delta table with complete sensor data schema:
-- MAGIC - Client identification
-- MAGIC - Acceleration (with and without gravity)
-- MAGIC - Rotation rates (gyroscope)
-- MAGIC - Orientation (compass, pitch, roll)
-- MAGIC - GPS location
-- MAGIC - Magnetometer readings
-- MAGIC - Timestamps

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS ${catalog_name}.${schema_name}.${table_name} (
    -- Device identification
    client_id STRING COMMENT 'Unique device identifier (12-char readable format)',
    timestamp TIMESTAMP COMMENT 'Sensor reading timestamp',

    -- Acceleration (m/s²) - linear motion without gravity
    acceleration_x DOUBLE COMMENT 'X-axis acceleration (m/s²)',
    acceleration_y DOUBLE COMMENT 'Y-axis acceleration (m/s²)',
    acceleration_z DOUBLE COMMENT 'Z-axis acceleration (m/s²)',

    -- Acceleration including gravity (m/s²)
    accel_gravity_x DOUBLE COMMENT 'X-axis acceleration with gravity (m/s²)',
    accel_gravity_y DOUBLE COMMENT 'Y-axis acceleration with gravity (m/s²)',
    accel_gravity_z DOUBLE COMMENT 'Z-axis acceleration with gravity (m/s²)',

    -- Rotation Rate (°/s) - gyroscope angular velocity
    rotation_alpha DOUBLE COMMENT 'Alpha rotation rate (°/s)',
    rotation_beta DOUBLE COMMENT 'Beta rotation rate (°/s)',
    rotation_gamma DOUBLE COMMENT 'Gamma rotation rate (°/s)',

    -- Orientation (degrees) - device angles
    orientation_alpha DOUBLE COMMENT 'Heading/compass (0-360°)',
    orientation_beta DOUBLE COMMENT 'Pitch angle (-180 to 180°)',
    orientation_gamma DOUBLE COMMENT 'Roll angle (-90 to 90°)',

    -- GPS Location
    latitude DOUBLE COMMENT 'GPS latitude',
    longitude DOUBLE COMMENT 'GPS longitude',
    altitude DOUBLE COMMENT 'Altitude above sea level (meters)',
    location_accuracy DOUBLE COMMENT 'GPS accuracy (meters)',
    altitude_accuracy DOUBLE COMMENT 'Altitude accuracy (meters)',
    speed DOUBLE COMMENT 'Speed (m/s)',
    heading DOUBLE COMMENT 'GPS heading (0-360°)',

    -- Magnetometer (µT) - magnetic field strength
    magnetometer_x DOUBLE COMMENT 'X-axis magnetic field (µT)',
    magnetometer_y DOUBLE COMMENT 'Y-axis magnetic field (µT)',
    magnetometer_z DOUBLE COMMENT 'Z-axis magnetic field (µT)',

    -- Metadata
    ingestion_time TIMESTAMP COMMENT 'Backend ingestion timestamp'
)
USING DELTA
PARTITIONED BY (DATE(timestamp))
COMMENT 'Mobile sensor data collected by ZeroStream app'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

-- Verify table creation
DESCRIBE TABLE EXTENDED ${catalog_name}.${schema_name}.${table_name};

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 4: Grant Catalog and Schema Permissions
-- MAGIC
-- MAGIC Grants USAGE permissions to allow access to the catalog and schema.

-- COMMAND ----------

-- Grant USAGE on catalog to all account users
GRANT USAGE ON CATALOG ${catalog_name} TO `account users`;

-- Grant USAGE on schema to all account users
GRANT USAGE ON SCHEMA ${catalog_name}.${schema_name} TO `account users`;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 5: Grant Table Permissions
-- MAGIC
-- MAGIC Grants SELECT (read) and MODIFY (write/stream) permissions on the table.

-- COMMAND ----------

-- Grant SELECT permission for reading data
GRANT SELECT ON TABLE ${catalog_name}.${schema_name}.${table_name} TO `account users`;

-- Grant MODIFY permission for streaming/writing data
GRANT MODIFY ON TABLE ${catalog_name}.${schema_name}.${table_name} TO `account users`;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 6: Grant Service Principal Permissions
-- MAGIC
-- MAGIC **IMPORTANT:** Replace `zerostream-streamer` with your actual service principal name.
-- MAGIC
-- MAGIC Uncomment and run these commands after creating your service principal:

-- COMMAND ----------

-- Uncomment these lines after creating service principal
-- GRANT USAGE ON CATALOG ${catalog_name} TO `zerostream-streamer`;
-- GRANT USAGE ON SCHEMA ${catalog_name}.${schema_name} TO `zerostream-streamer`;
-- GRANT SELECT, MODIFY ON TABLE ${catalog_name}.${schema_name}.${table_name} TO `zerostream-streamer`;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Verification & Testing

-- COMMAND ----------

-- Show all catalogs
SHOW CATALOGS;

-- COMMAND ----------

-- Show schemas in catalog
SHOW SCHEMAS IN ${catalog_name};

-- COMMAND ----------

-- Show tables in schema
SHOW TABLES IN ${catalog_name}.${schema_name};

-- COMMAND ----------

-- View table schema
DESCRIBE ${catalog_name}.${schema_name}.${table_name};

-- COMMAND ----------

-- Check table properties
SHOW TBLPROPERTIES ${catalog_name}.${schema_name}.${table_name};

-- COMMAND ----------

-- View grants on catalog
SHOW GRANTS ON CATALOG ${catalog_name};

-- COMMAND ----------

-- View grants on schema
SHOW GRANTS ON SCHEMA ${catalog_name}.${schema_name};

-- COMMAND ----------

-- View grants on table
SHOW GRANTS ON TABLE ${catalog_name}.${schema_name}.${table_name};

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Test: Insert Sample Record

-- COMMAND ----------

-- Insert a test sensor reading
INSERT INTO ${catalog_name}.${schema_name}.${table_name} VALUES (
    'test-device-001',           -- client_id
    CURRENT_TIMESTAMP(),         -- timestamp
    0.12, -0.34, 0.05,          -- acceleration x,y,z
    0.12, -0.34, 9.85,          -- accel_gravity x,y,z
    2.5, -1.2, 0.8,             -- rotation alpha,beta,gamma
    45.6, 12.3, -5.7,           -- orientation alpha,beta,gamma
    37.7749, -122.4194,         -- latitude, longitude
    15.2, 5.0, 2.0,             -- altitude, location_accuracy, altitude_accuracy
    2.5, 45.0,                  -- speed, heading
    25.5, -12.3, 48.7,          -- magnetometer x,y,z
    CURRENT_TIMESTAMP()          -- ingestion_time
);

-- COMMAND ----------

-- Verify the test record was inserted
SELECT * FROM ${catalog_name}.${schema_name}.${table_name}
WHERE client_id = 'test-device-001';

-- COMMAND ----------

-- Count total records
SELECT COUNT(*) as total_records
FROM ${catalog_name}.${schema_name}.${table_name};

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Sample Queries
-- MAGIC
-- MAGIC Example queries to analyze sensor data:

-- COMMAND ----------

-- Get latest reading for each device
SELECT
    client_id,
    MAX(timestamp) as last_reading,
    COUNT(*) as total_readings
FROM ${catalog_name}.${schema_name}.${table_name}
GROUP BY client_id
ORDER BY last_reading DESC;

-- COMMAND ----------

-- Get average acceleration by device
SELECT
    client_id,
    AVG(acceleration_x) as avg_accel_x,
    AVG(acceleration_y) as avg_accel_y,
    AVG(acceleration_z) as avg_accel_z,
    COUNT(*) as reading_count
FROM ${catalog_name}.${schema_name}.${table_name}
GROUP BY client_id;

-- COMMAND ----------

-- Get GPS path for a device (ordered by time)
SELECT
    client_id,
    timestamp,
    latitude,
    longitude,
    altitude,
    location_accuracy,
    speed
FROM ${catalog_name}.${schema_name}.${table_name}
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
ORDER BY timestamp;

-- COMMAND ----------

-- Get orientation statistics
SELECT
    client_id,
    AVG(orientation_alpha) as avg_heading,
    AVG(orientation_beta) as avg_pitch,
    AVG(orientation_gamma) as avg_roll,
    STDDEV(orientation_alpha) as stddev_heading
FROM ${catalog_name}.${schema_name}.${table_name}
GROUP BY client_id;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Cleanup (Optional)
-- MAGIC
-- MAGIC **WARNING:** Only run these commands if you want to delete the test record or entire table.

-- COMMAND ----------

-- Delete test record only
-- DELETE FROM ${catalog_name}.${schema_name}.${table_name}
-- WHERE client_id = 'test-device-001';

-- COMMAND ----------

-- Drop entire table (CAREFUL!)
-- DROP TABLE IF EXISTS ${catalog_name}.${schema_name}.${table_name};

-- Drop schema (CAREFUL!)
-- DROP SCHEMA IF EXISTS ${catalog_name}.${schema_name} CASCADE;

-- Drop catalog (CAREFUL!)
-- DROP CATALOG IF EXISTS ${catalog_name} CASCADE;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Setup Complete! ✓
-- MAGIC
-- MAGIC ### Next Steps:
-- MAGIC
-- MAGIC 1. **Create Service Principal**
-- MAGIC    ```bash
-- MAGIC    databricks service-principals create --display-name zerostream-streamer
-- MAGIC    databricks service-principals create-secret --service-principal-id <app-id>
-- MAGIC    ```
-- MAGIC
-- MAGIC 2. **Update config.env**
-- MAGIC    ```
-- MAGIC    ZEROBUS_CATALOG=sensor_catalog
-- MAGIC    ZEROBUS_SCHEMA=mobile_data
-- MAGIC    ZEROBUS_TABLE=sensor_data
-- MAGIC    ZEROBUS_API_KEY=<service-principal-secret>
-- MAGIC    ```
-- MAGIC
-- MAGIC 3. **Implement Backend ZeroBus Client**
-- MAGIC    - See CLAUDE.backend.md for architecture
-- MAGIC    - Implement services/zerobus_client.py
-- MAGIC    - Deploy zero_backend app
-- MAGIC
-- MAGIC 4. **Start Streaming Data**
-- MAGIC    - Open ZeroStream mobile app
-- MAGIC    - Start sensors
-- MAGIC    - Monitor this table for incoming data
