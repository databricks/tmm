# Databricks notebook source
# MAGIC %md
# MAGIC # 🛠️ Build a Custom AI Agent on Databricks Apps — *Start Here*
# MAGIC ### From Prompt to Production · Data + AI Summit 2026 · ~90 min
# MAGIC
# MAGIC You're a data engineer at **TechMart** (a fictional electronics retailer) standing up an AI
# MAGIC customer-support agent: **build** it on Databricks Apps, **govern** it, deliberately **break**
# MAGIC it, **measure** the breakage with LLM judges, **fix** it, and **prove** the fix.
# MAGIC
# MAGIC > **This is a coding-agent-driven lab.** You *direct* **Genie Code** and it writes/deploys for
# MAGIC > you. Every module has a click-through fallback so a hiccup never blocks you.

# COMMAND ----------

# MAGIC %md
# MAGIC ## How this lab works
# MAGIC 1. **Everything is pre-provisioned and shared** in `agent_apps_workshop.shared` — data, tools,
# MAGIC    Vector Search, governance, warehouse, and a **Lakebase** project for agent memory. You deploy
# MAGIC    your **own** app against those shared assets.
# MAGIC 2. **The illustrated guide lives in the lab-guide app** — the "Your lab values" cell prints its
# MAGIC    link. Keep it open in another tab.
# MAGIC 3. **A working agent starter is in `agent/`** (next to this notebook). Genie Code deploys and
# MAGIC    customizes it; its tools run **on-behalf-of-you (OBO)**, so you need no special grants.

# COMMAND ----------

# MAGIC %md
# MAGIC ## ⭐ Module 0 — Meet Genie Code & give it the lab context (2 min)
# MAGIC Genie Code is your in-workspace coding agent. Its built-in **skills** give it the platform
# MAGIC mechanics — they know nothing about *our* TechMart lab. **Do this now:**
# MAGIC 1. **Open Genie Code** — the panel in this notebook, or the icon in the top bar.
# MAGIC 2. **See what it knows:** ask *"What skills do you have available?"* (No TechMart skill — step 3
# MAGIC    fixes that.)
# MAGIC 3. **Hand it the lab context:** type **`@LAB_CONTEXT.md`** in your prompt (or **Add context →
# MAGIC    Attach files**).
# MAGIC
# MAGIC > 💡 **Re-attach `LAB_CONTEXT.md` in every new Genie chat** — context doesn't carry across
# MAGIC > threads. With it attached, short natural prompts just work.
# MAGIC
# MAGIC > 🚦 **Genie asks before it acts** — the **Allow** / **Run** prompts are part of the workflow,
# MAGIC > not an error. Review, click Allow, it keeps going.
# MAGIC
# MAGIC > ⚠️ **Leave "Auto-approve" OFF.** If you enable it, Genie auto-blocks the deploy steps as
# MAGIC > "unsafe" (creating your app is a workspace change) and you'll see *"Action denied / Skipped
# MAGIC > running cells."* That's the guardrail, not a real permission problem — just click
# MAGIC > **Approve and run all cells** (or turn Auto-approve off and click **Run**). The deploy is safe.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Your lab values
# MAGIC Run this cell — it prints the shared names you (and Genie Code) will use throughout the lab.

# COMMAND ----------

import re

email = (spark.sql("SELECT current_user() AS u").collect()[0]["u"] or "").strip()
# App names must be unique per deploy, so derive a per-user suffix from your email.
username = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", email.split("@")[0].lower())).strip("-")
if username and username[0].isdigit():
    username = "u-" + username

CATALOG = "agent_apps_workshop"
SCHEMA = "shared"
# Databricks Apps names must be lowercase letters/digits/hyphens and <= 30 chars (no trailing
# hyphen). Keep the TAIL of the username when truncating: lab usernames share a long common
# PREFIX and differ in the trailing digits — the tail is what makes each name unique.
APP_NAME = ("agent-apps-" + username[-19:].lstrip("-")).rstrip("-")
# The shared lab-guide app (deployed by workshop setup; one per workspace, all students CAN_USE).
# App URLs are <app-name>-<workspace-id>.<cloud-domain>; derive ours from the workspace id so the
# link works in every lab workspace without hardcoding.
def _guide_url() -> str:
    try:
        ws_id = dbutils.notebook.entry_point.getDbutils().notebook().getContext().workspaceId().get()
        return f"https://agent-lab-guide-{ws_id}.aws.databricksapps.com"
    except Exception:
        return ""  # fall back to UI navigation below

