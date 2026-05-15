# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 4 — Send a temperature reading to Zerobus
# MAGIC
# MAGIC You'll push one row directly into the Delta table `workshop.zerobus.course_temp`
# MAGIC via the **Zerobus REST API** — no Kafka, no Auto Loader, no cluster-side streaming.
# MAGIC
# MAGIC All the plumbing (OAuth token exchange, endpoint URL, payload shape, HTTP POST) is
# MAGIC fixed in the **DO NOT MODIFY** cell below. You only edit the two widgets at the top:
# MAGIC your city and the temperature reading.
# MAGIC
# MAGIC Credentials (service principal client_id / secret, Zerobus endpoint, workspace URL,
# MAGIC workspace id) are read at runtime from the shared Databricks secret scope `workshop`,
# MAGIC populated by the setup notebook. You never see or paste them.
# MAGIC
# MAGIC Schema of the target table:
# MAGIC
# MAGIC | column | type   |
# MAGIC |--------|--------|
# MAGIC | id     | STRING (UUID, generated per submission) |
# MAGIC | city   | STRING |
# MAGIC | temp   | FLOAT  |

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✏️ Edit this cell — your input
# MAGIC
# MAGIC Change the two widget values at the top of the notebook (City, Temperature °C),
# MAGIC then run the **Submit** cell below. Re-run as many times as you like; each run
# MAGIC writes one new row with a fresh UUID.

# COMMAND ----------

dbutils.widgets.text("city", "Munich",   "City")
dbutils.widgets.text("temp", "21.5",     "Temperature (°C)")

CITY = dbutils.widgets.get("city").strip()
TEMP = float(dbutils.widgets.get("temp"))

assert CITY, "Enter a city."
print(f"Prepared record: city={CITY!r}  temp={TEMP}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⛔ DO NOT MODIFY — Zerobus REST client (plumbing)
# MAGIC
# MAGIC Reads credentials from the `workshop` secret scope, exchanges them for an OAuth token
# MAGIC scoped to the target table, and posts a single-record JSON array to the Zerobus ingest
# MAGIC endpoint. If anything here breaks, flag your instructor — don't edit.

# COMMAND ----------

import json
import uuid
import requests

SCOPE          = "workshop"
CATALOG        = "workshop"
SCHEMA         = "zerobus"
TABLE          = "course_temp"

_CLIENT_ID     = dbutils.secrets.get(SCOPE, "zerobus_client_id")
_CLIENT_SECRET = dbutils.secrets.get(SCOPE, "zerobus_client_secret")
_ENDPOINT      = dbutils.secrets.get(SCOPE, "zerobus_endpoint")
_WORKSPACE_URL = dbutils.secrets.get(SCOPE, "zerobus_workspace_url")
_WORKSPACE_ID  = dbutils.secrets.get(SCOPE, "zerobus_workspace_id")


def _fetch_oauth_token() -> str:
    """Exchange SP client credentials for a Zerobus-scoped OAuth access token."""
    # UC OAuth authorization_details requires the underscore form of privilege names
    # (USE_CATALOG, USE_SCHEMA), unlike the spaced form accepted by the SQL GRANT statement.
    authorization_details = json.dumps([
        {"type": "unity_catalog_privileges", "privileges": ["USE_CATALOG"],
         "object_type": "CATALOG", "object_full_path": CATALOG},
        {"type": "unity_catalog_privileges", "privileges": ["USE_SCHEMA"],
         "object_type": "SCHEMA",  "object_full_path": f"{CATALOG}.{SCHEMA}"},
        {"type": "unity_catalog_privileges", "privileges": ["SELECT", "MODIFY"],
         "object_type": "TABLE",   "object_full_path": f"{CATALOG}.{SCHEMA}.{TABLE}"},
    ])
    resp = requests.post(
        f"{_WORKSPACE_URL}/oidc/v1/token",
        auth=(_CLIENT_ID, _CLIENT_SECRET),
        data={
            "grant_type": "client_credentials",
            "scope": "all-apis",
            "resource": f"api://databricks/workspaces/{_WORKSPACE_ID}/zerobusDirectWriteApi",
            "authorization_details": authorization_details,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def submit_temperature(city: str, temp: float) -> dict:
    """Send one {id, city, temp} record to Zerobus. Returns the payload sent."""
    record = {"id": str(uuid.uuid4()), "city": city, "temp": float(temp)}
    token = _fetch_oauth_token()
    resp = requests.post(
        f"{_ENDPOINT}/zerobus/v1/tables/{CATALOG}.{SCHEMA}.{TABLE}/insert",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=json.dumps([record]),   # Zerobus REST requires a JSON array, even for 1 row
        timeout=30,
    )
    resp.raise_for_status()
    return record

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📤 Submit — run to send your reading

# COMMAND ----------

sent = submit_temperature(CITY, TEMP)
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
