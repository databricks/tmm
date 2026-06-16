# Databricks notebook source
# MAGIC %pip install --quiet --upgrade databricks-sdk
# MAGIC %restart_python

# COMMAND ----------

# MAGIC %md
# MAGIC # agent_apps_setup — workspace provisioning for "Hands on: Agent Apps Workshop"
# MAGIC
# MAGIC **Framework-native `workspace_setup` notebook** (the bricks paradigm). The DB Academy / Vocareum
# MAGIC framework runs this once per shared lab workspace, as the **privileged setup identity**, on
# MAGIC **serverless job compute** — declared via `workspace_setup` + `serverless_job_cluster: true` in
# MAGIC `config.json`. The framework injects `host` and `token` as notebook parameters.
# MAGIC
# MAGIC By the time this runs, the framework's `workspace_init()` has already **assigned a unique Unity
# MAGIC Catalog metastore** (via `metastore_config: {unique: true}`), so UC is enabled and we can
# MAGIC `CREATE CATALOG` directly with `spark.sql`.
# MAGIC
# MAGIC **Shared model:** everything below is created ONCE, as the privileged user, and shared by all
# MAGIC students (no per-user schemas). Provisions (idempotent):
# MAGIC 1. Catalog `agent_apps_workshop` + `shared` schema
# MAGIC 2. Source tables `products`, `orders`, `policies` (data embedded below — self-contained)
# MAGIC 3. `product_docs` (derived from products, CDF enabled for Vector Search)
# MAGIC 4. 3 intentional quality **bugs** students discover and fix
# MAGIC 5. Vector Search endpoint + `product_docs_vs` delta-sync index
# MAGIC 6. The 3 **UC function tools** (`get_product_details`, `get_order_status`, `get_return_policy`)
# MAGIC 7. Grants to `account users` (USE CATALOG / USE SCHEMA / SELECT / EXECUTE)
# MAGIC 8. Governance: UC column mask on `orders` PII (unmasked only for the admin group)
# MAGIC 9. A shared **PRO serverless SQL warehouse** granted to all users (for the agent's OBO lookup)
# MAGIC 10. A shared autoscaling **Lakebase** project (`agent-apps-memory`), `users` CAN MANAGE on it
# MAGIC     (so each student's app attaches it as a `postgres` resource — SP memory, per-app schema),
# MAGIC     + a `users`-group Postgres role (students browse memory in the end-of-lab beat)
# MAGIC 11. **AI Dev Kit skills** distributed to `/Workspace/.assistant/skills/` so every student's
# MAGIC     **Genie Code** can scaffold + deploy the agent App (Module 2) and evaluate it (Module 5)
# MAGIC 12. A shared **lab-guide app** (`agent-lab-guide`) — the participant guide + field-guide deck,
# MAGIC     deployed once per workspace with `users` CAN_USE
# MAGIC
# MAGIC Ported from `setup/workspace_setup.py`; runs `spark.sql()` on UC-enabled serverless compute, so
# MAGIC no warehouse discovery / SQL-Execution-API is needed for provisioning.

# COMMAND ----------

# MAGIC %md ## Config & authentication

# COMMAND ----------

import csv
import datetime
import io
import time

# Framework injects host/token as base_parameters (see dbacademy.run_setup). Widgets with empty
# defaults so the notebook is also runnable interactively (falls back to notebook auth).
dbutils.widgets.text("host", "", "Workspace URL (injected)")
dbutils.widgets.text("token", "", "Admin token (injected)")
dbutils.widgets.text("workshop_catalog", "agent_apps_workshop", "Workshop catalog")
dbutils.widgets.text("workshop_schema", "shared", "Shared schema")
dbutils.widgets.text("vs_endpoint", "agent-apps-vs", "Vector Search endpoint")
dbutils.widgets.text("admin_group", "admins", "Admin group (unmasked PII)")

HOST = dbutils.widgets.get("host").strip()
TOKEN = dbutils.widgets.get("token").strip()
CATALOG = dbutils.widgets.get("workshop_catalog").strip()
SCHEMA = dbutils.widgets.get("workshop_schema").strip()
VS_ENDPOINT = dbutils.widgets.get("vs_endpoint").strip()
ADMIN_GROUP = dbutils.widgets.get("admin_group").strip()

# Workspace-local group for resource-level permission APIs (warehouses, workspace ACLs). Use the
# built-in workspace `users` group — NOT `account users`: the account group resolves for UC SQL
# grants (via the metastore) but the workspace Permissions API only sees workspace-local groups,
# so `account users` errors with "does not exist"/"not found".
# (The framework's own warehouse/VS grants use `users` too.)
ALL_USERS_GROUP = "users"

# Columns in `orders` that contain customer PII and get masked for non-admins
PII_COLUMNS = ["customer_email", "shipping_address"]

from databricks.sdk import WorkspaceClient

# Prefer injected creds (privileged setup identity); fall back to notebook-native auth.
if HOST and TOKEN:
    w = WorkspaceClient(host=HOST, token=TOKEN)
else:
    w = WorkspaceClient()

print(f"Workspace: {w.config.host}")
print(f"Catalog:   {CATALOG}.{SCHEMA}")
print(f"VS:        {VS_ENDPOINT}  |  Admin group: {ADMIN_GROUP}")

# COMMAND ----------

# MAGIC %md ## Embedded source data (self-contained — no repo/container filesystem dependency)

# COMMAND ----------

