"""
ZeroStream Backend with Modular Data Providers

Supports both Zerobus (Databricks SQL) and Lakebase (PostgreSQL) backends.
Switch between data sources via API or configuration.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import data providers
from providers import get_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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
# Configuration
# ==========================================


class Config:
    """Application configuration from environment variables

    Backend-specific vars use BACKEND_ prefix.
    Shared vars (DATABRICKS_HOST, ZEROBUS_*) have no prefix.
    """

    # Databricks workspace (shared)
    DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")

    # Backend-specific credentials
    DATABRICKS_TOKEN = os.getenv("BACKEND_DATABRICKS_TOKEN")

    # SQL Warehouse (Zerobus)
    SQL_WAREHOUSE_ID = os.getenv("BACKEND_SQL_WAREHOUSE_ID")
    SQL_WAREHOUSE_HTTP_PATH = os.getenv("BACKEND_SQL_WAREHOUSE_HTTP_PATH")

    # Unity Catalog (shared)
    CATALOG = os.getenv("ZEROBUS_CATALOG")
    SCHEMA = os.getenv("ZEROBUS_SCHEMA")
    TABLE = os.getenv("ZEROBUS_TABLE")

    # Lakebase settings (no prefix - backend-only)
    LAKEBASE_HOST = os.getenv("LAKEBASE_HOST")
    LAKEBASE_PORT = int(os.getenv("LAKEBASE_PORT", "5432"))
    LAKEBASE_DATABASE = os.getenv("LAKEBASE_DATABASE", "databricks_postgres")
    LAKEBASE_CATALOG = os.getenv("LAKEBASE_CATALOG")
    LAKEBASE_SCHEMA = os.getenv("LAKEBASE_SCHEMA")
    LAKEBASE_TABLE = os.getenv("LAKEBASE_TABLE")

    # Frontend URL (for QR code and mobile app link)
    FRONTEND_URL = os.getenv("BACKEND_FRONTEND_URL")


# ==========================================
# Data Models
# ==========================================


class SensorReading(BaseModel):
    """Single sensor reading from mobile device"""

    client_id: str = Field(..., description="12-character device ID")
    timestamp: str = Field(..., description="ISO timestamp")
    acceleration: Dict[str, float]
    accelerationIncludingGravity: Dict[str, float]
    rotationRate: Dict[str, float]
    orientation: Dict[str, float]
    location: Dict[str, float]
    magnetometer: Optional[Dict[str, float]] = None


class DataSourceSwitch(BaseModel):
    """Request to switch data source"""

    source: str = Field(..., description="Data source: 'zerobus' or 'lakebase'")


# ==========================================
# FastAPI Application
# ==========================================

app = FastAPI(
    title="ZeroStream Backend",
    description="Sensor data streaming with Zerobus/Lakebase support",
    version=get_version(),
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Global Exception Handler (ensures JSON errors)
# ==========================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return JSON error response"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url.path),
        },
    )


# ==========================================
# Global State
# ==========================================

config = Config()
current_provider = None  # ZerobusProvider or LakebaseProvider
current_source: str = None  # 'zerobus' or 'lakebase'
startup_errors: List[str] = []

# Track providers for switching (initialized on-demand)
providers: Dict[str, Any] = {}  # str -> ZerobusProvider | LakebaseProvider


# ==========================================
# Provider Management
# ==========================================


def initialize_provider(source_type: str):
    """Initialize a data provider of the specified type"""
    global providers

    try:
        provider = get_provider(source_type)

        # Store provider immediately so we can access its errors even if init fails
        providers[source_type] = provider

        # Validate configuration
        errors = provider.validate_config()
        if errors:
            for error in errors:
                logger.error(f"[{source_type}] Config Error: {error}")
            return None

        # Connect
        if not provider.connect():
            # validation_errors are populated by connect() on failure
            return None

        logger.info(f"[{source_type}] Provider initialized successfully")
        return provider

    except Exception as e:
        logger.error(f"[{source_type}] Failed to initialize: {str(e)}")
        return None


def switch_provider(source_type: str) -> bool:
    """Switch to a different data provider"""
    global current_provider, current_source, providers

    if source_type not in ["zerobus", "lakebase"]:
        raise ValueError(f"Invalid source type: {source_type}")

    # Check if provider already initialized
    if source_type in providers and providers[source_type].is_connected:
        current_provider = providers[source_type]
        current_source = source_type
        logger.info(f"Switched to existing {source_type} provider")
        return True

    # Initialize new provider
    provider = initialize_provider(source_type)
    if provider:
        providers[source_type] = provider
        current_provider = provider
        current_source = source_type
        logger.info(f"Switched to new {source_type} provider")
        return True

    return False


# ==========================================
# Startup / Shutdown
# ==========================================


@app.on_event("startup")
async def startup_event():
    """Backend startup - providers are initialized on-demand when requested"""
    version = get_version()
    logger.info("=" * 70)
    logger.info(f"ZeroStream Backend Starting (v{version})")
    logger.info("=" * 70)
    logger.info("Data providers: Zerobus (Databricks SQL) and Lakebase (PostgreSQL)")
    logger.info("Providers will be initialized on first use")
    logger.info("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up all providers on shutdown"""
    for name, provider in providers.items():
        if provider:
            provider.close()
            logger.info(f"[{name}] Provider closed")
    logger.info("ZeroStream Backend Shutdown")


