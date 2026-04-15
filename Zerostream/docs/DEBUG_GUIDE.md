# ZeroStream Debugging Guide

## Architecture Overview

**CRITICAL**: Understand the data flow before debugging:

```
Mobile Browser → Frontend App → ZeroBus API → Unity Catalog Table
                                                      ↓
Backend App ← (Reads via SQL Warehouse) ← Unity Catalog Table
```

**Frontend and Backend DO NOT communicate**. They are independent apps that share only the Unity Catalog table.

## Issue: Sensor Data Table is Empty

If your `sensor_data` table is empty despite sending data from your phone, follow these steps in order:

### Step 1: Verify Mobile Browser is Sending Data

1. Open the frontend app on your mobile device
2. Press "Start" to begin sensor collection
3. Watch for the blue dot to blink once per second (indicates data transmission)
4. Check browser console (if accessible on mobile):
   - Look for `[ZeroBus] Sent data at 2024-02-03T...`
   - Look for error messages

**Common Issues**:
- Sensors not enabled: Check browser permissions for motion and location
- GPS not available: May show 0,0 coordinates if location unavailable
- App not loaded: Verify you're accessing the correct frontend URL

### Step 2: Check Frontend App Logs

Access frontend app logs in Databricks Apps UI and look for:

**Success indicators**:
```
Received N sensor readings from client [client_id]
Successfully wrote N records to ZeroBus
```

**Failure indicators**:
```
ZEROBUS_ENDPOINT not configured
Service Principal credentials not configured
ZeroBus connection failed: ...
ZeroBus API error: [status code]
```

**What each error means**:
- `ZEROBUS_ENDPOINT not configured`: Missing environment variable, check app configuration
- `Service Principal credentials not configured`: Missing SERVICE_PRINCIPAL_ID or SERVICE_PRINCIPAL_SECRET
- `ZeroBus connection failed`: Network issue or wrong endpoint URL
- `ZeroBus API error: 401`: Authentication failed, check Service Principal credentials
- `ZeroBus API error: 404`: Table doesn't exist or wrong endpoint URL
- `ZeroBus API error: 403`: Service Principal lacks permission to write to table

### Step 3: Verify Frontend Configuration

Check that frontend app has required environment variables set:

```bash
# In Databricks Apps UI, check frontend app environment variables:
ZEROBUS_ENDPOINT=https://[workspace].cloud.databricks.com/api/2.0/unity-catalog/tables/[catalog].[schema].[table]/streaming/ingest
SERVICE_PRINCIPAL_ID=[your-service-principal-uuid]
SERVICE_PRINCIPAL_SECRET=[your-service-principal-secret]
```

**Test with curl**:
```bash
# Test if frontend is receiving data (should return success or error)
curl -X POST [YOUR-FRONTEND-URL]/api/stream \
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

### Step 4: Check Unity Catalog Table

Verify the table exists and has correct permissions:

```sql
-- Check if table exists
SHOW TABLES IN demo_frank.zerostream LIKE 'sensor_data';

-- Check table schema
DESCRIBE TABLE demo_frank.zerostream.sensor_data;

-- Count records
SELECT COUNT(*) FROM demo_frank.zerostream.sensor_data;

-- Check latest records
SELECT * FROM demo_frank.zerostream.sensor_data
ORDER BY timestamp DESC
LIMIT 10;

-- Check for your test client
SELECT * FROM demo_frank.zerostream.sensor_data
WHERE client_id = 'testclient123'
ORDER BY timestamp DESC;
```

**Common Issues**:
- Table doesn't exist: Run SQL commands from ZEROBUS_SETUP_GUIDE.md
- Permission denied: Service Principal needs MODIFY permission on table
- Schema mismatch: Check table schema matches DATA_SCHEMA.md

### Step 5: Verify Service Principal Permissions

The Service Principal needs specific permissions:

```sql
-- Grant necessary permissions to Service Principal
GRANT MODIFY ON TABLE demo_frank.zerostream.sensor_data TO `[service-principal-id]`;
GRANT SELECT ON TABLE demo_frank.zerostream.sensor_data TO `[service-principal-id]`;
GRANT USE CATALOG ON CATALOG demo_frank TO `[service-principal-id]`;
GRANT USE SCHEMA ON SCHEMA demo_frank.zerostream TO `[service-principal-id]`;
```

### Step 6: Test ZeroBus API Directly

Test the ZeroBus endpoint directly to isolate frontend issues:

```bash
# Test ZeroBus API with Service Principal auth
curl -X POST https://[workspace].cloud.databricks.com/api/2.0/unity-catalog/tables/demo_frank.zerostream.sensor_data/streaming/ingest \
  -u "[SERVICE_PRINCIPAL_ID]:[SERVICE_PRINCIPAL_SECRET]" \
  -H "Content-Type: application/json" \
  -d '{
    "records": [{
      "client_id": "curltest123",
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "acceleration_x": 0,
      "acceleration_y": 0,
      "acceleration_z": 9.8,
      "rotation_alpha": 0,
      "rotation_beta": 0,
      "rotation_gamma": 0,
      "latitude": 37.7749,
      "longitude": -122.4194,
      "altitude": 0,
      "accuracy": 10,
      "speed": 0,
      "heading": 0,
      "magnetic_x": null,
      "magnetic_y": null,
      "magnetic_z": null
    }]
  }'
