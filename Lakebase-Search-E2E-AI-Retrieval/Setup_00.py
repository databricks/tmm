# Databricks notebook source
# DBTITLE 1,Notebook title
# MAGIC %md
# MAGIC # Tech Product Search Demo — Setup
# MAGIC
# MAGIC Complete setup for the Lakebase search demo: project, products table with embeddings, agent memory, document pipeline, synced table, search indexes, and widget dependencies.
# MAGIC
# MAGIC | Component | Description |
# MAGIC | --- | --- |
# MAGIC | Products | 10K Amazon Electronics products with vector + BM25 indexes |
# MAGIC | Agent memory | 45 synthetic past conversations for the support agent |
# MAGIC | Document pipeline | Lakeflow SDP (chunk + embed) → Synced Table → Lakebase Search |
# MAGIC | Widget deps | Widget classes, document loading, embedding + chat functions |

# COMMAND ----------

# DBTITLE 1,Parameters
# ── Lakebase ─────────────────────────────────────────────────────────────
LAKEBASE_PROJECT_ID  = "tech-products-search"        # Lakebase project ID
LAKEBASE_BRANCH_ID   = "production"             # Lakebase branch
LAKEBASE_ENDPOINT_ID = "primary"                # Lakebase endpoint (compute)
LAKEBASE_DATABASE    = "tech_products_search"        # Postgres database name
PG_SCHEMA            = "tech_products_search"   # Postgres schema for all demo tables

# ── Unity Catalog ────────────────────────────────────────────────────────
UC_CATALOG = "main"                             # UC catalog for Delta tables (change if you can't create schemas in `main`)
UC_SCHEMA  = "tech_products_search"                  # UC schema for Delta tables

# ── Embedding ────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "databricks-qwen3-embedding-0-6b"
EMBEDDING_DIM   = 1024

# ── Chunking ─────────────────────────────────────────────────────────────
CHUNK_SIZE    = 1500                            # Characters per chunk
CHUNK_OVERLAP = 200                             # Overlap between chunks

# ── Pipeline ─────────────────────────────────────────────────────────────
PIPELINE_NAME = "document-chunking-embedding"   # Lakeflow Declarative Pipeline name

# ── Products & Search ────────────────────────────────────────────────────
MAX_PRODUCTS      = 10000
TOP_K             = 5
RRF_K             = 60
SEARCH_QUERY_TEXT = "wireless noise cancelling headphones"

# ── Agent ────────────────────────────────────────────────────────────────
LLM_ENDPOINT  = "databricks-claude-sonnet-4-5"
MEMORY_TABLE  = f"{PG_SCHEMA}.agent_memory"
CUSTOMER_NAME = ""

# ── Cleanup ──────────────────────────────────────────────────────────────
RUN_CLEANUP = False

# ── Derived Names (do not edit) ──────────────────────────────────────────
# Folder containing this notebook (works standalone and via %run from Demo_01)
import os as _os
DEMO_DIR = _os.path.dirname(
    dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
).removeprefix("/Workspace")                                               # e.g. /Users/<you>/search-demo
CHUNKS_TABLE      = f"{UC_CATALOG}.{UC_SCHEMA}.document_chunks_embedded"
SYNCED_TABLE_ID   = f"{UC_CATALOG}.{UC_SCHEMA}.synced_document_chunks"
BRANCH_PATH       = f"projects/{LAKEBASE_PROJECT_ID}/branches/{LAKEBASE_BRANCH_ID}"
ENDPOINT_PATH     = f"{BRANCH_PATH}/endpoints/{LAKEBASE_ENDPOINT_ID}"

# Aliases used by Demo_01 widgets
DATABASE_NAME  = LAKEBASE_DATABASE
PROJECT_ID     = LAKEBASE_PROJECT_ID
BRANCH_ID      = LAKEBASE_BRANCH_ID
ENDPOINT_ID    = LAKEBASE_ENDPOINT_ID
PG_VERSION     = 17
PRIMARY_MIN_CU = 1
PRIMARY_MAX_CU = 1
DOC_CATALOG    = UC_CATALOG
DOC_SCHEMA     = UC_SCHEMA
DOC_TABLE      = f"{PG_SCHEMA}.agent_documents"              # Lakebase Postgres table
CDF_HISTORY_TABLE = f"{UC_CATALOG}.{UC_SCHEMA}.lb_agent_documents_history"  # Delta CDF history
DOC_ID         = "buying-guide-headphones"

