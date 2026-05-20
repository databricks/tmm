# Databricks notebook source

# MAGIC %md
# MAGIC # Workshop setup — two catalogs (`de_workshop` for attendees, `ops_data` for shared ops assets)
# MAGIC
# MAGIC This setup script sets up everything that is needed by the workshop attendees. Run it as ADMIN.
# MAGIC It's idempotent: safe to re-run. Does not touch per-attendee schemas.
# MAGIC
# MAGIC The workshop uses **two catalogs**:
# MAGIC - `de_workshop` — attendee catalog. Each attendee owns a schema `de_workshop.<USER_ID>` and writes Lab 1/2/4 outputs there. In Vocareum-style training environments, this catalog is usually pre-provisioned; the `CREATE CATALOG IF NOT EXISTS` is a no-op there.
# MAGIC - `ops_data` — shared ops catalog. Holds the shared landing volume (Lab 2 source) and the Zerobus target + config tables (Lab 3). Created by this notebook so attendees never need write access to it.
# MAGIC
# MAGIC **Part A — Shared assets (in `ops_data`)**
# MAGIC 1. Catalog `de_workshop` (if not exists) and catalog `ops_data` (if not exists)
# MAGIC 2. Schema `ops_data.shared` (if not exists)
# MAGIC 3. Managed volume `ops_data.shared.landing` (if not exists)
# MAGIC 4. Folder `booking_fraud_flags/` in that volume seeded with JSONL fraud markers
# MAGIC    for **3%** of distinct `booking_id`s from `samples.wanderbricks.booking_updates`
# MAGIC 5. `USE_SCHEMA` grant on `ops_data.shared` to group `account users`
# MAGIC 6. `READ_VOLUME` grant on `ops_data.shared.landing` to group `account users`
# MAGIC
# MAGIC **Part B — Zerobus provisioning (in `ops_data`)** (uses the official `databricks-zerobus-ingest-sdk` over gRPC)
# MAGIC 1. Schema `ops_data.zerobus` + managed Delta table `ops_data.zerobus.measurements` (`id STRING, city STRING, temperature FLOAT, comment STRING`)
# MAGIC 2. Service principal `workshop-zerobus-sp` with a fresh OAuth client secret
# MAGIC 3. UC grants for that SP: `USE CATALOG` on `ops_data`, `USE SCHEMA` on `ops_data.zerobus`, `MODIFY + SELECT` on the table
# MAGIC 4. Config table `ops_data.zerobus.config` (single row: `client_id`, `client_secret`, `workspace_url`, `workspace_id`, `zerobus_endpoint`) with `SELECT` granted to `account users` — attendees read all five values from one place
# MAGIC 5. End-to-end smoke test that opens a gRPC stream as the SP, ingests one row, deletes it, and prints PASS — so any breakage shows up here, not in 1000 attendee notebooks

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0. Admin gate — stop if the runner is not a workspace admin
# MAGIC 
# MAGIC This notebook creates account-wide objects (schemas, volumes, service principals, OAuth secrets, account-group grants). It must be run by a workspace admin. A non-admin run would fail mid-way with permission errors and leave partial state behind.

# COMMAND ----------

from databricks.sdk import WorkspaceClient

_w = WorkspaceClient()
_me = _w.current_user.me()
_groups = {g.display for g in (_me.groups or [])}

if "admins" not in _groups:
    raise PermissionError(
        f"Setup must be run by a workspace admin. Current user '{_me.user_name}' is not a member of the `admins` group "
        f"(member of: {sorted(_groups) or 'no groups'}). Ask an admin to run this notebook."
    )

print(f"Admin check passed: {_me.user_name} is a workspace admin.")

# COMMAND ----------

dbutils.widgets.text("catalog", "de_workshop", "Workshop catalog")
dbutils.widgets.text("fraud_pct", "3.0", "% of bookings to flag as fraud")
dbutils.widgets.text("num_files", "5", "Number of JSONL files to split the seed across")
dbutils.widgets.text("zerobus_region", "us-west-2", "Zerobus region (e.g. us-west-2) — set to blank to skip Part B")

