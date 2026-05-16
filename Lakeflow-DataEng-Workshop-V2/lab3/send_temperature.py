# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 3 — Send a temperature reading to Zerobus
# MAGIC
# MAGIC You'll push one row directly into the Delta table `workshop.zerobus.measurements`
# MAGIC via the **official Zerobus Ingest SDK** (gRPC under the hood). The SDK handles
# MAGIC OAuth, `authorization_details`, and stream lifecycle — you only edit the three
# MAGIC widgets at the top: city, temperature, and an optional comment.
# MAGIC
# MAGIC Credentials (service principal client_id / secret, Zerobus endpoint, workspace URL)
# MAGIC are read at runtime from the shared UC config table `workshop.zerobus.config`,
# MAGIC populated by the setup notebook. You never paste them.
# MAGIC
# MAGIC ## One-time Environment setup (required before running on serverless)
# MAGIC
# MAGIC The Zerobus SDK is installed **once** via the notebook Environment, not via
# MAGIC `%pip install`. The Environment is pre-built into the runtime so the SDK is
# MAGIC importable from the first cell, with no per-session install delay (this matters
# MAGIC at 1000-attendee scale).
# MAGIC
# MAGIC 1. Top right of the notebook → **Environment** icon.
# MAGIC 2. **Dependencies** → **Add Dependency** → paste `databricks-zerobus-ingest-sdk`.
# MAGIC 3. Click **Apply**. The runtime restarts with the SDK ready to import.
# MAGIC
# MAGIC The package ships a manylinux x86_64 wheel (Rust-backed gRPC core via PyO3); its
# MAGIC only Python dep is `protobuf>=4.25,<7`. No PySpark, no compile step. If `import
# MAGIC zerobus...` fails below, the Environment hasn't been applied — repeat the steps
# MAGIC above before running the rest of the notebook.
# MAGIC
# MAGIC Schema of the target table:
# MAGIC
# MAGIC | column      | type                                    |
# MAGIC |-------------|-----------------------------------------|
# MAGIC | id          | STRING (UUID, generated per submission) |
# MAGIC | city        | STRING                                  |
# MAGIC | temperature | FLOAT                                   |
# MAGIC | comment     | STRING (optional free-form note)        |

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✏️ Edit this cell — your input
# MAGIC
# MAGIC Change the widget values at the top of the notebook (City, Temperature °C, Comment),
# MAGIC then run the **Submit** cell below. Re-run as many times as you like; each run
# MAGIC writes one new row with a fresh UUID. Comment may be left blank.

# COMMAND ----------

dbutils.widgets.text("city",        "Munich",        "City")
dbutils.widgets.text("temperature", "21.5",          "Temperature (°C)")
dbutils.widgets.text("comment",     "Hello Zerobus", "Comment (optional)")

CITY        = dbutils.widgets.get("city").strip()
TEMPERATURE = float(dbutils.widgets.get("temperature"))
COMMENT     = dbutils.widgets.get("comment")

assert CITY, "Enter a city."
print(f"Prepared record: city={CITY!r}  temperature={TEMPERATURE}  comment={COMMENT!r}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⛔ DO NOT MODIFY — Zerobus SDK client (plumbing)
# MAGIC
# MAGIC Reads credentials from `workshop.zerobus.config`, opens a stream via
# MAGIC `ZerobusSdk.create_stream(...)`, ingests one JSON record, flushes, and closes.
# MAGIC The SDK handles OAuth and `authorization_details` for us. If anything here breaks,
# MAGIC flag your instructor — don't edit.

# COMMAND ----------

import json
import uuid

from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

CATALOG = "workshop"
SCHEMA  = "zerobus"
TABLE   = "measurements"

_CONFIG        = spark.table(f"{CATALOG}.{SCHEMA}.config").first()
_CLIENT_ID     = _CONFIG["client_id"]
_CLIENT_SECRET = _CONFIG["client_secret"]
_WORKSPACE_URL = _CONFIG["workspace_url"]
# The SDK wants the bare host (no scheme, no path) for the gRPC endpoint:
_SERVER_ENDPOINT = _CONFIG["zerobus_endpoint"].replace("https://", "").rstrip("/")


def submit_temperature(city: str, temperature: float, comment: str = "") -> dict:
    """Send one {id, city, temperature, comment} record via the Zerobus Ingest SDK."""
    record = {
        "id":          str(uuid.uuid4()),
        "city":        city,
        "temperature": float(temperature),
        "comment":     comment or "",
    }
    sdk = ZerobusSdk(_SERVER_ENDPOINT, unity_catalog_url=_WORKSPACE_URL)
    table_props = TableProperties(f"{CATALOG}.{SCHEMA}.{TABLE}")
    options     = StreamConfigurationOptions(record_type=RecordType.JSON)
    stream      = sdk.create_stream(_CLIENT_ID, _CLIENT_SECRET, table_props, options)
    try:
        stream.ingest_record(json.dumps(record))
        stream.flush()
    finally:
        stream.close()
    return record

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📤 Submit — run to send your reading

# COMMAND ----------

sent = submit_temperature(CITY, TEMPERATURE, COMMENT)
print(f"✅ Sent to {CATALOG}.{SCHEMA}.{TABLE}: {sent}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔍 Verify — your row should appear (may take a few seconds)

# COMMAND ----------

from pyspark.sql.functions import col

display(
    spark.table(f"{CATALOG}.{SCHEMA}.{TABLE}")
         .where(col("city") == CITY)
         .orderBy("id")
)
