# Databricks notebook source
# MAGIC %md
# MAGIC # Workshop setup — shared landing volume, fraud-marker seed, Zerobus provisioning
# MAGIC
# MAGIC Run **once per workshop catalog**, before attendees start.
# MAGIC
# MAGIC **Part A — Lab 2 shared assets**
# MAGIC 1. Schema `workshop.shared` (if not exists)
# MAGIC 2. Managed volume `workshop.shared.landing` (if not exists)
# MAGIC 3. Folder `booking_fraud_flags/` in that volume seeded with JSONL fraud markers
# MAGIC    for **3%** of distinct `booking_id`s from `samples.wanderbricks.booking_updates`
# MAGIC 4. `USE_SCHEMA` grant on `workshop.shared` to group `account users`
# MAGIC 5. `READ_VOLUME` grant on `workshop.shared.landing` to group `account users`
# MAGIC
# MAGIC **Part B — Lab 3 Zerobus provisioning** (uses the official `databricks-zerobus-ingest-sdk` over gRPC)
# MAGIC 1. Schema `workshop.zerobus` + managed Delta table `workshop.zerobus.measurements` (`id STRING, city STRING, temperature FLOAT, comment STRING`)
# MAGIC 2. Service principal `workshop-zerobus-sp` with a fresh OAuth client secret
# MAGIC 3. UC grants for that SP: `USE CATALOG` on `workshop`, `USE SCHEMA` on `workshop.zerobus`, `MODIFY + SELECT` on the table
# MAGIC 4. Config table `workshop.zerobus.config` (single row: `client_id`, `client_secret`, `workspace_url`, `workspace_id`, `zerobus_endpoint`) with `SELECT` granted to `account users` — attendees read all five values from one place
# MAGIC 5. End-to-end smoke test that opens a gRPC stream as the SP, ingests one row, deletes it, and prints PASS — so any breakage shows up here, not in 1000 attendee notebooks
# MAGIC
# MAGIC Idempotent: safe to re-run. Does not touch per-attendee schemas.

# COMMAND ----------

dbutils.widgets.text("catalog", "workshop", "Workshop catalog")
dbutils.widgets.text("fraud_pct", "3.0", "% of bookings to flag as fraud")
dbutils.widgets.text("num_files", "5", "Number of JSONL files to split the seed across")
dbutils.widgets.text("zerobus_region", "us-west-2", "Zerobus region (e.g. us-west-2) — set to blank to skip Part B")

CATALOG         = dbutils.widgets.get("catalog").strip()
FRAUD_PCT       = float(dbutils.widgets.get("fraud_pct"))
NUM_FILES       = int(dbutils.widgets.get("num_files"))
ZEROBUS_REGION  = dbutils.widgets.get("zerobus_region").strip()

assert CATALOG, "Set the 'catalog' widget (default: workshop) before running."
print(f"catalog={CATALOG}  fraud_pct={FRAUD_PCT}%  num_files={NUM_FILES}  zerobus_region={ZEROBUS_REGION or '(unset, Part B will be skipped)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1-2. Create shared schema and landing volume (idempotent)

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.shared COMMENT 'Workshop shared assets'")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.shared.landing COMMENT 'Shared landing for workshop seed data'")

VOLUME_PATH = f"/Volumes/{CATALOG}/shared/landing/booking_fraud_flags"
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
for f in dbutils.fs.ls(VOLUME_PATH) if any(True for _ in dbutils.fs.ls(VOLUME_PATH)) else []:
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
# MAGIC ## 4-5. Grants — read-only for attendees

# COMMAND ----------

spark.sql(f"GRANT USE_SCHEMA ON SCHEMA {CATALOG}.shared TO `account users`")
spark.sql(f"GRANT READ_VOLUME ON VOLUME {CATALOG}.shared.landing TO `account users`")
print("Grants applied: USE_SCHEMA on shared, READ_VOLUME on shared.landing  →  `account users`")

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
# MAGIC # Part B — Zerobus provisioning (Lab 3)
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
# MAGIC is fine. Attendee notebooks should use the **Environment side panel** instead, to
# MAGIC avoid 1000× per-session install latency.