# ==========================================
# API Endpoints - Data Source Management
# ==========================================


@app.get("/api/datasource")
async def get_data_source():
    """Get current data source information"""
    return {
        "current": current_source,
        "available": ["zerobus", "lakebase"],
        "provider_name": current_provider.name if current_provider else None,
        "table": current_provider.full_table_name if current_provider else None,
        "connected": current_provider.is_connected if current_provider else False,
        "providers_initialized": list(providers.keys()),
    }


@app.post("/api/datasource")
async def set_data_source(request: DataSourceSwitch):
    """Switch to a different data source"""
    source = request.source.lower()

    if source not in ["zerobus", "lakebase"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Invalid data source: {source}",
                "valid_options": ["zerobus", "lakebase"],
            },
        )

    if source == current_source:
        return {
            "status": "unchanged",
            "message": f"Already using {source}",
            "current": current_source,
        }

    try:
        if switch_provider(source):
            return {
                "status": "switched",
                "previous": "lakebase" if source == "zerobus" else "zerobus",
                "current": current_source,
                "provider_name": current_provider.name,
                "table": current_provider.full_table_name,
            }
        else:
            # Get detailed error from provider if available
            error_details = []
            if source in providers and hasattr(providers[source], 'validation_errors'):
                error_details = providers[source].validation_errors

            raise HTTPException(
                status_code=503,
                detail={
                    "error": f"Failed to switch to {source}",
                    "message": "Provider initialization failed. Check configuration and logs.",
                    "current": current_source,
                    "details": error_details,
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching to {source}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "error": f"Failed to switch to {source}",
                "message": str(e),
                "current": current_source,
            },
        )


# ==========================================
# API Endpoints - Health & Status
# ==========================================


@app.get("/api/health")
async def health_check():
    """Health check endpoint with detailed status"""
    status = "healthy" if not startup_errors else "unhealthy"
    version = get_version()

    return {
        "service": "ZeroStream Backend",
        "version": version,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "data_source": {
            "current": current_source if current_provider else None,
            "provider": current_provider.name if current_provider else None,
            "connected": current_provider.is_connected if current_provider else False,
            "table": current_provider.full_table_name if current_provider else None,
        },
        "providers_initialized": list(providers.keys()),
        "errors": startup_errors if startup_errors else None,
    }


