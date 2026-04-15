import os
import logging
import math
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Version Management
# ==========================================

def get_version() -> str:
    """Read version from version.json and return display format (e.g., '0.18')"""
    version_file = Path(__file__).parent / "version.json"
    try:
        with open(version_file) as f:
            data = json.load(f)
            version_int = data.get("version", 0)
            return f"{version_int / 100:.2f}"
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return "0.00"

# ==========================================
# Data Models
# ==========================================

class Vector3D(BaseModel):
    x: float
    y: float
    z: float

class RotationData(BaseModel):
    alpha: float
    beta: float
    gamma: float

class LocationData(BaseModel):
    latitude: float
    longitude: float
    altitude: Optional[float] = 0
    accuracy: Optional[float] = 0
    altitudeAccuracy: Optional[float] = 0
    speed: Optional[float] = 0
    heading: Optional[float] = 0

class SensorData(BaseModel):
    clientId: str
    timestamp: str
    acceleration: Vector3D
    accelerationIncludingGravity: Vector3D
    rotationRate: RotationData
    orientation: RotationData
    location: LocationData
    magnetometer: Optional[Vector3D] = None

# ==========================================
# Configuration
# ==========================================

def get_config():
    """Get ZeroBus configuration from environment variables"""
    server_endpoint = os.getenv("FRONTEND_ZEROBUS_ENDPOINT")
    workspace_url = os.getenv("DATABRICKS_HOST")
    catalog = os.getenv("ZEROBUS_CATALOG")
    schema = os.getenv("ZEROBUS_SCHEMA")
    table = os.getenv("ZEROBUS_TABLE")
    client_id = os.getenv("FRONTEND_SERVICE_PRINCIPAL_ID")
    client_secret = os.getenv("FRONTEND_SERVICE_PRINCIPAL_SECRET")

    if not all([server_endpoint, workspace_url, catalog, schema, table, client_id, client_secret]):
        missing = [k for k, v in {
            "FRONTEND_ZEROBUS_ENDPOINT": server_endpoint,
            "DATABRICKS_HOST": workspace_url,
            "ZEROBUS_CATALOG": catalog,
            "ZEROBUS_SCHEMA": schema,
            "ZEROBUS_TABLE": table,
            "FRONTEND_SERVICE_PRINCIPAL_ID": client_id,
            "FRONTEND_SERVICE_PRINCIPAL_SECRET": client_secret
        }.items() if not v]
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    return {
        "server_endpoint": server_endpoint,
        "workspace_url": workspace_url,
        "table_name": f"{catalog}.{schema}.{table}",
        "client_id": client_id,
        "client_secret": client_secret,
    }

# ==========================================
# Data Transformation
# ==========================================

def safe_float(value) -> Optional[float]:
    """Convert value to float, returning None if invalid (NaN, Infinity, or None)"""
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None

def to_timestamp_micros(dt_obj) -> int:
    """Convert datetime to Unix timestamp in microseconds (for ZeroBus JSON ingestion)"""
    if dt_obj.tzinfo is not None:
        dt_obj = dt_obj.astimezone(timezone.utc)
    return int(dt_obj.timestamp() * 1_000_000)