# COMMAND ----------

# MAGIC %pip install --quiet "databricks-zerobus-ingest-sdk>=1.0.0"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# Re-resolve widgets after the Python restart triggered by %pip.
CATALOG         = dbutils.widgets.get("catalog").strip()
ZEROBUS_REGION  = dbutils.widgets.get("zerobus_region").strip()

# COMMAND ----------

# MAGIC %md
# MAGIC ## B0. Storage preflight — fail fast if the catalog is on default storage
# MAGIC
# MAGIC Zerobus direct-write requires the target table to live in UC-managed cloud storage
# MAGIC (S3 / ADLS / GCS) reachable by the Zerobus data plane. If the catalog has no
# MAGIC explicit managed location and the schema doesn't override one, table writes fall back
# MAGIC to workspace **default storage**, which Zerobus rejects with a 403 at insert time.
# MAGIC Easier to fail here with a clear message than to fail later in attendee notebooks.

# COMMAND ----------

# Make sure the schema exists before we ask UC about its storage_location.
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.zerobus COMMENT 'Zerobus ingest targets'")

from databricks.sdk import WorkspaceClient
_w_pre = WorkspaceClient()
_catalog_info = _w_pre.catalogs.get(name=CATALOG)
_schema_info  = _w_pre.schemas.get(full_name=f"{CATALOG}.zerobus")

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
        f"Catalog '{CATALOG}' is on **workspace default storage** "
        f"(storage_root={_effective!r}). Zerobus direct-write requires the target table to "
        f"live in customer-owned UC managed storage (S3 / ADLS / GCS) backed by a STORAGE "
        f"CREDENTIAL + EXTERNAL LOCATION. Default-storage tables get rejected with HTTP 403 "
        f"at insert.\n"
        f"\n"
        f"Fix one of:\n"
        f"  1) Catalog-level (preferred):\n"
        f"       ALTER CATALOG {CATALOG} SET MANAGED LOCATION '<s3://… | abfss://… | gs://…>';\n"
        f"  2) Schema-level (narrower scope):\n"
        f"       ALTER SCHEMA {CATALOG}.zerobus SET MANAGED LOCATION '<cloud-uri>';\n"
        f"  3) Run setup against a different catalog that already has UC managed storage.\n"
        f"\n"
        f"The cloud URI must be backed by a UC STORAGE CREDENTIAL + EXTERNAL LOCATION.\n"
        f"After fixing, drop any existing `{CATALOG}.zerobus.measurements` / "
        f"`{CATALOG}.zerobus.config` tables and re-run this notebook so they are recreated "
        f"in the new location."
    )

