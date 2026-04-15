"""
Zerobus Data Provider (Databricks SQL Warehouse)

Provides access to Unity Catalog Delta tables via Databricks SQL Connector.
This is the Zerobus data access path through SQL Warehouse.
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import Databricks SQL exceptions for proper error handling
try:
    from databricks.sql.exc import RequestError as DatabricksRequestError
except ImportError:
    # Fallback if exception class not available in older versions
    DatabricksRequestError = Exception


@dataclass
class LakeflowConfig:
    """Configuration for Zerobus (Databricks SQL) provider"""

    # Databricks workspace (required)
    databricks_host: str
    sql_warehouse_id: str
    sql_warehouse_http_path: str

    # Unity Catalog table (required)
    catalog: str
    schema: str
    table: str

    # Authentication (optional - either PAT token or service principal)
    databricks_token: Optional[str] = None
    service_principal_id: Optional[str] = None
    service_principal_secret: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LakeflowConfig":
        """Create config from environment variables (BACKEND_ prefix for backend-specific vars)"""
        return cls(
            databricks_host=os.getenv("DATABRICKS_HOST"),
            sql_warehouse_id=os.getenv("BACKEND_SQL_WAREHOUSE_ID"),
            sql_warehouse_http_path=os.getenv("BACKEND_SQL_WAREHOUSE_HTTP_PATH"),
            databricks_token=os.getenv("BACKEND_DATABRICKS_TOKEN"),
            service_principal_id=None,  # Backend uses token auth, not service principal
            service_principal_secret=None,
            catalog=os.getenv("ZEROBUS_CATALOG"),
            schema=os.getenv("ZEROBUS_SCHEMA"),
            table=os.getenv("ZEROBUS_TABLE"),
        )


class LakeflowProvider:
    """
    Data provider using Databricks SQL Warehouse (Zerobus).

    This provider connects to Unity Catalog Delta tables via
    Databricks SQL Connector. It's the Zerobus approach
    for querying Delta tables through SQL Warehouse.
    """

    def __init__(self, config: LakeflowConfig):
        self.config = config
        self.connection = None
        self.cursor = None
        self.is_connected = False
        self.validation_errors: List[str] = []

    @property
    def name(self) -> str:
        return "Zerobus (Databricks SQL)"

    @property
    def full_table_name(self) -> str:
        return f"{self.config.catalog}.{self.config.schema}.{self.config.table}"

    def validate_config(self) -> List[str]:
        """Validate Zerobus-specific configuration"""
        errors = []

        if not self.config.databricks_host:
            errors.append("DATABRICKS_HOST not configured")

        if not self.config.databricks_token and not self.config.service_principal_secret:
            errors.append(
                "No authentication configured "
                "(need DATABRICKS_TOKEN or SERVICE_PRINCIPAL_SECRET)"
            )

        if not self.config.sql_warehouse_id:
            errors.append(
                "SQL_WAREHOUSE_ID not configured - "
                "check SQL Warehouses in your workspace"
            )

        if not self.config.catalog:
            errors.append("ZEROBUS_CATALOG not configured")

        if not self.config.schema:
            errors.append("ZEROBUS_SCHEMA not configured")

        if not self.config.table:
            errors.append("ZEROBUS_TABLE not configured")

        self.validation_errors = errors
        return errors

    def connect(self) -> bool:
        """Establish connection to Databricks SQL Warehouse with timeout configuration"""
        try:
            from databricks import sql

            host = self.config.databricks_host.replace("https://", "")

            # Common connection parameters with socket timeout
            # Socket timeout prevents indefinite hangs and is automatically retried by the connector
            connection_params = {
                "server_hostname": host,
                "http_path": self.config.sql_warehouse_http_path,
                "_socket_timeout": 30,  # 30 second socket timeout (prevents indefinite hangs)
            }

            if self.config.service_principal_secret:
                logger.info(
                    f"[Zerobus] Connecting with service principal: "
                    f"{self.config.service_principal_id}"
                )
                self.connection = sql.connect(
                    service_principal_id=self.config.service_principal_id,
                    service_principal_secret=self.config.service_principal_secret,
                    **connection_params
                )
            else:
                logger.info("[Zerobus] Connecting with Personal Access Token")
                self.connection = sql.connect(
                    access_token=self.config.databricks_token,
                    **connection_params
                )

            self.cursor = self.connection.cursor()
            self.is_connected = True
            logger.info("[Zerobus] Database connection established with 30s socket timeout")
            return True

        except Exception as e:
            error_msg = f"[Zerobus] Failed to connect: {str(e)}"
            logger.error(error_msg)
            self.validation_errors.append(error_msg)

            if "404" in str(e):
                self.validation_errors.append(
                    f"SQL Warehouse not found. Check SQL_WAREHOUSE_ID "
                    f"({self.config.sql_warehouse_id})"
                )
            elif "401" in str(e) or "403" in str(e):
                self.validation_errors.append(
                    "Authentication failed. Check credentials."
                )
            elif "warehouse" in str(e).lower():
                self.validation_errors.append(
                    "SQL Warehouse issue. Ensure your warehouse is running."
                )

            return False

    def close(self) -> None:
        """Close the database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.is_connected = False
        logger.info("[Zerobus] Database connection closed")

    def _execute(self, sql: str, params: tuple = None) -> Any:
        """Execute a SQL query with health check and automatic reconnection on stale connections

        Implements three-layer protection:
        1. Health check: Simple query to validate connection before execution
        2. RequestError handling: Catches stale connection errors and reconnects
        3. SQL error categorization: Provides helpful error messages
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("[Zerobus] Database connection lost and reconnection failed")

        # Health check: Test connection before executing actual query
        # This catches stale connections before they cause query failures
        try:
            self.cursor.execute("SELECT 1")
            logger.debug("[Zerobus] Connection health check passed")
        except DatabricksRequestError as e:
            # Connection is stale - this is the most common case after hours of inactivity
            logger.warning(f"[Zerobus] Health check failed with RequestError (stale connection): {e}")
            logger.info("[Zerobus] Attempting to reconnect...")
            self.is_connected = False

            # Try to reconnect
            if not self.connect():
                raise Exception(f"[Zerobus] Failed to reconnect after stale connection detection: {e}")

            logger.info("[Zerobus] Successfully reconnected after stale connection")
        except Exception as e:
            # Other connection errors
            logger.error(f"[Zerobus] Health check failed: {e}")
            self.is_connected = False
            raise Exception(f"[Zerobus] Connection health check failed: {e}")

        # Execute the actual query with error handling
        try:
            return self.cursor.execute(sql, params) if params else self.cursor.execute(sql)

        except DatabricksRequestError as e:
            # RequestError means network/connection issue - attempt reconnection
            logger.error(f"[Zerobus] RequestError during query execution (connection lost): {e}")
            logger.info("[Zerobus] Attempting to reconnect and retry query...")
            self.is_connected = False

            # Try to reconnect and retry once
            if self.connect():
                logger.info("[Zerobus] Reconnected successfully, retrying query")
                try:
                    return self.cursor.execute(sql, params) if params else self.cursor.execute(sql)
                except Exception as retry_error:
                    raise Exception(f"[Zerobus] Query failed after reconnection: {retry_error}")
            else:
                raise Exception(f"[Zerobus] Failed to reconnect after RequestError: {e}")

        except Exception as e:
            error_str = str(e).lower()
            # Provide helpful error messages for common SQL errors
            if "column" in error_str and "not found" in error_str:
                raise Exception(f"[Zerobus] Column not found - table schema may need updating: {e}")
            elif "table" in error_str and ("not found" in error_str or "does not exist" in error_str):
                raise Exception(f"[Zerobus] Table not found - check ZEROBUS_CATALOG/SCHEMA/TABLE config: {e}")
            elif "warehouse" in error_str or "terminated" in error_str:
                raise Exception(f"[Zerobus] SQL Warehouse stopped - please start it in Databricks: {e}")
            else:
                # Log full exception details for debugging
                logger.error(f"[Zerobus] Query execution failed: {e}", exc_info=True)
                raise

    def get_count(self) -> int:
        """Get total record count"""
        self._execute(f"SELECT COUNT(*) FROM {self.full_table_name}")
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def get_locations(self, full_trace: bool = False, client_id: str = None, max_points: int = None) -> List[Dict[str, Any]]:
        """Get device locations for map display

        Args:
            full_trace: If True, return all points for trace visualization (requires client_id)
            client_id: Required when full_trace=True, filters to only this client's data
            max_points: Ignored for ZeroBus provider (no subsampling needed for streaming table)
        """
        if full_trace:
            if not client_id:
                raise ValueError("full_trace=True requires a client_id to prevent full table scan")
            # PERFORMANCE: Filter by client_id in SQL rather than fetching all data
            # Z-ORDER on (client_id, timestamp) enables efficient data skipping
            self._execute(f"""
                SELECT
                    client_id,
                    latitude,
                    longitude,
                    timestamp,
                    speed,
                    heading,
                    orientation_beta,
                    orientation_gamma
                FROM {self.full_table_name}
                WHERE client_id = '{client_id}'
                  AND latitude IS NOT NULL
                  AND longitude IS NOT NULL
                  AND latitude != 0
                  AND longitude != 0
                ORDER BY timestamp DESC
            """)
        else:
            self._execute(f"""
                WITH latest_locations AS (
                    SELECT
                        client_id,
                        latitude,
                        longitude,
                        timestamp,
                        speed,
                        heading,
                        orientation_beta,
                        orientation_gamma,
                        ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY timestamp DESC) as rn
                    FROM {self.full_table_name}
                    WHERE latitude IS NOT NULL
                      AND longitude IS NOT NULL
                      AND latitude != 0
                      AND longitude != 0
                )
                SELECT
                    client_id,
                    latitude,
                    longitude,
                    timestamp,
                    speed,
                    heading,
                    orientation_beta,
                    orientation_gamma
                FROM latest_locations
                WHERE rn = 1
            """)

        results = self.cursor.fetchall()
        locations = []
        for row in results:
            locations.append({
                "uid": row[0],
                "latitude": float(row[1]),
                "longitude": float(row[2]),
                "last_timestamp": row[3].isoformat() if row[3] else None,
                "speed": float(row[4]) if row[4] is not None else None,
                "heading": float(row[5]) if row[5] is not None else None,
                "orientation_beta": float(row[6]) if row[6] is not None else None,
                "orientation_gamma": float(row[7]) if row[7] is not None else None,
            })
        return locations

    def get_clients(self) -> Dict[str, Any]:
        """Get list of all clients with their stats"""
        self._execute(f"""
            WITH client_stats AS (
                SELECT
                    client_id,
                    COUNT(*) as event_count,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen
                FROM {self.full_table_name}
                GROUP BY client_id
            ),
            latest_locations AS (
                SELECT
                    client_id,
                    latitude,
                    longitude,
                    ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY timestamp DESC) as rn
                FROM {self.full_table_name}
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                  AND latitude != 0 AND longitude != 0
            )
            SELECT
                cs.client_id,
                cs.event_count,
                cs.first_seen,
                cs.last_seen,
                ll.latitude as last_lat,
                ll.longitude as last_lon
            FROM client_stats cs
            LEFT JOIN latest_locations ll ON cs.client_id = ll.client_id AND ll.rn = 1
            ORDER BY cs.last_seen DESC
        """)

        results = self.cursor.fetchall()
        now = datetime.now(timezone.utc)
        clients = []

        for row in results:
            last_seen = row[3]
            is_active = False

            if last_seen:
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                time_diff = (now - last_seen).total_seconds()
                is_active = time_diff < 300  # 5 minutes

            clients.append({
                "client_id": row[0],
                "event_count": row[1],
                "first_seen": row[2].isoformat() if row[2] else None,
                "last_seen": row[3].isoformat() if row[3] else None,
                "is_active": is_active,
                "last_location": {
                    "latitude": float(row[4]) if row[4] else None,
                    "longitude": float(row[5]) if row[5] else None,
                },
            })

        return {
            "clients": clients,
            "total": len(clients),
            "active": sum(1 for c in clients if c["is_active"]),
        }

    def get_stream_data(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent sensor readings for streaming table view

        Args:
            limit: Maximum number of records to return
        """
        self._execute(f"""
            SELECT
                client_id,
                timestamp,
                orientation_beta,
                orientation_gamma,
                latitude,
                longitude,
                heading
            FROM {self.full_table_name}
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
              AND latitude != 0
              AND longitude != 0
            ORDER BY timestamp DESC
            LIMIT {limit}
        """)

        results = self.cursor.fetchall()
        records = []
        for row in results:
            records.append({
                "client_id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "pitch": float(row[2]) if row[2] is not None else None,
                "roll": float(row[3]) if row[3] is not None else None,
                "latitude": float(row[4]) if row[4] is not None else None,
                "longitude": float(row[5]) if row[5] is not None else None,
                "heading": float(row[6]) if row[6] is not None else None,
            })
        return records

    def get_status(self) -> Dict[str, Any]:
        """Get detailed system status"""
        record_count = 0
        latest_record = None
        estimated_size_mb = 0
        unique_devices = 0

        if self.is_connected:
            try:
                # Get total count and unique devices
                self._execute(f"""
                    SELECT
                        COUNT(*) as total_records,
                        COUNT(DISTINCT client_id) as unique_devices
                    FROM {self.full_table_name}
                """)
                result = self.cursor.fetchone()
                record_count = result[0]
                unique_devices = result[1]

                # Get latest record
                self._execute(f"""
                    SELECT client_id, timestamp, received_at
                    FROM {self.full_table_name}
                    ORDER BY received_at DESC
                    LIMIT 1
                """)
                result = self.cursor.fetchone()
                if result:
                    latest_record = {
                        "client_id": result[0],
                        "timestamp": result[1].isoformat() if result[1] else None,
                        "received_at": result[2].isoformat() if result[2] else None,
                    }

                # Estimate data size (~288 bytes per row with overhead)
                bytes_per_row = 288
                estimated_size_bytes = record_count * bytes_per_row
                estimated_size_mb = round(estimated_size_bytes / (1024 * 1024), 2)

            except Exception as e:
                logger.error(f"[Zerobus] Status query error: {str(e)}")

        return {
            "total_records": record_count,
            "unique_devices": unique_devices,
            "estimated_size_mb": estimated_size_mb,
            "latest_record": latest_record,
        }
