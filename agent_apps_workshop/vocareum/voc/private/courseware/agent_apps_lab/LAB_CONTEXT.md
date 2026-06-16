# TechMart Agent Lab — context for Genie Code

> **How to use this file:** In Genie Code, attach it as context (**Add context → Attach files**, or
> type **`@LAB_CONTEXT.md`**) at the start of a working session. It gives Genie the lab-specific facts
> the general Databricks skills don't know. Lean on whatever preloaded skills are available for the
> mechanics — e.g. the MLflow-evaluation skill for the evaluate module, and the Vector Search / Unity
> Catalog skills for the data tools. (Skill names vary by Genie Code version; deploying needs no
> "apps" skill at all — the shipped `02_Deploy_App` notebook IS the deploy path.)

You are helping a workshop participant — a **non-admin lab user** — stand up a **TechMart**
customer-support agent on Databricks Apps. Everything is already provisioned; help them *use* it
(deploy, govern, break, evaluate), and prefer the shipped `agent/` folder over writing one from scratch.

## Pre-provisioned, shared, read-only (catalog `agent_apps_workshop.shared`)
- Tables `products`, `orders`, `policies`, `product_docs`, and a Vector Search index `product_docs_vs`.
- UC function tools: `get_product_details`, `get_order_status`, `get_return_policy`.
- SQL warehouse named **`agent-apps-shared`** — resolve it **by name**, never hardcode an id.
- A Unity Catalog column mask redacts `orders` customer PII for non-admins (the governance story).
- A ready-to-run agent already lives in the participant's **`agent/` folder** — deploy and customize it.

## The one hard constraint — DATA access runs on-behalf-of-the-user (OBO)
The participant is **non-admin and cannot grant their app's service principal anything on the shared
data.** So the agent calls all data tools **as the signed-in user** (OBO), and the deployed app's
**`user_api_scopes` must include `sql` and `vector-search`.** Grant the service principal nothing on
the catalog. (The LLM runs as the app SP on Foundation Model APIs, pay-per-token, which needs no
grant.) The first time the participant opens the app they get a **"Permission Requested"** consent
screen — they click **Authorize**, then chat.

## Conversation memory (Lakebase) — pre-wired, don't rebuild it
The shipped `agent/app.py` stores each chat session's transcript in the shared **Lakebase** project
`agent-apps-memory` using the documented Databricks Apps pattern: the app is **created with a
`postgres` resource** (step 1 of the deploy sequence below), which auto-creates a Postgres role for
the app's service principal. Transcripts are written **as the app SP** into a **per-app schema**
(`memory_<app-name>`, underscores for hyphens) that the SP creates and owns on first use — tables
`agent_sessions` / `agent_messages`. **Do not rewrite the memory code, add database grants, or
create memory tables in the `public` schema.** If memory ever fails the chat degrades gracefully to
single-turn (the UI shows "memory: off") — the lab still works. Near the end of the lab participants
visit the Lakebase UI and query their app's schema to see their conversation history.

## The planted bugs (they drive Module 4 "break it" and Module 5 "evaluate & fix")
The data intentionally contradicts itself: a **discontinued** product whose marketing doc still says
it's available; a product-doc **warranty (3 yr)** that conflicts with the official **policy (1 yr)**; and
an over-permissive **"Customer Satisfaction Policy (Extended)."** A good agent trusts the authoritative
tables / official policy over the marketing docs, and the evaluation should measure exactly that.

## Deploying the app — RUN the shipped `02_Deploy_App` notebook (do NOT regenerate the sequence)
The participant's folder ships **`02_Deploy_App`** — the validated deploy sequence as runnable,
idempotent cells. **To deploy: open `02_Deploy_App` and Run All** (run it for the participant, or
tell them to). Re-running it any time is safe, and it is also the documented repair whenever the
app's chat header shows **"memory: off"** (it recreates the Postgres role and restarts the app).
**Do not hand-write the REST sequence yourself**: the role-creation step hits a platform race —
in the first minutes after app creation the roles API can transiently return
`400 ROLE_ALREADY_EXISTS` *for a role that does not exist* — and only the notebook's
list-check-and-retry logic handles it reliably. A regenerated recipe WILL misread that 400.

