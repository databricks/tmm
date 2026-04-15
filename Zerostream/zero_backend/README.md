# ZeroStream Backend Dashboard

Real-time visualization dashboard for ZeroStream sensor data.

## Data Sources

The backend supports two data sources that can be switched at runtime:

### Zerobus (Databricks SQL)
- Traditional approach using `databricks-sql-connector`
- Queries Unity Catalog Delta tables via SQL Warehouse
- Higher latency due to warehouse startup time

### Lakebase (PostgreSQL)
- Low-latency PostgreSQL-compatible access using `psycopg`
- Data replicated from Unity Catalog via Lakeflow Connect
- Optimized for dashboard workloads with faster response times

Switch between sources using the toggle in the dashboard UI or via the `/api/datasource` endpoint.

## Features

### Landing Page
- **QR Code Display** - Displays QR code for the mobile frontend app
- **Quick Access** - Direct link to open the mobile app
- **Navigation** - Button to access the dashboard

### Dashboard Page
- **Real-Time Counter** - Large animated display showing total sensor events
- **Global Map** - OpenLayers map showing all user locations worldwide
  - Blue markers for active users (within activity threshold)
  - Grey markers for inactive users
  - Hover tooltips with device ID and last active timestamp
  - Zoomable and pannable
- **Configurable Settings**
  - Refresh interval (1-60 seconds)
  - Activity threshold (1-60 minutes)
  - Settings saved to localStorage

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript
- **Mapping**: OpenLayers 9.0
- **Styling**: Dark theme with CSS variables
- **Deployment**: Databricks Apps

## API Endpoints

### Dashboard Endpoints

- `GET /` - Serve dashboard UI
- `GET /api/health` - Health check with data source info
- `GET /api/status` - Detailed status with data statistics
- `GET /api/count` - Total event count
- `GET /api/locations` - User locations with timestamps
- `GET /api/clients` - List all clients with statistics

### Data Source Management

- `GET /api/datasource` - Get current data source info
- `POST /api/datasource` - Switch data source (`{"source": "zerobus"}` or `{"source": "lakebase"}`)

## Configuration

Settings are loaded from `../config.env`:

```bash
# Databricks Configuration
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-token
DATABRICKS_USER=your-email@company.com

# Backend App Settings
BACKEND_APP_NAME=zerobackend
BACKEND_SOURCE_PATH=./zero_backend

# Zerobus Settings (Unity Catalog / SQL Warehouse)
SQL_WAREHOUSE_ID=your-warehouse-id
SQL_WAREHOUSE_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
ZEROBUS_CATALOG=main
ZEROBUS_SCHEMA=default
ZEROBUS_TABLE=sensor_data

# Lakebase Settings (PostgreSQL-compatible)
LAKEBASE_ID=your-lakebase-instance-id
LAKEBASE_HOST=instance-xxx.database.cloud.databricks.com
LAKEBASE_PORT=5432
LAKEBASE_DATABASE=databricks_postgres
LAKEBASE_USER=your-email@databricks.com
LAKEBASE_CATALOG=your_lakebase_catalog
LAKEBASE_SCHEMA=your_schema
LAKEBASE_TABLE=sensor_data

# Default data source: zerobus or lakebase
DEFAULT_DATA_SOURCE=zerobus
```

## Local Development

```bash
# Install dependencies
cd zero_backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run locally
python app.py

# Access at http://localhost:8001
```

## Deployment

### Deploy Backend Only
```bash
./deploy-backend.sh
```

### Deploy Both Frontend and Backend
```bash
# Sequential (safer)
./deploy-all.sh

# Parallel (faster)
./deploy-all.sh parallel
```

## Directory Structure

```
zero_backend/
├── app.py                 # FastAPI application
├── app.yaml               # Databricks Apps config
├── requirements.txt       # Python dependencies
├── providers/             # Modular data providers
│   ├── __init__.py        # Factory and exports
│   ├── base.py            # Abstract DataProvider interface
│   ├── lakeflow_provider.py # Zerobus (Databricks SQL) implementation
│   └── lakebase_provider.py # Lakebase (PostgreSQL) implementation
├── static/
│   ├── index.html         # Dashboard UI
│   ├── css/
│   │   └── style.css      # Light theme styles
│   ├── js/
│   │   └── app.js         # Dashboard logic + OpenLayers
│   └── images/
│       └── zerostream-qr.png  # Frontend QR code
└── README.md
```

## Data Flow

```
                    ┌─────────────────────┐
                    │  Mobile Frontend    │
                    │  (Sensor Data)      │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │     ZeroBus         │
                    │  (Data Ingestion)   │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Delta Table       │
                    │ (Unity Catalog)     │
                    └─────────┬───────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌─────────────────┐             ┌─────────────────┐
    │    Zerobus      │ ──Repl.──▶  │    Lakebase     │
    │  (SQL Warehouse)│             │   (PostgreSQL)  │
    └────────┬────────┘             └────────┬────────┘
             │                               │
             └───────────┬───────────────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │   Backend API       │
               │  (/api/datasource)  │
               └─────────┬───────────┘
                         │
                         ▼
               ┌─────────────────────┐
               │   Dashboard UI      │
               │  (Auto-refresh)     │
               └─────────────────────┘
```

## Architecture

The backend uses a modular provider architecture:

```
zero_backend/
├── providers/
│   ├── __init__.py           # Factory function and exports
│   ├── base.py               # Abstract DataProvider interface
│   ├── lakeflow_provider.py  # Zerobus (Databricks SQL) implementation
│   └── lakebase_provider.py  # Lakebase (PostgreSQL) implementation
└── app.py                    # FastAPI application
```

This allows seamless switching between data sources and easy addition of new providers in the future.

## Notes

- The backend runs on port 8001 (vs frontend on 8000)
- QR code points to the frontend mobile app
- Settings are persisted in browser localStorage
- Map uses CartoDB dark tiles for consistent theming
- Activity threshold determines active vs inactive user markers
