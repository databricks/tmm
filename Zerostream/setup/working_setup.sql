-- Use the catalog
USE CATALOG demo_frank;

-- Create schema
CREATE SCHEMA IF NOT EXISTS zerobus
COMMENT 'Schema for mobile sensor data';

-- Use the schema
USE SCHEMA zerobus;

-- Create the sensor data table with liquid clustering
CREATE TABLE IF NOT EXISTS sensors (
    -- Metadata
    id STRING NOT NULL,
    client_id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Motion sensors
    acceleration_x DOUBLE,
    acceleration_y DOUBLE,
    acceleration_z DOUBLE,
    rotation_alpha DOUBLE,
    rotation_beta DOUBLE,
    rotation_gamma DOUBLE,
    
    -- Location
    latitude DOUBLE,
    longitude DOUBLE,
    altitude DOUBLE,
    accuracy DOUBLE,
    speed DOUBLE,
    heading DOUBLE,
    
    -- Magnetometer
    magnetic_x DOUBLE,
    magnetic_y DOUBLE,
    magnetic_z DOUBLE,
    
    -- Processing metadata
    received_at TIMESTAMP,  -- Removed DEFAULT CURRENT_TIMESTAMP()
    processing_time_ms LONG
)
USING DELTA
CLUSTER BY (client_id, timestamp)
COMMENT 'Mobile sensor data from ZeroStream app';

-- Verify table creation
DESCRIBE TABLE sensors;



