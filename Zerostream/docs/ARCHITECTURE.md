# ZeroStream Architecture



# ZeroStream Architecture

## Data Flow

```
Mobile Browser
    ↓ (JavaScript POST to /api/stream)
Frontend App (zero_frontend)
    ↓ (ZeroBus API with Service Principal auth)
ZeroBus Streaming Service
    ↓ (Ingestion)
Unity Catalog Table (demo_frank.zerostream.sensor_data)
    ↑ (SQL queries)
Backend App (zero_backend) - Dashboard
```

## Components

### 1. Mobile Browser
- Collects sensor data (accelerometer, GPS, magnetometer, etc.)
- Sends data to Frontend App via JavaScript
- Uses relative URL `/api/stream`

### 2. Frontend App (`zero_frontend`)
- **Purpose**: Sensor data collection endpoint
- **Receives**: POST requests from mobile browsers
- **Writes to**: ZeroBus API (NOT directly to database)
- **Authentication**: Service Principal for ZeroBus access
- **Key endpoint**: `/api/stream` - receives and forwards sensor data

### 3. ZeroBus Streaming Service
- **Purpose**: High-throughput data ingestion
- **Receives**: Streaming data from Frontend via API
- **Stores**: Data in Unity Catalog Delta table
- **Authentication**: Service Principal credentials
- **Endpoint**: Configured in `ZEROBUS_ENDPOINT`

### 4. Unity Catalog Table
- **Location**: `demo_frank.zerostream.sensor_data`
- **Format**: Delta table with liquid clustering
- **Clustering**: By `client_id` and `timestamp`
- **Purpose**: Persistent storage for all sensor data

### 5. Backend App (`zero_backend`)
- **Purpose**: Dashboard and visualization
- **Reads from**: Unity Catalog table (read-only)
- **Features**: Map, client list, event counter
- **Authentication**: Service Principal for SQL Warehouse access

## Important Notes

- **Frontend and Backend DO NOT communicate**
- **Frontend does NOT write directly to database**
- **Frontend uses ZeroBus API for streaming ingestion**
- **Service Principal enables ZeroBus API access**
- **Both apps need database credentials but for different purposes**:
  - Frontend: For ZeroBus API authentication
  - Backend: For SQL Warehouse queries

## Service Principal Requirements

The Service Principal needs permissions for:
1. **ZeroBus API access** - to stream data (used by Frontend)
2. **SQL Warehouse access** - to query data (used by Backend)
3. **Unity Catalog table access** - READ for Backend, WRITE via ZeroBus for Frontend