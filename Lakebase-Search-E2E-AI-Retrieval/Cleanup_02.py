# Databricks notebook source
# DBTITLE 1,Cleanup — Tech Product Search Demo
# MAGIC %md
# MAGIC # Cleanup — Tech Product Search Demo
# MAGIC
# MAGIC Tears down **every** resource created by `Demo_01` and `Setup_00` so you can start fresh.
# MAGIC
# MAGIC | Phase | What it removes |
# MAGIC | --- | --- |
# MAGIC | 1 | Lakeflow Job (table-update trigger) |
# MAGIC | 2 | Synced Tables (`synced_document_chunks`, `synced_agent_docs`) |
# MAGIC | 3 | Lakebase CDF configs (deletes via SDK, or cleaned with project) |
# MAGIC | 4 | Lakeflow SDP Pipeline + MV + Pipeline Notebook |
# MAGIC | 5 | UC Schema `tech_products_search` (CASCADE — drops CDF history tables, streaming tables, MVs) |
# MAGIC | 6 | Lakebase database `tech_products_search` (all tables: products, agent_memory, agent_documents, etc.) |
# MAGIC | 7 | *(optional)* Lakebase project `tech-products-search` |
# MAGIC
# MAGIC Run all cells top-to-bottom. Each phase is idempotent — safe to re-run.

# COMMAND ----------

# DBTITLE 1,Parameters
# ── Must match Demo_01 / Setup_00 parameters ──────────────────────────
PROJECT_ID = "tech-products-search"
DATABASE_NAME = "tech_products_search"
UC_CATALOG = "main"              # must match Setup_00
UC_SCHEMA = "tech_products_search"
PIPELINE_NAME = "document-chunking-embedding"
JOB_NAME = f"{PIPELINE_NAME}-trigger"

# Set True to also delete the Lakebase project (takes ~2 min to recreate)
DELETE_PROJECT = True

print(f"Target: UC={UC_CATALOG}.{UC_SCHEMA}  Lakebase={PROJECT_ID}/{DATABASE_NAME}")
print(f"Pipeline: {PIPELINE_NAME}  Job: {JOB_NAME}")
print(f"DELETE_PROJECT={DELETE_PROJECT}")

# COMMAND ----------

# DBTITLE 1,SDK + helpers
# MAGIC %pip install "psycopg[binary]>=3.1.0,<4" -q

# COMMAND ----------

# DBTITLE 1,Connect to Lakebase
import requests
import psycopg
from psycopg import sql
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
workspace_host = w.config.host.rstrip("/")
auth_headers = w.config.authenticate()
current_user = w.current_user.me().user_name

def api_request(method, path, *, json_body=None, params=None, ok=(200,)):
    url = f"{workspace_host}{path}"
    resp = requests.request(method, url, headers=auth_headers, json=json_body, params=params)
    if resp.status_code not in ok:
        raise RuntimeError(f"{method} {path} → {resp.status_code}: {resp.text[:300]}")
    return resp

ENDPOINT_PATH = f"projects/{PROJECT_ID}/branches/production/endpoints/primary"

def generate_database_token():
    url = f"{workspace_host}/api/2.0/postgres/credentials"
    resp = requests.request("POST", url, headers=auth_headers, json={"endpoint": ENDPOINT_PATH}, timeout=30)
    resp.raise_for_status()
    return resp.json()["token"]

def connect_postgres(dbname):
    ep = w.postgres.get_endpoint(name=ENDPOINT_PATH)
    host = ep.status.hosts.host
    token = generate_database_token()
    return psycopg.connect(
        host=host, port=5432, dbname=dbname,
        user=current_user, password=token,
        sslmode="require", autocommit=True,
    )

print(f"✓ Ready as {current_user}")

# COMMAND ----------

# DBTITLE 1,Resolve Pipeline & Job IDs by name
# ── Resolve pipeline ID ────────────────────────────────────────────────
PIPELINE_ID = None
try:
    for _p in w.pipelines.list_pipelines(filter=f"name LIKE '{PIPELINE_NAME}'"):
        if _p.name == PIPELINE_NAME:
            PIPELINE_ID = _p.pipeline_id
            break
except Exception:
    pass
print(f"Pipeline: {PIPELINE_ID or '(not found — already cleaned)'}")

# ── Resolve job ID ────────────────────────────────────────────────────
JOB_ID = None
try:
    for _j in w.jobs.list(name=JOB_NAME):
        if _j.settings and _j.settings.name == JOB_NAME:
            JOB_ID = _j.job_id
            break
except Exception:
    pass
print(f"Job:      {JOB_ID or '(not found — already cleaned)'}")

# ── Pipeline notebook path ────────────────────────────────────────────
# Setup_00 generates this notebook next to itself (same folder as Cleanup_02)
import os as _os
DEMO_DIR = _os.path.dirname(
    dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
).removeprefix("/Workspace")
PIPELINE_NB_PATH = f"{DEMO_DIR}/pipeline_document_chunks"
print(f"Notebook: {PIPELINE_NB_PATH}")