import re

_CATALOG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REGION_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

CATALOG         = dbutils.widgets.get("catalog").strip()
ZEROBUS_REGION  = dbutils.widgets.get("zerobus_region").strip()

# Shared ops catalog — fixed name. Holds the shared landing volume (Lab 2 source)
# and the Zerobus target + config tables (Lab 3). Kept separate from `CATALOG`
# (the attendee catalog) so attendee grants and ops-asset grants don't intermingle.
OPS_CATALOG = "ops_data"

try:
    FRAUD_PCT = float(dbutils.widgets.get("fraud_pct"))
except ValueError as e:
    raise ValueError("Set 'fraud_pct' to a numeric percentage, e.g. 3.0.") from e

try:
    NUM_FILES = int(dbutils.widgets.get("num_files"))
except ValueError as e:
    raise ValueError("Set 'num_files' to a positive integer, e.g. 5.") from e

if not _CATALOG_RE.fullmatch(CATALOG):
    raise ValueError(
        "Set 'catalog' to a simple UC identifier: letters, numbers, and underscores; "
        "it must start with a letter or underscore."
    )
if not _CATALOG_RE.fullmatch(OPS_CATALOG):
    raise ValueError(
        f"OPS_CATALOG={OPS_CATALOG!r} is not a valid UC identifier."
    )
if not 0.0 <= FRAUD_PCT <= 100.0:
    raise ValueError("Set 'fraud_pct' between 0 and 100.")
if NUM_FILES < 1:
    raise ValueError("Set 'num_files' to at least 1.")
if ZEROBUS_REGION and not _REGION_RE.fullmatch(ZEROBUS_REGION):
    raise ValueError("Set 'zerobus_region' to a region-like value such as 'us-west-2', or blank to skip Part B.")

print(f"catalog={CATALOG}  ops_catalog={OPS_CATALOG}  fraud_pct={FRAUD_PCT}%  num_files={NUM_FILES}  zerobus_region={ZEROBUS_REGION or '(unset, Part B will be skipped)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1-2. Create catalogs, shared schema, and landing volume (idempotent)

# COMMAND ----------

# `de_workshop` is the attendee catalog. In Vocareum-style training environments it's
# usually pre-provisioned; the CREATE is a no-op there. Outside Vocareum the notebook
# creates it so it stays self-contained.
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG} COMMENT 'Attendee catalog for Lakeflow DataEng Workshop V2 — per-USER_ID schemas live here'")
# `ops_data` is the shared ops catalog. Holds the shared landing volume and the
# Zerobus target + config tables. Always created here (idempotent).
spark.sql(f"CREATE CATALOG IF NOT EXISTS {OPS_CATALOG} COMMENT 'Workshop ops/shared assets — Zerobus targets and shared landing volume'")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {OPS_CATALOG}.shared COMMENT 'Workshop shared assets'")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {OPS_CATALOG}.shared.landing COMMENT 'Shared landing for workshop seed data'")

