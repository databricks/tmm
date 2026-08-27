"""Dual-mode config: runs both locally (CLI profile) and inside Databricks Apps (injected SP)."""
import os
import traceback
from functools import lru_cache
from databricks.sdk import WorkspaceClient


def sdk_version() -> str:
    """Installed databricks-sdk version (best-effort)."""
    try:
        import importlib.metadata as _m
        return _m.version("databricks-sdk")
    except Exception:
        try:
            import databricks.sdk as _s
            return getattr(_s, "__version__", "unknown")
        except Exception:
            return "unknown"

IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))

# ---- Demo constants (overridable via env / app resources) ----
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "")
GOLD_TABLE = os.environ.get("GOLD_TABLE", "")
# Native Lakebase synced table (reverse ETL) — lives in Postgres schema "lakebase_101_schema", fed by a managed pipeline
SYNCED_TABLE = os.environ.get("SYNCED_TABLE", "lakebase_101_schema.customer_360_synced")
# Full 50k customer directory (id + name + fake sales) — managed synced table (Postgres name) + its UC Delta source
DIRECTORY_TABLE = os.environ.get("DIRECTORY_TABLE", "lakebase_101_schema.customers_directory_synced")
DIRECTORY_SOURCE = os.environ.get("DIRECTORY_SOURCE", "")
# Multi-million-row sales fact for the heavy-analytics showdown — managed synced table (PG) + its UC Delta source
SALES_TABLE = os.environ.get("SALES_TABLE", "lakebase_101_schema.sales_events_synced")
SALES_SOURCE = os.environ.get("SALES_SOURCE", "")
SYNC_PIPELINE_ID = os.environ.get("SYNC_PIPELINE_ID", "")
PGDATABASE = os.environ.get("PGDATABASE", "lakebase_101_db")
# Lakebase host — injected from app.yaml env or resource binding
DEFAULT_PGHOST = os.environ.get("PGHOST", "")


@lru_cache(maxsize=1)
def get_workspace_client() -> WorkspaceClient:
    if IS_DATABRICKS_APP:
        return WorkspaceClient()
    profile = os.environ.get("DATABRICKS_PROFILE", "DEFAULT")
    return WorkspaceClient(profile=profile)


# Lakebase endpoint resource name (injected via app.yaml env)
LAKEBASE_ENDPOINT = os.environ.get("LAKEBASE_ENDPOINT", "")


def get_oauth_token() -> str:
    """Lakebase-scoped credential via generate_database_credential.

    The workspace OAuth token (w.config.authenticate()) is workspace-scoped
    and REJECTED by Lakebase Postgres. We must mint a Lakebase JWT instead.
    """
    w = get_workspace_client()
    if LAKEBASE_ENDPOINT:
        if not hasattr(w, "postgres"):
            # The most common misconfiguration: an SDK too old to know Lakebase
            # endpoints. Fail with an actionable message instead of a bare
            # AttributeError buried in a swallowed exception.
            raise RuntimeError(
                f"databricks-sdk {sdk_version()} has no `postgres` API. Lakebase "
                f"endpoint credentials require databricks-sdk>=0.80.0 — pin a newer "
                f"version in requirements.txt and redeploy."
            )
        return w.postgres.generate_database_credential(endpoint=LAKEBASE_ENDPOINT).token
    # Last resort: workspace token (will likely be rejected by Lakebase)
    headers = w.config.authenticate()
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


# Env vars worth surfacing when debugging a connection. Secret-ish ones are
# reported as presence-only so we never leak a token into a response body.
_DEBUG_ENV_PRESENCE = ["PGPASSWORD"]
_DEBUG_ENV_PLAIN = [
    "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGSSLMODE",
    "LAKEBASE_ENDPOINT", "WAREHOUSE_ID", "DATABRICKS_HOST", "DATABRICKS_APP_NAME",
]


def lakebase_diagnostics() -> dict:
    """One-stop connection diagnostic for the /api/debug endpoint.

    Walks the exact path the app uses — SDK -> mint credential -> connect ->
    inspect schemas/tables -> count configured tables — and captures the real
    error (with traceback) at whichever step fails, instead of swallowing it.
    """
    d = {
        "mode": "databricks-app" if IS_DATABRICKS_APP else "local",
        "sdk_version": sdk_version(),
        "lakebase_endpoint": LAKEBASE_ENDPOINT,
        "configured_tables": {
            "synced": SYNCED_TABLE, "directory": DIRECTORY_TABLE, "sales": SALES_TABLE,
        },
        "env": {k: os.environ.get(k) for k in _DEBUG_ENV_PLAIN},
    }
    d["env"].update({k: ("<set>" if os.environ.get(k) else None) for k in _DEBUG_ENV_PRESENCE})

    # --- SDK / workspace client ---
    try:
        w = get_workspace_client()
        d["has_postgres_api"] = hasattr(w, "postgres")
        d["has_database_api"] = hasattr(w, "database")
        try:
            d["current_user"] = w.current_user.me().user_name
        except Exception as e:
            d["current_user_error"] = repr(e)
    except Exception:
        d["workspace_client_error"] = traceback.format_exc(limit=4)

    # --- step 1: mint the Lakebase credential ---
    try:
        tok = get_oauth_token()
        d["token_mint_ok"] = True
        d["token_prefix"] = (tok[:10] + "…") if tok else None
    except Exception:
        d["token_mint_ok"] = False
        d["token_mint_error"] = traceback.format_exc(limit=4)

    # --- step 2: connect + probe ---
    from . import db  # lazy: db imports this module
    params = get_pg_params()
    d["pg_params"] = params
    try:
        info = db.query(
            "SELECT current_database() AS db, current_user AS usr, "
            "current_setting('search_path') AS search_path, "
            "(SELECT array_agg(schema_name ORDER BY schema_name) "
            " FROM information_schema.schemata) AS schemas",
            one=True,
        )
        d["connect_ok"] = True
        d["connection_info"] = info
        try:
            d["visible_tables"] = db.query(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog','information_schema') "
                "ORDER BY 1, 2 LIMIT 200"
            )
        except Exception as e:
            d["visible_tables_error"] = repr(e)
        # counts on each configured table — surfaces missing tables / grants
        counts = {}
        for tbl in (SYNCED_TABLE, DIRECTORY_TABLE, SALES_TABLE):
            try:
                counts[tbl] = db.query(f"SELECT count(*) AS n FROM {tbl}", one=True)["n"]
            except Exception as e:
                counts[tbl] = f"ERROR: {e}"
        d["table_counts"] = counts
    except Exception:
        d["connect_ok"] = False
        d["connect_error"] = traceback.format_exc(limit=6)
    return d