# COMMAND ----------

# DBTITLE 1,Phase 1 — Delete Lakeflow Job
# Delete the table-update triggered job
if JOB_ID:
    try:
        resp = api_request("POST", "/api/2.1/jobs/delete", json_body={"job_id": JOB_ID}, ok=(200, 404))
        if resp.status_code == 404:
            print(f"Job {JOB_ID} already deleted")
        else:
            print(f"✓ Deleted job {JOB_ID} ({JOB_NAME})")
    except Exception as e:
        print(f"⚠ Job deletion: {e}")
else:
    print(f"(skip) Job '{JOB_NAME}' not found — already clean")

# COMMAND ----------

# DBTITLE 1,Phase 2 — Delete Synced Tables
synced_tables = [
    f"{UC_CATALOG}.{UC_SCHEMA}.synced_document_chunks",
    f"{UC_CATALOG}.{UC_SCHEMA}.synced_agent_docs",
]

for st_name in synced_tables:
    fqn = f"synced_tables/{st_name}"
    try:
        w.postgres.delete_synced_table(name=fqn)
        print(f"✓ Deleted synced table: {st_name}")
    except Exception as e:
        if "NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
            print(f"  (skip) {st_name} — not found")
        else:
            print(f"⚠ {st_name}: {e}")

# COMMAND ----------

# DBTITLE 1,Phase 3 — Delete Lakebase CDF configs
# Delete CDF configs explicitly (they are also removed with the project in Phase 7,
# but explicit cleanup is needed if DELETE_PROJECT=False).
BRANCH_PATH = f"projects/{PROJECT_ID}/branches/production"
_cdf_parent = None
try:
    for _d in w.postgres.list_databases(parent=BRANCH_PATH):
        if _d.status and _d.status.postgres_database == DATABASE_NAME:
            _cdf_parent = _d.name
            break
except Exception:
    pass

if _cdf_parent:
    try:
        for _cfg in w.postgres.list_cdf_configs(parent=_cdf_parent):
            try:
                w.postgres.delete_cdf_config(name=_cfg.name)
                print(f"\u2713 Deleted CDF config: {_cfg.name}")
            except Exception as e:
                print(f"  \u26a0 CDF config {_cfg.name}: {e}")
    except Exception as e:
        print(f"  \u26a0 Could not list CDF configs: {e}")
else:
    print("(skip) No database found — CDF configs will be removed with project in Phase 7.")

# COMMAND ----------

# DBTITLE 1,Phase 4 — Delete Lakeflow Pipeline
# Delete the SDP pipeline (also drops the MV it owns)
if PIPELINE_ID:
    try:
        resp = api_request(
            "DELETE",
            f"/api/2.0/pipelines/{PIPELINE_ID}",
            ok=(200, 404),
        )
        if resp.status_code == 404:
            print(f"Pipeline {PIPELINE_ID} already deleted")
        else:
            print(f"✓ Deleted pipeline {PIPELINE_ID} ({PIPELINE_NAME})")
            print("  (MV document_chunks_embedded dropped with it)")
    except Exception as e:
        print(f"⚠ Pipeline deletion: {e}")
else:
    print(f"(skip) Pipeline '{PIPELINE_NAME}' not found — already clean")

# Delete the pipeline notebook
try:
    w.workspace.delete(path=PIPELINE_NB_PATH)
    print(f"✓ Deleted pipeline notebook: {PIPELINE_NB_PATH}")
except Exception as e:
    if "not found" in str(e).lower() or "NOT_FOUND" in str(e):
        print(f"  (pipeline notebook already deleted)")
    else:
        print(f"⚠ Notebook deletion: {e}")

# COMMAND ----------

# DBTITLE 1,Phase 5 — Drop UC Schema (CASCADE)
# Drop all remaining UC objects: agent_documents, lb_products_history,
# lb_agent_documents_history, document_chunks_embedded, and any others.
import time

# Give the pipeline deletion a moment to release the MV
time.sleep(5)

try:
    spark.sql(f"DROP SCHEMA IF EXISTS {UC_CATALOG}.{UC_SCHEMA} CASCADE")
    print(f"✓ Dropped schema {UC_CATALOG}.{UC_SCHEMA} (CASCADE)")
except Exception as e:
    print(f"⚠ Schema drop: {e}")
    # If CASCADE fails, try dropping known tables individually
    for tbl in [
        "synced_document_chunks", "synced_agent_docs",
        "document_chunks_embedded", "agent_documents_current",
        "lb_agent_documents_history", "lb_agent_memory_history",
        "lb_products_history",
    ]:
        try:
            spark.sql(f"DROP TABLE IF EXISTS {UC_CATALOG}.{UC_SCHEMA}.{tbl}")
            print(f"  ✓ Dropped {tbl}")
        except Exception:
            pass
    try:
        spark.sql(f"DROP SCHEMA IF EXISTS {UC_CATALOG}.{UC_SCHEMA}")
        print(f"  ✓ Dropped schema (after manual table drops)")
    except Exception as e2:
        print(f"  ⚠ Schema still won't drop: {e2}")

