# Databricks notebook source
# MAGIC %md
# MAGIC # 🚀 Module 2 fallback — Deploy your agent (click-through)
# MAGIC ### The validated deploy sequence as runnable cells — just **Run All**
# MAGIC
# MAGIC Genie Code typically *runs this notebook* for you in Module 2. It's also the click-through
# MAGIC fallback: use it when you'd rather click than chat, a Genie deploy hiccuped, or the chat header
# MAGIC says **"memory: off"**. Re-running it is safe: it waits for any deployment already in flight,
# MAGIC preserves the Lakebase resource, and tracks the exact deployment created by this run.
# MAGIC
# MAGIC The five steps: **create** the app with its Lakebase memory resource → **wait** for compute →
# MAGIC **set up database access** for memory → **set the OBO scopes** → **deploy**, confirm memory,
# MAGIC and print your app URL.
# MAGIC
# MAGIC > ⏱️ A fresh deploy takes **5–10 minutes**, mostly waiting. While it runs, go meet your agent:
# MAGIC > open `agent/app.py` and find `build_agent()` (the guide walks you through it).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup — who you are, what we'll call the app
# MAGIC Same app-name derivation as `00_Start_Here`. No edits needed — just run.

# COMMAND ----------

import json
import re
import time

import requests

EMAIL = (spark.sql("SELECT current_user() AS u").collect()[0]["u"] or "").strip()
username = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", EMAIL.split("@")[0].lower())).strip("-")
if username and username[0].isdigit():
    username = "u-" + username
# Keep the TAIL when truncating — lab usernames share a long common prefix and differ in the
# trailing digits (same rule as 00_Start_Here; don't build a different name here).
APP_NAME = ("agent-apps-" + username[-19:].lstrip("-")).rstrip("-")
assert APP_NAME and len(APP_NAME) <= 30 and re.fullmatch(r"[a-z0-9-]+", APP_NAME), APP_NAME

TOKEN = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
HOST = "https://" + spark.conf.get("spark.databricks.workspaceUrl")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

SOURCE_CODE_PATH = f"/Workspace/Users/{EMAIL}/agent_apps_lab/agent"
LAKEBASE_PROJECT = "agent-apps-memory"
LAKEBASE_BRANCH = "production"
ROLES_PATH = f"/api/2.0/postgres/projects/{LAKEBASE_PROJECT}/branches/{LAKEBASE_BRANCH}/roles"
APP_PATH = f"/api/2.0/apps/{APP_NAME}"
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")

POSTGRES_RESOURCE = {
    "name": "postgres",
    "postgres": {
        "branch": f"projects/{LAKEBASE_PROJECT}/branches/{LAKEBASE_BRANCH}",
        "database": f"projects/{LAKEBASE_PROJECT}/branches/{LAKEBASE_BRANCH}/databases/databricks-postgres",
        "permission": "CAN_CONNECT_AND_CREATE",
    },
}


def api(method, path, body=None):
    """One REST call -> (status_code, parsed_json_or_text). Never raises on HTTP errors."""
    r = requests.request(method, HOST + path, headers=HEADERS, json=body, timeout=60)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"_raw": r.text}


def fail(step, status, body):
    raise RuntimeError(
        f"❌ {step} failed with HTTP {status}.\n"
        f"Response body:\n{json.dumps(body, indent=2)[:3000]}\n"
        f"Fix the cause and re-run this notebook — every step is safe to repeat."
    )


def deployment_state(deployment):
    return ((deployment or {}).get("status") or {}).get("state", "")


def wait_for_app(predicate, label, timeout_s=15 * 60, every_s=10):
    """Poll the app until predicate(app) returns (display_state, True)."""
    deadline = time.time() + timeout_s
    while True:
        status, current_app = api("GET", APP_PATH)
        if status != 200:
            fail(f"Polling the app while waiting for {label}", status, current_app)
        state, done = predicate(current_app)
        if done:
            return current_app
        if time.time() > deadline:
            fail(f"Waiting for {label} ({timeout_s // 60} min timeout)", status, current_app)
        print(f"   {label}: currently {state or '…'} — checking again in {every_s}s")
        time.sleep(every_s)