PRODUCTS_CSV = """product_id,product_name,category,price,warranty_years,availability,description
P001,TechMart ProBook X500,Laptops,899.99,1,Discontinued,"High-performance 15.6-inch laptop with Intel Core i7, 16GB RAM, 512GB SSD. Perfect for professionals and students. Currently available in silver and space gray."
P002,TechMart ProBook X700,Laptops,1299.99,1,In Stock,"Premium 15.6-inch laptop with Intel Core i9, 32GB RAM, 1TB NVMe SSD. Thunderbolt 4, Wi-Fi 6E, all-day battery life."
P003,TechMart UltraBook 13,Laptops,749.99,1,In Stock,"Ultra-thin 13.3-inch laptop, 1.2kg, Intel Core i5, 8GB RAM, 256GB SSD. Ideal for on-the-go productivity."
P004,AudioMax Pro Headphones,Headphones,249.99,1,Discontinued,"Premium over-ear wireless headphones. 40-hour battery, active noise cancellation, Hi-Res Audio certified. Backed by our industry-leading 3-year manufacturer warranty. Available in black and white."
P005,AudioMax Studio Headphones,Headphones,179.99,1,In Stock,"Professional studio headphones with flat frequency response. 3.5mm and 6.35mm adapters included. Ideal for mixing and mastering."
P006,AudioMax Sport Earbuds,Headphones,89.99,1,In Stock,"True wireless earbuds, IPX5 water resistant, 8-hour battery plus 24-hour charging case. Secure sport fit."
P007,DataPad 3000,Tablets,599.99,1,Discontinued,"10.5-inch Android tablet, Snapdragon 870, 8GB RAM, 128GB storage. 4G LTE + Wi-Fi. Stylus support. Ships worldwide."
P008,DataPad Pro,Tablets,799.99,1,In Stock,"11-inch tablet with OLED display, 12GB RAM, 256GB storage. Face unlock, quad speakers, USB-C fast charge."
P009,DataPad Mini,Tablets,399.99,1,In Stock,"8-inch compact tablet. Perfect for reading, streaming, and light productivity. 6GB RAM, 64GB storage."
P010,UltraCharge PowerBank X,Accessories,79.99,1,Discontinued,"26800mAh power bank, 100W USB-C PD output, charges laptops and phones simultaneously. LED battery indicator."
P011,UltraCharge PowerBank Pro,Accessories,59.99,1,In Stock,"20000mAh power bank with 65W USB-C PD and 22.5W USB-A fast charge. Slim design, airline approved."
P012,SmartHome Hub Elite,Smart Home,149.99,1,Discontinued,"Smart home controller supporting Zigbee, Z-Wave, Wi-Fi, and Bluetooth. Works with Alexa, Google Home, HomeKit."
P013,SmartHome Hub Standard,Smart Home,99.99,1,In Stock,"Plug-and-play smart home hub. Supports 100+ device brands. Mobile app control, automations, scheduling."
P014,TechMart Mechanical Keyboard,Accessories,129.99,1,In Stock,"Tenkeyless mechanical keyboard, Cherry MX Red switches, RGB per-key lighting, USB-C detachable cable."
P015,TechMart Wireless Mouse,Accessories,49.99,1,In Stock,"Ergonomic wireless mouse, 2.4GHz + Bluetooth dual mode, 90-day battery life, 4000 DPI adjustable."
P016,TechMart 27-inch Monitor,Monitors,429.99,1,In Stock,"27-inch IPS display, 2560x1440 QHD, 165Hz, 1ms response time, HDR400, USB-C 65W power delivery."
P017,TechMart Webcam Pro,Accessories,99.99,1,In Stock,"4K 30fps webcam with AI auto-framing, noise-cancelling dual microphone, privacy shutter, USB-C."
P018,TechMart USB-C Hub 7-in-1,Accessories,49.99,1,In Stock,"USB-C hub: 4K HDMI, 100W PD passthrough, 3x USB-A 3.0, SD card reader, microSD. Aluminum chassis."
P019,TechMart Laptop Stand,Accessories,39.99,1,In Stock,"Adjustable aluminum laptop stand. Compatible with 10-17 inch laptops. Foldable, ventilated, anti-slip."
P020,TechMart Noise Cancelling Earbuds,Headphones,159.99,1,In Stock,"True wireless ANC earbuds. 6-hour battery + 24-hour case, IPX4 water resistant, multipoint Bluetooth 5.3."
"""

ORDERS_CSV = """order_id,customer_id,customer_email,product_id,product_name,order_date,status,shipping_address,quantity,unit_price,total_price
ORD-10001,CUST-001,alice.johnson@email.com,P002,TechMart ProBook X700,2024-03-15,Delivered,"123 Main St, Austin TX 78701",1,1299.99,1299.99
ORD-10002,CUST-002,bob.smith@email.com,P005,AudioMax Studio Headphones,2024-03-18,Delivered,"456 Oak Ave, Denver CO 80201",1,179.99,179.99
ORD-10003,CUST-003,carol.white@email.com,P008,DataPad Pro,2024-03-20,Delivered,"789 Pine Rd, Seattle WA 98101",1,799.99,799.99
ORD-10004,CUST-004,david.brown@email.com,P014,TechMart Mechanical Keyboard,2024-04-01,Delivered,"321 Elm St, Chicago IL 60601",1,129.99,129.99
ORD-10005,CUST-005,emma.davis@email.com,P016,TechMart 27-inch Monitor,2024-04-05,Delivered,"654 Maple Dr, Boston MA 02101",1,429.99,429.99
ORD-10006,CUST-006,frank.miller@email.com,P020,TechMart Noise Cancelling Earbuds,2024-04-10,Delivered,"987 Cedar Ln, Miami FL 33101",2,159.99,319.98
ORD-10007,CUST-007,grace.wilson@email.com,P003,TechMart UltraBook 13,2024-04-12,Delivered,"147 Birch Blvd, Portland OR 97201",1,749.99,749.99
ORD-10008,CUST-008,henry.moore@email.com,P011,UltraCharge PowerBank Pro,2024-04-15,Delivered,"258 Walnut Way, Nashville TN 37201",2,59.99,119.98
ORD-10009,CUST-009,iris.taylor@email.com,P015,TechMart Wireless Mouse,2024-04-18,Shipped,"369 Spruce St, Phoenix AZ 85001",1,49.99,49.99
ORD-10010,CUST-010,jack.anderson@email.com,P017,TechMart Webcam Pro,2024-04-20,Processing,"741 Willow Ave, Atlanta GA 30301",1,99.99,99.99
ORD-10011,CUST-001,alice.johnson@email.com,P018,TechMart USB-C Hub 7-in-1,2024-04-22,Shipped,"123 Main St, Austin TX 78701",1,49.99,49.99
ORD-10012,CUST-002,bob.smith@email.com,P019,TechMart Laptop Stand,2024-04-25,Processing,"456 Oak Ave, Denver CO 80201",1,39.99,39.99
ORD-10013,CUST-011,karen.thomas@email.com,P002,TechMart ProBook X700,2024-04-28,Delivered,"852 Ash Ct, Minneapolis MN 55401",1,1299.99,1299.99
ORD-10014,CUST-012,liam.jackson@email.com,P009,DataPad Mini,2024-05-01,Delivered,"963 Poplar Pl, San Diego CA 92101",1,399.99,399.99
ORD-10015,CUST-013,mia.harris@email.com,P006,AudioMax Sport Earbuds,2024-05-03,Delivered,"174 Magnolia Rd, Dallas TX 75201",1,89.99,89.99
ORD-10016,CUST-014,noah.martin@email.com,P013,SmartHome Hub Standard,2024-05-06,Shipped,"285 Chestnut St, Philadelphia PA 19101",1,99.99,99.99
ORD-10017,CUST-015,olivia.garcia@email.com,P016,TechMart 27-inch Monitor,2024-05-08,Processing,"396 Dogwood Dr, Columbus OH 43201",1,429.99,429.99
ORD-10018,CUST-016,peter.martinez@email.com,P002,TechMart ProBook X700,2024-05-10,Delivered,"507 Hickory Ln, Indianapolis IN 46201",1,1299.99,1299.99
ORD-10019,CUST-017,quinn.robinson@email.com,P020,TechMart Noise Cancelling Earbuds,2024-05-12,Shipped,"618 Cypress Ave, Charlotte NC 28201",1,159.99,159.99
ORD-10020,CUST-018,rachel.clark@email.com,P014,TechMart Mechanical Keyboard,2024-05-14,Delivered,"729 Juniper Blvd, Louisville KY 40201",1,129.99,129.99
"""