### Background — what `02_Deploy_App` does (reference only; don't re-implement it)
It uses the **Databricks Apps REST API** with the notebook's own token (this lab user can't use
the CLI for mutating ops; the SDK has no `deploy`):
`token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()`;
`host = "https://" + spark.conf.get("spark.databricks.workspaceUrl")`; `headers = {"Authorization": f"Bearer {token}"}`.
Then, in order:
1. **Create (with the Lakebase memory resource):** `POST {host}/api/2.0/apps` body
   ```json
   {"name": APP_NAME, "description": "...",
    "resources": [{"name": "postgres", "postgres": {
      "branch": "projects/agent-apps-memory/branches/production",
      "database": "projects/agent-apps-memory/branches/production/databases/databricks-postgres",
      "permission": "CAN_CONNECT_AND_CREATE"}}]}
   ```
   The `postgres` resource is the agent's conversation memory (those resource paths are canonical —
   workshop setup created them; the `database` field needs the FULL path shown). `APP_NAME` must be
   lowercase letters/digits/hyphens and **≤ 30 chars** (see `00_Start_Here` — use the `APP_NAME` it
   prints; don't build a longer one).
2. **Wait** for `compute_status.state == "ACTIVE"` (poll `GET {host}/api/2.0/apps/{APP_NAME}`).
3. **Create the app's Postgres role** (REQUIRED for memory — on this platform the resource does not
   auto-provision it). FIRST re-GET the app and read `service_principal_client_id` — it is only
   reliably populated once compute is ACTIVE; **verify it is a non-empty UUID before posting**:
   ```
   POST {host}/api/2.0/postgres/projects/agent-apps-memory/branches/production/roles
   body {"spec": {"identity_type": "SERVICE_PRINCIPAL",
                  "postgres_role": "<service_principal_client_id>",
                  "auth_method": "LAKEBASE_OAUTH_V1",
                  "membership_roles": ["DATABRICKS_SUPERUSER"]}}
   ```
   **Must end in HTTP 200, or the role actually appearing in the roles list** (`GET` the same
   path). ⚠️ Right after app creation this POST can 400 `ROLE_ALREADY_EXISTS` for a role that
   does NOT exist — "already exists" counts ONLY if the roles list shows it; otherwise back off
   and re-POST until a clean 200. Any other status is a hard failure: print the body, stop, and
   do not deploy until this succeeds.
4. **Set OBO scopes:** `PATCH {host}/api/2.0/apps/{APP_NAME}` body `{"user_api_scopes": ["sql", "vector-search"]}`.
5. **Deploy source:** `POST {host}/api/2.0/apps/{APP_NAME}/deployments` body
   `{"source_code_path": "/Workspace/Users/<you>/agent_apps_lab/agent"}`, then poll until
   `app_status.state == "RUNNING"`. The app URL is in the GET response.
   ⚠️ The role must exist BEFORE the first deployment (a late role needs an app stop/start to
   flush the cached credential), AND the deployment itself can DELETE the role — after RUNNING,
   re-verify the roles list and recreate + restart if it vanished. `02_Deploy_App` does all of
   this. If memory shows "off": **re-run `02_Deploy_App`**.

## Lab-specific notes that save time
- A shared **lab-guide app** named `agent-lab-guide` runs in this workspace (all participants have
  CAN_USE): the full participant guide at `/` and a slide-deck field guide at `/deck`. Its URL is
  `https://agent-lab-guide-<workspace-id>.aws.databricksapps.com` (also printed by `00_Start_Here`).
  Point the participant there for module steps, screenshots, and troubleshooting.
- The shipped `agent/` is already correct (FMAPI-aware LLM client, pinned deps, and a browser chat UI at
  `GET /`) — **don't rewrite its LLM setup.** If the deployed app ever fails to start, read `https://<app-url>/logz`.
- Test in the browser: open the app URL, click **Authorize** on the consent screen, then chat. (Same-origin
  requests carry the user's `X-Forwarded-Access-Token`, so tools run OBO and PII masking follows the user.)
- The Module 5 evaluation runs **in a notebook** with the agent in-process (so tool calls are OBO as
  you). Use the preloaded **MLflow-evaluation** skill for the MLflow/judges specifics.

## Module 5 — use the pre-built `05_Evaluate_and_Fix` notebook
A validated eval notebook ships in this folder — **open `05_Evaluate_and_Fix` and Run All** (or tell me
"run the Module 5 eval notebook"). The participant only edits the `fixed_instructions` cell. It already
encodes the gotchas below, so you shouldn't need to hand-write the harness:
- **Pin `databricks-vectorsearch==0.73`** in the `%pip install` (0.74 breaks an import) and
  `nest_asyncio.apply()` after restart.
- **CRITICAL: `mlflow.openai.autolog(disable=True)` BEFORE `mlflow.genai.evaluate`** (evaluate
  re-enables openai autolog, which breaks the Agents-SDK-on-FMAPI path — mlflow #15692). The
  manual `@mlflow.trace` on the predict fn is the one clean trace per row; call
  `mlflow.set_experiment(...)` first.
- Judges: `Guidelines` scorers with conditional wording ("if not about X, pass"); predict_fn's
  param name must match the `inputs` key. Small set — read per-row, not means.
- **The warranty flip needs the right tool call:** `get_return_policy(topic)` filters by a policy
  CATEGORY — `get_return_policy('warranty')` returns the 1-yr term; passing a product name
  (`get_return_policy('AudioMax Pro')`) returns empty. The `fixed_instructions` cell tells the agent to
  call it with a category (not a product name), which is what flips warranty from 3-yr (fail) to 1-yr (pass).