```

If this works, the problem is in the frontend app. If it fails, the problem is with ZeroBus configuration or permissions.

## Backend Dashboard Issues

### Backend Showing No Data

The backend reads from the Unity Catalog table - it doesn't receive data from frontend.

1. **Check Backend Logs**:
   - Look for `STARTUP VALIDATION SUCCESSFUL` or errors
   - Check for SQL query failures

2. **Verify SQL Warehouse Configuration**:
   ```bash
   # Check environment variables in backend app:
   SQL_WAREHOUSE_ID=[your-warehouse-id]
   SQL_WAREHOUSE_HTTP_PATH=/sql/1.0/warehouses/[warehouse-id]
   SERVICE_PRINCIPAL_ID=[same-as-frontend]
   SERVICE_PRINCIPAL_SECRET=[same-as-frontend]
   ```

3. **Test Backend API**:
   ```bash
   # Health check
   curl [BACKEND-URL]/api/health

   # Event count
   curl [BACKEND-URL]/api/count

   # Client list
   curl [BACKEND-URL]/api/clients

   # Location data
   curl [BACKEND-URL]/api/locations
   ```

4. **Check SQL Warehouse Status**:
   - Go to SQL Warehouses in Databricks UI
   - Ensure warehouse is running (not stopped)
   - Check warehouse has permission to read the table

**Common Backend Issues**:
- `Database not connected`: SQL Warehouse ID is wrong or warehouse is stopped
- `Missing catalog/schema/table`: Table doesn't exist
- `Authentication failed`: Service Principal credentials are wrong
- Empty responses: Table exists but has no data (check frontend first)

## Deployment Issues

### After Deployment, App Not Working

1. **Redeploy with Latest Code**:
   ```bash
   ./deploy-app.sh zerostream ./zero_frontend
   ./deploy-app.sh zerobackend ./zero_backend
   ```

2. **Check App Status**:
   - Go to Databricks Apps UI
   - Verify both apps show "Running" status
   - Check app logs for startup errors

3. **Verify Environment Variables**:
   - Apps inherit variables from config.env during deployment
   - Check Apps UI → Settings → Environment Variables
   - Ensure all required variables are set

### Environment Variable Not Being Used

If you updated config.env but app still uses old values:

1. Environment variables are set during deployment, not read at runtime
2. After changing config.env, you MUST redeploy:
   ```bash
   ./deploy-app.sh [app-name] [app-path]
   ```

## Common Error Messages and Solutions

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `ZEROBUS_ENDPOINT not configured` | Missing env var | Set ZEROBUS_ENDPOINT in config.env and redeploy |
| `Service Principal credentials not configured` | Missing auth | Set SERVICE_PRINCIPAL_ID and SECRET in config.env |
| `ZeroBus API error: 401` | Auth failed | Verify Service Principal credentials are correct |
| `ZeroBus API error: 403` | Permission denied | Grant MODIFY permission to Service Principal |
| `ZeroBus API error: 404` | Wrong endpoint | Check ZEROBUS_ENDPOINT URL is correct |
| `Database not connected` | SQL Warehouse issue | Check SQL_WAREHOUSE_ID and ensure warehouse is running |
| `Table not found` | Missing table | Run SQL setup from ZEROBUS_SETUP_GUIDE.md |

## Design Principle Reminder

This application follows "No Fallbacks, No Dummy Data":
- Configuration errors cause immediate failure
- No silent fallbacks to default values
- No mock/dummy data returned
- This is intentional - errors should be visible immediately

If you see an error message, it means configuration is missing or incorrect. Fix the configuration, don't expect fallback behavior.

## Getting Additional Help

If the above steps don't resolve your issue:

1. **Collect Information**:
   - Frontend app logs (full startup + recent activity)
   - Backend app logs (full startup + recent activity)
   - Browser console output from mobile device
   - SQL query results from table
   - Configuration values (redact secrets)

2. **Verify Each Component**:
   - Mobile → Frontend: Use browser dev tools
   - Frontend → ZeroBus: Check frontend logs
   - ZeroBus → Table: Query table directly
   - Table → Backend: Check backend logs and queries

3. **Check Permissions**:
   - Service Principal has MODIFY on table (for frontend)
   - Service Principal has SELECT on table (for backend)
   - SQL Warehouse has READ access to catalog