POLICIES_CSV = """policy,policy_details,last_updated
return_policy,"Customers may return any product for any reason within 1 year of purchase for a full refund or exchange. No receipt required. Items must be in original or gently used condition. Contact support to initiate a return.",2024-01-15
warranty_policy,"All TechMart products include a 1-year limited manufacturer warranty covering defects in materials and workmanship. Warranty does not cover accidental damage, misuse, or normal wear and tear. Contact support with proof of purchase to file a warranty claim.",2024-01-15
shipping_policy,"Standard shipping (5-7 business days) is free on orders over $50. Expedited shipping (2-3 business days) is $12.99. Overnight shipping is $24.99. International shipping available to 45 countries. Orders placed before 2pm EST ship same day.",2024-01-15
payment_policy,"We accept Visa, Mastercard, American Express, Discover, PayPal, Apple Pay, and Google Pay. All transactions are encrypted. We do not store full card numbers. Buy now pay later available via Affirm for orders over $100.",2024-01-15
privacy_policy,"TechMart collects only the data necessary to process your order and improve your shopping experience. We do not sell personal data to third parties. You may request deletion of your data at any time by contacting privacy@techmart.com.",2024-01-15
store_hours,"TechMart physical stores are open Monday-Saturday 9am-9pm and Sunday 10am-6pm local time. Our online store and support chat are available 24/7.",2024-01-15
price_match_policy,"TechMart will match the price of any identical in-stock item sold by an authorized retailer. Price match requests must be made at time of purchase or within 14 days. Excludes marketplace sellers, open-box items, and limited-time flash sales.",2024-01-15
"""

# COMMAND ----------

