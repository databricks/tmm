"""Dual-mode config: runs both locally (CLI profile) and inside Databricks Apps (injected SP)."""
import os
from functools import lru_cache
from databricks.sdk import WorkspaceClient

IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))

# ---- Demo constants (overridable via env / app resources) ----
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "")
GOLD_TABLE = os.environ.get("GOLD_TABLE", "")
# Native Lakebase synced table (reverse ETL) — lives in Postgres schema "dais_demo", fed by a managed pipeline
SYNCED_TABLE = os.environ.get("SYNCED_TABLE", "dais_demo.customer_360_synced")
# Full 50k customer directory (id + name + fake sales) — managed synced table (Postgres name) + its UC Delta source
DIRECTORY_TABLE = os.environ.get("DIRECTORY_TABLE", "dais_demo.customers_directory_synced")
DIRECTORY_SOURCE = os.environ.get("DIRECTORY_SOURCE", "")
# Multi-million-row sales fact for the heavy-analytics showdown — managed synced table (PG) + its UC Delta source
SALES_TABLE = os.environ.get("SALES_TABLE", "dais_demo.sales_events_synced")
SALES_SOURCE = os.environ.get("SALES_SOURCE", "")
SYNC_PIPELINE_ID = os.environ.get("SYNC_PIPELINE_ID", "")
PGDATABASE = os.environ.get("PGDATABASE", "shop")
# Lakebase host — injected from app.yaml env or resource binding
DEFAULT_PGHOST = os.environ.get("PGHOST", "")


@lru_cache(maxsize=1)
def get_workspace_client() -> WorkspaceClient:
    if IS_DATABRICKS_APP:
        return WorkspaceClient()
    profile = os.environ.get("DATABRICKS_PROFILE", "DEFAULT")
    return WorkspaceClient(profile=profile)


def get_oauth_token() -> str:
    """Workspace OAuth token. Doubles as the Lakebase Postgres password for this identity."""
    w = get_workspace_client()
    headers = w.config.authenticate()  # {'Authorization': 'Bearer <token>'}
    return headers["Authorization"].replace("Bearer ", "")


def get_workspace_host() -> str:
    if IS_DATABRICKS_APP:
        host = os.environ.get("DATABRICKS_HOST", "")
        if host and not host.startswith("http"):
            host = f"https://{host}"
        return host
    return get_workspace_client().config.host


def get_pg_password() -> str:
    """Lakebase password: a native-login role password if set, else the OAuth token (local dev)."""
    return os.environ.get("PGPASSWORD") or get_oauth_token()


def get_pg_params() -> dict:
    """Connection params for Lakebase. Uses injected resource env in the app, fallbacks locally."""
    if IS_DATABRICKS_APP:
        user = os.environ.get("PGUSER") or get_workspace_client().current_user.me().user_name
    else:
        user = os.environ.get("PGUSER") or get_workspace_client().current_user.me().user_name
    return {
        "host": os.environ.get("PGHOST", DEFAULT_PGHOST),
        "port": int(os.environ.get("PGPORT", "5432")),
        "dbname": os.environ.get("PGDATABASE", PGDATABASE),
        "user": user,
    }

@lru_cache(maxsize=1)
def get_sync_pipeline_id() -> str:
    """Discover the synced-table pipeline dynamically — no hardcoded ID needed."""
    if not IS_DATABRICKS_APP:
        return os.environ.get("SYNC_PIPELINE_ID", "")
    w = get_workspace_client()
    target = f"{GOLD_TABLE.replace('.', '.').rsplit('.', 1)[0]}.customer_360_synced"
    for p in w.pipelines.list_pipelines(filter=f"name LIKE '%customer_360_synced%'"):
        if "lakebase_101_catalog" in (p.name or ""):
            return p.pipeline_id
    return ""