def wait_for_no_pending_deployment(timeout_s=20 * 60):
    """Let a previous Run All finish instead of colliding with it."""
    status, current_app = api("GET", APP_PATH)
    if status != 200:
        fail("Checking for an existing deployment", status, current_app)
    pending = current_app.get("pending_deployment") or {}
    if not pending:
        return current_app
    pending_id = pending.get("deployment_id", "")
    print(
        "A deployment is already in progress"
        f"{f' ({pending_id})' if pending_id else ''} — waiting for it to finish before continuing …"
    )
    if pending_id:
        wait_for_deployment(pending_id, timeout_s=timeout_s)
    return wait_for_app(
        lambda a: (
            deployment_state(a.get("pending_deployment")) or "settling",
            not bool(a.get("pending_deployment")),
        ),
        "previous deployment finished",
        timeout_s=timeout_s,
    )


def wait_for_no_app_update(timeout_s=20 * 60):
    """Wait for a configuration update started by an earlier Run All, if any."""
    status, update = api("GET", f"{APP_PATH}/update")
    if status == 404:
        return
    if status != 200:
        fail("Checking for an existing app configuration update", status, update)
    state = ((update.get("status") or {}).get("state") or "").upper()
    if state != "IN_PROGRESS":
        return
    print("An app configuration update is already in progress — waiting for it to finish …")
    deadline = time.time() + timeout_s
    while True:
        status, update = api("GET", f"{APP_PATH}/update")
        if status != 200:
            fail("Polling the existing app configuration update", status, update)
        state = ((update.get("status") or {}).get("state") or "").upper()
        if state in ("SUCCEEDED", "NOT_UPDATED"):
            return
        if state == "FAILED":
            # The desired state is verified below; a new field-masked update can repair it.
            print("   previous app configuration update failed — retrying the desired configuration.")
            return
        if time.time() > deadline:
            fail("Waiting for existing app configuration update (20 min timeout)", status, update)
        print(f"   app configuration update: {state or 'PENDING'} — checking again in 10s")
        time.sleep(10)


def wait_for_deployment(deployment_id, timeout_s=20 * 60):
    """Wait for the deployment created by this notebook run, not an older RUNNING release."""
    deadline = time.time() + timeout_s
    while True:
        status, deployment = api("GET", f"{APP_PATH}/deployments/{deployment_id}")
        if status != 200:
            fail(f"Polling deployment {deployment_id}", status, deployment)
        state = deployment_state(deployment)
        if state == "SUCCEEDED":
            return deployment
        if state in ("FAILED", "CANCELLED"):
            fail(f"Deployment {deployment_id} ended in {state}", status, deployment)
        if time.time() > deadline:
            fail(f"Waiting for deployment {deployment_id} (20 min timeout)", status, deployment)
        print(f"   deployment {deployment_id}: {state or 'PENDING'} — checking again in 10s")
        time.sleep(10)


def wait_for_deployment_to_be_active(deployment_id, timeout_s=10 * 60):
    """Wait for the successful deployment to become active and for its pending marker to clear."""
    return wait_for_app(
        lambda a: (
            (a.get("app_status") or {}).get("state", ""),
            (a.get("active_deployment") or {}).get("deployment_id") == deployment_id
            and not a.get("pending_deployment")
            and (a.get("app_status") or {}).get("state") == "RUNNING",
        ),
        f"deployment {deployment_id} active and app RUNNING",
        timeout_s=timeout_s,
    )


