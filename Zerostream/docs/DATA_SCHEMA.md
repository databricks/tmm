# ZeroStream Data Schema

## Architecture Overview

**CRITICAL**: Understand the data flow:

```
Mobile Browser → Frontend App → ZeroBus API → Unity Catalog Table
                                                      ↓
Backend App ← (Reads via SQL Warehouse) ← Unity Catalog Table
```

**Frontend writes to ZeroBus, Backend reads from table. They do NOT communicate.**

## Data Flow Transformations

### 1. Mobile Browser → Frontend (JavaScript POST)

Mobile browser collects sensor data and sends to frontend `/api/stream`:

```javascript
// Format sent from browser (camelCase)
{
  clientId: "quantumray42",         // 12-char identifier
  timestamp: "2024-02-03T10:30:00Z", // ISO 8601
  acceleration: {x: 0.1, y: 0.2, z: 9.8},
  accelerationIncludingGravity: {x: 0.1, y: 0.2, z: 9.8},
  rotationRate: {alpha: 0, beta: 0, gamma: 0},
  orientation: {alpha: 45, beta: 10, gamma: 5},
  location: {
    latitude: 37.7749,
    longitude: -122.4194,
    altitude: 10,
    accuracy: 5,
    speed: 0,
    heading: 0
  },
  magnetometer: {x: 0, y: 0, z: 0}  // Optional
}
```

### 2. Frontend → ZeroBus API (Service Principal OAuth2)

Frontend transforms data to flat structure and sends to ZeroBus REST API:

```json
// POST to https://[databricks-host]/api/2.0/zerobus/ingest/{catalog}/{schema}/{table}
// Authorization: Bearer [OAuth2_ACCESS_TOKEN]
//
// OAuth2 token obtained via:
// POST /oidc/v1/token with grant_type=client_credentials
{
  "records": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "client_id": "quantumray42",
      "timestamp": "2024-02-03T10:30:00Z",
      "acceleration_x": 0.1,
      "acceleration_y": 0.2,
      "acceleration_z": 9.8,
      "rotation_alpha": 0,
      "rotation_beta": 0,
      "rotation_gamma": 0,
      "latitude": 37.7749,
      "longitude": -122.4194,
      "altitude": 10,
      "accuracy": 5,
      "speed": 0,
      "heading": 0,
      "magnetic_x": 0,
      "magnetic_y": 0,
      "magnetic_z": 0,
      "received_at": "2024-02-03T10:30:00Z",
      "processing_time_ms": 0
    }
  ]
}
```

**Authentication**: Service Principal OAuth2 (not Basic Auth)
- Get token from `/oidc/v1/token` endpoint
- Use Bearer token in Authorization header
- Token cached and refreshed automatically

### 3. ZeroBus API → Unity Catalog Table

ZeroBus handles ingestion into Delta table. The table schema must match the fields sent by frontend:

```sql
CREATE TABLE IF NOT EXISTS demo_frank.zerostream.sensor_data (
    -- Client identification
    client_id STRING NOT NULL,             -- 12-char readable identifier
    timestamp TIMESTAMP NOT NULL,          -- When sensor reading was taken

    -- Motion sensors (from DeviceMotionEvent)
    acceleration_x DOUBLE,                 -- Linear acceleration (m/s²) excluding gravity
    acceleration_y DOUBLE,
    acceleration_z DOUBLE,
    rotation_alpha DOUBLE,                 -- Rotation rate (deg/s)
    rotation_beta DOUBLE,
    rotation_gamma DOUBLE,

    -- GPS Location (from Geolocation API)
    latitude DOUBLE,                       -- GPS latitude in degrees
    longitude DOUBLE,                      -- GPS longitude in degrees
    altitude DOUBLE,                       -- Altitude in meters above sea level
    accuracy DOUBLE,                       -- Horizontal accuracy in meters
    speed DOUBLE,                          -- Speed in meters/second
    heading DOUBLE,                        -- Direction of travel (0-360 degrees)

    -- Magnetometer (from DeviceOrientationEvent)
    magnetic_x DOUBLE,                     -- Magnetic field strength (μT)
    magnetic_y DOUBLE,
    magnetic_z DOUBLE
)
USING DELTA
CLUSTER BY (client_id, timestamp);
```

**Important Notes**:
- Fields are NULLABLE (not all devices have all sensors)
- No `id` field - Unity Catalog handles internal row identification
- No `received_at` or `processing_time_ms` - ZeroBus handles metadata
- Liquid clustering by `client_id` and `timestamp` for efficient queries

### 4. Unity Catalog Table → Backend (SQL Warehouse)

Backend reads from table using SQL queries:

```python
# Backend queries the table
SELECT client_id, timestamp, latitude, longitude, ...
FROM demo_frank.zerostream.sensor_data
ORDER BY timestamp DESC
```

## Field Mapping Reference

| Browser (camelCase) | Frontend Transform | ZeroBus/Database (snake_case) | Type |
|---------------------|-------------------|-------------------------------|------|
| clientId | client_id | client_id | STRING |
| timestamp | timestamp | timestamp | TIMESTAMP |
| acceleration.x | acceleration_x | acceleration_x | DOUBLE |
| acceleration.y | acceleration_y | acceleration_y | DOUBLE |
| acceleration.z | acceleration_z | acceleration_z | DOUBLE |
| rotationRate.alpha | rotation_alpha | rotation_alpha | DOUBLE |
| rotationRate.beta | rotation_beta | rotation_beta | DOUBLE |
| rotationRate.gamma | rotation_gamma | rotation_gamma | DOUBLE |
| location.latitude | latitude | latitude | DOUBLE |
| location.longitude | longitude | longitude | DOUBLE |
| location.altitude | altitude | altitude | DOUBLE |
| location.accuracy | accuracy | accuracy | DOUBLE |
| location.speed | speed | speed | DOUBLE |
| location.heading | heading | heading | DOUBLE |
| magnetometer.x | magnetic_x | magnetic_x | DOUBLE |
| magnetometer.y | magnetic_y | magnetic_y | DOUBLE |
| magnetometer.z | magnetic_z | magnetic_z | DOUBLE |