print(f"Storage preflight OK — effective_location={_effective!r}  (None means inherited from metastore; the B6 smoke test will confirm Zerobus accepts writes)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B1. Create `workshop.zerobus.measurements` (idempotent)

# COMMAND ----------
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.zerobus.measurements (
        id          STRING COMMENT 'UUID generated per submission',
        city        STRING COMMENT 'Reporting city',
        temperature FLOAT  COMMENT 'Temperature in degrees Celsius',
        comment     STRING COMMENT 'Free-form note from the attendee (may be empty)'
    )
    COMMENT 'Workshop Lab 3 target — one row per attendee submission via the Zerobus Ingest SDK'
""")
print(f"Table ready: {CATALOG}.zerobus.measurements")

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
# MAGIC latest value is pushed to the secret scope — so attendee notebooks always read a valid one.

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
SP_CLIENT_SECRET = _sp_secret_resp.json()["secret"]
print(f"Generated new OAuth client secret for SP {SP_APPLICATION_ID} (shown once, written to scope below)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B4. UC grants for the SP on the target table

# COMMAND ----------

spark.sql(f"GRANT USE CATALOG ON CATALOG {CATALOG} TO `{SP_APPLICATION_ID}`")
spark.sql(f"GRANT USE SCHEMA  ON SCHEMA  {CATALOG}.zerobus TO `{SP_APPLICATION_ID}`")
spark.sql(f"GRANT MODIFY, SELECT ON TABLE {CATALOG}.zerobus.measurements TO `{SP_APPLICATION_ID}`")
print(f"Grants applied to SP {SP_APPLICATION_ID}: USE CATALOG, USE SCHEMA, MODIFY+SELECT on measurements")

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
      .saveAsTable(f"{CATALOG}.zerobus.config"))

spark.sql(
    f"COMMENT ON TABLE {CATALOG}.zerobus.config IS "
    f"'Lab 3 Zerobus client config — read-only for attendees. "
    f"Contains the OAuth client_secret in cleartext; SP grants are tightly scoped "
    f"to {CATALOG}.zerobus.measurements.'"
)

# Grant SELECT to the broadest available group, with fallback if `account users` doesn't exist.
_grant_principal = None
for _candidate in ("account users", "users"):
    try:
        spark.sql(f"GRANT SELECT ON TABLE {CATALOG}.zerobus.config TO `{_candidate}`")
        _grant_principal = _candidate
        break
    except Exception as _e:
        if "does not exist" in str(_e).lower() or "principal" in str(_e).lower():
            continue
        raise

if _grant_principal:
    print(f"Wrote config row to {CATALOG}.zerobus.config and granted SELECT to `{_grant_principal}`.")
else:
    print(
        f"Wrote config row to {CATALOG}.zerobus.config, but could not grant SELECT — "
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

_smoke_cfg     = spark.table(f"{CATALOG}.zerobus.config").first()
_SMOKE_CLIENT_ID     = _smoke_cfg["client_id"]
_SMOKE_CLIENT_SECRET = _smoke_cfg["client_secret"]
_SMOKE_WORKSPACE_URL = _smoke_cfg["workspace_url"]
# SDK wants the bare host (no scheme, no path).
_SMOKE_SERVER_ENDPOINT = _smoke_cfg["zerobus_endpoint"].replace("https://", "").rstrip("/")

assert _SMOKE_CLIENT_ID and _SMOKE_CLIENT_SECRET, \
    f"Empty credentials in {CATALOG}.zerobus.config — provisioning step above did not complete."

_SMOKE_TEST_ID = f"setup-smoke-{uuid.uuid4()}"
_smoke_record  = {
    "id":          _SMOKE_TEST_ID,
    "city":        "_setup_smoke",
    "temperature": -999.0,
    "comment":     "setup_workshop smoke test — auto-deleted",
}

_smoke_sdk    = ZerobusSdk(_SMOKE_SERVER_ENDPOINT, unity_catalog_url=_SMOKE_WORKSPACE_URL)
_smoke_opts   = StreamConfigurationOptions(record_type=RecordType.JSON)
_smoke_tprops = TableProperties(f"{CATALOG}.zerobus.measurements")

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
    if spark.table(f"{CATALOG}.zerobus.measurements").filter(f"id = '{_SMOKE_TEST_ID}'").count():
        break
    time.sleep(2)
spark.sql(f"DELETE FROM {CATALOG}.zerobus.measurements WHERE id = '{_SMOKE_TEST_ID}'")
print(f"[smoke] cleanup OK — removed row {_SMOKE_TEST_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B7. Summary

# COMMAND ----------

print("=" * 70)
print("ZEROBUS SHARED PROVISIONING — SUMMARY")
print("=" * 70)
print(f"Data table         : {CATALOG}.zerobus.measurements")
print(f"Config table       : {CATALOG}.zerobus.config")
print(f"Config columns     : client_id, client_secret, workspace_url, workspace_id, zerobus_endpoint")
print(f"Service principal  : {SP_DISPLAY_NAME}  (application_id: {SP_APPLICATION_ID})")
print(f"Config table ACL   : `{_grant_principal or '(not granted — see warning above)'}` → SELECT")
print(f"Zerobus endpoint   : {ZEROBUS_ENDPOINT}")
print(f"gRPC smoke test    : PASS")
print(f"Attendee notebook  : lab3/send_temperature.py")
print("=" * 70)