print("Setup Configuration:")
print(f"  Lakebase:        {LAKEBASE_DATABASE}.{PG_SCHEMA}.*")
print(f"  Products:        {MAX_PRODUCTS} max, embeddings via {EMBEDDING_MODEL}")
print(f"  Pipeline Output: {CHUNKS_TABLE}")
print(f"  Synced Table:    {SYNCED_TABLE_ID}")
print(f"  Embedding:       {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
print(f"  Chunking:        {CHUNK_SIZE} chars, {CHUNK_OVERLAP} overlap")

# COMMAND ----------

# DBTITLE 1,Install dependencies
# MAGIC %pip install "psycopg[binary]>=3.1.0,<4" huggingface_hub --upgrade "databricks-sdk>=0.118.0" --quiet

# COMMAND ----------

# DBTITLE 1,SDK client and Lakebase helpers
import re
import time
import pandas as pd
import psycopg
from psycopg import sql as pg_sql
import requests
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import CdfConfig

w = WorkspaceClient()
workspace_host = w.config.host.rstrip("/")
auth_headers = w.config.authenticate()
current_user = w.current_user.me().user_name

if "Authorization" not in auth_headers:
    raise RuntimeError("Notebook authentication headers were not available.")

if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", LAKEBASE_PROJECT_ID):
    raise ValueError("LAKEBASE_PROJECT_ID must be RFC-1123 compatible.")
if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", LAKEBASE_DATABASE):
    raise ValueError("LAKEBASE_DATABASE must be a simple Postgres identifier.")

from requests.auth import AuthBase

class _DatabricksAuth(AuthBase):
    """Auto-refresh auth with cached fallback for widget callbacks.

    Widget callbacks (anywidget observe handlers) run outside the notebook
    command execution context, so w.config.authenticate() raises
    'Missing api_token'.  We cache the last good token at creation time
    and fall back to it when the runtime refresh fails.
    """
    def __init__(self, ws_client):
        self._w = ws_client
        self._cached = dict(ws_client.config.authenticate())
    def __call__(self, r):
        try:
            fresh = self._w.config.authenticate()
            self._cached = dict(fresh)
        except Exception:
            pass  # fall back to cached token (widget callback context)
        r.headers.update(self._cached)
        return r

session = requests.Session()
session.auth = _DatabricksAuth(w)


def api_request(method, path, *, params=None, json_body=None, ok=(200, 201, 202, 204)):
    """REST helper for Databricks API calls."""
    url = f"{workspace_host}{path}"
    response = session.request(method=method, url=url, params=params, json=json_body, timeout=120)
    if response.status_code not in ok:
        try:
            details = response.json()
        except Exception:
            details = response.text
        raise RuntimeError(f"{method} {path} failed with status {response.status_code}: {details}")
    if response.status_code == 204 or not response.text:
        return None
    return response.json()


def maybe_get(path):
    """GET that returns None on 404 instead of raising."""
    url = f"{workspace_host}{path}"
    response = session.get(url, timeout=120)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        try:
            details = response.json()
        except Exception:
            details = response.text
        raise RuntimeError(f"GET {path} failed with status {response.status_code}: {details}")
    return response.json()


def generate_database_token():
    """Mint a short-lived OAuth token for Lakebase Postgres."""
    resp = session.post(
        f"{workspace_host}/api/2.0/postgres/credentials",
        json={"endpoint": ENDPOINT_PATH},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["token"]


_pg_endpoint_host = None

def connect_postgres(dbname=LAKEBASE_DATABASE):
    """Connect to Lakebase Postgres with auto-generated OAuth token."""
    global _pg_endpoint_host
    try:
        ep = w.postgres.get_endpoint(name=ENDPOINT_PATH)
        _pg_endpoint_host = ep.status.hosts.host
    except Exception:
        if _pg_endpoint_host is None:
            raise  # no cached host available yet
    token = generate_database_token()
    return psycopg.connect(
        host=_pg_endpoint_host, port=5432, dbname=dbname,
        user=current_user, password=token,
        sslmode="require", autocommit=True,
    )


def fetch_pg_df(query_text, params=None, dbname=LAKEBASE_DATABASE):
    """Execute a query against Lakebase and return a pandas DataFrame."""
    with connect_postgres(dbname) as conn:
        with conn.cursor() as cur:
            cur.execute(query_text, params or ())
            rows = cur.fetchall()
            columns = [col.name for col in cur.description]
    return pd.DataFrame(rows, columns=columns)


# Ensure Lakebase project exists (auto-creates production branch + primary endpoint)
from databricks.sdk.service.postgres import Project, ProjectSpec
try:
    w.postgres.get_project(name=f"projects/{LAKEBASE_PROJECT_ID}")
except Exception:
    print(f"  Creating project {LAKEBASE_PROJECT_ID}...")
    w.postgres.create_project(
        project=Project(spec=ProjectSpec(display_name=LAKEBASE_PROJECT_ID, pg_version=17)),
        project_id=LAKEBASE_PROJECT_ID,
    ).wait()
    print(f"  ✓ Project created (with production branch + primary endpoint)")

# Resolve the database resource name (create if missing after fresh project setup)
CDF_PARENT = None
for _d in w.postgres.list_databases(parent=BRANCH_PATH):
    if _d.status and _d.status.postgres_database == LAKEBASE_DATABASE:
        CDF_PARENT = _d.name
        break
if not CDF_PARENT:
    from databricks.sdk.service.postgres import Database, DatabaseDatabaseSpec
    _owner_role = next(iter(w.postgres.list_roles(parent=BRANCH_PATH))).name
    _db = w.postgres.create_database(
        parent=BRANCH_PATH,
        database=Database(spec=DatabaseDatabaseSpec(
            role=_owner_role,
            postgres_database=LAKEBASE_DATABASE,
        )),
        database_id=LAKEBASE_DATABASE.replace("_", "-"),
    ).wait()
    CDF_PARENT = _db.name
    print(f"  ✓ Created database: {CDF_PARENT}")

# Ensure the Postgres schema exists for all demo tables
with connect_postgres() as _conn:
    with _conn.cursor() as _cur:
        _cur.execute(pg_sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
            pg_sql.Identifier(PG_SCHEMA)
        ))
        try:
            _cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_vector CASCADE")
            _cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_text")
        except Exception as _ext_err:
            print(f"  ⚠ Search extensions: {_ext_err}")
            print("    → Enable 'Lakebase Search' on the project in the Databricks UI, then re-run this cell.")

print(f"\u2713 Connected as {current_user}")
print(f"  Endpoint: {ENDPOINT_PATH}")
print(f"  Database: {CDF_PARENT}")
print(f"  PG Schema: {PG_SCHEMA}")

# COMMAND ----------

# DBTITLE 1,Create agent_documents Lakebase table with sample documents
# ── Create the agent_documents Lakebase Postgres table (source of truth) ─
# The agent writes documents directly to this Lakebase table.
# Lakebase CDF captures row-level changes → Delta history table in UC.
# REPLICA IDENTITY FULL is required for CDF to capture full row data.

with connect_postgres() as _conn:
    with _conn.cursor() as _cur:
        _cur.execute(pg_sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.{} (
                doc_id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """).format(pg_sql.Identifier(PG_SCHEMA), pg_sql.Identifier("agent_documents")))
        _cur.execute(f"ALTER TABLE {DOC_TABLE} REPLICA IDENTITY FULL")

# ── Sample agent documents ────────────────────────────────────────────
_AGENT_DOCUMENTS = [
    (
        "buying-guide-headphones",
        "Noise-Cancelling Headphones Buying Guide",
        """
# Noise-Cancelling Headphones Buying Guide

## Why Active Noise Cancellation (ANC) Matters
Active noise cancellation uses built-in microphones to detect ambient sound and generates an inverse audio signal to cancel it out. This is especially valuable for frequent travellers, open-office workers, and anyone who needs focus in noisy environments. ANC is most effective against low-frequency, continuous sounds like engine hum and air conditioning.

## ANC Types: Feedforward, Feedback, and Hybrid
Feedforward ANC places microphones on the outside of the earcup to capture ambient noise before it reaches your ear. Feedback ANC uses microphones inside the earcup to monitor what you actually hear. Hybrid systems combine both approaches for broader noise reduction across more frequencies, and are found in premium models from Sony, Bose, and Apple.

## Battery Life Considerations
ANC headphones rely on battery power. Most models offer 20-40 hours of playback with ANC enabled. Look for fast-charging support — many premium headphones deliver 3-5 hours of playback from a 10-minute charge. If you fly frequently, prioritize models with USB-C charging over older micro-USB designs.

## Comfort and Fit
Over-ear (circumaural) designs distribute weight across a larger surface area and generally offer the best ANC performance because they physically seal the ear. On-ear (supra-aural) models are more compact but may clamp more tightly. In-ear models (earbuds) are the most portable but typically have weaker ANC due to their smaller drivers and microphones. Consider the weight of the headphones — models over 300g can cause fatigue during extended sessions.

## Connectivity: Bluetooth Multipoint and Latency
Bluetooth multipoint allows you to connect to two devices simultaneously — useful for switching between a laptop and phone without re-pairing. Look for Bluetooth 5.0 or later for better range and stability. For gaming or video editing, check the latency specification; some ANC headphones offer a low-latency mode that reduces audio lag below 50ms.

## Sound Quality and Codec Support
Beyond ANC, sound quality depends on driver size, tuning, and codec support. SBC is the baseline codec for all Bluetooth devices. aptX and aptX HD (Qualcomm) offer higher bitrate audio for compatible Android devices. LDAC (Sony) supports up to 990 kbps for high-resolution audio. AAC is the preferred codec for Apple devices. For wired listening, a 3.5mm or USB-C audio input bypasses Bluetooth limitations entirely.

## Price Tiers and Recommendations
Budget models ($50-$100) offer basic ANC and acceptable sound quality. Mid-range ($100-$300) typically adds multipoint, better ANC, and premium build materials. Premium models ($300+) deliver the strongest ANC, best sound quality, and features like adaptive EQ and spatial audio. Consider your primary use case: travel, office, or fitness, as this determines which features matter most.

## Transparency and Ambient Modes
Transparency mode (also called ambient or hear-through mode) uses the same external microphones as ANC to pipe outside sound into your ears. This lets you hear announcements at the airport, talk to a colleague, or stay aware of traffic without removing the headphones. The best implementations sound natural and keep your own voice from sounding muffled. Cheaper models often add a noticeable hiss or make voices sound thin and processed. Some models let you adjust the level of transparency or boost voices specifically.

## Adaptive and Personalized ANC
Adaptive ANC continuously measures the noise around you and adjusts the cancellation strength in real time, for example ramping up on a plane and backing off in a quiet office. Personalized ANC goes further by running a short calibration that accounts for the shape of your ear canal, your hair, or glasses that may break the earcup seal. These features matter most for people who move between very different environments during the day. Fixed-level ANC can feel oppressive in quiet rooms and insufficient in loud ones.

## Microphone Quality for Calls
If you take many calls, microphone performance is as important as playback quality. Look for models with beamforming microphone arrays (four to eight mics) and AI-based voice isolation that suppresses keyboard clicks, traffic, and background chatter. Earbuds with a bone-conduction sensor can detect when you are speaking and filter out other voices. Always check independent call-quality samples, because manufacturer claims rarely reflect performance on a windy street or in a busy cafe.

## Wind Noise Handling
Wind is the most common weakness of ANC headphones. Because external microphones pick up turbulence as loud low-frequency noise, ANC can actually make wind sound worse. Premium models include wind detection that automatically switches microphones or reduces ANC when gusts are detected. Mesh-covered microphone ports and recessed mic placement also help. If you cycle, run, or walk outdoors frequently, read reviews specifically mentioning wind performance before buying.

## Spatial Audio and Head Tracking
Spatial audio processes stereo or multichannel content so that it sounds like it comes from speakers placed around you rather than from inside your head. With head tracking, the sound stage stays anchored to your screen as you turn your head. This is most compelling for movies and supported streaming content. Support depends on the ecosystem: Apple Spatial Audio works best with Apple devices, while Sony 360 Reality Audio and Dolby Atmos implementations vary in quality across platforms.

## Companion Apps and EQ Customization
Most premium headphones come with a companion app that unlocks equalizer presets, custom EQ bands, ANC level control, button remapping, and firmware updates. A good app remembers your settings on the headphones themselves so they persist across devices. Some apps offer hearing tests that build a personal sound profile. Before buying, check whether the app requires an account, how often it is updated, and whether key features are locked behind it, since a poorly maintained app can limit the headphones over time.

## Controls: Touch vs Physical Buttons
Touch controls on the earcup look clean and allow swipe gestures for volume and track skipping, but they can trigger accidentally when adjusting the fit or wearing a hat. Physical buttons are more reliable in cold weather, with gloves, or when exercising. Many users prefer a hybrid: a physical button for ANC and power, touch for playback. Voice assistant integration (Siri, Google Assistant, Alexa) is common, and some models support hands-free wake words that work without pressing anything.

## Wear Detection and Auto-Pause
Wear detection sensors pause playback when you take the headphones off and resume when you put them back on. Some models also power down automatically after a period of inactivity to save battery. This is convenient for office use where you frequently remove headphones to talk to colleagues. Check whether the feature can be disabled, because sensors occasionally misfire when the headphones are worn around the neck or pushed slightly off the ear.

## Build Quality and Materials
Headband and hinge construction determine how long headphones survive daily use. Metal sliders and reinforced hinges outlast all-plastic designs, which are the most common point of failure. Protein leather earpads are soft but can flake after a few years; replaceable earpads are a strong sign of a product designed to last. Check whether the manufacturer sells replacement pads and headband cushions, and whether the battery can be serviced, since a sealed battery often defines the usable lifespan.

## Foldability and Carrying Cases
For travel, look for headphones that fold flat or collapse into a compact shape and ship with a hard-shell case. A rigid case protects the hinges and headband in a crowded backpack or overhead bin. Some flagship models trade foldability for a more rigid, premium headband, which makes them bulkier to pack. Earbud cases should fit comfortably in a pocket and support wireless charging so they can be topped up on a charging pad overnight.

## Wired Mode and Airplane Adapters
A wired input remains useful for in-flight entertainment systems, older laptops, and situations where Bluetooth latency matters. Check whether the headphones work passively when the battery is dead, or whether wired mode still requires power. USB-C audio input can deliver lossless digital audio from compatible phones and laptops. A dual-prong airplane adapter is still included with some travel-oriented models and is worth having if you fly with airlines that use older seat jacks.

## Firmware Updates and Longevity
Firmware updates can improve ANC, add codec support, fix connection bugs, or occasionally change features you rely on. Brands with a track record of supporting products for several years tend to deliver better long-term value. Before upgrading firmware, read release notes and community feedback, because updates have occasionally reduced ANC strength or battery life. Products that allow firmware rollback or delay automatic updates give you more control.

## Hearing Health and Safe Listening
One of the underrated benefits of ANC is that it lets you listen at lower volumes, because you no longer need to drown out background noise. Many phones and companion apps track exposure levels and warn you when you exceed safe listening limits, typically around 80 dB for 40 hours per week. Some headphones include volume limiters suitable for children. If you wear headphones for many hours a day, take regular breaks and keep the volume at roughly 60 percent of maximum.

## ANC Pressure Sensation
Some people experience a sensation of pressure or fullness in the ears when strong ANC is active, similar to being on a descending airplane. This is a perceptual effect caused by the absence of low-frequency sound rather than actual pressure. Adaptive ANC, lower ANC levels, or models tuned for a gentler effect can reduce the discomfort. If you are sensitive to this sensation, try headphones in a store or buy from a retailer with a generous return policy.

## Use Case Recommendations: Travel and Commuting
For long-haul flights and train commutes, prioritize strong low-frequency ANC, comfort over several hours, long battery life, foldability, and a hard case. Over-ear models generally perform best on planes. For daily commuters who walk or cycle part of the way, a good transparency mode and wind handling are just as important. Multipoint connectivity helps if you switch between a phone for music and a laptop for calls during the commute.

## Use Case Recommendations: Office and Fitness
In an open-plan office, call quality, comfort with glasses, multipoint pairing, and a natural transparency mode matter more than maximum ANC strength. For workouts, choose secure-fitting earbuds with an IPX4 or higher rating, physical controls, and wind-resistant microphones. Over-ear headphones are rarely ideal for the gym because they trap heat and sweat. Many people end up owning two products: over-ear headphones for travel and work, and earbuds for exercise.
""",
    ),
    (
        "buying-guide-smartwatch",
        "Smartwatch Buying Guide",
        """
# Smartwatch Buying Guide

## Choosing the Right Ecosystem
The smartwatch you buy is largely determined by your phone. Apple Watch works only with iPhone. Wear OS watches (Google) work with both Android and iOS, though features are limited on iOS. Samsung Galaxy Watch and Google Pixel Watch are the leading Wear OS options. Garmin and Fitbit offer cross-platform compatibility with deeper fitness focus.

## Key Health Sensors
Modern smartwatches include heart rate sensors, SpO2 (blood oxygen), sleep tracking, and increasingly ECG (electrocardiogram) and skin temperature sensors. For serious athletes, GPS accuracy and barometric altitude are critical. Some models now offer blood pressure monitoring, though accuracy varies. Consider which health metrics you actually need — paying for sensors you never use wastes battery.

## Battery Life Trade-offs
Full-featured smartwatches with always-on displays typically last 1-2 days. Fitness-focused watches (Garmin, Fitbit) can last 5-14 days by using simpler displays and fewer background sensors. Solar charging in Garmin models extends battery further for outdoor use. If you travel frequently, consider a watch that charges via standard USB-C rather than proprietary magnetic pucks.

## Display Technology
OLED displays offer vibrant colors and deep blacks, ideal for always-on watch faces. AMOLED is the most common variant. MIP (memory-in-pixel) displays, used in Garmin watches, are more visible in bright sunlight and consume less power but show fewer colors. Choose OLED for everyday smartwatch use and MIP for outdoor sports.

## Water Resistance and Durability
5 ATM water resistance means you can swim and shower with the watch. 10 ATM is suitable for snorkeling and water sports. Look for IP68 or IP6X dust resistance for rugged environments. Sapphire glass displays resist scratches far better than the standard Gorilla Glass found on most models. Military-grade durability (MIL-STD-810) matters if you work outdoors or do adventure sports.

## Price Tiers
Budget ($100-$200): Basic notifications, heart rate, step tracking. Mid-range ($200-$400): GPS, SpO2, sleep stages, NFC payments. Premium ($400-$800+): ECG, advanced materials (titanium, sapphire), cellular connectivity, fall detection. Consider whether cellular connectivity is worth the ongoing carrier cost — most users rarely need it.

## Sleep Tracking Accuracy
Sleep tracking combines motion data, heart rate, and heart rate variability to estimate sleep stages such as light, deep, and REM sleep. Consumer devices are reasonably accurate at detecting total sleep time but less reliable at distinguishing individual stages. Comfort matters: a bulky watch can disturb sleep, so some users prefer a lighter band or a dedicated ring for overnight tracking. Look for features like sleep scores, bedtime reminders, and smart alarms that wake you during a light sleep phase.

## GPS and Navigation
Built-in GPS lets you track runs, rides, and hikes without carrying a phone. Dual-frequency (multi-band) GNSS significantly improves accuracy in cities with tall buildings and under dense tree cover. Outdoor-focused models add offline maps, turn-by-turn navigation, breadcrumb trails, and back-to-start routing. Keep in mind that continuous GPS is the single biggest drain on battery, so check how many hours of GPS tracking a watch supports, not just its standby battery life.

## Fitness and Training Features
Beyond step counts, modern smartwatches estimate VO2 max, training load, recovery time, and readiness scores. Running-focused watches provide pace guidance, interval workouts, running dynamics, and race predictions. Cyclists should look for power meter and sensor support over Bluetooth or ANT+. Swimmers need pool and open-water modes with stroke detection. If you train seriously, evaluate the quality of the companion app and its ability to export data to platforms like Strava or TrainingPeaks.

## Notifications and Smart Features
The core smartwatch experience is glanceable notifications: messages, calendar alerts, and calls on your wrist. Check whether you can reply to messages with quick replies, voice dictation, or a keyboard, as this varies by ecosystem and phone platform. Third-party app availability also differs widely: Apple Watch and Wear OS have large app stores, while fitness brands focus on a smaller set of curated apps. Music storage and streaming support are useful for running without a phone.

## Contactless Payments
NFC payments let you pay with your watch at supported terminals, which is convenient during workouts or when your hands are full. Apple Pay, Google Wallet, Samsung Wallet, Garmin Pay, and Fitbit Pay are the main options, but bank support varies by country and card issuer. Before buying, verify that your bank works with the payment system on the watch you are considering. Some watches also support transit cards and digital car keys in select regions.

## Safety Features
Fall detection, emergency SOS, and incident detection can automatically contact emergency services or chosen contacts if you are injured. Cellular models can do this without a nearby phone, which is valuable for solo runners, hikers, and older adults. Some outdoor watches support satellite messaging for areas without cell coverage. Live location sharing lets family members follow your activity in real time. These features often require initial setup, so configure them on day one.

## Bands, Sizing, and Comfort
Case size affects comfort, battery capacity, and screen readability. Smaller wrists usually suit 40-42mm cases, while larger wrists can wear 44-47mm cases comfortably. Quick-release bands make it easy to swap a silicone sport band for leather or metal for the office. Breathable nylon or fabric bands are more comfortable for all-day and overnight wear. Accurate heart rate readings depend on a snug fit just above the wrist bone, especially during intense exercise.

## Software Support and Longevity
Smartwatch lifespan is often limited by software support rather than hardware. Apple typically supports watches with new watchOS releases for several years, and major Wear OS manufacturers now promise multiple years of updates. Fitness-focused brands tend to keep adding features to older devices through firmware updates. Battery capacity degrades over time, so check whether the manufacturer offers battery service. A watch with long software support and a serviceable battery usually delivers the best long-term value.
""",
    ),
    (
        "buying-guide-portable-charger",
        "Portable Charger & Power Bank Buying Guide",
        """
# Portable Charger & Power Bank Buying Guide

## Capacity: How Much Do You Need?
Capacity is measured in milliamp-hours (mAh). A 10,000 mAh power bank can fully charge a typical phone 2-3 times. 20,000 mAh gives 4-6 charges but is heavier and bulkier. For a weekend trip, 10,000 mAh is usually enough. For longer travel or charging multiple devices, consider 20,000-30,000 mAh. Remember that actual usable capacity is about 65-70% of the rated capacity due to voltage conversion losses.

## Charging Speed: Watts and Protocols
Charging speed is measured in watts (W). Standard USB charging delivers 5W (slow). Quick Charge 3.0 delivers up to 18W. USB Power Delivery (PD) can deliver 18-100W, enabling fast charging of phones, tablets, and even laptops. Look for PD 3.0 or later for the best compatibility. A 30W PD charger can charge a phone to 50% in 30 minutes. 65W or higher can charge a laptop.

## Ports and Compatibility
USB-C is now the standard for modern devices. Look for at least one USB-C PD port and one USB-A port for legacy devices. Some power banks support passthrough charging (charging the bank and a device simultaneously). Multi-device chargers with 2-4 ports are ideal for travel. Check cable support: some chargers include a built-in USB-C cable, others require you to bring your own.

## Battery Chemistry and Safety
Most power banks use lithium-ion (Li-ion) or lithium-polymer (Li-Po) cells. Li-Po is lighter and more flexible in shape but slightly less energy-dense. Look for safety certifications: UL, CE, and FCC. Quality chargers include overcharge protection, temperature monitoring, and short-circuit prevention. Avoid no-name brands — battery fires are rare but catastrophic. TSA allows power banks up to 100 Wh (roughly 27,000 mAh at 3.7V) in carry-on luggage only.

## Solar and Wireless Options
Solar power banks are useful for extended outdoor trips but charge very slowly (days of sunlight for a full charge). They are best as backup, not primary charging. Wireless charging (Qi) is convenient but slower than wired — typically 5-15W vs 30-65W wired. Some power banks combine a built-in wireless pad with USB-C PD ports for maximum flexibility.

## Price Tiers
Budget ($15-$30): 5,000-10,000 mAh, basic USB-A, slow charging. Mid-range ($30-$60): 10,000-20,000 mAh, USB-C PD 18-30W, multi-port. Premium ($60-$120+): 20,000+ mAh, 65W+ PD, passthrough charging, digital displays, ruggedized. For travel, prioritize weight-to-capacity ratio and PD charging speed.

## Real-World Capacity vs Rated Capacity
The rated mAh figure refers to the internal battery cells at 3.7V, not the energy delivered to your device at 5V or higher. Conversion losses and heat mean that a power bank typically delivers 60-70 percent of its rated capacity in practice. A 10,000 mAh power bank therefore provides roughly 6,000-7,000 mAh to a phone. Watt-hours (Wh) are a more useful measure for comparing banks and for checking airline limits, because they account for voltage.

## Air Travel Rules
Most airlines allow power banks only in carry-on luggage, never in checked bags. Banks under 100Wh (about 27,000 mAh at 3.7V) are allowed without approval. Banks between 100Wh and 160Wh usually require airline approval, and anything above 160Wh is generally prohibited. The capacity in Wh should be printed clearly on the casing; unmarked power banks may be confiscated at security. Some airlines also restrict using power banks during the flight, so check the carrier policy before travelling.

## Charging Laptops and Tablets
To charge a laptop, you need a power bank that supports USB Power Delivery at a wattage close to your laptop charger, typically 45W to 100W. A 65W bank can charge most ultrabooks at full speed, while larger performance laptops may need 100W or 140W with USB PD 3.1. Capacity matters too: 20,000 mAh roughly equals one full laptop charge for a 50-60Wh battery. Check that the included cable is rated for the required wattage, since many cables are limited to 60W.

## Passthrough Charging
Passthrough charging lets the power bank charge your devices while it is itself being recharged from the wall. This is convenient for travellers with a single wall outlet: plug the bank into the outlet and your phone into the bank overnight. Not all power banks support it, and some reduce output speed while passthrough is active. Frequent passthrough use can generate extra heat and slightly accelerate battery wear, so it is best used when needed rather than as a permanent setup.

## Displays and Smart Features
Many modern power banks include a digital display showing exact remaining percentage, input and output wattage, and estimated time to full. This is more useful than the traditional four LED indicator, especially when charging multiple devices. Some premium models connect to a phone app over Bluetooth to show per-port statistics and allow custom charging limits. A low-current trickle mode is helpful for charging earbuds and smartwatches, which can otherwise cause the bank to shut off prematurely.

## MagSafe and Magnetic Power Banks
Magnetic power banks snap onto the back of compatible phones and charge wirelessly without cables. They are convenient for quick top-ups on the go, but wireless charging is less efficient than wired charging, so you get fewer full charges per mAh and more heat. Capacities are typically 5,000-10,000 mAh to keep the bank slim. Look for models with a USB-C port that can also charge the phone with a cable at higher speed when efficiency matters more than convenience.

## Durability and Ruggedization
For outdoor use, look for power banks with an IP65 or higher rating, rubberized corners, and port covers that keep out dust and water. Rugged models are heavier, but they survive drops, rain, and cold weather better than slim aluminum designs. Lithium batteries lose capacity temporarily in freezing temperatures, so keep the bank in an inside pocket during winter activities. Built-in flashlights and carabiner loops are common extras on camping-oriented models.

## Storage and Battery Care
To maximize lifespan, store power banks at roughly 50 percent charge in a cool, dry place, and top them up every few months if they are not in use. Avoid leaving them in hot cars or direct sunlight, which accelerates degradation and can create safety risks. Most quality banks last 300-500 full charge cycles before capacity drops noticeably. If a power bank swells, becomes unusually hot, or smells, stop using it immediately and recycle it at an appropriate battery collection point.
""",
    ),
    (
        "buying-guide-mechanical-keyboard",
        "Mechanical Keyboard Buying Guide",
        """
# Mechanical Keyboard Buying Guide

## Switch Types: Linear, Tactile, and Clicky
Linear switches (Cherry MX Red, Gateron Yellow) provide smooth, consistent keystrokes with no tactile bump. They are preferred by gamers for fast, rapid presses. Tactile switches (Cherry MX Brown, Zealio V2) have a noticeable bump at actuation, giving feedback without a click. They suit typists who want confirmation without noise. Clicky switches (Cherry MX Blue, Kailh Box White) produce an audible click at actuation — satisfying for some, annoying for open-office neighbors.

## Form Factor and Layout
Full-size (104 keys) includes the numpad and is standard for desktop use. TKL (tenkeyless, 87 keys) removes the numpad for a more compact footprint. 75% and 65% layouts further reduce size by removing navigation clusters and some function keys. 60% keyboards eliminate all dedicated arrow keys and F-row, relying on layer-based Fn combinations. Choose based on desk space and whether you use the numpad regularly.

## Wireless vs Wired
Wired keyboards offer zero latency and no charging — essential for competitive gaming. Wireless (2.4 GHz dongle) offers near-zero latency with the convenience of cable-free desk. Bluetooth is convenient for multi-device switching but has higher latency and is not ideal for gaming. Some keyboards offer tri-mode connectivity (wired, 2.4 GHz, Bluetooth). Look for USB-C charging rather than micro-USB.

## Keycaps and Materials
ABS keycaps are standard on budget keyboards but develop a shiny surface over time. PBT keycaps are more durable, resistant to shine, and available in various textures. Double-shot PBT keycaps have legends molded as a separate layer, preventing wear-through. Keycap profile (OEM, Cherry, SA, XDA) affects typing feel and aesthetics. Aftermarket keycap sets let you customize the look and feel extensively.

## Hot-Swap PCBs
Hot-swappable keyboards let you change switches without soldering — just pull the old switch out and push a new one in. This is invaluable for trying different switches and extending keyboard life. Look for PCBs that support both 3-pin and 5-pin switches. Most hot-swap boards use standard MX-style switch sockets, giving you access to hundreds of switch options.

## Price Tiers
Budget ($50-$90): Pre-built, ABS keycaps, basic switches, wired. Mid-range ($90-$200): Hot-swap, PBT keycaps, wireless options, premium switches. Premium ($200-$500+): Custom builds, aluminum cases, high-end switches, gasket mounts. For your first mechanical keyboard, a hot-swap board in the $100-150 range offers the best balance of quality and flexibility.

## Mounting Styles and Typing Feel
The way the plate and PCB are mounted inside the case strongly affects typing feel and sound. Tray mount is the most common and affordable, but can feel stiff and uneven across the board. Gasket mount suspends the plate on soft gaskets, producing a softer, more consistent feel and a deeper sound. Top mount and leaf-spring designs offer other trade-offs between flex and firmness. If you type for many hours a day, a gasket-mounted board can noticeably reduce finger fatigue.

## Sound Dampening and Acoustics
Modern enthusiast keyboards often include several layers of dampening foam between the plate and PCB and at the bottom of the case. These layers remove hollow pinging and produce the deeper thocky or crisp clacky sounds popular in the community. Factory-lubricated switches and stabilizers further reduce scratchiness and rattle. If you work in a shared office, combine dampened boards with linear or silent switches. Sound tests on video are useful but vary depending on the microphone and desk surface.

## Stabilizers
Stabilizers keep larger keys such as the spacebar, Enter, Shift, and Backspace level when pressed off-center. Poorly tuned stabilizers rattle and feel mushy, and they are one of the most common complaints on budget keyboards. Screw-in PCB-mounted stabilizers are the most stable, while plate-mounted versions are easier to replace. Lubricating stabilizer wires and housings dramatically improves sound and feel, and many mid-range boards now ship with pre-lubed stabilizers.

## Polling Rate and Gaming Performance
Polling rate determines how often the keyboard reports to the computer. Standard keyboards poll at 1000Hz, meaning a 1ms reporting interval, while gaming models now offer 4000Hz or 8000Hz. Higher polling rates reduce input latency slightly but use more CPU and battery. Hall effect and magnetic switches allow adjustable actuation points and rapid trigger, which resets keys as soon as they start to rise. Competitive players benefit most; for typing, these features make little difference.

## Ergonomic Layouts
Split keyboards separate the left and right halves so your arms stay at shoulder width, reducing wrist strain. Tenting raises the inner edges to reduce forearm pronation, and columnar or ortholinear layouts align keys with natural finger movement. These designs require an adjustment period of a few weeks. A low-profile board or a wrist rest helps if a standard board feels too tall. If you experience pain while typing, an ergonomic layout combined with good desk posture is worth considering.

## Software and Programmability
Programmable keyboards let you remap keys, create layers, and record macros. Open-source firmware like QMK and VIA or VIAL allows changes through a web or desktop app without installing proprietary software, and settings are stored on the keyboard itself. Proprietary vendor software can be convenient but sometimes requires background services and an account. Layers are especially useful on compact layouts, giving you function keys, arrows, and media controls without extra physical keys.

## Connectivity Details for Wireless Boards
Wireless mechanical keyboards typically offer three modes: wired USB-C, a 2.4GHz dongle for low latency, and Bluetooth for multi-device pairing. Bluetooth is convenient for switching between a laptop, tablet, and phone, but it has higher latency and can be less stable. Battery life varies from a few weeks with RGB off to just a few days with full lighting. Check whether the dongle can be stored inside the keyboard and whether the board works fully while charging.

## Maintenance and Cleaning
Mechanical keyboards are easy to maintain compared to laptop keyboards. Remove keycaps with a keycap puller and clean underneath with compressed air or a soft brush every few months. Keycaps can be washed in warm soapy water and dried thoroughly before reinstalling. With a hot-swap board, a single faulty switch can be replaced in seconds. Avoid eating over the keyboard, and use a dust cover if the board sits unused for long periods to keep debris out of the switches.
""",
    ),
    (
        "playbook-customer-support-triage",
        "Customer Support Triage Playbook",
        """
# Customer Support Triage Playbook

## Step 1: Identify the Issue Category
When a customer contacts support, classify the issue into one of five categories: product defect, shipping or delivery, billing or refund, usage or setup, and feature request. This determines the escalation path. Use the customer's initial message to make a preliminary classification, then refine after gathering more information. If multiple categories apply, prioritize based on urgency: billing disputes and product defects take precedence over feature requests.

## Step 2: Gather Context from Memory
Before responding, search the customer's past interactions. Look for: previous orders, stated preferences (budget, brand loyalty, technical comfort), recurring issues, and open tickets. This context helps you personalize the response and avoid asking for information the customer has already provided. Use the search_memory tool with the customer's name or ID.

## Step 3: Product Search Strategy
For product-related questions, use hybrid search (vector + BM25) to find relevant products. Vector search excels for semantic queries like 'comfortable headphones for long flights'. Text search is better for exact product names or model numbers. If the customer mentions a specific feature (e.g., 'USB-C charging'), use text search to filter precisely. Run hybrid search when the query mixes intent with specific terms.

## Step 4: Recommendation Logic
When recommending products, apply the customer's preferences as filters: price range, minimum rating threshold (default 4.0+), category preferences, and brand exclusions. Present 3-5 options ranked by relevance. Include a brief rationale for each recommendation connecting it to the customer's stated needs. Avoid recommending products the customer has previously returned or complained about.

## Step 5: Escalation Criteria
Escalate to a specialist if: the issue involves a safety concern (battery, overheating), the customer requests a refund above $500, the customer has had three or more unresolved contacts about the same issue, or the issue requires technical knowledge beyond product search. Document the escalation reason in the ticket and notify the specialist team.

## Step 6: Closing and Follow-Up
After resolving the issue, summarize the outcome in two sentences, confirm the customer is satisfied, and create a memory entry recording what was resolved. If the issue required a product recommendation, note which products were suggested and whether the customer indicated interest. Set a follow-up reminder if the customer was unsure or wanted to think about it.

## Tone and Communication Guidelines
Use a friendly, concise, and professional tone. Acknowledge the customer's frustration early when there is a problem, and avoid blaming the customer or other teams. Prefer short paragraphs and plain language over technical jargon unless the customer uses technical terms first. Confirm understanding by restating the issue in one sentence before proposing a solution. Never promise outcomes that depend on another team, such as refund approvals, without stating that they are subject to review.

## Handling Product Defects
For suspected product defects, gather the order number, purchase date, product model, and a clear description of the symptom. Ask whether the issue appears consistently or intermittently and which troubleshooting steps the customer has already tried. Walk through basic checks such as firmware updates, resetting the device, and testing with a different cable or charger. If the product is within the warranty period and the defect is confirmed, offer a replacement or repair according to the warranty policy.

## Shipping and Delivery Issues
For delayed or missing deliveries, check the tracking status and the carrier estimate before responding. If the package is marked as delivered but the customer has not received it, ask them to check with neighbors and building reception, and wait 24 hours before opening a carrier investigation. Damaged packages should be documented with photos. Offer a reship or refund according to the shipping policy once the carrier confirms loss or damage, and record the outcome in the ticket.

## Billing and Refund Requests
Verify the charge in the order history before discussing refunds. Explain the refund timeline clearly: refunds usually appear on the original payment method within 5-10 business days depending on the bank. For duplicate charges, confirm both transactions and escalate to the billing team with transaction IDs. Refunds above the standard approval threshold require specialist review. Always confirm the refund amount and method in writing at the end of the conversation.

## Using Customer History Effectively
Before responding, review the customer's recent memories and tickets: past purchases, returns, preferences, and unresolved issues. Reference relevant history naturally, for example noting that they previously preferred over-ear headphones, rather than reciting the full record. Do not surface sensitive details unless they are needed to resolve the current issue. If the history reveals a recurring problem with the same product, treat it as a priority and consider escalation earlier than usual.

## Product Comparison Requests
When a customer asks to compare products, limit the comparison to the three or four attributes that matter most for their stated use case, such as battery life, comfort, and price for travel headphones. Present the comparison in a short structured format and finish with a clear recommendation and the reason for it. Use product data from search results rather than memory, and mention when information like stock availability may have changed since the last update.

## Quality Assurance and Ticket Documentation
Every ticket should include the issue category, a short summary, the actions taken, the outcome, and any follow-up commitments. Use consistent tags so that recurring issues can be identified in weekly reports. Avoid copying entire conversations into the ticket; focus on the facts another agent would need to continue the case. Tickets are reviewed periodically for accuracy, tone, and policy compliance, and good documentation reduces repeat contacts.

## Measuring Success
Support performance is measured by first-contact resolution rate, customer satisfaction scores, average handling time, and the rate of repeat contacts within seven days. Recommendation quality is tracked by whether customers click on or purchase suggested products. Focus on resolving the issue completely rather than closing tickets quickly, because unresolved issues lead to repeat contacts and lower satisfaction. Share recurring product problems with the product team through the weekly feedback channel.
""",
    ),
]

# ── Upsert all documents into Lakebase ─────────────────────────────────
with connect_postgres() as _conn:
    with _conn.cursor() as _cur:
        for _doc_id, _title, _content in _AGENT_DOCUMENTS:
            _cur.execute(
                f"INSERT INTO {DOC_TABLE} (doc_id, title, content) "
                f"VALUES (%s, %s, %s) "
                f"ON CONFLICT (doc_id) DO UPDATE SET "
                f"title = EXCLUDED.title, content = EXCLUDED.content, updated_at = now()",
                (_doc_id, _title, _content.strip()),
            )

_row_count = int(fetch_pg_df(f"SELECT count(*) AS cnt FROM {DOC_TABLE}", dbname=DATABASE_NAME).iloc[0]["cnt"])
print(f"Lakebase table: {DOC_TABLE} ({_row_count} document(s))")
display(fetch_pg_df(f"SELECT doc_id, title, length(content) AS content_len, updated_at FROM {DOC_TABLE} ORDER BY title", dbname=DATABASE_NAME))

# COMMAND ----------

# DBTITLE 1,Products
# MAGIC %md
# MAGIC ## Products
# MAGIC Load real Amazon Electronics products from HuggingFace, generate embeddings, and create the Lakebase table with vector + BM25 search indexes.

# COMMAND ----------

# DBTITLE 1,Load Amazon Electronics products
import re
from huggingface_hub import hf_hub_download

# ── Download real Amazon Electronics product metadata from HuggingFace ──
print("Downloading Amazon Electronics metadata from HuggingFace...")
local_path = hf_hub_download(
    repo_id="McAuley-Lab/Amazon-Reviews-2023",
    filename="raw_meta_Electronics/full-00000-of-00010.parquet",
    repo_type="dataset",
)
raw = pd.read_parquet(local_path)
print(f"Raw parquet: {len(raw):,} rows, columns: {list(raw.columns)}")

# ── Clean and build products_df ──
def _clean_list(val):
    """Convert list/array columns to a clean joined string."""
    if val is None:
        return ""
    if isinstance(val, list):
        return "; ".join(str(v).strip() for v in val if str(v).strip())
    s = str(val).strip()
    s = re.sub(r"^\[|\]$", "", s)  # strip outer brackets
    s = re.sub(r"'", "", s)         # strip quotes
    return s.strip()

def _clean_price(val):
    """Extract numeric price from string like '$29.99' or range like '$10 - $20'."""
    if val is None:
        return None
    s = str(val).strip()
    nums = re.findall(r"[\d]+\.?\d*", s)
    if nums:
        return float(nums[0])
    return None

# Filter: must have a title, title length >= 10
df = raw[raw["title"].notna() & (raw["title"].str.len() >= 10)].copy()

# Drop exact duplicate titles, shuffle, take first MAX_PRODUCTS
df = df.drop_duplicates(subset="title").sample(frac=1, random_state=42).head(MAX_PRODUCTS).reset_index(drop=True)

# Build clean columns
df["clean_desc"] = df["description"].apply(_clean_list)
df["clean_feat"] = df["features"].apply(_clean_list)
df["price_numeric"] = df["price"].apply(_clean_price)
df["rating_numeric"] = pd.to_numeric(df["average_rating"], errors="coerce")

# Build the search body: title + description excerpt + features excerpt
def _build_body(row):
    parts = [row["title"]]
    if row["clean_desc"]:
        parts.append(row["clean_desc"][:300])
    if row["clean_feat"]:
        parts.append(row["clean_feat"][:200])
    return ". ".join(parts)

df["body"] = df.apply(_build_body, axis=1)

# Assemble final products_df
products_df = pd.DataFrame({
    "product_id": range(1, len(df) + 1),
    "title": df["title"].values,
    "body": df["body"].values,
    "root_category": df["main_category"].fillna("Electronics").values,
    "rating": df["rating_numeric"].fillna(0).astype(str).values,
    "final_price": df["price_numeric"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A").values,
    "price_numeric": df["price_numeric"].fillna(0).values,
    "rating_numeric": df["rating_numeric"].fillna(0).values,
})

print(f"\nLoaded {len(products_df):,} real Amazon Electronics products")
print(f"Categories: {products_df['root_category'].nunique()}")
print(f"Price range: ${products_df['price_numeric'][products_df['price_numeric'] > 0].min():.2f} – ${products_df['price_numeric'].max():.2f}")
print(f"Avg rating: {products_df['rating_numeric'][products_df['rating_numeric'] > 0].mean():.2f}")
print(f"Avg body length: {products_df['body'].str.len().mean():.0f} chars")
display(products_df[["product_id", "title", "root_category", "rating_numeric", "price_numeric"]].head(10))

# COMMAND ----------

# DBTITLE 1,Generate embeddings
import json
import time as _time

# Skip if products already exist in Lakebase with embeddings
try:
    _existing = fetch_pg_df(f"SELECT count(*) AS cnt FROM {PG_SCHEMA}.products", dbname=DATABASE_NAME)
    _existing_count = int(_existing.iloc[0]["cnt"])
except Exception:
    _existing_count = 0


def _embed_batch_rest(texts, model=EMBEDDING_MODEL):
    """Embed a list of texts via direct REST call."""
    resp = session.post(
        f"{workspace_host}/serving-endpoints/{model}/invocations",
        json={"input": texts},
        timeout=120,
    )
    resp.raise_for_status()
    return [item["embedding"] for item in resp.json()["data"]]


if _existing_count >= MAX_PRODUCTS:
    print(f"\u2713 Products table already has {_existing_count} rows — skipping embedding generation.")
    embedding_records = []
else:
    BATCH_SIZE = 50
    embedding_records = []
    _t0 = _time.time()

    for start in range(0, len(products_df), BATCH_SIZE):
        batch = products_df.iloc[start:start + BATCH_SIZE]
        texts = batch["body"].tolist()

        emb_list = _embed_batch_rest(texts)

        for idx, (_, row) in enumerate(batch.iterrows()):
            embedding_records.append({
                "product_id": int(row["product_id"]) if row["product_id"] else 0,
                "title": row["title"],
                "body": row["body"],
                "root_category": row["root_category"] or "Unknown",
                "rating": float(row["rating_numeric"]) if row["rating_numeric"] else None,
                "price": float(row["price_numeric"]) if row["price_numeric"] else None,
                "embedding": [float(v) for v in emb_list[idx]],
            })

        done = min(start + BATCH_SIZE, len(products_df))
        elapsed = _time.time() - _t0
        rate = done / elapsed if elapsed > 0 else 0
        eta = (len(products_df) - done) / rate if rate > 0 else 0
        print(f"Embedded {done}/{len(products_df)}  ({rate:.0f}/s, ETA {eta:.0f}s)")

    print(f"\nTotal embedding records: {len(embedding_records)}  ({_time.time() - _t0:.1f}s)")

# COMMAND ----------

# DBTITLE 1,Create Lakebase products table and indexes
# Skip table creation if it already has the expected row count
try:
    _tbl_count = int(fetch_pg_df(f"SELECT count(*) AS cnt FROM {PG_SCHEMA}.products", dbname=DATABASE_NAME).iloc[0]["cnt"])
except Exception:
    _tbl_count = 0

if _tbl_count >= MAX_PRODUCTS:
    print(f"\u2713 Products table already has {_tbl_count} rows \u2014 skipping table creation.")
else:
    if not embedding_records:
        raise RuntimeError(
            "No embedding_records in memory and table is missing/empty. "
            "Run the 'Generate embeddings' cell first."
        )
    with connect_postgres(DATABASE_NAME) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_vector CASCADE;")
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_text;")

            cur.execute(pg_sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(pg_sql.Identifier(PG_SCHEMA)))
            cur.execute(pg_sql.SQL("DROP TABLE IF EXISTS {}.products").format(pg_sql.Identifier(PG_SCHEMA)))
            cur.execute(f"""
                CREATE TABLE {PG_SCHEMA}.products (
                    id SERIAL PRIMARY KEY,
                    product_id BIGINT,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    root_category TEXT,
                    rating NUMERIC(3,1),
                    price NUMERIC(10,2),
                    embedding vector(1024),
                    body_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', body)) STORED
                )
            """)

            for rec in embedding_records:
                emb_literal = "[" + ",".join(f"{v:.12f}" for v in rec["embedding"]) + "]"
                cur.execute(
                    f"""INSERT INTO {PG_SCHEMA}.products (product_id, title, body, root_category, rating, price, embedding)
                       VALUES (%s, %s, %s, %s, %s, %s, %s::vector)""",
                    (rec["product_id"], rec["title"], rec["body"],
                     rec["root_category"], rec["rating"], rec["price"], emb_literal)
                )

            conn.commit()

            cur.execute(f"CREATE INDEX IF NOT EXISTS products_embedding_ann_idx ON {PG_SCHEMA}.products USING lakebase_ann(embedding vector_cosine_ops)")
            cur.execute(f"CREATE INDEX IF NOT EXISTS products_body_bm25_idx ON {PG_SCHEMA}.products USING lakebase_bm25(body_tsv)")
            cur.execute(f"CREATE INDEX IF NOT EXISTS products_category_idx ON {PG_SCHEMA}.products (root_category)")
            cur.execute(f"CREATE INDEX IF NOT EXISTS products_rating_idx ON {PG_SCHEMA}.products (rating)")
            cur.execute(f"CREATE INDEX IF NOT EXISTS products_price_idx ON {PG_SCHEMA}.products (price)")
            conn.commit()

count = fetch_pg_df(f"SELECT count(*) as cnt FROM {PG_SCHEMA}.products", dbname=DATABASE_NAME).iloc[0]["cnt"]
print(f"Products in Lakebase: {count}")

cats = fetch_pg_df(f"SELECT DISTINCT root_category FROM {PG_SCHEMA}.products ORDER BY root_category", dbname=DATABASE_NAME)
print(f"Categories indexed: {len(cats)}")
for c in cats["root_category"].tolist():
    print(f"  {c}")

lakebase_search_ready = True

# COMMAND ----------

# DBTITLE 1,Agent Memory Table
# MAGIC %md
# MAGIC ## Agent Memory Table
# MAGIC
# MAGIC The support agent in Demo_01 uses a `agent_memory` table in Lakebase to store synthetic past conversations with a customer. Each memory is embedded with the same embedding model used for search, enabling semantic `search_memory` tool calls from the agent.

# COMMAND ----------

# DBTITLE 1,Create agent_memory table in Lakebase
# ── Long-term agent memory: synthetic past conversations with one customer ──
# This table is used by the support agent in Demo_01 for search_memory tool calls.
MEMORY_TABLE = f"{PG_SCHEMA}.agent_memory"
CUSTOMER_NAME = ""

# (kind, occurred_on, memory)
_MEMORIES = [
    ("preference", "2026-01-14", "the customer flies twice a month for work and wants headphones that block jet engine noise on long flights."),
    ("preference", "2026-01-14", "the customer refuses to spend more than about $300 on audio gear, but will stretch the budget for a TV."),
    ("preference", "2026-02-03", "the customer returned a pair of Bose over-ear headphones because the earcups clamped too tightly after two hours."),
    ("preference", "2026-02-03", "the customer prefers lightweight on-ear or in-ear designs over bulky over-ear headphones."),
    ("preference", "2026-02-20", "the customer is deep in the Samsung ecosystem: Galaxy S25 Ultra phone and Galaxy Watch 6."),
    ("preference", "2026-03-02", "the customer only wants USB-C charging now and complains about anything still shipping micro-USB."),
    ("preference", "2026-03-11", "the customer dislikes subscription add-ons and asks every time whether a device needs a monthly plan."),
    ("preference", "2026-03-18", "the customer rates battery life as the single most important spec for portable devices."),
    ("preference", "2026-04-05", "the customer wants products rated 4.3 stars or higher and reads the one-star reviews first."),
    ("preference", "2026-04-22", "the customer asked to avoid white or silver finishes; prefers matte black hardware."),
    ("preference", "2026-05-09", "the customer is a PlayStation gamer and has no interest in Xbox or PC gaming hardware."),
    ("preference", "2026-05-30", "the customer cares about free shipping more than fast shipping and will wait a week to avoid a fee."),
    ("past_order", "2025-11-21", "Order #10233: Sony 65-inch 4K OLED Smart TV, delivered November 2025, the customer rated it 5 stars."),
    ("past_order", "2025-12-02", "Order #10288: Nintendo Switch OLED bought as a holiday gift for the customer's nephew."),
    ("past_order", "2026-01-08", "Order #10341: JBL True Wireless Earbuds, $129.99, the customer still uses these at the gym."),
    ("past_order", "2026-01-30", "Order #10377: Bose Over-Ear Studio Headphones, $279.99, returned on 2026-02-03 for comfort reasons."),
    ("past_order", "2026-02-14", "Order #10402: Ninja Air Fryer, $149.99, the customer mentioned it replaced a broken toaster oven."),
    ("past_order", "2026-03-06", "Order #10455: Apple Watch Ultra 2 purchased for the customer's partner, not for the customer."),
    ("past_order", "2026-03-27", "Order #10488: Anker-style USB-C charging accessories and a Bluetooth car adapter for a rental car."),
    ("past_order", "2026-04-12", "Order #10532: PlayStation 5 Console Digital Edition, the customer's main gaming device."),
    ("past_order", "2026-04-29", "Order #10566: Philips Hue Smart Light Bulb Starter Kit for the living room."),
    ("past_order", "2026-05-16", "Order #10604: Garmin GPS Running Watch, returned because it duplicated the Galaxy Watch features."),
    ("past_order", "2026-06-03", "Order #10651: Dyson Cordless Vacuum, the customer praised it for dog hair on rugs."),
    ("past_order", "2026-07-19", "Order #10702: Nextbase Dash Cam with 7-inch display for a cross-country road trip."),
    ("support_ticket", "2026-02-05", "Ticket T-8841: return label issued for the Bose headphones; refund cleared in four days."),
    ("support_ticket", "2026-03-29", "Ticket T-9014: dash cam SD card not recognized, resolved by a firmware update, the customer was satisfied."),
    ("support_ticket", "2026-04-15", "Ticket T-9120: PS5 shipment delayed two days; the customer was offered a $20 credit and accepted."),
    ("support_ticket", "2026-05-02", "Ticket T-9188: Hue bridge would not pair with the Samsung phone; fixed by resetting the router."),
    ("support_ticket", "2026-05-18", "Ticket T-9241: Garmin watch return approved outside the normal window as a goodwill exception."),
    ("support_ticket", "2026-06-21", "Ticket T-9333: the customer asked whether the OLED TV firmware supports Dolby Atmos passthrough to a soundbar."),
    ("support_ticket", "2026-08-04", "Ticket T-9460: billing question about a duplicate charge on the vacuum order, refunded same day."),
    ("support_ticket", "2026-09-09", "Ticket T-9572: the customer reported the gym earbuds losing Bluetooth connection near treadmills."),
    ("intent", "2026-06-25", "the customer browsed Dolby Atmos soundbars three times but never purchased, hesitating on price."),
    ("intent", "2026-07-02", "the customer asked whether a soundbar needs an HDMI eARC port to work with the Sony OLED TV."),
    ("intent", "2026-07-30", "the customer compared mirrorless camera bodies for a trip to Patagonia in early 2027."),
    ("intent", "2026-08-14", "the customer looked at robot vacuums but worried they would get stuck on the apartment's thick rugs."),
    ("intent", "2026-08-28", "the customer asked about espresso machines under $400 that do not require pods."),
    ("intent", "2026-09-15", "the customer is shopping for noise cancelling headphones again, this time for an upcoming 11-hour flight."),
    ("intent", "2026-09-22", "the customer asked which tablets are best for reading technical PDFs on planes."),
    ("intent", "2026-09-28", "the customer mentioned wanting a second monitor for a small desk, ideally ultrawide."),
    ("context", "2026-01-05", "the customer lives in a one-bedroom Chicago apartment, so large appliances rarely fit."),
    ("context", "2026-01-05", "the customer has a golden retriever that sheds heavily, which drives cleaning purchases."),
    ("context", "2026-02-26", "the customer works as a field engineer and is away from home roughly ten days a month."),
    ("context", "2026-04-08", "the customer's apartment has no dedicated office, so the TV doubles as a work monitor."),
    ("context", "2026-06-10", "the customer shares the account with a partner who buys most of the kitchen gear."),
]

try:
    _mem_count = int(fetch_pg_df(f"SELECT count(*) AS cnt FROM {MEMORY_TABLE}").iloc[0]["cnt"])
except Exception:
    _mem_count = 0

if _mem_count >= len(_MEMORIES):
    print(f"\u2713 {MEMORY_TABLE} already has {_mem_count} rows \u2014 skipping memory build.")
else:
    # Embed every memory in one pass, mapping embeddings back by text (not row order)
    _mem_texts = [m[2] for m in _MEMORIES]
    _mem_sdf = spark.createDataFrame([(t,) for t in _mem_texts], ["text"])
    _mem_rows = _mem_sdf.selectExpr(
        "text", f"ai_query('{EMBEDDING_MODEL}', text) AS embedding"
    ).collect()
    _mem_emb = {r["text"]: [float(v) for v in r["embedding"]] for r in _mem_rows}
    print(f"Embedded {len(_mem_emb)} memories")

    with connect_postgres() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_vector CASCADE;")
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_text;")
            cur.execute(f"DROP TABLE IF EXISTS {MEMORY_TABLE}")
            cur.execute(f"""
                CREATE TABLE {MEMORY_TABLE} (
                    id SERIAL PRIMARY KEY,
                    kind TEXT NOT NULL,
                    occurred_on DATE,
                    memory TEXT NOT NULL,
                    embedding vector({EMBEDDING_DIM}),
                    memory_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', memory)) STORED
                )
            """)
            for kind, day, text in _MEMORIES:
                emb = _mem_emb[text]
                cur.execute(
                    f"INSERT INTO {MEMORY_TABLE} (kind, occurred_on, memory, embedding) "
                    f"VALUES (%s, %s, %s, %s::vector)",
                    (kind, day, text, "[" + ",".join(f"{v:.12f}" for v in emb) + "]"),
                )
            conn.commit()
            _idx = MEMORY_TABLE.replace(".", "_")
            cur.execute(f"CREATE INDEX IF NOT EXISTS {_idx}_embedding_ann_idx ON {MEMORY_TABLE} USING lakebase_ann(embedding vector_cosine_ops)")
            cur.execute(f"CREATE INDEX IF NOT EXISTS {_idx}_memory_bm25_idx ON {MEMORY_TABLE} USING lakebase_bm25(memory_tsv)")
            cur.execute(f"CREATE INDEX IF NOT EXISTS {_idx}_kind_idx ON {MEMORY_TABLE} (kind)")
            conn.commit()

_mem_summary = fetch_pg_df(
    f"SELECT kind, count(*) AS memories FROM {MEMORY_TABLE} GROUP BY kind ORDER BY 2 DESC"
)
print(f"Memories for {CUSTOMER_NAME}: {int(_mem_summary['memories'].sum())}")
display(_mem_summary)

# COMMAND ----------

# DBTITLE 1,Phase 1: Create UC schema
# ── Ensure UC schema exists ────────────────────────────────────────────
print(f"Ensuring UC schema {UC_CATALOG}.{UC_SCHEMA} exists...")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {UC_CATALOG}.{UC_SCHEMA}")
print(f"\u2713 Schema {UC_CATALOG}.{UC_SCHEMA} ready")

# COMMAND ----------

# DBTITLE 1,Verify setup
# Verify Postgres schema and agent_memory exist
_tables_ok = False
try:
    with connect_postgres() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
                (PG_SCHEMA,),
            )
            _tables = [r[0] for r in cur.fetchall()]
            print(f"\u2713 Lakebase schema '{PG_SCHEMA}' has {len(_tables)} table(s): {_tables}")
            _tables_ok = len(_tables) > 0
except Exception as e:
    print(f"\u26a0 Could not verify Lakebase schema: {e}")

# Verify UC schema
try:
    _uc_tables = spark.sql(f"SHOW TABLES IN {UC_CATALOG}.{UC_SCHEMA}").collect()
    print(f"\u2713 UC schema {UC_CATALOG}.{UC_SCHEMA} has {len(_uc_tables)} table(s)")
except Exception as e:
    print(f"\u26a0 UC schema check: {e}")

print("\n\u2713 Setup verification complete.")

# COMMAND ----------

# DBTITLE 1,Phase 1b: Start Lakebase CDF
# ── Start Lakebase CDF (Postgres → Delta change feed) ─────────────────
# CDF is configured at the schema level — ALL tables in the Postgres schema
# are included automatically. The CDF history table for agent_documents will be:
#   lb_agent_documents_history in {UC_CATALOG}.{UC_SCHEMA}

# Check if CDF is already configured
_cdf_exists = False
try:
    for _cfg in w.postgres.list_cdf_configs(parent=CDF_PARENT):
        if _cfg.postgres_schema == PG_SCHEMA:
            _cdf_exists = True
            print(f"✓ CDF already configured for schema '{PG_SCHEMA}'")
            print(f"  Config: {_cfg.name}")
            break
except Exception:
    pass

if not _cdf_exists:
    print(f"Starting CDF for Postgres schema '{PG_SCHEMA}'...")
    print(f"  Source:      {LAKEBASE_DATABASE}.{PG_SCHEMA}.* (all tables)")
    print(f"  Destination: {UC_CATALOG}.{UC_SCHEMA} (lb_<table>_history)")
    _op = w.postgres.create_cdf_config(
        parent=CDF_PARENT,
        cdf_config=CdfConfig(
            catalog=UC_CATALOG,
            schema=UC_SCHEMA,
            postgres_schema=PG_SCHEMA,
        ),
    )
    print(f"  ✓ CDF config created")

# ── Wait for the CDF history table to appear ──────────────────────────
print(f"\nWaiting for {CDF_HISTORY_TABLE} to appear...")
import time as _t
_t0 = _t.time()
while True:
    try:
        _cnt = spark.sql(f"SELECT count(*) AS cnt FROM {CDF_HISTORY_TABLE}").collect()[0]["cnt"]
        print(f"\n✓ CDF history table ready: {CDF_HISTORY_TABLE} ({_cnt} rows)")
        break
    except Exception:
        _elapsed = int(_t.time() - _t0)
        if _elapsed % 15 == 0:
            print(f"  [{_elapsed}s] waiting...")
        if _elapsed > 300:
            raise TimeoutError(f"CDF history table did not appear within 5 minutes")
        _t.sleep(5)

# COMMAND ----------

# DBTITLE 1,Phase 2: Lakeflow Spark Declarative Pipeline
# MAGIC %md
# MAGIC ## Phase 2: Lakeflow Spark Declarative Pipeline
# MAGIC
# MAGIC The chunking + embedding logic runs inside a Lakeflow Spark Declarative Pipeline (SDP) with two stages:
# MAGIC
# MAGIC **Stage 1 — APPLY CHANGES**: A streaming table (`agent_documents_current`) reads the Lakebase CDF history table (`lb_agent_documents_history`) and applies CDC processing to reconstruct the current state of each document. Deletes are handled; preimages are filtered out.
# MAGIC
# MAGIC **Stage 2 — Materialized View**: `document_chunks_embedded` reads from the current-state streaming table, chunks each document using `ai_prep_search` (~5K-character chunks), and embeds each chunk via `ai_query()` with 1024-dim vectors.
# MAGIC
# MAGIC **Why APPLY CHANGES + MV?** APPLY CHANGES efficiently maintains the current state of documents from the CDF change log (handling inserts, updates, and deletes). The MV then handles the compute-heavy chunking and embedding. This pattern correctly handles documents that can be updated or deleted \u2014 on each refresh it recomputes results to reflect current source state. With **incremental refresh** on serverless, only changed documents are re-chunked and re-embedded.
# MAGIC
# MAGIC The pipeline supports two modes — no external scheduler is required in either case:
# MAGIC
# MAGIC | Mode | How it works | Best for |
# MAGIC | --- | --- | --- |
# MAGIC | **Continuous** | Pipeline stays running, processes changes as they arrive (seconds\~minutes latency). No scheduling needed. | Near-real-time search freshness |
# MAGIC | **Triggered** | Pipeline runs on demand or via a Lakeflow Job cron, processes all pending changes, then stops. Cheaper at rest. | Hourly/daily freshness is sufficient |

# COMMAND ----------

# DBTITLE 1,Phase 2a: Create Pipeline Notebook & SDP Pipeline
import base64
from databricks.sdk.service.workspace import ImportFormat, Language

# ── Pipeline notebook (SQL MV definition) ──────────────────────────────
PIPELINE_NB_PATH = f"{DEMO_DIR}/pipeline_document_chunks"   # generated next to this notebook
_mv_source = f"""-- Databricks notebook source
-- Stage 1: Reconstruct current document state from Lakebase CDF
CREATE OR REFRESH STREAMING TABLE agent_documents_current
COMMENT 'Current state of agent documents, reconstructed from Lakebase CDF'

-- COMMAND ----------

APPLY CHANGES INTO LIVE.agent_documents_current
FROM STREAM({CDF_HISTORY_TABLE})
KEYS (doc_id)
SEQUENCE BY _sort_by
COLUMNS doc_id, title, content, updated_at, _pg_change_type
STORED AS SCD TYPE 1
APPLY AS DELETE WHEN _pg_change_type = 'delete'

-- COMMAND ----------

-- Stage 2: Chunk and embed documents for hybrid search
-- ai_prep_search splits documents into ~5K-character chunks (docs shorter than that
-- stay a single chunk). chunk_to_embed is the context-enriched text used for embedding.
CREATE OR REFRESH MATERIALIZED VIEW document_chunks_embedded
COMMENT 'Chunked (ai_prep_search) and embedded document fragments for hybrid search'
AS
WITH source_docs AS (
    SELECT doc_id, title, content
    FROM LIVE.agent_documents_current
    WHERE content IS NOT NULL AND length(content) > 0
),
prepped AS (
    SELECT
        doc_id,
        title,
        ai_prep_search(content) AS result
    FROM source_docs
)
SELECT
    chunk.value:chunk_id::STRING AS chunk_id,
    doc_id,
    chunk.value:chunk_position::INT AS chunk_idx,
    title,
    chunk.value:chunk_to_retrieve::STRING AS chunk_text,
    ai_query(
        '{EMBEDDING_MODEL}',
        chunk.value:chunk_to_embed::STRING,
        returnType => 'ARRAY<DOUBLE>'
    ) AS embedding
FROM prepped, LATERAL variant_explode(result:document.contents) AS chunk
"""

w.workspace.import_(
    path=PIPELINE_NB_PATH,
    content=base64.b64encode(_mv_source.encode()).decode(),
    format=ImportFormat.SOURCE,
    language=Language.SQL,
    overwrite=True,
)
print(f"\u2713 Pipeline notebook created: {PIPELINE_NB_PATH}")

# ── Create or reuse SDP pipeline ──────────────────────────────────────
from databricks.sdk.service.pipelines import PipelineLibrary, NotebookLibrary

PIPELINE_ID = None
try:
    for _p in w.pipelines.list_pipelines(filter=f"name LIKE '{PIPELINE_NAME}'"):
        if _p.name == PIPELINE_NAME:
            PIPELINE_ID = _p.pipeline_id
            print(f"\u2713 Pipeline already exists: {PIPELINE_ID}")
            break
except Exception:
    pass

if not PIPELINE_ID:
    _created = w.pipelines.create(
        name=PIPELINE_NAME,
        catalog=UC_CATALOG,
        target=UC_SCHEMA,
        libraries=[PipelineLibrary(notebook=NotebookLibrary(path=PIPELINE_NB_PATH))],
        serverless=True,
        continuous=False,
        channel="CURRENT",
    )
    PIPELINE_ID = _created.pipeline_id
    print(f"\u2713 Created pipeline: {PIPELINE_ID}")

print(f"  Name:   {PIPELINE_NAME}")
print(f"  Target: {UC_CATALOG}.{UC_SCHEMA}")
print(f"  Mode:   Triggered (serverless)")

# COMMAND ----------

# DBTITLE 1,Phase 2b: Run Pipeline & Wait
# ── Verify source data exists ──────────────────────────────────────────
try:
    _dcnt = spark.sql(
        f"SELECT count(*) AS cnt FROM {CDF_HISTORY_TABLE}"
    ).collect()[0]["cnt"]
    print(f"Source: {_dcnt} row(s) in CDF history table {CDF_HISTORY_TABLE}")
except Exception:
    raise RuntimeError(
        f"CDF history table {CDF_HISTORY_TABLE} not found.\n"
        f"Start Lakebase CDF first (Phase 1b), then re-run."
    )

# ── Trigger pipeline update ────────────────────────────────────────────
print(f"\nStarting pipeline update ({PIPELINE_ID})...")
w.pipelines.start_update(pipeline_id=PIPELINE_ID)

# ── Wait for completion ────────────────────────────────────────────────
_t0 = time.time()
while True:
    _p = w.pipelines.get(pipeline_id=PIPELINE_ID)
    _ps = _p.state.value if _p.state else "UNKNOWN"
    _elapsed = int(time.time() - _t0)

    if _ps == "IDLE":
        # Pipeline returned to idle — check latest update result
        if _p.latest_updates:
            _us = _p.latest_updates[0].state.value if _p.latest_updates[0].state else "UNKNOWN"
            if _us == "COMPLETED":
                print(f"\n\u2713 Pipeline update completed ({_elapsed}s)")
                break
            elif _us in ("FAILED", "CANCELED"):
                raise RuntimeError(
                    f"Pipeline update {_us} — check the pipeline UI for details."
                )
        break

    if _elapsed % 15 == 0:
        print(f"  [{_elapsed}s] {_ps}...")

    if _elapsed > 600:
        raise TimeoutError("Pipeline did not complete within 10 minutes.")
    time.sleep(5)

# ── Verify output ──────────────────────────────────────────────────────
_ccnt = spark.sql(f"SELECT count(*) AS cnt FROM {CHUNKS_TABLE}").collect()[0]["cnt"]
print(f"\u2713 {_ccnt} embedded chunks in {CHUNKS_TABLE}")
display(spark.sql(f"""
    SELECT chunk_id, doc_id, chunk_idx, title,
           left(chunk_text, 80) AS preview, size(embedding) AS emb_dim
    FROM {CHUNKS_TABLE} ORDER BY doc_id, chunk_idx
"""))

# COMMAND ----------

# DBTITLE 1,Phase 2c: Create Triggered Job
JOB_NAME = f"{PIPELINE_NAME}-trigger"

# ── Check if job already exists ────────────────────────────────────────
JOB_ID = None
try:
    for _j in w.jobs.list(name=JOB_NAME):
        if _j.settings and _j.settings.name == JOB_NAME:
            JOB_ID = _j.job_id
            break
except Exception:
    pass

if JOB_ID:
    print(f"\u2713 Job already exists: {JOB_ID}")
else:
    _resp = session.post(
        f"{workspace_host}/api/2.1/jobs/create",
        json={
            "name": JOB_NAME,
            "tasks": [{
                "task_key": "update_chunks",
                "pipeline_task": {"pipeline_id": PIPELINE_ID},
            }],
            "trigger": {
                "table_update": {
                    "table_names": [CDF_HISTORY_TABLE],
                    "min_time_between_triggers_seconds": 60,
                    "wait_after_last_change_seconds": 61,
                },
            },
        },
        timeout=30,
    )
    _resp.raise_for_status()
    JOB_ID = _resp.json()["job_id"]
    print(f"\u2713 Created job: {JOB_ID}")

print(f"  Name:    {JOB_NAME}")
print(f"  Trigger: table update on {CDF_HISTORY_TABLE}")
print(f"  Action:  run pipeline {PIPELINE_ID}")

# COMMAND ----------

# DBTITLE 1,Phase 3: Create Synced Table to Lakebase (Snapshot mode)
# ── Phase 3: Create a Synced Table in Snapshot mode (UC MV → Lakebase Postgres)
# Snapshot mode does a full copy each sync — no CDF required.
# This avoids MATERIALIZED_VIEW_CDF_REQUIRES_EXTERNAL_METADATA when the
# source is a Materialized View (MVs don't expose CDF without external metadata).
from databricks.sdk.service.postgres import (
    SyncedTable,
    SyncedTableSyncedTableSpec,
    SyncedTableSyncedTableSpecTypeOverride,
    SyncedTableSyncedTableSpecPgSpecificType,
    SyncedTableSyncedTableSpecSyncedTableSchedulingPolicy,
)

# Verify pipeline output exists
_source_exists = False
try:
    _src_cnt = spark.sql(f"SELECT count(*) AS cnt FROM {CHUNKS_TABLE}").collect()[0]["cnt"]
    _source_exists = _src_cnt > 0
    print(f"\u2713 Pipeline output: {_src_cnt} chunks in {CHUNKS_TABLE}")
except Exception:
    print(f"\u26a0 Pipeline output table not found: {CHUNKS_TABLE}")
    print(f"  Run Phase 2b first, then re-run this cell.")

if _source_exists:
    # Clean up any stale synced table from a previous run
    try:
        w.postgres.delete_synced_table(name=f"synced_tables/{SYNCED_TABLE_ID}")
        print("  Cleaned up stale synced table definition")
        import time as _st; _st.sleep(5)
    except Exception:
        pass

    # Also drop any leftover Postgres table from manual runs
    _pg_table = SYNCED_TABLE_ID.split(".")[-1]  # synced_document_chunks
    try:
        with connect_postgres() as conn:
            with conn.cursor() as cur:
                cur.execute(pg_sql.SQL("DROP TABLE IF EXISTS {}.{} CASCADE").format(
                    pg_sql.Identifier(PG_SCHEMA), pg_sql.Identifier(_pg_table)
                ))
    except Exception:
        pass

    # Create the Synced Table via SDK
    print(f"\nCreating Synced Table: {SYNCED_TABLE_ID}")
    print(f"  Source: {CHUNKS_TABLE}")
    print(f"  Target: {LAKEBASE_DATABASE}.{PG_SCHEMA}.{_pg_table}")
    print(f"  Type override: embedding → vector({EMBEDDING_DIM})")
    print(f"  Mode: SNAPSHOT (full copy, no CDF required)")

    _op = w.postgres.create_synced_table(
        synced_table_id=SYNCED_TABLE_ID,
        synced_table=SyncedTable(
            spec=SyncedTableSyncedTableSpec(
                source_table_full_name=CHUNKS_TABLE,
                branch=BRANCH_PATH,
                postgres_database=LAKEBASE_DATABASE,
                primary_key_columns=["chunk_id"],
                scheduling_policy=SyncedTableSyncedTableSpecSyncedTableSchedulingPolicy.SNAPSHOT,
                type_overrides=[
                    SyncedTableSyncedTableSpecTypeOverride(
                        column_name="embedding",
                        pg_type=SyncedTableSyncedTableSpecPgSpecificType.PG_SPECIFIC_TYPE_VECTOR,
                        size=EMBEDDING_DIM,
                    ),
                ],
                create_database_objects_if_missing=True,
            ),
        ),
    )

    # Wait for the sync to complete
    print("\nWaiting for initial sync...")
    import time as _st
    _t0 = _st.time()
    while True:
        _info = w.postgres.get_synced_table(name=f"synced_tables/{SYNCED_TABLE_ID}")
        _state = _info.status.detailed_state.value if _info.status and _info.status.detailed_state else "UNKNOWN"
        _elapsed = int(_st.time() - _t0)

        if "ONLINE" in _state:
            print(f"\n\u2713 Synced Table online ({_elapsed}s)")
            if _info.status and _info.status.pipeline_id:
                print(f"  Sync pipeline: {_info.status.pipeline_id}")
            break
        if "FAILED" in _state or "ERROR" in _state:
            _msg = _info.status.message if _info.status else "unknown"
            raise RuntimeError(f"Synced Table failed: {_state} — {_msg}")
        if _elapsed % 15 == 0:
            print(f"  [{_elapsed}s] {_state}...")
        if _elapsed > 300:
            raise TimeoutError("Synced Table did not come online within 5 minutes.")
        _st.sleep(5)

    # Verify data in Lakebase
    _lb_cnt = fetch_pg_df(
        f"SELECT count(*) AS cnt FROM {PG_SCHEMA}.{_pg_table}"
    )
    print(f"\u2713 {_lb_cnt['cnt'].iloc[0]} chunks in Lakebase ({PG_SCHEMA}.{_pg_table})")
    # ── Wire the sync into the triggered job ─────────────────────────────
    # Snapshot-mode synced tables only sync on creation; later syncs must be
    # triggered explicitly. Add a task that runs the synced table's pipeline
    # after the chunking pipeline. The synced table is recreated on each run
    # of this cell (new pipeline ID), so the job task is refreshed here too.
    SYNC_PIPELINE_ID = _info.status.pipeline_id
    _resp = session.post(
        f"{workspace_host}/api/2.1/jobs/update",
        json={
            "job_id": JOB_ID,
            "new_settings": {
                "tasks": [
                    {
                        "task_key": "update_chunks",
                        "pipeline_task": {"pipeline_id": PIPELINE_ID},
                    },
                    {
                        "task_key": "sync_to_lakebase",
                        "depends_on": [{"task_key": "update_chunks"}],
                        "pipeline_task": {"pipeline_id": SYNC_PIPELINE_ID},
                    },
                ],
            },
        },
        timeout=30,
    )
    _resp.raise_for_status()
    print(f"\u2713 Job {JOB_ID}: update_chunks \u2192 sync_to_lakebase (pipeline {SYNC_PIPELINE_ID})")


# COMMAND ----------

# DBTITLE 1,Phase 3: Create Lakebase search indexes
# Create search indexes on the synced Lakebase table
_pg_table = SYNCED_TABLE_ID.split(".")[-1]

_synced_pg_exists = False
try:
    _check = fetch_pg_df(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
        params=(PG_SCHEMA, _pg_table),
    )
    _synced_pg_exists = len(_check) > 0
except Exception:
    pass

if _synced_pg_exists:
    print(f"Creating search indexes on {_pg_table}...")
    with connect_postgres() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_vector CASCADE")
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_text")

            # ANN index for vector (semantic) search
            cur.execute(pg_sql.SQL("""
                CREATE INDEX IF NOT EXISTS {idx} ON {schema}.{tbl}
                USING lakebase_ann(embedding vector_cosine_ops)
            """).format(
                idx=pg_sql.Identifier(f"{_pg_table}_embedding_ann_idx"),
                schema=pg_sql.Identifier(PG_SCHEMA),
                tbl=pg_sql.Identifier(_pg_table),
            ))
            print("  \u2713 ANN index (vector cosine)")

            # BM25 index for text (keyword) search
            # Synced tables are owned by the sync SP so we can't ALTER to add a
            # tsvector column. Use an expression index instead.
            cur.execute(pg_sql.SQL("""
                CREATE INDEX IF NOT EXISTS {idx} ON {schema}.{tbl}
                USING lakebase_bm25((to_tsvector('english'::regconfig, chunk_text)))
            """).format(
                idx=pg_sql.Identifier(f"{_pg_table}_text_bm25_idx"),
                schema=pg_sql.Identifier(PG_SCHEMA),
                tbl=pg_sql.Identifier(_pg_table),
            ))
            print("  \u2713 BM25 index (text search — expression index)")

            # B-tree index for filtered search
            cur.execute(pg_sql.SQL("""
                CREATE INDEX IF NOT EXISTS {idx} ON {schema}.{tbl}(doc_id)
            """).format(
                idx=pg_sql.Identifier(f"{_pg_table}_doc_id_idx"),
                schema=pg_sql.Identifier(PG_SCHEMA),
                tbl=pg_sql.Identifier(_pg_table),
            ))
            print("  \u2713 B-tree index (doc_id)")

    print(f"\n\u2713 All indexes ready on {_pg_table}")
else:
    print(f"\u26a0 Synced table not yet in Lakebase ({_pg_table}).")
    print("  Run the Lakeflow Pipeline and wait for the Synced Table to sync, then re-run this cell.")

# COMMAND ----------

# DBTITLE 1,End-to-end verification
print("=" * 60)
print("Pipeline Infrastructure Status")
print("=" * 60)

# 1. Lakebase schema
try:
    with connect_postgres() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY 1",
                (PG_SCHEMA,),
            )
            _pg_tbls = [r[0] for r in cur.fetchall()]
    print(f"\n\u2713 Lakebase schema:     {PG_SCHEMA} has {len(_pg_tbls)} table(s): {_pg_tbls}")
except Exception as e:
    print(f"\n\u2717 Lakebase schema:     {e}")

# 2. Pipeline output
try:
    chunks_cnt = spark.sql(f"SELECT count(*) AS cnt FROM {CHUNKS_TABLE}").collect()[0]["cnt"]
    print(f"\u2713 Pipeline output:     {chunks_cnt} chunks in {CHUNKS_TABLE}")
except Exception:
    print(f"\u25cb Pipeline output:     {CHUNKS_TABLE} not yet created (run the pipeline)")

# 3. Synced table
try:
    st = w.postgres.get_synced_table(name=f"synced_tables/{SYNCED_TABLE_ID}")
    print(f"\u2713 Synced Table:        {st.name}")
except Exception:
    print(f"\u25cb Synced Table:        {SYNCED_TABLE_ID} not yet created")

# 4. Lakebase indexes
_pg_table = SYNCED_TABLE_ID.split(".")[-1]
try:
    _idx = fetch_pg_df(
        "SELECT indexname FROM pg_indexes WHERE schemaname = %s AND tablename = %s",
        params=(PG_SCHEMA, _pg_table),
    )
    if len(_idx) > 0:
        print(f"\u2713 Lakebase indexes:    {len(_idx)} on {_pg_table}")
        for _, row in _idx.iterrows():
            print(f"    {row['indexname']}")
    else:
        print(f"\u25cb Lakebase indexes:    none on {_pg_table}")
except Exception:
    print(f"\u25cb Lakebase indexes:    table not yet in Lakebase")

print("\n" + "=" * 60)
print("Next steps:")
print(f"  1. Create the Lakeflow Pipeline: '{PIPELINE_NAME}'")
print(f"  2. Run the pipeline to populate {CHUNKS_TABLE}")
print(f"  3. Re-run the Synced Table and Index cells above")
print("=" * 60)

# COMMAND ----------

# DBTITLE 1,Agent LLM & Widget Dependencies
# MAGIC %md
# MAGIC ## Agent LLM & Widget Dependencies
# MAGIC Import all widget classes, load product documents from Lakebase, probe embedding endpoints, and connect the agent LLM. Demo_01 uses `%run ./Setup_00` to inherit these variables and functions.

# COMMAND ----------

# DBTITLE 1,Build widget dependencies
import importlib.util
import json
import subprocess
import sys

# ── Install anywidget if needed ────────────────────────────────────────
if importlib.util.find_spec("anywidget") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anywidget"])

# ── Widget modules ──────────────────────────────────────────────────────
WIDGETS_PATH = f"/Workspace{DEMO_DIR}/widgets"   # widgets/ folder shipped with this repo
if WIDGETS_PATH not in sys.path:
    sys.path.insert(0, WIDGETS_PATH)

import importlib
import lakebase_search_widgets as _lsw_mod
importlib.reload(_lsw_mod)
from lakebase_search_widgets import HybridSearchWidget, TextSearchWidget, VectorSearchWidget, ProductSearchBarWidget

import support_agent_widget as _saw_mod
importlib.reload(_saw_mod)
from support_agent_widget import SupportAgentWidget, TOOL_SPECS

import agent_document_widget as _adw_mod
importlib.reload(_adw_mod)
from agent_document_widget import AgentDocumentWidget

import document_search_agent_widget as _dsaw_mod
importlib.reload(_dsaw_mod)
from document_search_agent_widget import DocumentSearchAgentWidget

# ── Load documents from Lakebase for widget use ─────────────────────────
_rows = fetch_pg_df(
    f"SELECT id, title, body, embedding::text FROM {PG_SCHEMA}.products ORDER BY id",
    dbname=DATABASE_NAME,
)
documents = []
for r in _rows.to_dict("records"):
    emb_str = r["embedding"].strip("[]")
    documents.append({
        "id": int(r["id"]),
        "title": r["title"],
        "body": r["body"],
        "embedding": [float(v) for v in emb_str.split(",")],
    })

# ── Probe embedding endpoints ───────────────────────────────────────────
_CANDIDATES = [
    "databricks-gte-large-en",
    "databricks-bge-large-en",
    "databricks-gte-qwen2-7b-instruct",
]
available_models = []
for _ep in _CANDIDATES:
    try:
        spark.sql("SELECT ai_query(:m, 'test') AS e", args={"m": _ep}).collect()
        available_models.append(_ep)
    except Exception:
        pass
if EMBEDDING_MODEL not in available_models:
    available_models.insert(0, EMBEDDING_MODEL)
available_models_json = json.dumps(available_models)

# ── Embedding function ──────────────────────────────────────────────────
def embed_fn(query_text: str, model: str) -> list:
    """Embed via direct REST call."""
    resp = session.post(
        f"{workspace_host}/serving-endpoints/{model}/invocations",
        json={"input": query_text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

print(f"Models: {available_models}")
print(f"Documents: {len(documents)}")
print(f"Widget classes loaded: VectorSearchWidget, HybridSearchWidget, ProductSearchBarWidget, SupportAgentWidget, AgentDocumentWidget, DocumentSearchAgentWidget")

# COMMAND ----------

# DBTITLE 1,Connect the agent LLM
# ── Agent LLM connection ────────────────────────────────────────────────
def chat_fn(messages, tools=None):
    """One tool-calling chat round trip. Auth comes from the notebook session."""
    payload = {"messages": messages, "max_tokens": 900}
    if tools:
        payload["tools"] = tools
    response = session.post(
        f"{workspace_host}/serving-endpoints/{LLM_ENDPOINT}/invocations",
        json=payload,
        timeout=180,
    )
    if response.status_code != 200:
        raise RuntimeError(f"LLM call failed ({response.status_code}): {response.text[:300]}")
    return response.json()["choices"][0]["message"]

_probe = chat_fn([{"role": "user", "content": "Reply with the single word: ready"}])
print(f"Agent LLM: {LLM_ENDPOINT} \u2192 {(_probe.get('content') or '').strip()[:40]}")
print(f"Tools exposed to the agent: {[t['function']['name'] for t in TOOL_SPECS]}")

# COMMAND ----------

# DBTITLE 1,Cleanup demo resources
cleanup_status = {
    "cleanup_requested": RUN_CLEANUP,
    "table_dropped": False,
    "database_dropped": False,
    "project_deleted": False,
}

if not RUN_CLEANUP:
    print("Cleanup is disabled. Set RUN_CLEANUP = True in the parameters cell and rerun this cell.")
else:
    try:
        with connect_postgres(DATABASE_NAME) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS products")
        cleanup_status["table_dropped"] = True
    except Exception as exc:
        cleanup_status["table_drop_error"] = str(exc)

    try:
        with connect_postgres("databricks_postgres") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                    (DATABASE_NAME,),
                )
                cur.execute(pg_sql.SQL("DROP DATABASE IF EXISTS {}").format(pg_sql.Identifier(DATABASE_NAME)))
        cleanup_status["database_dropped"] = True
    except Exception as exc:
        cleanup_status["database_drop_error"] = str(exc)

    try:
        api_request(
            "DELETE",
            f"/api/2.0/postgres/projects/{PROJECT_ID}",
            params={"purge": "true"},
            ok=(200, 202, 204),
        )
        cleanup_status["project_deleted"] = True
    except Exception as exc:
        cleanup_status["project_delete_error"] = str(exc)

    print("Cleanup attempted with purge=true.")

print(cleanup_status)