## Schema Synchronization

**CRITICAL**: Frontend and database schema MUST match because:

1. Frontend flattens nested JSON into database columns
2. ZeroBus expects exact column names matching table schema
3. Missing or misnamed fields will cause ingestion failure

### When Making Schema Changes

1. **Update database table first** (ALTER TABLE or recreate)
2. **Update frontend transformation** in `zero_frontend/app.py` (lines ~100-126)
3. **Test with curl** to verify ZeroBus accepts new format
4. **Deploy frontend** with updated transformation
5. **Update this documentation**

Backend does NOT need updates for schema changes (it only reads, doesn't transform).

## Validation Rules

### Frontend Validation
- `clientId` must be exactly 12 characters
- `timestamp` must be valid ISO 8601 format
- All numeric fields must be valid numbers (not NaN or Infinity)
- Magnetometer is optional (can be null)

### Database Constraints
- `client_id` and `timestamp` are NOT NULL
- All sensor fields are NULLABLE (devices may lack sensors)
- Use DOUBLE precision for all numeric values
- Timestamps stored in UTC

## Testing Schema Sync

### 1. Test with curl

```bash
# Test frontend endpoint with sample data
curl -X POST [FRONTEND-URL]/api/stream \
  -H "Content-Type: application/json" \
  -d '[{
    "clientId": "testclient123",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "acceleration": {"x": 0, "y": 0, "z": 9.8},
    "accelerationIncludingGravity": {"x": 0, "y": 0, "z": 9.8},
    "rotationRate": {"alpha": 0, "beta": 0, "gamma": 0},
    "orientation": {"alpha": 0, "beta": 0, "gamma": 0},
    "location": {"latitude": 37.7749, "longitude": -122.4194, "altitude": 0, "accuracy": 10, "speed": 0, "heading": 0},
    "magnetometer": {"x": 0, "y": 0, "z": 0}
  }]'
```

### 2. Verify in database

```sql
-- Check if test data arrived
SELECT * FROM demo_frank.zerostream.sensor_data
WHERE client_id = 'testclient123'
ORDER BY timestamp DESC
LIMIT 1;
```

### 3. Check frontend logs

Look for success or error messages:
- Success: `Successfully wrote N records to ZeroBus`
- Error: `ZeroBus API error: [details]`

## Common Schema Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Field name mismatch | ZeroBus 400 error | Check frontend transformation matches table columns |
| Type mismatch | ZeroBus 400 error | Ensure all sensor values are numbers, not strings |
| Missing required field | ZeroBus 400 error | `client_id` and `timestamp` must always be present |
| Extra fields ignored | Data missing columns | Add columns to table before sending new fields |
| Null values | No error, nulls stored | This is expected for optional sensors |

## Schema Evolution Best Practices

### Adding a New Sensor Field

Example: Adding gyroscope data

1. **Extend database schema**:
   ```sql
   ALTER TABLE demo_frank.zerostream.sensor_data
   ADD COLUMNS (
     gyro_x DOUBLE,
     gyro_y DOUBLE,
     gyro_z DOUBLE
   );
   ```

2. **Update frontend** (`zero_frontend/app.py`):
   ```python
   record = {
       "client_id": reading.clientId,
       "timestamp": reading.timestamp,
       # ... existing fields ...
       "gyro_x": reading.gyroscope.x if reading.gyroscope else None,
       "gyro_y": reading.gyroscope.y if reading.gyroscope else None,
       "gyro_z": reading.gyroscope.z if reading.gyroscope else None,
   }
   ```

3. **Update browser collection** (`static/js/sensors.js`)

4. **Test and deploy**

Backend automatically picks up new columns in SELECT queries.

### Removing a Field

1. Frontend stops sending the field (ZeroBus ignores extra columns in table)
2. Later: ALTER TABLE DROP COLUMN (optional cleanup)

### Renaming a Field

1. Add new column to table
2. Update frontend to send both old and new names
3. Deploy and verify data flows to new column
4. Update frontend to send only new name
5. Drop old column from table

## Deployment Checklist

Before deploying frontend changes:

- [ ] Database table has all columns that frontend will send
- [ ] Frontend transformation in `app.py` matches table schema exactly
- [ ] All required fields (client_id, timestamp) are always populated
- [ ] Test with curl shows successful write to ZeroBus
- [ ] No schema mismatch errors in frontend logs

Backend deployment:
- [ ] Backend queries only reference existing table columns
- [ ] No schema mismatch errors in backend logs when querying

## Where to Find Schema Definitions

1. **Database table**: Run `DESCRIBE TABLE demo_frank.zerostream.sensor_data`
2. **Frontend transformation**: `zero_frontend/app.py` lines ~100-126
3. **Browser data format**: `zero_frontend/static/js/sensors.js`
4. **Backend queries**: `zero_backend/app.py` SQL SELECT statements

Keep all four in sync when making changes.