def transform_sensor_data(readings: List[SensorData]) -> List[dict]:
    """Transform sensor readings to table schema dictionaries"""
    records = []

    for reading in readings:
        try:
            ts = datetime.fromisoformat(reading.timestamp.replace('Z', '+00:00'))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            received_at = datetime.now(timezone.utc)
        except Exception as e:
            logger.error(f"Invalid timestamp: {reading.timestamp} - {e}")
            continue

        record = {
            "id": str(uuid.uuid4()),
            "client_id": reading.clientId,
            "timestamp": to_timestamp_micros(ts),
            "acceleration_x": safe_float(reading.acceleration.x if reading.acceleration else None),
            "acceleration_y": safe_float(reading.acceleration.y if reading.acceleration else None),
            "acceleration_z": safe_float(reading.acceleration.z if reading.acceleration else None),
            "rotation_alpha": safe_float(reading.rotationRate.alpha if reading.rotationRate else None),
            "rotation_beta": safe_float(reading.rotationRate.beta if reading.rotationRate else None),
            "rotation_gamma": safe_float(reading.rotationRate.gamma if reading.rotationRate else None),
            "orientation_alpha": safe_float(reading.orientation.alpha if reading.orientation else None),
            "orientation_beta": safe_float(reading.orientation.beta if reading.orientation else None),
            "orientation_gamma": safe_float(reading.orientation.gamma if reading.orientation else None),
            "latitude": safe_float(reading.location.latitude if reading.location else None),
            "longitude": safe_float(reading.location.longitude if reading.location else None),
            "altitude": safe_float(reading.location.altitude if reading.location else None),
            "accuracy": safe_float(reading.location.accuracy if reading.location else None),
            "speed": safe_float(reading.location.speed if reading.location else None),
            "heading": safe_float(reading.location.heading if reading.location else None),
            "magnetic_x": safe_float(reading.magnetometer.x if reading.magnetometer else None),
            "magnetic_y": safe_float(reading.magnetometer.y if reading.magnetometer else None),
            "magnetic_z": safe_float(reading.magnetometer.z if reading.magnetometer else None),
            "received_at": to_timestamp_micros(received_at),
            "processing_time_ms": 0
        }
        records.append(record)

    return records

# ==========================================
# ZeroBus Push
# ==========================================

def push_to_zerobus(records: List[dict]) -> dict:
    """Push records to ZeroBus (creates stream, pushes records, closes stream)"""
    config = get_config()

    sdk = ZerobusSdk(config["server_endpoint"], config["workspace_url"])
    table_properties = TableProperties(config["table_name"])
    options = StreamConfigurationOptions(record_type=RecordType.JSON)

    stream = sdk.create_stream(
        config["client_id"],
        config["client_secret"],
        table_properties,
        options
    )

    successful = 0
    failed = 0

    try:
        for record in records:
            try:
                ack = stream.ingest_record(record)
                ack.wait_for_ack()
                successful += 1
            except Exception as e:
                logger.error(f"Failed to ingest record {record.get('id', 'unknown')}: {e}")
                failed += 1
    finally:
        stream.close()

    logger.info(f"Ingestion complete: {successful} successful, {failed} failed")
    return {"successful": successful, "failed": failed}

# ==========================================
# API Endpoints
# ==========================================

@app.post("/api/stream")
async def stream_sensor_data(data: List[SensorData]):
    """Receive sensor data and stream to ZeroBus"""
    try:
        logger.info(f"Received {len(data)} sensor readings from client {data[0].clientId if data else 'unknown'}")

        records = transform_sensor_data(data)
        if not records:
            raise HTTPException(status_code=400, detail="No valid records after transformation")

        result = push_to_zerobus(records)

        if result["successful"] > 0:
            return {
                "status": "success" if result["failed"] == 0 else "partial_success",
                "records_ingested": result["successful"],
                "records_failed": result["failed"],
                "client_id": data[0].clientId if data else None,
                "message": f"Ingested {result['successful']}/{len(records)} records"
            }
        else:
            raise HTTPException(status_code=503, detail="Failed to ingest any records")

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        config = get_config()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "endpoint": config["server_endpoint"],
            "table": config["table_name"],
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }

@app.get("/api/version")
async def get_app_version():
    """Return application version"""
    version = get_version()
    return {
        "version": version,
        "app": "zerostream",
        "timestamp": datetime.now().isoformat(),
    }

# ==========================================
# Static Files with Version Injection
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve index.html with version injected"""
    version = get_version()
    index_path = Path(__file__).parent / "static" / "index.html"
    html = index_path.read_text()
    html = html.replace("__VERSION__", version)
    return HTMLResponse(content=html)

# Mount static files for CSS, JS, images (but not index.html)
app.mount("/", StaticFiles(directory="static", html=False), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