GUIDE_URL = _guide_url()

print(f"Signed in as:         {email}")
print(f"Shared TechMart data: {CATALOG}.{SCHEMA}   (products, orders, policies, product_docs + product_docs_vs)")
print(f"Agent tools (UC fns): {CATALOG}.{SCHEMA}.{{get_product_details, get_order_status, get_return_policy}}")
print(f"SQL warehouse:        agent-apps-shared   (your agent runs the tools on-behalf-of-you)")
print(f"Your app name:        {APP_NAME}   (you deploy your own app; <=30 chars)")
print(f"Your memory schema:   memory_{APP_NAME.replace('-', '_')}   (your agent's Lakebase conversation history lives here)")
print(f"Lab guide app:        {GUIDE_URL or 'Compute -> Apps -> agent-lab-guide'}   (guide at /, slide deck at /deck)")
print()
print("👉 Next: open 01_Explore_Data (Module 1). When you're ready for Module 2, open Genie Code,")
print("   attach LAB_CONTEXT.md (Add context / @LAB_CONTEXT.md), and say: \"I'm in the TechMart agent lab — help me start Module 2.\"")

if GUIDE_URL:
    displayHTML(
        f'<div style="font-family:system-ui;font-size:15px;padding:10px 14px;background:#fff3f1;'
        f'border-left:4px solid #ff3621;border-radius:0 8px 8px 0">'
        f'📖 <b>Keep the lab guide open in another tab:</b> '
        f'<a href="{GUIDE_URL}" target="_blank">{GUIDE_URL}</a> '
        f'&nbsp;·&nbsp; <a href="{GUIDE_URL}/deck" target="_blank">field-guide deck</a></div>'
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## The modules (full illustrated instructions in the lab-guide app — link above ↑)
# MAGIC | # | Module | You'll… |
# MAGIC |---|---|---|
# MAGIC | 1 | **Explore the data** | Browse `agent_apps_workshop.shared` — notice some odd product docs. Open `01_Explore_Data`. |
# MAGIC | 2 | **Build & deploy the agent** | Direct Genie Code to deploy the `agent/` starter as your own **Databricks App** — its tools run **on-behalf-of-you (OBO)**. (Fallback: **`02_Deploy_App`** → Run All.) |
# MAGIC | 3 | **Govern with OBO** | Because your agent runs **on-behalf-of-you**, the UC **column mask** auto-redacts customer PII in the order lookup for non-admins — see it live in your agent. |
# MAGIC | 4 | **Break it** | Chat with your agent and surface the planted quality bugs. |
# MAGIC | 5 | **Evaluate & fix** | Open **`05_Evaluate_and_Fix`** (ready to run) — **MLflow LLM judges** → baseline → fix the prompt → re-eval → **prove** the gain. |
# MAGIC | 5½ | **Visit your agent's memory** | **Compute → Lakebase → Open Lakebase** → project "Agent Apps Workshop Memory" → SQL Editor → query `agent_messages` in **your app's schema** (printed above) — every chat is there. |
# MAGIC | 6 | **Productionize** | Recap the **DABs** deploy + CI/CD; traces in UC; debug with Genie. |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stuck? (click-through fallback)
# MAGIC Every module has a no-code path. Module 2's is **`02_Deploy_App`** (same folder): **Run All**
# MAGIC deploys without Genie, and re-running it fixes a "memory: off" header. Your instructor can
# MAGIC also share a reference app URL.
# MAGIC
# MAGIC Ready? Open **`01_Explore_Data`** for Module 1, then **Genie Code** for Module 2. 🚀
