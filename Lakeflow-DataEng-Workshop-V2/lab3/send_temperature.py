# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 3 — Send a temperature reading to Zerobus
# MAGIC
# MAGIC You'll push one row directly into the Delta table `workshop.zerobus.measurements`
# MAGIC via the **Zerobus REST API** — no Kafka, no Auto Loader, no cluster-side streaming.
# MAGIC
# MAGIC All the plumbing (OAuth token exchange, endpoint URL, payload shape, HTTP POST) is
# MAGIC fixed in the **DO NOT MODIFY** cell below. You only edit the three widgets at the top:
# MAGIC your city, the temperature reading, and an optional comment.
# MAGIC
# MAGIC Credentials (service principal client_id / secret, Zerobus endpoint, workspace URL,
# MAGIC workspace id) are read at runtime from the shared UC config table
# MAGIC `workshop.zerobus.config`, populated by the setup notebook. You never paste them.
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
# MAGIC ## ⛔ DO NOT MODIFY — Zerobus REST client (plumbing)
# MAGIC
# MAGIC Reads credentials from the `workshop.zerobus.config` table, exchanges them for an OAuth
# MAGIC token scoped to the target table, and posts a single-record JSON array to the Zerobus
# MAGIC ingest endpoint. If anything here breaks, flag your instructor — don't edit.

# COMMAND ----------

import json
import uuid
import requests

CATALOG        = "workshop"
SCHEMA         = "zerobus"
TABLE          = "measurements"

_CONFIG        = spark.table(f"{CATALOG}.{SCHEMA}.config").first()
_CLIENT_ID     = _CONFIG["client_id"]
_CLIENT_SECRET = _CONFIG["client_secret"]
_ENDPOINT      = _CONFIG["zerobus_endpoint"]
_WORKSPACE_URL = _CONFIG["workspace_url"]
_WORKSPACE_ID  = _CONFIG["workspace_id"]


def _fetch_oauth_token() -> str:
    """Exchange SP client credentials for a Zerobus-scoped OAuth access token."""
    # Per the official Zerobus REST recipe, authorization_details must carry the full
    # UC chain (CATALOG + SCHEMA + TABLE) and privilege names use the spaced form
    # ("USE CATALOG", "USE SCHEMA") — the same form `SHOW GRANTS` reports. Underscore
    # form is rejected as `invalid_authorization_details`. A token minted without the
    # catalog/schema entries triggers a 403 from /insert at write time.
    authorization_details = json.dumps([
        {"type": "unity_catalog_privileges", "privileges": ["USE CATALOG"],
         "object_type": "CATALOG", "object_full_path": CATALOG},
        {"type": "unity_catalog_privileges", "privileges": ["USE SCHEMA"],
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
    if not resp.ok:
        raise RuntimeError(
            f"OAuth token request failed: {resp.status_code} {resp.reason}\n"
            f"  body: {resp.text[:500]}"
        )
    return resp.json()["access_token"]


def submit_temperature(city: str, temperature: float, comment: str = "") -> dict:
    """Send one {id, city, temperature, comment} record to Zerobus. Returns the payload sent."""
    record = {
        "id":          str(uuid.uuid4()),
        "city":        city,
        "temperature": float(temperature),
        "comment":     comment or "",
    }
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
    if not resp.ok:
        raise RuntimeError(
            f"Zerobus insert failed: {resp.status_code} {resp.reason}\n"
            f"  url:   {resp.url}\n"
            f"  body:  {resp.text[:500]}\n"
            f"  x-request-id: {resp.headers.get('x-request-id')}"
        )
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
