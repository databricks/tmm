# Databricks notebook source
# MAGIC %md
# MAGIC # Workshop setup — gRPC variant verification
# MAGIC
# MAGIC This notebook is a thin companion to `setup_workshop.py`. Run it **after**
# MAGIC `setup_workshop.py` succeeds, on the same workspace, with the same `catalog` and
# MAGIC `zerobus_region` widgets. It does **not** re-provision anything — it only verifies
# MAGIC that the **gRPC** ingest path works on this workspace using the official
# MAGIC `databricks-zerobus-ingest-sdk`, so the workshop owner sees any breakage before
# MAGIC 1000 attendees do.
# MAGIC
# MAGIC ## One-time Environment setup (required before running on serverless)
# MAGIC
# MAGIC The Zerobus SDK is installed **once** via the notebook Environment, not via
# MAGIC `%pip install`. The Environment is pre-built into the runtime so the SDK is
# MAGIC importable from the first cell, with no per-session install delay.
# MAGIC
# MAGIC 1. Top right of the notebook → **Environment** icon.
# MAGIC 2. **Dependencies** → **Add Dependency** → paste `databricks-zerobus-ingest-sdk`.
# MAGIC 3. Click **Apply**. The runtime restarts with the SDK ready to import.
# MAGIC
# MAGIC The package has no PySpark dep and ships a manylinux x86_64 wheel; its only
# MAGIC Python dep is `protobuf>=4.25,<7`. If `import zerobus...` fails below, the
# MAGIC Environment hasn't been applied — repeat the steps above before re-running.

# COMMAND ----------

dbutils.widgets.text("catalog", "workshop", "Workshop catalog")
CATALOG = dbutils.widgets.get("catalog").strip()
SCHEMA  = "zerobus"
TABLE   = "measurements"
print(f"Verifying gRPC ingest into {CATALOG}.{SCHEMA}.{TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Smoke test — open a stream as the SP, ingest one row, clean up

# COMMAND ----------

import json
import time
import uuid

from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

cfg            = spark.table(f"{CATALOG}.{SCHEMA}.config").first()
CLIENT_ID      = cfg["client_id"]
CLIENT_SECRET  = cfg["client_secret"]
WORKSPACE_URL  = cfg["workspace_url"]
# SDK wants the bare host (no scheme, no path).
SERVER_ENDPOINT = cfg["zerobus_endpoint"].replace("https://", "").rstrip("/")

assert CLIENT_ID and CLIENT_SECRET, "Empty credentials in workshop.zerobus.config — re-run setup_workshop.py"
print(f"server_endpoint = {SERVER_ENDPOINT}")
print(f"workspace_url   = {WORKSPACE_URL}")
print(f"client_id (4)   = ...{CLIENT_ID[-4:]}")

TEST_ID = f"grpc-smoke-{uuid.uuid4()}"
record  = {
    "id":          TEST_ID,
    "city":        "_grpc_smoke",
    "temperature": -999.0,
    "comment":     "setup_workshop_grpc smoke test — safe to delete",
}

sdk = ZerobusSdk(SERVER_ENDPOINT, unity_catalog_url=WORKSPACE_URL)
opts = StreamConfigurationOptions(record_type=RecordType.JSON)
tprops = TableProperties(f"{CATALOG}.{SCHEMA}.{TABLE}")

print("opening stream...")
stream = sdk.create_stream(CLIENT_ID, CLIENT_SECRET, tprops, opts)
try:
    print("ingesting...")
    stream.ingest_record(json.dumps(record))
    stream.flush()
    print(f"flushed ok (id={TEST_ID})")
finally:
    stream.close()
    print("stream closed")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cleanup — remove the smoke-test row

# COMMAND ----------

# Spark runs as the user (admin), not the SP — so this DELETE doesn't need an SP grant.
for _ in range(10):
    if spark.table(f"{CATALOG}.{SCHEMA}.{TABLE}").filter(f"id = '{TEST_ID}'").count():
        break
    time.sleep(2)

deleted = spark.sql(
    f"DELETE FROM {CATALOG}.{SCHEMA}.{TABLE} WHERE id = '{TEST_ID}'"
)
print(f"cleanup OK — removed smoke-test row {TEST_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Result

# COMMAND ----------

print("=" * 70)
print("ZEROBUS gRPC SMOKE TEST — PASS")
print("=" * 70)
print(f"Table              : {CATALOG}.{SCHEMA}.{TABLE}")
print(f"SDK                : databricks-zerobus-ingest-sdk")
print(f"Endpoint           : {SERVER_ENDPOINT}")
print(f"Attendee notebook  : lab3/send_temperature_grpc.py")
print("=" * 70)