print(f"Signed in as: {EMAIL}")
print(f"App name:     {APP_NAME}")
print(f"App source:   {SOURCE_CODE_PATH}")
print(f"Memory schema (once deployed): memory_{APP_NAME.replace('-', '_')}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Create the app (with its Lakebase memory resource)
# MAGIC The `postgres` resource is your agent's memory. An existing app is reused as-is.

# COMMAND ----------

status, app = api("GET", APP_PATH)
app_existed = status == 200

if app_existed:
    print(f"App '{APP_NAME}' already exists — reusing it.")
    if not any((res or {}).get("name") == "postgres" for res in app.get("resources") or []):
        print("⚠️ Existing app has NO postgres resource — Step 4 will restore it safely.")
elif status == 404:
    print(f"Creating app '{APP_NAME}' …")
    status, body = api(
        "POST",
        "/api/2.0/apps",
        {
            "name": APP_NAME,
            "description": "TechMart customer-support agent (DAIS 2026 lab)",
            "resources": [POSTGRES_RESOURCE],
        },
    )
    if status != 200:
        fail("App creation", status, body)
    print("   created.")
else:
    fail(f"Looking up app '{APP_NAME}'", status, app)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Wait for app compute, read the service-principal id
# MAGIC First-time compute takes a few minutes; the SP id is only reliable once compute is ACTIVE.

# COMMAND ----------

print("Waiting for app compute to be ACTIVE (first provision takes a few minutes) …")
deadline = time.time() + 15 * 60
while True:
    status, app = api("GET", APP_PATH)
    if status != 200:
        fail("Polling the app", status, app)
    compute = (app.get("compute_status") or {}).get("state", "")
    if compute == "ACTIVE":
        break
    if compute == "ERROR":
        fail("App compute provisioning", status, app)
    if time.time() > deadline:
        fail("Waiting for ACTIVE compute (15 min timeout)", status, app)
    print(f"   compute: {compute or 'PENDING'} … checking again in 10s")
    time.sleep(10)

SP_ID = ""
deadline = time.time() + 5 * 60
while True:
    status, app = api("GET", APP_PATH)
    SP_ID = (app.get("service_principal_client_id") or "").strip()
    if UUID_RE.fullmatch(SP_ID):
        break
    if time.time() > deadline:
        fail("Reading a non-empty service_principal_client_id (5 min timeout)", status, app)
    print("   service_principal_client_id not populated yet … checking again in 10s")
    time.sleep(10)

print(f"✅ Compute ACTIVE. App service principal: {SP_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Set up the app's database access (memory)
# MAGIC The app's service principal gets its own Postgres role on the shared Lakebase project.
# MAGIC Provisioning right after app creation is eventually consistent, so this cell verifies and
# MAGIC retries until confirmed — **a few retries are normal**. Anything unexpected stops loudly.

# COMMAND ----------

# Why verify-then-retry: (1) right after app creation the role POST can return ALREADY_EXISTS
# for a role that does NOT exist yet — "already exists" only counts if the role is IN the roles
# list; otherwise back off and retry. (2) provisioning may create a role that the deployment
# later replaces — step 5 re-verifies post-deploy.
def sp_role_listed():
    """True iff the roles list actually contains an object for our SP."""
    status, body = api("GET", ROLES_PATH)
    if status != 200:
        print(f"   (roles list returned HTTP {status} — treating as 'not listed')")
        return False
    return SP_ID.lower() in json.dumps(body).lower()


ROLE_SPEC = {
    "spec": {
        "identity_type": "SERVICE_PRINCIPAL",
        "postgres_role": SP_ID,
        "auth_method": "LAKEBASE_OAUTH_V1",
        "membership_roles": ["DATABRICKS_SUPERUSER"],
    }
}


def ensure_sp_role(context=""):
    """Make sure the app SP's Postgres role exists. Returns True iff this call created it."""
    if sp_role_listed():
        print(f"✅ Postgres role for {SP_ID} is in the roles list{context} — nothing to create.")
        return False
    print(f"Creating Postgres role for {SP_ID}{context} …")
    deadline = time.time() + 15 * 60
    attempt = 0
    while True:
        attempt += 1
        status, body = api("POST", ROLES_PATH, ROLE_SPEC)
        if status == 200:
            print(f"✅ Role created (HTTP 200, attempt {attempt}).")
            return True
        body_text = json.dumps(body).upper()
        if status in (400, 409) and "ALREADY_EXISTS" in body_text:
            if sp_role_listed():
                # A real duplicate (e.g. a concurrent attempt won the race) — that's success.
                print(f"✅ Role exists (confirmed in the roles list, attempt {attempt}).")
                return False
            if time.time() > deadline:
                fail(
                    "Postgres role creation — still getting the transient ALREADY_EXISTS "
                    "rejection after 15 min of retries",
                    status,
                    body,
                )
            wait = min(15 + 5 * attempt, 60)
            # The API said the role exists but the roles list disagrees — provisioning is still
            # settling right after creation. Retry until both agree.
            print(
                f"   attempt {attempt}: database provisioning is still settling — "
                f"retrying in {wait}s (normal for the first few minutes) …"
            )
            time.sleep(wait)
            continue
        fail("Postgres role creation", status, body)


ensure_sp_role(" (pre-deploy)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Preserve Lakebase and set the OBO scopes
# MAGIC `sql` + `vector-search`: the two ways your agent's tools act **as you** (that's the consent
# MAGIC screen you'll click through on first open). This uses a field-masked app update, so changing
# MAGIC scopes cannot detach the `postgres` memory resource. If an earlier **Run All** is still
# MAGIC deploying, this step waits for it rather than colliding with it.

# COMMAND ----------

DESIRED_SCOPES = ["sql", "vector-search"]


def postgres_resource_is_correct(resource):
    pg = (resource or {}).get("postgres") or {}
    desired = POSTGRES_RESOURCE["postgres"]
    return (
        (resource or {}).get("name") == "postgres"
        and pg.get("branch") == desired["branch"]
        and pg.get("database") == desired["database"]
        and pg.get("permission") == desired["permission"]
    )


wait_for_no_pending_deployment()
wait_for_no_app_update()
status, app = api("GET", APP_PATH)
if status != 200:
    fail("Reading the app before its configuration update", status, app)

current_resources = app.get("resources") or []
postgres_ok = any(postgres_resource_is_correct(res) for res in current_resources)
scopes_ok = set(app.get("user_api_scopes") or []) == set(DESIRED_SCOPES)

update_fields = []
app_update = {}
if not postgres_ok:
    # Replace only the resource named "postgres" and retain every unrelated resource.
    app_update["resources"] = [
        res for res in current_resources if (res or {}).get("name") != "postgres"
    ] + [POSTGRES_RESOURCE]
    update_fields.append("resources")
if not scopes_ok:
    app_update["user_api_scopes"] = DESIRED_SCOPES
    update_fields.append("user_api_scopes")

if update_fields:
    print(f"Updating app configuration: {', '.join(update_fields)} …")
    status, body = api(
        "POST",
        f"{APP_PATH}/update",
        {"update_mask": ",".join(update_fields), "app": app_update},
    )
    if status != 200:
        fail("Updating the app configuration", status, body)

    deadline = time.time() + 20 * 60
    while True:
        status, update = api("GET", f"{APP_PATH}/update")
        if status != 200:
            fail("Polling the app configuration update", status, update)
        state = ((update.get("status") or {}).get("state") or "").upper()
        if state == "SUCCEEDED":
            break
        if state == "FAILED":
            fail("App configuration update", status, update)
        if time.time() > deadline:
            fail("Waiting for app configuration update (20 min timeout)", status, update)
        print(f"   app configuration update: {state or 'PENDING'} — checking again in 10s")
        time.sleep(10)
else:
    print("App configuration already correct — no update needed.")

status, app = api("GET", APP_PATH)
if status != 200:
    fail("Verifying the app configuration", status, app)
if not any(postgres_resource_is_correct(res) for res in app.get("resources") or []):
    fail("Verifying the postgres resource after the app update", status, app)
if set(app.get("user_api_scopes") or []) != set(DESIRED_SCOPES):
    fail("Verifying user_api_scopes after the app update", status, app)
print("✅ postgres resource attached; user_api_scopes = ['sql', 'vector-search']")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Deploy the source and wait for RUNNING
# MAGIC Deploys your `agent/` folder and waits for RUNNING. Once the app is up, it **double-checks
# MAGIC the memory setup** and restarts the app once if it needed a refresh — so memory works on your
# MAGIC very first chat. (A restart here is routine; the cell tells you when it happens.)

# COMMAND ----------

print("Starting deployment …")
status, body = api("POST", f"{APP_PATH}/deployments", {"source_code_path": SOURCE_CODE_PATH})
if status != 200:
    fail("Creating the deployment", status, body)
DEPLOYMENT_ID = (body.get("deployment_id") or "").strip()
if not DEPLOYMENT_ID:
    fail("Reading deployment_id from the deployment response", status, body)

print(f"Deployment created: {DEPLOYMENT_ID}")
wait_for_deployment(DEPLOYMENT_ID)
app = wait_for_deployment_to_be_active(DEPLOYMENT_ID)

# A deployment can reset database access that was set up just before it ran, so re-verify now
# that the dust has settled and recreate the role if needed — this is what makes memory work on
# the FIRST run.
role_recreated_post_deploy = ensure_sp_role(" (final check)")

if role_recreated_post_deploy:
    # This deployment started before its final Postgres role existed, so refresh its
    # database credential once. A normal re-run does not need an extra stop/start: the
    # new deployment already started a fresh runtime.
    print("Restarting the app once so it picks up its database credential (routine) …")
    status, body = api("POST", f"{APP_PATH}/stop")
    if status != 200:
        fail("Stopping the app", status, body)
    wait_for_app(
        lambda a: (
            (a.get("compute_status") or {}).get("state"),
            (a.get("compute_status") or {}).get("state") in ("STOPPED", "DELETED"),
        ),
        "app STOPPED",
        timeout_s=5 * 60,
    )
    status, body = api("POST", f"{APP_PATH}/start")
    if status != 200:
        fail("Starting the app", status, body)
    app = wait_for_app(
        lambda a: ((a.get("app_status") or {}).get("state"), (a.get("app_status") or {}).get("state") == "RUNNING"),
        "app RUNNING (after restart)",
    )

APP_URL = app.get("url", "")
print()
print("🎉 Your agent is RUNNING!")
print(f"   App URL:       {APP_URL}")
print(f"   Memory schema: memory_{APP_NAME.replace('-', '_')}")
displayHTML(
    f'<div style="font-family:system-ui;font-size:15px;padding:10px 14px;background:#f0fdf4;'
    f'border-left:4px solid #16a34a;border-radius:0 8px 8px 0">'
    f'🎉 <b>Deployed:</b> <a href="{APP_URL}" target="_blank">{APP_URL}</a><br>'
    f'First open shows a <b>"Permission Requested"</b> consent screen (Databricks SQL + Vector '
    f'Search) — click <b>Authorize</b>, then chat. The chat header should say '
    f'<b>memory:&nbsp;session</b>; if it ever says <b>memory:&nbsp;off</b>, just re-run this notebook.</div>'
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Done — back to the lab
# MAGIC 1. **Open your app URL** (above) → **Authorize** on the consent screen → say hello.
# MAGIC 2. Check the chat header shows **memory: session** (your agent remembers the conversation —
# MAGIC    you'll go look at the actual rows in Lakebase in Module 5½).
# MAGIC 3. Continue with **Module 3** in the lab guide (the OBO governance story — try order
# MAGIC    `ORD-10001` and watch the PII come back redacted).
# MAGIC
# MAGIC > Something off? Re-running this whole notebook is always safe — it reuses the app, repairs
# MAGIC > the role, re-deploys, and restarts only when needed.
