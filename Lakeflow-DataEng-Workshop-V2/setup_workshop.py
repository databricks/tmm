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
# MAGIC **Part B — Lab 4 Zerobus provisioning**
# MAGIC 1. Schema `workshop.zerobus` + managed Delta table `workshop.zerobus.course_temp` (`id STRING, city STRING, temp FLOAT`)
# MAGIC 2. Service principal `workshop-zerobus-sp` with a fresh OAuth client secret
# MAGIC 3. UC grants for that SP: `USE CATALOG` on `workshop`, `USE SCHEMA` on `workshop.zerobus`, `MODIFY + SELECT` on the table
# MAGIC 4. Databricks secret scope `workshop` holding `zerobus_client_id`, `zerobus_client_secret`, `zerobus_endpoint`, `zerobus_workspace_id`, `zerobus_workspace_url`
# MAGIC 5. `READ` ACL on the scope granted to group `account users` — attendees read via `dbutils.secrets.get(...)`, nobody copy-pastes credentials
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
# MAGIC # Part B — Zerobus provisioning (Lab 4)
# MAGIC
# MAGIC Creates the target table, a shared service principal, UC grants, and a secret scope.
# MAGIC Skip by leaving the `zerobus_region` widget blank.

# COMMAND ----------

if not ZEROBUS_REGION:
    dbutils.notebook.exit("zerobus_region not set — skipping Part B.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B1. Create `workshop.zerobus.course_temp` (idempotent)

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.zerobus COMMENT 'Zerobus ingest targets'")
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.zerobus.course_temp (
        id    STRING,
        city  STRING,
        temp  FLOAT
    )
    COMMENT 'Workshop Lab 4 target — one row per attendee submission via Zerobus REST'
""")
print(f"Table ready: {CATALOG}.zerobus.course_temp")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B2. Create (or reuse) the shared service principal

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import AclPermission

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
spark.sql(f"GRANT MODIFY, SELECT ON TABLE {CATALOG}.zerobus.course_temp TO `{SP_APPLICATION_ID}`")
print(f"Grants applied to SP {SP_APPLICATION_ID}: USE CATALOG, USE SCHEMA, MODIFY+SELECT")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B5. Compute endpoint/workspace values and write the secret scope

# COMMAND ----------

ctx              = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
WORKSPACE_URL    = "https://" + spark.conf.get("spark.databricks.workspaceUrl")
WORKSPACE_ID     = ctx.workspaceId().getOrElse(None)
ZEROBUS_ENDPOINT = f"https://{WORKSPACE_ID}.zerobus.{ZEROBUS_REGION}.cloud.databricks.com"

print(f"WORKSPACE_URL    = {WORKSPACE_URL}")
print(f"WORKSPACE_ID     = {WORKSPACE_ID}")
print(f"ZEROBUS_ENDPOINT = {ZEROBUS_ENDPOINT}")

# COMMAND ----------

SCOPE = "workshop"
try:
    w.secrets.create_scope(scope=SCOPE)
    print(f"Created secret scope: {SCOPE}")
except Exception as e:
    if "RESOURCE_ALREADY_EXISTS" in str(e) or "already exists" in str(e).lower():
        print(f"Secret scope already exists: {SCOPE}")
    else:
        raise

for k, v in [
    ("zerobus_client_id",     SP_APPLICATION_ID),
    ("zerobus_client_secret", SP_CLIENT_SECRET),
    ("zerobus_endpoint",      ZEROBUS_ENDPOINT),
    ("zerobus_workspace_id",  str(WORKSPACE_ID)),
    ("zerobus_workspace_url", WORKSPACE_URL),
]:
    w.secrets.put_secret(scope=SCOPE, key=k, string_value=v)

w.secrets.put_acl(scope=SCOPE, principal="account users", permission=AclPermission.READ)
print(f"Wrote 5 secrets to scope '{SCOPE}' and granted READ to `account users`.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B6. Summary — copy these values for the instructor record
# MAGIC
# MAGIC Attendees never touch these directly — their notebook reads from the `workshop` scope.

# COMMAND ----------

print("=" * 70)
print("ZEROBUS SHARED PROVISIONING — SUMMARY")
print("=" * 70)
print(f"Table              : {CATALOG}.zerobus.course_temp")
print(f"Service principal  : {SP_DISPLAY_NAME}  (application_id: {SP_APPLICATION_ID})")
print(f"Secret scope       : {SCOPE}")
print(f"Secret keys        : zerobus_client_id, zerobus_client_secret, zerobus_endpoint,")
print(f"                     zerobus_workspace_id, zerobus_workspace_url")
print(f"Scope ACL          : `account users` → READ")
print(f"Zerobus endpoint   : {ZEROBUS_ENDPOINT}")
print("=" * 70)