# COMMAND ----------

# DBTITLE 1,Phase 6 — Drop Lakebase database
# Drop all Lakebase tables (from every user schema), then the database itself
try:
    with connect_postgres(DATABASE_NAME) as conn:
        with conn.cursor() as cur:
            # Find all user tables across all non-system schemas
            cur.execute("""
                SELECT schemaname, tablename FROM pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema', '__db_system', 'wal2delta')
            """)
            tables = cur.fetchall()
            for schema, tbl in tables:
                cur.execute(sql.SQL("DROP TABLE IF EXISTS {}.{} CASCADE").format(
                    sql.Identifier(schema), sql.Identifier(tbl)
                ))
                print(f"  \u2713 Dropped Lakebase table: {schema}.{tbl}")
            if not tables:
                print("  (no tables in database)")
except Exception as e:
    print(f"\u26a0 Lakebase table cleanup: {e}")

# Drop the database
try:
    with connect_postgres("databricks_postgres") as conn:
        with conn.cursor() as cur:
            # Terminate other connections
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (DATABASE_NAME,),
            )
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(DATABASE_NAME)
            ))
    print(f"✓ Dropped Lakebase database: {DATABASE_NAME}")
except Exception as e:
    print(f"⚠ Database drop: {e}")

# COMMAND ----------

# DBTITLE 1,Phase 7 — Delete Lakebase project (optional)
if not DELETE_PROJECT:
    print(f"Skipping project deletion (set DELETE_PROJECT = True to remove).")
    print(f"Project '{PROJECT_ID}' is retained — Demo_01 will reuse it on next run.")
else:
    try:
        api_request(
            "DELETE",
            f"/api/2.0/postgres/projects/{PROJECT_ID}",
            params={"purge": "true"},
            ok=(200, 202, 204),
        )
        print(f"✓ Deleted Lakebase project: {PROJECT_ID} (purge=true)")
        print("  Note: recreating takes ~2 minutes on next Demo_01 run.")
    except Exception as e:
        print(f"⚠ Project deletion: {e}")

# COMMAND ----------

# DBTITLE 1,Verification
# ── Verify everything is gone ─────────────────────────────────────────
print("=" * 60)
print("Cleanup Verification")
print("=" * 60)

# UC Schema
try:
    tables = spark.sql(f"SHOW TABLES IN {UC_CATALOG}.{UC_SCHEMA}").collect()
    print(f"\n✗ UC schema still exists with {len(tables)} table(s)")
except Exception:
    print(f"\n✓ UC schema {UC_CATALOG}.{UC_SCHEMA} — gone")

# Job
if JOB_ID:
    try:
        resp = api_request("GET", f"/api/2.1/jobs/get?job_id={JOB_ID}", ok=(200, 404))
        if resp.status_code == 404:
            print(f"✓ Job {JOB_ID} — gone")
        else:
            print(f"✗ Job {JOB_ID} still exists")
    except Exception:
        print(f"✓ Job {JOB_ID} — gone")
else:
    print(f"✓ Job '{JOB_NAME}' — not found (clean)")

# Pipeline
if PIPELINE_ID:
    try:
        resp = api_request("GET", f"/api/2.0/pipelines/{PIPELINE_ID}", ok=(200, 404))
        if resp.status_code == 404:
            print(f"✓ Pipeline {PIPELINE_ID} — gone")
        else:
            print(f"✗ Pipeline {PIPELINE_ID} still exists")
    except Exception:
        print(f"✓ Pipeline {PIPELINE_ID} — gone")
else:
    print(f"✓ Pipeline '{PIPELINE_NAME}' — not found (clean)")

# Pipeline notebook
try:
    w.workspace.get_status(path=PIPELINE_NB_PATH)
    print(f"✗ Pipeline notebook still exists: {PIPELINE_NB_PATH}")
except Exception:
    print(f"✓ Pipeline notebook — gone")

# Lakebase database
try:
    with connect_postgres(DATABASE_NAME) as conn:
        print(f"✗ Lakebase database '{DATABASE_NAME}' still exists")
except Exception:
    print(f"✓ Lakebase database '{DATABASE_NAME}' — gone")

# Lakebase project
try:
    p = w.postgres.get_project(name=f"projects/{PROJECT_ID}")
    if DELETE_PROJECT:
        print(f"✗ Lakebase project '{PROJECT_ID}' still exists")
    else:
        print(f"✓ Lakebase project '{PROJECT_ID}' — retained (as expected)")
except Exception:
    print(f"✓ Lakebase project '{PROJECT_ID}' — gone")

print("\n" + "=" * 60)
print("Done. Run Setup_00 then Demo_01 to rebuild from scratch.")
print("=" * 60)