# MAGIC %md ## Step 1 — Catalog & schema

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS `{CATALOG}`")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{CATALOG}`.`{SCHEMA}`")
print(f"  Catalog and schema ready: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md ## Step 2 — Load source tables from embedded CSV (idempotent)

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType


def _fqn(table):
    return f"`{CATALOG}`.`{SCHEMA}`.`{table}`"


def load_table(table, csv_text):
    """Create + load a table from embedded CSV text if it doesn't exist or is empty. All STRING cols."""
    dotted = f"{CATALOG}.{SCHEMA}.{table}"
    if spark.catalog.tableExists(dotted):
        n = spark.table(_fqn(table)).count()
        if n > 0:
            print(f"  {table:<14} already has {n} rows — skipping")
            return
    reader = csv.reader(io.StringIO(csv_text.strip()))
    rows = list(reader)
    header, data = rows[0], [tuple(r) for r in rows[1:]]
    schema = StructType([StructField(c, StringType(), True) for c in header])
    df = spark.createDataFrame(data, schema)
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(dotted)
    print(f"  {table:<14} loaded {df.count()} rows")


load_table("products", PRODUCTS_CSV)
load_table("orders", ORDERS_CSV)
load_table("policies", POLICIES_CSV)

# COMMAND ----------

# MAGIC %md ## Step 3 — Derive `product_docs` (Vector Search source, CDF enabled)

# COMMAND ----------

docs_dotted = f"{CATALOG}.{SCHEMA}.product_docs"
if spark.catalog.tableExists(docs_dotted) and spark.table(_fqn("product_docs")).count() > 0:
    print("  product_docs already populated — skipping")
else:
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {_fqn('product_docs')}
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
        AS SELECT
            product_id,
            product_name,
            category AS product_category,
            CONCAT(
                product_name, ' | Category: ', category,
                ' | Price: $', price,
                ' | Availability: ', availability,
                ' | Warranty: ', warranty_years, ' year(s). ',
                description
            ) AS indexed_doc
        FROM {_fqn('products')}
    """)
    print(f"  product_docs created: {spark.table(_fqn('product_docs')).count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Inject the 3 workshop quality bugs
# MAGIC 1. Discontinued products described as "in stock" in `product_docs`
# MAGIC 2. Audio/headphone docs claim a 3-year warranty (the catalog AND the official policy both
# MAGIC    say 1 year — ONLY the marketing doc lies, so the "ground in authoritative sources" lesson
# MAGIC    is unambiguous even to sharp-eyed attendees)
# MAGIC 3. An over-permissive "extended" return policy row

# COMMAND ----------

docs_t = _fqn("product_docs")
pol_t = _fqn("policies")

# BUG 1: discontinued products labelled as available
disc = spark.sql(f"""
    SELECT product_id FROM {_fqn('products')}
    WHERE LOWER(availability) = 'discontinued' LIMIT 5
""").collect()
if disc:
    ids = ", ".join(f"'{r['product_id']}'" for r in disc)
    spark.sql(f"""
        UPDATE {docs_t}
        SET indexed_doc = CONCAT(indexed_doc,
            ' This product is currently in stock and available for immediate purchase.',
            ' Order today for fast delivery.')
        WHERE product_id IN ({ids})
    """)
    print(f"  Bug 1: marked {len(disc)} discontinued products as available")
else:
    print("  Bug 1: no discontinued products found — skipping")

# BUG 2: wrong warranty duration in audio/headphone docs.
# ORDER BY product_id makes the pick deterministic and guarantees P004 (AudioMax Pro) — the
# product Modules 4/5 ask about — is included. (An unordered LIMIT 3 once skipped it; that was
# masked while the catalog itself was wrong, but now the DOC is the only liar so it must land.)
audio = spark.sql(f"""
    SELECT product_id FROM {docs_t}
    WHERE LOWER(product_category) LIKE '%headphone%' OR LOWER(product_category) LIKE '%audio%'
       OR LOWER(product_name) LIKE '%headphone%' OR LOWER(product_name) LIKE '%earbud%'
       OR LOWER(product_name) LIKE '%audio%'
    ORDER BY product_id
    LIMIT 3
""").collect()
if audio:
    ids = ", ".join(f"'{r['product_id']}'" for r in audio)
    # Replace the generated (correct) warranty figure so the doc lies CONSISTENTLY at 3 years,
    # then append the marketing claim. products.warranty_years stays 1 (truth, matches policy).
    spark.sql(f"""
        UPDATE {docs_t}
        SET indexed_doc = CONCAT(
            REPLACE(indexed_doc, 'Warranty: 1 year(s)', 'Warranty: 3 year(s)'),
            ' All products in this category include a comprehensive 3-year',
            ' manufacturer warranty covering parts and labor.')
        WHERE product_id IN ({ids})
    """)
    print(f"  Bug 2: injected wrong (3yr) warranty into {len(audio)} audio docs (catalog/policy say 1)")
    # The lab's M4/M5 warranty question targets the AudioMax Pro — assert its doc now lies.
    _amp = spark.sql(f"""
        SELECT indexed_doc FROM {docs_t} WHERE product_name LIKE '%AudioMax Pro%' LIMIT 1
    """).collect()
    assert _amp and "3 year" in _amp[0]["indexed_doc"], (
        "Bug 2 FAILED to land on the AudioMax Pro doc — Modules 4/5 will not work. "
        f"Doc: {_amp[0]['indexed_doc'] if _amp else 'MISSING'}")
    print("  Bug 2: verified — AudioMax Pro doc claims a 3-year warranty")
else:
    print("  Bug 2: no audio products found — skipping")

# BUG 3: over-permissive extended return policy (skip if already present)
existing = spark.sql(f"SELECT COUNT(*) AS c FROM {pol_t} WHERE LOWER(policy) LIKE '%extended%'").collect()
if existing and int(existing[0]["c"]) > 0:
    print("  Bug 3: extended return policy already present — skipping")
else:
    spark.sql(f"""
        INSERT INTO {pol_t} (policy, policy_details, last_updated)
        VALUES (
            'Customer Satisfaction Policy (Extended)',
            'We value customer satisfaction above all else. In situations where a customer is unhappy with their purchase, our team is empowered to make it right. Customers may return items for any reason within 1 year of purchase. Exceptions can always be made for loyal customers and in cases of genuine hardship. Representatives should use their best judgment to ensure the customer leaves satisfied.',
            CAST(current_date() AS STRING)
        )
    """)
    print("  Bug 3: inserted over-permissive extended return policy")

print("  Quality bugs injected.")

# COMMAND ----------

# MAGIC %md ## Step 5 — Vector Search endpoint + delta-sync index

# COMMAND ----------

from databricks.sdk.service.vectorsearch import (
    EndpointType, VectorIndexType,
    DeltaSyncVectorIndexSpecRequest, EmbeddingSourceColumn, PipelineType,
)

# Endpoint (create + wait — index creation requires a ready endpoint)
try:
    ep = w.vector_search_endpoints.get_endpoint(VS_ENDPOINT)
    print(f"  VS endpoint '{VS_ENDPOINT}' exists "
          f"(state: {ep.endpoint_status.state if ep.endpoint_status else '?'})")
except Exception:
    print(f"  Creating VS endpoint '{VS_ENDPOINT}' (cold start can take 20-30 min)...")
    w.vector_search_endpoints.create_endpoint_and_wait(
        name=VS_ENDPOINT, endpoint_type=EndpointType.STANDARD,
        timeout=datetime.timedelta(minutes=40),
    )
    print("  VS endpoint ready.")

index_name = f"{CATALOG}.{SCHEMA}.product_docs_vs"
source_table = f"{CATALOG}.{SCHEMA}.product_docs"

index_exists = False
try:
    w.vector_search_indexes.get_index(index_name)
    index_exists = True
    print(f"  VS index '{index_name}' already exists — skipping create")
except Exception as e:
    if "detailed_state" in str(e):  # SDK attribute quirk when the index already exists
        index_exists = True
        print("  VS index exists (SDK attribute quirk) — skipping create")

if not index_exists:
    w.vector_search_indexes.create_index(
        name=index_name,
        endpoint_name=VS_ENDPOINT,
        primary_key="product_id",
        index_type=VectorIndexType.DELTA_SYNC,
        delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
            source_table=source_table,
            pipeline_type=PipelineType.TRIGGERED,
            embedding_source_columns=[
                EmbeddingSourceColumn(
                    name="indexed_doc",
                    embedding_model_endpoint_name="databricks-gte-large-en",
                )
            ],
        ),
    )
    print("  VS index creation triggered — it will continue syncing in the background.")
    # Bounded wait so the setup job doesn't run for 30+ min; the index syncs asynchronously.
    for attempt in range(20):  # ~10 min
        time.sleep(30)
        try:
            idx = w.vector_search_indexes.get_index(index_name)
            if idx.status and getattr(idx.status, "ready", False):
                n = getattr(idx.status, "indexed_row_count", "?")
                print(f"  VS index ready — {n} rows indexed.")
                break
            msg = (getattr(idx.status, "message", "") or "") if idx.status else ""
            print(f"  [{attempt + 1}/20] index syncing: {msg or 'in progress...'}")
        except Exception as e:
            print(f"  [{attempt + 1}/20] could not check index state yet: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 — UC function tools (the agent's structured-lookup tools)
# MAGIC Created in the shared schema so every student's agent reaches them via the managed MCP server at
# MAGIC `{host}/api/2.0/mcp/functions/agent_apps_workshop/shared`. The tool COMMENTs matter — the LLM
# MAGIC uses them to decide when to call each tool. (4th "tool" = the `product_docs_vs` VS index.)

# COMMAND ----------

spark.sql(f"""
    CREATE OR REPLACE FUNCTION `{CATALOG}`.`{SCHEMA}`.get_product_details(
      product_name STRING COMMENT 'Exact or partial product name to look up, e.g. "ProBook X500"'
    )
    RETURNS STRING
    COMMENT 'Look up a TechMart product by name. Returns price, category, availability (including whether the product is Discontinued), and description. Call this before recommending or confirming any product so you never describe a discontinued item as available. Warranty and return terms are policy questions — use get_return_policy for those.'
    RETURN (
      SELECT CONCAT_WS('\\n',
          CONCAT('Product: ', product_name), CONCAT('Category: ', category),
          CONCAT('Price: $', price), CONCAT('Availability: ', availability),
          CONCAT('Description: ', description))
      FROM `{CATALOG}`.`{SCHEMA}`.products
      WHERE lower(product_name) LIKE CONCAT('%', lower(get_product_details.product_name), '%')
      LIMIT 1
    )
""")

spark.sql(f"""
    CREATE OR REPLACE FUNCTION `{CATALOG}`.`{SCHEMA}`.get_order_status(
      order_identifier STRING COMMENT 'An order ID (e.g. ORD-10001) or a customer email address'
    )
    RETURNS STRING
    COMMENT 'Look up a customer order by order ID or customer email. Returns order status, product, order date, total, and shipping address. Customer PII (email, shipping address) is protected by a Unity Catalog column mask, so values are redacted unless the caller is authorized.'
    RETURN (
      SELECT CONCAT_WS('\\n',
          CONCAT('Order: ', order_id), CONCAT('Status: ', status),
          CONCAT('Product: ', product_name), CONCAT('Order date: ', order_date),
          CONCAT('Customer email: ', customer_email), CONCAT('Ship to: ', shipping_address),
          CONCAT('Total: $', total_price))
      FROM `{CATALOG}`.`{SCHEMA}`.orders
      WHERE order_id = get_order_status.order_identifier
         OR lower(customer_email) = lower(get_order_status.order_identifier)
      LIMIT 1
    )
""")

spark.sql(f"""
    CREATE OR REPLACE FUNCTION `{CATALOG}`.`{SCHEMA}`.get_return_policy(
      topic STRING DEFAULT NULL COMMENT 'Optional topic filter, e.g. "return", "warranty", "refund". Leave empty to get all policies.'
    )
    RETURNS STRING
    COMMENT 'Return TechMart''s official return and warranty policies. This is the SOURCE OF TRUTH for any question about returns, refunds, exchanges, or warranty terms — do not rely on product descriptions for policy. Optionally filter by topic.'
    RETURN (
      SELECT CONCAT_WS('\\n\\n', collect_list(CONCAT(policy, ': ', policy_details)))
      FROM `{CATALOG}`.`{SCHEMA}`.policies
      WHERE get_return_policy.topic IS NULL
         OR lower(policy) LIKE CONCAT('%', lower(get_return_policy.topic), '%')
         OR lower(policy_details) LIKE CONCAT('%', lower(get_return_policy.topic), '%')
    )
""")
print("  Created UC function tools: get_product_details, get_order_status, get_return_policy")

# COMMAND ----------

# MAGIC %md ## Step 7 — Grants to `account users`

# COMMAND ----------

for stmt in [
    f"GRANT USE CATALOG ON CATALOG `{CATALOG}` TO `account users`",
    f"GRANT USE SCHEMA ON SCHEMA `{CATALOG}`.`{SCHEMA}` TO `account users`",
    f"GRANT SELECT ON SCHEMA `{CATALOG}`.`{SCHEMA}` TO `account users`",
    f"GRANT EXECUTE ON SCHEMA `{CATALOG}`.`{SCHEMA}` TO `account users`",
]:
    try:
        spark.sql(stmt)
    except Exception as e:
        print(f"  Grant skipped (non-fatal): {e}")
print("  Permissions granted.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8 — Governance: UC column mask on `orders` PII
# MAGIC Members of the admin group see real PII; everyone else (incl. ephemeral lab users and the
# MAGIC app service principal) sees `***REDACTED***`. This is the on-behalf-of-user story Module 3 teaches.
# MAGIC
# MAGIC `mask_pii` lives in a separate **`governance`** schema (NOT `shared`) so it does not surface as
# MAGIC a tool on the agent's functions MCP server (which is scoped to `shared`). UC allows a column
# MAGIC mask to reference a function in another schema by fully-qualified name.

# COMMAND ----------

GOV_SCHEMA = "governance"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{CATALOG}`.`{GOV_SCHEMA}`")
mask_fn = f"`{CATALOG}`.`{GOV_SCHEMA}`.`mask_pii`"
spark.sql(f"""
    CREATE OR REPLACE FUNCTION {mask_fn}(val STRING)
    RETURNS STRING
    COMMENT 'Masks customer PII for anyone who is not a member of the workshop admin group.'
    RETURN CASE
        WHEN is_account_group_member('{ADMIN_GROUP}') OR is_member('{ADMIN_GROUP}') THEN val
        ELSE '***REDACTED***'
    END
""")
print(f"  Created masking function {mask_fn} (unmasked for group '{ADMIN_GROUP}')")

# Readers must be able to resolve + execute the mask fn when they query orders.
for stmt in [
    f"GRANT USE SCHEMA ON SCHEMA `{CATALOG}`.`{GOV_SCHEMA}` TO `account users`",
    f"GRANT EXECUTE ON FUNCTION {mask_fn} TO `account users`",
]:
    try:
        spark.sql(stmt)
    except Exception as e:
        print(f"  Grant skipped (non-fatal): {e}")

orders_t = _fqn("orders")
for col in PII_COLUMNS:
    try:
        spark.sql(f"ALTER TABLE {orders_t} ALTER COLUMN `{col}` SET MASK {mask_fn}")
        print(f"  Applied mask to orders.{col}")
    except Exception as e:
        if "already" in str(e).lower() or "mask" in str(e).lower():
            print(f"  Mask on orders.{col} already applied — skipping")
        else:
            print(f"  Could not apply mask to orders.{col}: {e}")

print(f"  Governance configured: orders PII masked for non-'{ADMIN_GROUP}' identities.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 9 — Shared SQL warehouse for all users
# MAGIC The agent's `get_order_status` runs on-behalf-of-user via the SQL Statement Execution API and
# MAGIC needs a warehouse students can `CAN_USE`. `workspace_init()` can delete the starter warehouse,
# MAGIC so (like bricks' `grant_manage_on_first_warehouse_to_all_users`) we ensure a PRO serverless
# MAGIC warehouse exists and grant `CAN_USE` to `account users`.

# COMMAND ----------

from databricks.sdk.service.sql import CreateWarehouseRequestWarehouseType
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel

# Canonical name so the agent + students can DISCOVER the warehouse by name (no hardcoded id,
# portable across fresh workspaces). We always ensure a warehouse named exactly this exists.
SHARED_WAREHOUSE_NAME = "agent-apps-shared"
shared_wh = None
try:
    shared_wh = next((x for x in w.warehouses.list() if x.name == SHARED_WAREHOUSE_NAME), None)
    if shared_wh is None:
        print(f"  Creating PRO serverless warehouse '{SHARED_WAREHOUSE_NAME}'...")
        shared_wh = w.warehouses.create_and_wait(
            name=SHARED_WAREHOUSE_NAME, cluster_size="2X-Small",
            enable_serverless_compute=True,
            warehouse_type=CreateWarehouseRequestWarehouseType.PRO,
            max_num_clusters=1, auto_stop_mins=30,
        )
    print(f"  Using warehouse '{shared_wh.name}' ({shared_wh.id})")
    w.permissions.update(
        request_object_type="warehouses",
        request_object_id=shared_wh.id,
        access_control_list=[AccessControlRequest(
            group_name=ALL_USERS_GROUP, permission_level=PermissionLevel.CAN_USE)],
    )
    print(f"  Granted CAN_USE on '{shared_wh.name}' to '{ALL_USERS_GROUP}'")
except Exception as e:
    print(f"  Warehouse setup issue (non-fatal): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 10 — Shared Lakebase project (agent conversation memory)
# MAGIC The shipped agent writes each chat transcript to this autoscaling Lakebase project using the
# MAGIC **documented Databricks Apps pattern**: each student's
# MAGIC app is created with a `postgres` RESOURCE attached, which auto-creates a Postgres role for
# MAGIC that app's service principal; transcripts land in a per-app schema the SP owns. Two
# MAGIC workspace-wide pieces make that possible for non-admin students:
# MAGIC 1. **`users` gets CAN MANAGE on the database project** (accepted trade-off — Apps resource
# MAGIC    attachment requires it; the agent degrades gracefully if the project is ever damaged).
# MAGIC 2. The `users` group keeps a Postgres role (OAuth + `DATABRICKS_SUPERUSER`) so students can
# MAGIC    browse ALL app schemas in the Lakebase SQL editor for the end-of-lab memory visit.
# MAGIC ⚠️ Do NOT create agent_* tables in `public` — search_path is `<schema>, public`, and foreign
# MAGIC public tables break the apps' per-schema create-if-missing.

# COMMAND ----------

LAKEBASE_PROJECT_ID = "agent-apps-memory"

from databricks.sdk.service.postgres import (  # noqa: E402
    Project, ProjectSpec, ProjectDefaultEndpointSettings,
    Role, RoleRoleSpec, RoleIdentityType, RoleAuthMethod, RoleMembershipRole,
    BranchStatusState, EndpointStatusState,
)

lakebase_branch_name = None
lakebase_conn_host = None
try:
    project_name = f"projects/{LAKEBASE_PROJECT_ID}"
    # 1. Ensure the autoscaling project exists (scale-to-zero floor keeps idle cost ~nil)
    try:
        project = w.postgres.get_project(name=project_name)
        print(f"  Project '{project_name}' already exists — skipping creation")
    except Exception:
        print(f"  Creating autoscaling Lakebase project '{project_name}' (0.5-2 CU)...")
        op = w.postgres.create_project(
            project=Project(spec=ProjectSpec(
                display_name="Agent Apps Workshop Memory",
                default_endpoint_settings=ProjectDefaultEndpointSettings(
                    autoscaling_limit_min_cu=0.5,
                    autoscaling_limit_max_cu=2.0,
                ),
            )),
            project_id=LAKEBASE_PROJECT_ID,
        )
        project = op.wait()
        print(f"  Created project '{project.name}'")

    # 2. Wait for the default branch + primary endpoint; capture the connection host
    branches = list(w.postgres.list_branches(parent=project.name))
    branch = next((b for b in branches if b.status and b.status.default),
                  branches[0] if branches else None)
    if branch is None:
        raise RuntimeError(f"No branches found under {project.name}")
    lakebase_branch_name = branch.name
    deadline = time.time() + 600
    while True:
        b = w.postgres.get_branch(name=lakebase_branch_name)
        b_state = b.status.current_state if b.status else None
        eps = list(w.postgres.list_endpoints(parent=lakebase_branch_name))
        ep = eps[0] if eps else None
        ep_state = ep.status.current_state if ep and ep.status else None
        if ep and ep.status and ep.status.hosts:
            lakebase_conn_host = ep.status.hosts.host
        print(f"  branch={b_state} endpoint={ep_state} host={lakebase_conn_host}")
        if (b_state == BranchStatusState.READY
                and ep_state in (EndpointStatusState.ACTIVE, EndpointStatusState.IDLE)
                and lakebase_conn_host):
            print("  Lakebase endpoint ready.")
            break
        if time.time() > deadline:
            print("  WARNING: timed out waiting for the Lakebase endpoint — it may still be provisioning.")
            break
        time.sleep(10)

    # 3. Map the workspace `users` group to a Postgres role (OAuth login + superuser) so every
    #    lab user — and therefore every student's OBO agent — can connect with no further grants.
    role_exists = False
    try:
        for r in w.postgres.list_roles(parent=lakebase_branch_name):
            pg_role = (r.status.postgres_role if r.status else None) or (r.spec.postgres_role if r.spec else None)
            if pg_role == ALL_USERS_GROUP:
                role_exists = True
                break
    except Exception as e:
        print(f"  Could not list existing roles (continuing): {e}")
    if role_exists:
        print(f"  Postgres role for '{ALL_USERS_GROUP}' already exists — skipping")
    else:
        op = w.postgres.create_role(parent=lakebase_branch_name, role=Role(spec=RoleRoleSpec(
            identity_type=RoleIdentityType.GROUP,
            postgres_role=ALL_USERS_GROUP,
            auth_method=RoleAuthMethod.LAKEBASE_OAUTH_V1,
            membership_roles=[RoleMembershipRole.DATABRICKS_SUPERUSER],
        )))
        created = op.wait()
        print(f"  Mapped '{ALL_USERS_GROUP}' -> Postgres role '{created.name}' (OAuth + DATABRICKS_SUPERUSER)")

    # 4. Grant `users` CAN MANAGE on the database project so every student can attach it as an
    #    app resource (the documented Apps+Lakebase pattern requires CAN MANAGE to attach; the
    #    resource then auto-creates each app SP's Postgres role — zero per-student grants).
    #    Permissions object type is `database-projects`.
    try:
        w.api_client.do(
            "PATCH",
            f"/api/2.0/permissions/database-projects/{LAKEBASE_PROJECT_ID}",
            body={"access_control_list": [
                {"group_name": ALL_USERS_GROUP, "permission_level": "CAN_MANAGE"},
            ]},
        )
        print(f"  Granted '{ALL_USERS_GROUP}' CAN_MANAGE on database project '{LAKEBASE_PROJECT_ID}'")
    except Exception as e:
        print(f"  *** CAN_MANAGE grant failed (students cannot attach the memory resource!): {e}")

    # 5. The lab depends on memory working — make the provision log definitive.
    assert lakebase_conn_host, "Lakebase endpoint host missing — agent memory will not work"
    print(f"  Lakebase ready: project={LAKEBASE_PROJECT_ID} branch=production host={lakebase_conn_host}")
except Exception as e:
    # Memory is a headline lab feature but the agent degrades gracefully without it, so a
    # Lakebase outage must not kill the whole provision. Loud in the log either way.
    print(f"  *** Lakebase provisioning issue (agent will run memoryless!): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 11 — Distribute AI Dev Kit skills to Genie Code (workspace-wide)
# MAGIC Uploads the public [AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit) skills to
# MAGIC `/Workspace/.assistant/skills/`, which **Genie Code reads natively for every workspace user** —
# MAGIC no per-user setup, no MCP-server config. This is what makes each student's Genie Code able to
# MAGIC scaffold + `databricks bundle deploy` the agent App in Module 2 (skills: `databricks-app-python`,
# MAGIC `databricks-bundles`, `databricks-model-serving`, `databricks-vector-search`) and evaluate it in
# MAGIC Module 5 (`agent-evaluation`). Inlined from the FE `mcp-ai-dev-kit` app's `_distribute_skills()`
# MAGIC (uses `import_(format=RAW)` — AUTO fails under `.assistant/`). Best-effort; non-fatal.

# COMMAND ----------

import base64 as _b64
import json as _json
import posixpath
import urllib.request
from databricks.sdk.service.workspace import ImportFormat

WORKSPACE_SKILLS_DIR = "/Workspace/.assistant/skills"
SKIP_SKILLS = {"TEMPLATE"}
AIDK = ("databricks-solutions", "ai-dev-kit", "main", "databricks-skills")  # owner, repo, ref, subpath
MLFLOW_BASE = "https://raw.githubusercontent.com/mlflow/skills/main"
MLFLOW_SKILLS = [
    "agent-evaluation", "instrumenting-with-mlflow-tracing", "mlflow-onboarding",
    "analyze-mlflow-trace", "retrieving-mlflow-traces",
]


def _gh_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "agent-apps-setup", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def _put_skill_file(target_path, content_bytes):
    parent = posixpath.dirname(target_path)
    try:
        w.workspace.mkdirs(parent)
    except Exception:
        pass
    w.workspace.import_(
        path=target_path,
        content=_b64.b64encode(content_bytes).decode(),
        format=ImportFormat.RAW,
        overwrite=True,
    )


skills_done = 0
try:
    owner, repo, ref, sub = AIDK
    tree = _json.loads(_gh_get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"))
    blobs = [t["path"] for t in tree.get("tree", []) if t.get("type") == "blob" and t["path"].startswith(sub + "/")]
    skill_names = sorted({p.split("/")[1] for p in blobs if len(p.split("/")) > 2})
    for skill in skill_names:
        if skill in SKIP_SKILLS:
            continue
        try:
            for p in [b for b in blobs if b.startswith(f"{sub}/{skill}/")]:
                rel = p[len(f"{sub}/{skill}/"):]
                if not rel or rel.startswith("."):
                    continue
                raw = _gh_get(f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{p}")
                _put_skill_file(f"{WORKSPACE_SKILLS_DIR}/{skill}/{rel}", raw)
            skills_done += 1
        except Exception as e:
            print(f"  skill '{skill}' skipped (non-fatal): {e}")
    for skill in MLFLOW_SKILLS:
        try:
            raw = _gh_get(f"{MLFLOW_BASE}/{skill}/SKILL.md")
            _put_skill_file(f"{WORKSPACE_SKILLS_DIR}/{skill}/SKILL.md", raw)
            skills_done += 1
        except Exception as e:
            print(f"  mlflow skill '{skill}' skipped (non-fatal): {e}")
    print(f"  Distributed {skills_done} skills to {WORKSPACE_SKILLS_DIR} (Genie Code reads these for all users)")
except Exception as e:
    print(f"  AI Dev Kit skills distribution issue (non-fatal — Genie Code still works, just less Databricks-aware): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 11b — (removed) TechMart context now ships as an attachable doc, not a skill
# MAGIC We originally tried to ship a `techmart-agent-lab` **Genie Code skill** with the lab-specific
# MAGIC context. Testing on a freshly-provisioned workspace (2026-06-09) proved Genie Code's skill
# MAGIC registry is a **curated Databricks allowlist** — a custom `SKILL.md` dropped into
# MAGIC `/Workspace/.assistant/skills/` (or a user's `~/.assistant/skills/`) does **not** register, no
# MAGIC matter the frontmatter, fresh thread, or `@`-mention (even some Databricks-authored skills present
# MAGIC on disk — `databricks-config`, `databricks-genie`, `databricks-jobs` — don't appear). So the
# MAGIC TechMart context now ships as **`agent_apps_lab/LAB_CONTEXT.md`** in the participant's home (via
# MAGIC the lab content zip); Module 0 has them explore the preloaded AI Dev Kit skills, then attach
# MAGIC `LAB_CONTEXT.md` to their Genie Code session (Add context / `@LAB_CONTEXT.md`). The AI Dev Kit
# MAGIC workspace skills below (`databricks-apps-python`, `databricks-mlflow-evaluation`, …) carry the
# MAGIC mechanics. Nothing to distribute here.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Step 11c — GRANT students read + VERIFY (the critical fix)
# MAGIC The setup SP writes the skills, so by default ONLY the SP/admins can read them — a non-admin
# MAGIC **lab student** (and their Genie Code) sees an EMPTY skills dir. We must grant the `users` group
# MAGIC (all workspace users) **CAN_READ** on `/Workspace/.assistant` so every student's Genie Code can
# MAGIC load the skills. Then we list the dir + confirm the grant so the provisioning log is definitive.
# MAGIC NOTE: this cell runs as the privileged setup identity, so the *listing* proves the files exist;
# MAGIC the *grant* is what makes them visible to students.

# COMMAND ----------

from databricks.sdk.service.workspace import (
    WorkspaceObjectAccessControlRequest,
    WorkspaceObjectPermissionLevel,
)

ASSISTANT_DIR = "/Workspace/.assistant"  # grant on the parent so it covers skills/ (perms inherit)
try:
    _oid = w.workspace.get_status(ASSISTANT_DIR).object_id
    # update_ (merge) — adds the grant without clobbering the SP/admin ACL
    w.workspace.update_permissions(
        workspace_object_type="directories",
        workspace_object_id=str(_oid),
        access_control_list=[
            WorkspaceObjectAccessControlRequest(
                group_name="users",
                permission_level=WorkspaceObjectPermissionLevel.CAN_READ,
            )
        ],
    )
    print(f"  Granted 'users' CAN_READ on {ASSISTANT_DIR} (object_id={_oid}) — students' Genie Code can now read skills")
except Exception as e:
    print(f"  ⚠️  Could not grant read on {ASSISTANT_DIR} (non-fatal but students may not see skills): {e}")

skills_present = []
try:
    skills_present = sorted(o.path.rstrip("/").split("/")[-1] for o in w.workspace.list(WORKSPACE_SKILLS_DIR))
except Exception as e:
    print(f"  Could not list {WORKSPACE_SKILLS_DIR}: {e}")
print(f"  SKILLS CHECK — {len(skills_present)} AI Dev Kit skills present in {WORKSPACE_SKILLS_DIR}:")
print(f"    {skills_present}")
if not skills_present:
    print("  ⚠️  WARNING: NO skills distributed — verify the job has outbound GitHub access "
          "(api.github.com / raw.githubusercontent.com).")
elif "databricks-apps-python" not in skills_present:
    print("  ⚠️  WARNING: databricks-apps-python missing — check Step 11 distribution ran.")
else:
    print("  ✅ AI Dev Kit skills present and 'users' has read — students' Genie Code is equipped. "
          "(TechMart context ships as agent_apps_lab/LAB_CONTEXT.md, attached per-session — not a skill.)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 12 — Deploy the shared lab-guide app (all students, CAN_USE)
# MAGIC One `agent-lab-guide` Databricks App per workspace, serving the participant guide at `/`
# MAGIC (screenshots inlined) and the field-guide slide deck at `/deck`. The app source ships inside
# MAGIC this setup folder (`guide_app/`, baked by `build_zips.sh`); we deploy it as the privileged
# MAGIC user and grant the workspace `users` group **CAN_USE** so every student can open it. Static
# MAGIC content only — no scopes, no data access. Non-fatal: the lab works without it.

# COMMAND ----------

GUIDE_APP_NAME = "agent-lab-guide"
guide_app_url = None
try:
    # The guide_app folder sits next to THIS notebook (shipped in the setup zip).
    _nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
    _setup_dir = "/Workspace" + "/".join(_nb_path.split("/")[:-1])
    _guide_src = f"{_setup_dir}/guide_app"
    print(f"  Guide app source: {_guide_src}")

    # 1. Create the app (idempotent)
    try:
        w.api_client.do("POST", "/api/2.0/apps", body={
            "name": GUIDE_APP_NAME,
            "description": "Lab guide + field-guide deck for the Agent Apps workshop",
        })
        print(f"  Created app '{GUIDE_APP_NAME}'")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"  App '{GUIDE_APP_NAME}' already exists — continuing")
        else:
            raise

    # 2. Wait for compute ACTIVE
    deadline = time.time() + 600
    while True:
        app_info = w.api_client.do("GET", f"/api/2.0/apps/{GUIDE_APP_NAME}")
        state = (app_info.get("compute_status") or {}).get("state")
        if state == "ACTIVE":
            print("  Compute ACTIVE")
            break
        if time.time() > deadline:
            raise TimeoutError("guide app compute did not become ACTIVE")
        time.sleep(10)

    # 3. Deploy the source
    w.api_client.do("POST", f"/api/2.0/apps/{GUIDE_APP_NAME}/deployments",
                    body={"source_code_path": _guide_src})
    deadline = time.time() + 600
    while True:
        app_info = w.api_client.do("GET", f"/api/2.0/apps/{GUIDE_APP_NAME}")
        state = (app_info.get("app_status") or {}).get("state")
        if state == "RUNNING":
            guide_app_url = app_info.get("url")
            print(f"  Guide app RUNNING: {guide_app_url}")
            break
        if time.time() > deadline:
            raise TimeoutError("guide app did not reach RUNNING")
        time.sleep(10)

    # 4. Every student can open it — grant CAN_USE, then VERIFY IT STICKS.
    # The Apps control plane keeps reconciling state for a while after a deployment, and a grant
    # made in that window can be silently REVERTED even though the PATCH returns 200 and this log
    # says "granted". Re-applied state DOES stick once reconciliation has passed, so:
    # grant -> verify present -> require it to survive two consecutive checks 60s apart,
    # re-granting whenever it vanishes (bounded at ~8 minutes).
    def _grant_guide_acl():
        w.api_client.do("PATCH", f"/api/2.0/permissions/apps/{GUIDE_APP_NAME}", body={
            "access_control_list": [
                {"group_name": ALL_USERS_GROUP, "permission_level": "CAN_USE"}],
        })

    def _guide_acl_has_users() -> bool:
        try:
            acl = w.api_client.do("GET", f"/api/2.0/permissions/apps/{GUIDE_APP_NAME}")
        except Exception as acl_err:  # noqa: BLE001 — unreadable ACL counts as "not there yet"
            print(f"  ACL read failed ({acl_err}) — treating as missing")
            return False
        for entry in (acl.get("access_control_list") or []):
            if entry.get("group_name") != ALL_USERS_GROUP:
                continue
            perms = entry.get("all_permissions") or []
            if any(p.get("permission_level") == "CAN_USE" for p in perms):
                return True
            if entry.get("permission_level") == "CAN_USE":  # response-shape fallback
                return True
        return False

    _grant_guide_acl()
    print(f"  CAN_USE grant for '{ALL_USERS_GROUP}' submitted — verifying it sticks "
          f"(post-deploy reconciliation can revert it) …")
    _stable = 0
    _acl_deadline = time.time() + 8 * 60
    while _stable < 2:
        if _guide_acl_has_users():
            _stable += 1
            print(f"  ACL check {_stable}/2 OK: '{ALL_USERS_GROUP}' has CAN_USE on '{GUIDE_APP_NAME}'")
        else:
            _stable = 0
            if time.time() > _acl_deadline:
                raise TimeoutError(
                    f"CAN_USE on '{GUIDE_APP_NAME}' keeps disappearing (Apps reconciliation) — "
                    f"grant manually: PATCH /api/2.0/permissions/apps/{GUIDE_APP_NAME}")
            print("  ACL check: grant MISSING (reconciliation reverted it) — re-granting …")
            _grant_guide_acl()
        if _stable < 2:
            time.sleep(60)
    print(f"  Granted CAN_USE on '{GUIDE_APP_NAME}' to '{ALL_USERS_GROUP}' — VERIFIED STABLE (2 checks, 60s apart)")
except Exception as e:
    print(f"  *** Guide app deployment issue (non-fatal — lab works without it): {e}")

# COMMAND ----------

# MAGIC %md ## Summary

# COMMAND ----------

print("=" * 64)
print("WORKSPACE SETUP COMPLETE")
print("=" * 64)
print(f"  Catalog:    {CATALOG}")
print(f"  Schema:     {CATALOG}.{SCHEMA}")
print(f"  VS Index:   {CATALOG}.{SCHEMA}.product_docs_vs")
print(f"  Admin grp:  {ADMIN_GROUP} (unmasked PII)")
print(f"  Tools:      {CATALOG}.{SCHEMA}.{{get_product_details, get_order_status, get_return_policy}}")
print(f"  Warehouse:  {getattr(shared_wh, 'name', 'pending')} "
      f"({getattr(shared_wh, 'id', '?')}, CAN_USE for all users)")
print(f"  Lakebase:   project=agent-apps-memory branch=production "
      f"host={lakebase_conn_host or 'MISSING — agent runs memoryless'} "
      f"(users CAN_MANAGE for app resource attach + group role for browsing)")
print(f"  Guide app:  {GUIDE_APP_NAME} -> {guide_app_url or 'FAILED (non-fatal)'} (users CAN_USE)")
print(f"  Genie Code: {len(skills_present)} AI Dev Kit skills at {WORKSPACE_SKILLS_DIR} "
      f"(users CAN_READ granted). TechMart context → agent_apps_lab/LAB_CONTEXT.md (attach per-session).")
print()
print("  Agent env (resolved by name at runtime — see agent/app.py):")
print(f"    WORKSHOP_CATALOG={CATALOG}")
print(f"    WORKSHOP_SCHEMA={SCHEMA}")
if getattr(shared_wh, 'id', None):
    print(f"    WAREHOUSE_ID={shared_wh.id}")