@app.get("/api/version")
async def get_app_version():
    """Return application version"""
    version = get_version()
    return {
        "version": version,
        "app": "zerobackend",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/status")
async def get_status():
    """Get detailed system status with data statistics"""
    if not current_provider or not current_provider.is_connected:
        raise HTTPException(
            status_code=503,
            detail={"error": "No data provider connected", "issues": startup_errors},
        )

    try:
        data_status = current_provider.get_status()

        return {
            "healthy": not bool(startup_errors),
            "database_connected": current_provider.is_connected,
            "data_source": {
                "type": current_source,
                "provider": current_provider.name,
                "table": current_provider.full_table_name,
            },
            "configuration": {
                "workspace": config.DATABRICKS_HOST,
                "zerobus_catalog": config.CATALOG,
                "lakebase_catalog": config.LAKEBASE_CATALOG,
            },
            "data": data_status,
            "errors": startup_errors if startup_errors else [],
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Status query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# API Endpoints - Data Queries
# ==========================================


@app.get("/api/count")
async def get_event_count():
    """Get total event count"""
    if not current_provider or not current_provider.is_connected:
        raise HTTPException(
            status_code=503,
            detail={"error": "Service not ready", "issues": startup_errors},
        )

    try:
        count = current_provider.get_count()
        return {
            "count": count,
            "source": current_source,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Count query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locations")
async def get_locations(full_trace: bool = False, client_id: str = None, max_points: int = 500):
    """Get device locations for map display

    Args:
        full_trace: If True, return all points for trace visualization
        client_id: If provided with full_trace, filter to only this client's data
        max_points: Maximum points for full_trace (default 500). If more points exist,
                   SQL subsampling evenly distributes points across the time range.
    """
    if not current_provider or not current_provider.is_connected:
        raise HTTPException(
            status_code=503,
            detail={"error": "Service not ready", "issues": startup_errors},
        )

    try:
        locations = current_provider.get_locations(full_trace=full_trace, client_id=client_id, max_points=max_points)
        # Get SQL execution time if available (Lakebase provider tracks this)
        sql_time_ms = getattr(current_provider, 'last_sql_time_ms', None)
        return {
            "locations": locations,
            "source": current_source,
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id,  # Echo back for debugging
            "max_points": max_points if full_trace else None,
            "subsampled": len(locations) == max_points if full_trace else False,
            "sql_time_ms": sql_time_ms,  # SQL execution time (Lakebase only)
        }

    except Exception as e:
        logger.error(f"Locations query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clients")
async def get_clients():
    """Get list of all clients with their stats"""
    if not current_provider or not current_provider.is_connected:
        raise HTTPException(
            status_code=503,
            detail={"error": "Service not ready", "issues": startup_errors},
        )

    try:
        result = current_provider.get_clients()
        return {
            **result,
            "source": current_source,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Clients query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream-data")
async def get_stream_data(limit: int = 50):
    """Get recent sensor readings for streaming table view

    Args:
        limit: Maximum number of records to return (default 50)
    """
    if not current_provider or not current_provider.is_connected:
        raise HTTPException(
            status_code=503,
            detail={"error": "Service not ready", "issues": startup_errors},
        )

    try:
        records = current_provider.get_stream_data(limit=limit)
        return {
            "records": records,
            "count": len(records),
            "source": current_source,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        error_str = str(e)
        logger.error(f"Stream data query error: {error_str}", exc_info=True)

        # Provide helpful error messages for common issues
        if "warehouse" in error_str.lower() or "TERMINATED" in error_str:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "SQL Warehouse unavailable",
                    "message": "The SQL Warehouse may be stopped. Please start it in your Databricks workspace.",
                    "original_error": error_str,
                },
            )
        elif "connection" in error_str.lower() or "timeout" in error_str.lower() or "request to server" in error_str.lower():
            # Catch RequestError and other connection issues
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Database connection failed",
                    "message": "Connection to SQL Warehouse was lost or became stale. The connection has been automatically restored. Please refresh the page.",
                    "original_error": error_str,
                    "hint": "This typically happens after long periods of inactivity. The connection should now be restored."
                },
            )
        elif "stale connection" in error_str.lower() or "reconnect" in error_str.lower():
            # Explicit stale connection detection from provider
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Stale connection detected",
                    "message": "The database connection became stale and reconnection failed. Please try again.",
                    "original_error": error_str,
                },
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Query failed",
                    "message": error_str,
                },
            )


# ==========================================
# Static Files with Version Injection
# ==========================================


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve index.html - defaults to lakebase view"""
    return serve_dashboard_page("lakebase")


@app.get("/lakebase", response_class=HTMLResponse)
async def serve_lakebase():
    """Serve dashboard with Lakebase (PostgreSQL) view"""
    return serve_dashboard_page("lakebase")


@app.get("/zerobus", response_class=HTMLResponse)
async def serve_zerobus():
    """Serve ZeroBus streaming data table view"""
    return serve_zerobus_page()


def serve_dashboard_page(initial_source: str) -> HTMLResponse:
    """Serve index.html with version, frontend URL, and initial source injected"""
    version = get_version()
    frontend_url = config.FRONTEND_URL or ""

    index_path = Path(__file__).parent / "static" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")

    html = index_path.read_text()
    html = html.replace("__VERSION__", version)
    html = html.replace("__FRONTEND_URL__", frontend_url)
    html = html.replace("__INITIAL_SOURCE__", initial_source)

    return HTMLResponse(content=html)


def serve_zerobus_page() -> HTMLResponse:
    """Serve zerobus.html (streaming data table) with version injected"""
    version = get_version()

    page_path = Path(__file__).parent / "static" / "zerobus.html"
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="zerobus.html not found")

    html = page_path.read_text()
    html = html.replace("__VERSION__", version)

    return HTMLResponse(content=html)


# Mount static files for CSS, JS, images (but index.html is handled above)
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=False), name="static")

# ==========================================
# Main Entry Point
# ==========================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))

    # Load config from file if exists
    config_file = "../config.env"
    if os.path.exists(config_file):
        logger.info(f"Loading configuration from {config_file}")
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

    uvicorn.run(app, host="0.0.0.0", port=port)