VOLUME_PATH = f"/Volumes/{OPS_CATALOG}/shared/landing/booking_fraud_flags"
dbutils.fs.mkdirs(VOLUME_PATH)
print(f"Volume folder ready: {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Seed fraud markers (3% of bookings, written as JSONL)
# MAGIC 
# MAGIC Re-run overwrites the seeded files so attendees always see a fresh, consistent set.

# COMMAND ----------

from pyspark.sql import functions as F

REASONS = [
    "velocity_check_failed",
    "stolen_card_report",
    "unusual_location",
    "device_fingerprint_mismatch",
    "suspicious_pattern",
]

bookings = (
    spark.table("samples.wanderbricks.booking_updates")
    .select("booking_id")
    .distinct()
)

fraction = FRAUD_PCT / 100.0
flagged = (
    bookings.sample(withReplacement=False, fraction=fraction, seed=42)
    .withColumn("flag", F.lit("fraud"))
    .withColumn(
        "reason",
        F.element_at(F.array(*[F.lit(r) for r in REASONS]),
                     (F.abs(F.hash("booking_id")) % len(REASONS)) + 1),
    )
    .withColumn(
        "flagged_at",
        F.date_format(
            F.expr("current_timestamp() - make_interval(0, 0, 0, abs(hash(booking_id)) % 90)"),
            "yyyy-MM-dd'T'HH:mm:ss'Z'",
        ),
    )
    .withColumn(
        "confidence",
        F.round(F.lit(0.70) + (F.abs(F.hash("booking_id")) % 3000) / 10000.0, 4),
    )
)

marker_count = flagged.count()
print(f"Generated {marker_count} fraud markers ({FRAUD_PCT}% of distinct bookings)")

# COMMAND ----------

# Clear any prior seed files so re-runs produce a clean directory, then write JSONL.
for f in dbutils.fs.ls(VOLUME_PATH):
    if f.name.endswith(".json") or f.name.startswith("_"):
        dbutils.fs.rm(f.path)

(flagged
    .repartition(NUM_FILES)
    .write
    .mode("overwrite")
    .format("json")
    .save(VOLUME_PATH))

# Rename part-*.json files so the directory stays tidy (Auto Loader reads either form).
for f in dbutils.fs.ls(VOLUME_PATH):
    if f.name.startswith("part-") and f.name.endswith(".json"):
        idx = f.name.split("-")[1]
        dbutils.fs.mv(f.path, f"{VOLUME_PATH}/fraud_markers_{idx}.json")
    elif f.name.startswith("_"):
        dbutils.fs.rm(f.path)

print("Seed files written:")
for f in dbutils.fs.ls(VOLUME_PATH):
    print(f"  {f.name}  ({f.size} bytes)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4-5. Grants — VOLUME is read-only for attendees

# COMMAND ----------

spark.sql(f"GRANT USE CATALOG ON CATALOG {OPS_CATALOG} TO `account users`")
spark.sql(f"GRANT USE_SCHEMA ON SCHEMA {OPS_CATALOG}.shared TO `account users`")
spark.sql(f"GRANT READ_VOLUME ON VOLUME {OPS_CATALOG}.shared.landing TO `account users`")
print(f"Grants applied: USE CATALOG on {OPS_CATALOG}, USE_SCHEMA on {OPS_CATALOG}.shared, READ_VOLUME on {OPS_CATALOG}.shared.landing  →  `account users`")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

sample = (
    spark.read.format("json")
    .load(VOLUME_PATH)
    .limit(5)
)
display(sample)

total = spark.read.format("json").load(VOLUME_PATH).count()
print(f"Total markers in volume: {total}")
print(f"Expected ~{int(47726 * FRAUD_PCT / 100)} at {FRAUD_PCT}% of ~47,726 distinct bookings")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC # Part B — Zerobus provisioning  
# MAGIC 
# MAGIC Creates the target table, a shared service principal, UC grants, a UC config table,
# MAGIC and runs an end-to-end gRPC SDK smoke test. Skip by leaving the `zerobus_region`
# MAGIC widget blank.

# COMMAND ----------

if not ZEROBUS_REGION:
    dbutils.notebook.exit("zerobus_region not set — skipping Part B.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install the Zerobus Ingest SDK (interactive — runs once at setup)
# MAGIC 
# MAGIC `databricks-zerobus-ingest-sdk` is needed for the smoke test in B6 below. The setup
# MAGIC notebook is run interactively by the workshop owner once, so an inline `%pip install`
# MAGIC is fine. The attendee notebook (`labs/03-Zerobus/send_city_iot_data.py`) uses the
# MAGIC same `%pip install` + `dbutils.library.restartPython()` pattern in its first cell,
# MAGIC so attendees just hit Run all — no Environment-panel click-through.

# COMMAND ----------

# MAGIC %pip install --quiet "databricks-zerobus-ingest-sdk>=1.0.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# Re-resolve widgets and constants after the Python restart triggered by %pip.
import re

_CATALOG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REGION_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

CATALOG         = dbutils.widgets.get("catalog").strip()
ZEROBUS_REGION  = dbutils.widgets.get("zerobus_region").strip()
OPS_CATALOG     = "ops_data"

if not _CATALOG_RE.fullmatch(CATALOG):
    raise ValueError(
        "Set 'catalog' to a simple UC identifier: letters, numbers, and underscores; "
        "it must start with a letter or underscore."
    )
if not _CATALOG_RE.fullmatch(OPS_CATALOG):
    raise ValueError(f"OPS_CATALOG={OPS_CATALOG!r} is not a valid UC identifier.")
if ZEROBUS_REGION and not _REGION_RE.fullmatch(ZEROBUS_REGION):
    raise ValueError("Set 'zerobus_region' to a region-like value such as 'us-west-2', or blank to skip Part B.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B0. Storage preflight — fail fast if the catalog is on default storage
# MAGIC 
# MAGIC 
# MAGIC **The test below is WIP, don't try to run the Zerobus lab with default storage on a serverless only environment unless the requirements for Zerobus have changed.**
# MAGIC 
# MAGIC Zerobus direct-write requires the target table to live in UC-managed cloud storage
# MAGIC (S3 / ADLS / GCS) reachable by the Zerobus data plane. If the catalog has no
# MAGIC explicit managed location and the schema doesn't override one, table writes fall back
# MAGIC to workspace **default storage**, which Zerobus rejects with a 403 at insert time.
# MAGIC Easier to fail here with a clear message than to fail later in attendee notebooks.

# COMMAND ----------

# Make sure the schema exists before we ask UC about its storage_location.
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {OPS_CATALOG}.zerobus COMMENT 'Zerobus ingest targets'")

from databricks.sdk import WorkspaceClient
_w_pre = WorkspaceClient()
_catalog_info = _w_pre.catalogs.get(name=OPS_CATALOG)
_schema_info  = _w_pre.schemas.get(full_name=f"{OPS_CATALOG}.zerobus")

_catalog_loc = getattr(_catalog_info, "storage_root",     None)
_schema_loc  = getattr(_schema_info,  "storage_location", None) or getattr(_schema_info, "storage_root", None)
_effective   = _schema_loc or _catalog_loc

# Workspace default-storage buckets observed in practice: `s3://dbstorage-` on AWS.
# We only fail if we see a *confirmed* default-storage URI. Catalogs that inherit storage
# from the metastore (typical) won't have their own storage_root — that's fine, the
# B6 gRPC smoke test below will catch any actual ingest failure.
_DEFAULT_STORAGE_MARKERS = (
    "s3://dbstorage-",  # AWS Databricks default storage (confirmed)
)
_is_default_storage = bool(_effective) and any(
    _effective.startswith(p) for p in _DEFAULT_STORAGE_MARKERS
)

if _is_default_storage:
    raise RuntimeError(
        f"\nZerobus storage preflight FAILED.\n"
        f"\n"
        f"Catalog '{OPS_CATALOG}' is on **workspace default storage** "
        f"(storage_root={_effective!r}). Zerobus direct-write requires the target table to "
        f"live in customer-owned UC managed storage (S3 / ADLS / GCS) backed by a STORAGE "
        f"CREDENTIAL + EXTERNAL LOCATION. Default-storage tables get rejected with HTTP 403 "
        f"at insert.\n"
        f"\n"

    )

print(f"Storage preflight OK — effective_location={_effective!r}  (None means inherited from metastore; the B6 smoke test will confirm Zerobus accepts writes)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B1. Create `ops_data.zerobus.measurements`

# COMMAND ----------

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {OPS_CATALOG}.zerobus.measurements (
        id          STRING COMMENT 'UUID generated per submission',
        city        STRING COMMENT 'Reporting city',
        temperature FLOAT  COMMENT 'Temperature in degrees Celsius',
        comment     STRING COMMENT 'Free-form note from the attendee (may be empty)'
    )
    COMMENT 'Workshop Lab 3 target — one row per attendee submission via the Zerobus Ingest SDK'
""")
print(f"Table ready: {OPS_CATALOG}.zerobus.measurements")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B2. Create (or reuse) the shared service principal

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
SP_DISPLAY_NAME = "workshop-zerobus-sp"

existing = [sp for sp in w.service_principals.list(filter=f"displayName eq '{SP_DISPLAY_NAME}'")]
if existing:
    sp = existing[0]
    print(f"Reusing SP: {sp.display_name}  application_id={sp.application_id}")
else:
    sp = w.service_principals.create(display_name=SP_DISPLAY_NAME, active=True)
    print(f"Created SP: {sp.display_name}  application_id={sp.application_id}")

SP_APPLICATION_ID = sp.application_id
SP_ID             = sp.id  # workspace-scoped SP id

# COMMAND ----------

# MAGIC %md
# MAGIC ## B3. Generate a fresh OAuth client secret for the SP
# MAGIC 
# MAGIC Each run rotates the secret. Old secrets keep working until they expire, but only the
# MAGIC latest value is written to the config table — so attendee notebooks always read a valid one.

# COMMAND ----------

# The workspace-level SP-OAuth-secret proxy endpoint isn't uniformly exposed across SDK
# versions (missing on databricks-sdk 0.20.x which ships on DBR serverless), so we call
# the REST endpoint directly. Returns secretHash, secret, createTime, expireTime, status.
import requests

_ctx_api_token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
_host_for_sp_api = "https://" + spark.conf.get("spark.databricks.workspaceUrl")
_sp_secret_resp = requests.post(
    f"{_host_for_sp_api}/api/2.0/accounts/servicePrincipals/{SP_ID}/credentials/secrets",
    headers={"Authorization": f"Bearer {_ctx_api_token}"},
    timeout=30,
)
_sp_secret_resp.raise_for_status()
_sp_secret_json   = _sp_secret_resp.json()
SP_CLIENT_SECRET  = _sp_secret_json["secret"]

# Capture expireTime so the workshop owner can see when this credential stops working.
# Databricks returns it as ISO 8601 / RFC 3339 (e.g. "2026-08-18T10:24:33Z"). Be defensive
# in case the format ever shifts — fall back to printing whatever the API returned.
SP_SECRET_EXPIRE_RAW    = _sp_secret_json.get("expireTime")
SP_SECRET_EXPIRE_HUMAN  = "(expireTime not returned by API)"
if SP_SECRET_EXPIRE_RAW:
    try:
        from datetime import datetime, timezone
        # Python <3.11 doesn't parse trailing 'Z' in fromisoformat; normalise it.
        _exp_dt    = datetime.fromisoformat(SP_SECRET_EXPIRE_RAW.replace("Z", "+00:00"))
        _days_left = (_exp_dt - datetime.now(timezone.utc)).days
        SP_SECRET_EXPIRE_HUMAN = f"{SP_SECRET_EXPIRE_RAW} (in {_days_left} days)"
    except Exception as _e:
        SP_SECRET_EXPIRE_HUMAN = f"{SP_SECRET_EXPIRE_RAW} (could not parse: {_e})"

print(f"Generated new OAuth client secret for SP {SP_APPLICATION_ID} (shown once, written to config below)")
print(f"Secret expires: {SP_SECRET_EXPIRE_HUMAN}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B4. UC grants for the SP on the target table

# COMMAND ----------

spark.sql(f"GRANT USE CATALOG ON CATALOG {OPS_CATALOG} TO `{SP_APPLICATION_ID}`")
spark.sql(f"GRANT USE SCHEMA  ON SCHEMA  {OPS_CATALOG}.zerobus TO `{SP_APPLICATION_ID}`")
spark.sql(f"GRANT MODIFY, SELECT ON TABLE {OPS_CATALOG}.zerobus.measurements TO `{SP_APPLICATION_ID}`")
print(f"Grants applied to SP {SP_APPLICATION_ID}: USE CATALOG on {OPS_CATALOG}, USE SCHEMA on {OPS_CATALOG}.zerobus, MODIFY+SELECT on measurements")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B5. Compute endpoint/workspace values and write the config table

# COMMAND ----------

ctx              = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
WORKSPACE_URL    = "https://" + spark.conf.get("spark.databricks.workspaceUrl")
WORKSPACE_ID     = ctx.workspaceId().getOrElse(None)
ZEROBUS_ENDPOINT = f"https://{WORKSPACE_ID}.zerobus.{ZEROBUS_REGION}.cloud.databricks.com"

print(f"WORKSPACE_URL    = {WORKSPACE_URL}")
print(f"WORKSPACE_ID     = {WORKSPACE_ID}")
print(f"ZEROBUS_ENDPOINT = {ZEROBUS_ENDPOINT}")

# COMMAND ----------

# Single-row UC config table next to the data table. Attendees read all five values
# from here (including the SP client_secret in cleartext — they need it to mint
# OAuth tokens, and the SP's UC grants are tightly bounded to measurements).
from pyspark.sql import Row

config_row = Row(
    client_id        = SP_APPLICATION_ID,
    client_secret    = SP_CLIENT_SECRET,
    workspace_url    = WORKSPACE_URL,
    workspace_id     = str(WORKSPACE_ID),
    zerobus_endpoint = ZEROBUS_ENDPOINT,
)
(spark.createDataFrame([config_row])
      .write.mode("overwrite")
      .saveAsTable(f"{OPS_CATALOG}.zerobus.config"))

spark.sql(
    f"COMMENT ON TABLE {OPS_CATALOG}.zerobus.config IS "
    f"'Lab 3 Zerobus client config — read-only for attendees. "
    f"Contains the OAuth client_secret in cleartext; SP grants are tightly scoped "
    f"to {OPS_CATALOG}.zerobus.measurements.'"
)

# Grant attendees the read path to the Zerobus assets:
#   USE SCHEMA ops_data.zerobus         (traverse to the tables)
#   SELECT on ops_data.zerobus.config   (read credentials)
#   SELECT on ops_data.zerobus.measurements (verification SELECT in the lab notebook)
# USE CATALOG on ops_data is granted in Part A (for the shared volume) and covers this too.
# Falls back to `users` if `account users` isn't a workspace principal.
_grant_principal = None
for _candidate in ("account users", "users"):
    try:
        spark.sql(f"GRANT USE SCHEMA ON SCHEMA {OPS_CATALOG}.zerobus TO `{_candidate}`")
        spark.sql(f"GRANT SELECT ON TABLE {OPS_CATALOG}.zerobus.config       TO `{_candidate}`")
        spark.sql(f"GRANT SELECT ON TABLE {OPS_CATALOG}.zerobus.measurements TO `{_candidate}`")
        _grant_principal = _candidate
        break
    except Exception as _e:
        if "does not exist" in str(_e).lower() or "principal" in str(_e).lower():
            continue
        raise

if _grant_principal:
    print(f"Wrote config row to {OPS_CATALOG}.zerobus.config and granted USE SCHEMA + SELECT (config, measurements) to `{_grant_principal}`.")
else:
    print(
        f"Wrote config row to {OPS_CATALOG}.zerobus.config, but could not grant SELECT — "
        f"neither `account users` nor `users` exists as a workspace principal. "
        f"Grant SELECT manually."
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## B6. gRPC end-to-end smoke test
# MAGIC 
# MAGIC Open a stream as the freshly-provisioned SP, ingest one dummy row, clean it up.
# MAGIC Any breakage (wrong endpoint, missing grants, storage misconfig that the preflight
# MAGIC didn't catch, SDK install drift) surfaces here at setup time — not in 1000 attendee
# MAGIC notebooks later.

# COMMAND ----------

import json
import time
import uuid

from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

_smoke_cfg     = spark.table(f"{OPS_CATALOG}.zerobus.config").first()
_SMOKE_CLIENT_ID     = _smoke_cfg["client_id"]
_SMOKE_CLIENT_SECRET = _smoke_cfg["client_secret"]
_SMOKE_WORKSPACE_URL = _smoke_cfg["workspace_url"]
# SDK wants the bare host (no scheme, no path).
_SMOKE_SERVER_ENDPOINT = _smoke_cfg["zerobus_endpoint"].replace("https://", "").rstrip("/")

assert _SMOKE_CLIENT_ID and _SMOKE_CLIENT_SECRET, \
    f"Empty credentials in {OPS_CATALOG}.zerobus.config — provisioning step above did not complete."

_SMOKE_TEST_ID = f"setup-smoke-{uuid.uuid4()}"
_smoke_record  = {
    "id":          _SMOKE_TEST_ID,
    "city":        "_setup_smoke",
    "temperature": -999.0,
    "comment":     "setup_workshop smoke test — auto-deleted",
}

_smoke_sdk    = ZerobusSdk(_SMOKE_SERVER_ENDPOINT, unity_catalog_url=_SMOKE_WORKSPACE_URL)
_smoke_opts   = StreamConfigurationOptions(record_type=RecordType.JSON)
_smoke_tprops = TableProperties(f"{OPS_CATALOG}.zerobus.measurements")

print(f"[smoke] server_endpoint = {_SMOKE_SERVER_ENDPOINT}")
print(f"[smoke] workspace_url   = {_SMOKE_WORKSPACE_URL}")
print(f"[smoke] client_id (4)   = ...{_SMOKE_CLIENT_ID[-4:]}")
print(f"[smoke] opening stream...")
_smoke_stream = _smoke_sdk.create_stream(
    _SMOKE_CLIENT_ID, _SMOKE_CLIENT_SECRET, _smoke_tprops, _smoke_opts
)
try:
    _smoke_stream.ingest_record(json.dumps(_smoke_record))
    _smoke_stream.flush()
    print(f"[smoke] flushed ok (id={_SMOKE_TEST_ID})")
finally:
    _smoke_stream.close()
    print("[smoke] stream closed")

# Cleanup — Spark runs as the user (admin), not the SP, so DELETE doesn't need an SP grant.
for _ in range(10):
    if spark.table(f"{OPS_CATALOG}.zerobus.measurements").filter(f"id = '{_SMOKE_TEST_ID}'").count():
        break
    time.sleep(2)
spark.sql(f"DELETE FROM {OPS_CATALOG}.zerobus.measurements WHERE id = '{_SMOKE_TEST_ID}'")
print(f"[smoke] cleanup OK — removed row {_SMOKE_TEST_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B7. Summary

# COMMAND ----------

print("=" * 70)
print("ZEROBUS SHARED PROVISIONING — SUMMARY")
print("=" * 70)
print(f"Catalogs           : {CATALOG} (attendees), {OPS_CATALOG} (shared ops assets)")
print(f"Data table         : {OPS_CATALOG}.zerobus.measurements")
print(f"Config table       : {OPS_CATALOG}.zerobus.config")
print(f"Config columns     : client_id, client_secret, workspace_url, workspace_id, zerobus_endpoint")
print(f"Service principal  : {SP_DISPLAY_NAME}  (application_id: {SP_APPLICATION_ID})")
print(f"OAuth secret expires: {SP_SECRET_EXPIRE_HUMAN}")
print(f"Config table ACL   : `{_grant_principal or '(not granted — see warning above)'}` → SELECT")
print(f"Zerobus endpoint   : {ZEROBUS_ENDPOINT}")
print(f"gRPC smoke test    : PASS")
print(f"Attendee notebook  : labs/03-Zerobus/send_city_iot_data.py")
print("=" * 70)
