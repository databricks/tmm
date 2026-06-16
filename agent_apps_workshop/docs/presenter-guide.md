# Presenter Guide — Build a Custom AI Agent on Databricks Apps
### From Prompt to Production · ~90 min · Genie-Code-driven hands-on lab

> Ground truth for the participant flow is [`lab-guide/README.md`](lab-guide/README.md). This guide
> is for whoever runs the room.
>
> Adapted from Robert Mosley's
> [databricks-agentic-app-workshop](https://github.com/rmosleydb/databricks-agentic-app-workshop).

---

## 0. What this lab is (presenter framing)

Attendees play a data engineer at **TechMart** (fictional electronics retailer). Each one directs
**Genie Code** (the in-workspace coding agent) to deploy their **own** customer-support agent as a
**Databricks App**, watches **Unity Catalog governance follow their identity** through the deployed
app (on-behalf-of-user auth + a PII column mask), deliberately **breaks** the agent on planted data
bugs, **measures** the breakage with MLflow `Guidelines` LLM judges, **fixes** it with a prompt
change, and **proves** the fix with numbers and real traces.

That arc *is* the platform story: **Apps = runtime**, **OpenAI Agents SDK = bring-your-own-harness**,
**OBO + UC = governance**, **MLflow = agent ops**, **Genie Code = how teams build now**, and
(Module 6 framing) **DABs = productionization**.

### 30-second pitch (say this)
> "You're going to deploy your own AI customer-support agent on Databricks Apps — with **zero
> special permissions**, because every data call runs *as you*. You'll watch enterprise governance
> follow your identity straight through the deployed app, then break the agent, measure the breakage
> with LLM judges, fix it, and *prove* it improved with real traces and numbers. That's the whole
> agent hardening loop, in 90 minutes."

### Audience & mode
- Practitioners (data engineers / ML / app devs) comfortable **directing a coding agent** rather
  than hand-writing code. Presenter demos live from a student-view workspace; attendees follow on
  their own lab login.
- Everything has a **fallback** — if a Genie deploy stalls, have them **Run All in
  `02_Deploy_App`** (the deploy as deterministic, re-runnable code); if even that's mid-flight,
  share your reference app URL and keep moving.
  **Protect Modules 4–5 (break → evaluate → fix); that's the payoff.**

### The two design facts that explain everything (have these ready)
1. **Students are non-admin and can grant their app's service principal *nothing* on the shared
   data.** So data access is **all-OBO**: every data call (UC functions via SQL warehouse, Vector
   Search) uses the signed-in user's forwarded token. The constraint *is* the governance lesson.
   **Conversation memory uses the documented SP pattern:** each app attaches the shared Lakebase
   project as a `postgres` resource (setup grants `users` CAN MANAGE on the project to allow it),
   which auto-creates the app SP's database role; transcripts land in a per-app schema the SP owns.
   SP-side calls are the LLM (FMAPI, pay-per-token, no grant) and memory. Two auth patterns, each
   where it belongs — call that out in Module 5½.
2. **The LLM is `databricks-gpt-5-4` on purpose** (set via `LLM_ENDPOINT` in `agent/app.yaml`). It's
   the fastest reliable tool-caller **that still exhibits the planted warranty bug**. Some frontier
   models *self-correct* the bug — which would gut Modules 4–5. Great wrap-up color (see §6), but
   never swap the baseline model casually.

---

## 1. Before the session (admin / presenter setup)

### Provision the lab workspace
- Rebuild the payload and upload it to your lab platform — see the repo
  [`README.md`](../README.md) ("Run it yourself"). `bash .../build_zips.sh` produces the three
  `dist/` files (`config.json`, `agent_apps_setup.zip`, `agent_apps_lab.zip`).
- ⚠️ **`workspace_setup` runs ONCE per workspace.** Re-uploading the payload and spinning fresh
  students only re-runs the per-student content. Any change to `agent_apps_setup.py` needs a
  **fresh workspace provision** to take effect.
- After a fresh provision, read the **setup log** and confirm, in order:
  - Catalog `agent_apps_workshop.shared`: tables `products`, `orders`, `policies`, `product_docs`
    (with the **3 planted bugs**), the 3 UC function tools, VS index `product_docs_vs` **ONLINE**,
    SQL warehouse **`agent-apps-shared`** (resolved by name, never by id).
  - UC **column mask** on `orders.customer_email` + `shipping_address` (non-admins see
    `***REDACTED***`).
  - Genie Code skills distributed **and `users` granted CAN_READ on `/Workspace/.assistant`** —
    without that grant students' Genie Code sees **zero** skills.
  - Lakebase project **`agent-apps-memory`** ready (endpoint host in the log), **`users` granted
    CAN_MANAGE on the project** (required for students' apps to attach it as a resource), and the
    `users`-group Postgres role mapped (for the Module 5½ SQL-editor browse). If this step failed
    the lab still runs; chats are just single-turn and you skip Module 5½. ⚠️ CAN_MANAGE means a
    student *could* damage the shared project — accepted trade-off; the agent degrades gracefully
    (memory: off) and everything else is unaffected.
  - The **lab-guide app** `agent-lab-guide` RUNNING (URL in the log) with `users` CAN_USE — the
    participant guide at `/`, the field-guide deck at `/deck`. Put the deck on the projector for
    walk-in; tell the room: "the guide link is printed by your first notebook cell."

### T-15m (presenter) — pre-flight
- From a **student-view** login: run `00_Start_Here` (values cell prints, app name ≤30 chars),
  spot-check `01_Explore_Data` (PII masked), and ideally **deploy your own app** — it doubles as the
  **reference fallback app** for stragglers. Verify in its chat UI:
  - *"What's the status of order ORD-10001? Include the customer's email and address."* →
    **`***REDACTED***`**.
  - *"How long is the AudioMax Pro warranty?"* → **"3-year"** (the planted bug is intact — this is
    the canary; if it answers 1 year, someone changed the model or prompt: stop and investigate).
- Have these screens open: `00_Start_Here`, Catalog (on `agent_apps_workshop.shared`), your deployed
  app's chat UI, the MLflow **Experiments** page, the participant guide, this guide.
- For a large room: the lab shares one warehouse, VS endpoint, and FMAPI quota, so **stagger the
  Module 2 deploys and Module 5 Run-Alls** table by table rather than counting everyone in at once.

---

## 2. Timing (90 min — approximate; protect M4–M5)

| Time | Module | What the presenter does |
|---|---|---|
| 0:00–0:08 | **0 · Intro & Genie Code** | Pitch + TechMart story; everyone runs the values cell, opens Genie Code, attaches `LAB_CONTEXT.md` |
| 0:08–0:18 | **1 · Explore** (10m) | Run `01_Explore_Data`; the masked-PII reveal; tease "the docs aren't quite right…" |
| 0:18–0:33 | **2 · Build & deploy** (15m, mostly waiting) | Naive prompt → Genie deploys via REST; while it polls, walk the agent architecture |
| 0:33–0:40 | **3 · Govern (OBO)** (7m) | Consent screen → Authorize → ORD-10001 redacted **through the app** |
| 0:40–0:48 | **4 · Break it** (8m) | Probe the planted bugs; the "3-year warranty" lie lands |
| 0:48–1:08 | **5 · Evaluate & fix** (20m) | `05_Evaluate_and_Fix` Run-All; read judges per-row in MLflow; the warranty flip |
| 1:08–1:13 | **5½ · Lakebase memory** (5m) | Lakebase UI → `agent-apps-memory` → query `memory_<app>.agent_messages`: "that's your chat, as OLTP rows, written by YOUR app's SP into a schema it owns" |
| 1:13–1:23 | **6 · Productionize** (10m) | DABs/CI framing; judges as regression gates; the "evaluate before you swap" model story |
| 1:23–1:30 | **Wrap + buffer** | The hardening loop; soak up overruns |

---

## 3. Module-by-module presenter script

> Format per module: **Goal** · **Say** · **Do / show** · **Genie prompt** · **Expected** ·
> **Talking points / watch-outs**

### Module 0 — Meet Genie Code & attach the lab context (8m)
- **Goal:** set the story; everyone's Genie Code grounded in the lab.
- **Say:** the 30-sec pitch + "You're a data engineer at TechMart; leadership greenlit an AI support
  agent; the data's already in Unity Catalog — but it isn't perfect."
- **Do / show:** open `agent_apps_lab/00_Start_Here`, run the **"Your lab values"** cell — point at
  the printed `APP_NAME` ("yours is unique, and it's capped at 30 characters — use exactly this
  one"). Open **Genie Code**, ask *"what skills do you have available?"*, then attach the context:
  type **`@LAB_CONTEXT.md`** (or Add context → Attach files).
- **Expected:** Genie lists a few dozen Databricks-authored skills; the attach grounds it in
  TechMart specifics.
- **Talking points / watch-outs:**
  - "The skills give Genie the *platform mechanics*; `LAB_CONTEXT.md` gives it *our lab* — the
    shared assets, the OBO rule, and the pointer to the runnable deploy notebook."
  - **Don't name specific skills from stage** — the catalog varies by workspace version. "Skim
    *your* list" is the safe phrasing.
  - Drill the habit now: **re-attach `@LAB_CONTEXT.md` in every new Genie chat** — context doesn't
    carry across threads. Most mid-lab "Genie is confused" moments are a missing re-attach.
  - Genie's approval gates (`Allow` / `Run` buttons) surprise first-timers — tell them up front:
    "Genie asks before it executes; approving those is part of the workflow." **And tell them to
    leave Genie's _Auto-approve_ OFF** — with it on, Genie blocks the app-creating deploy steps as
    "unsafe" (you'll see *"Action denied / Skipped running cells"*); just click **Approve and run
    all cells**, or use the `02_Deploy_App` Run-All fallback.

### Module 1 — Explore the data (10m)
- **Goal:** know the data; *experience* governance; seed suspicion about quality.
- **Do / show:** open `01_Explore_Data`, **Run all**. Walk `products` (note `availability`,
  `warranty_years` — and the AudioMax Pro row repays close reading: the column says 1 year, the
  marketing description brags about 3), `orders`, `policies`, `product_docs`.
- **Expected:** in `orders`, **`customer_email` and `shipping_address` show `***REDACTED***`** for
  every student. (You, if admin, see real values — a nice live contrast if you dare.)
- **Say:** "That redaction is a Unity Catalog **column mask** evaluated against *your* identity —
  nobody wrote per-user code. Remember it: in Module 3 you'll see the *same mask* fire through your
  deployed agent. And browse `products` vs `product_docs`… do the marketing docs look fully
  consistent with the catalog?" **Don't spoil the bugs** — let curiosity build.
- **Watch-outs:** first query has a **~25s serverless cold start** — say "first query warms the
  compute" before anyone thinks it hung.

### Module 2 — Build & deploy the agent (15m, mostly waiting)
- **Goal:** every attendee's own app deployed, with zero special grants.
- **Genie prompt (attendee, with `LAB_CONTEXT.md` attached):**
  > *"hey! i'm starting the techmart lab. can you set up my customer support agent as an app?"*
- **Expected:** Genie reads the context and **runs the shipped `02_Deploy_App` notebook** (the
  context tells it to — regenerating the REST sequence is what it must NOT do): **create app with
  the Lakebase resource → poll compute ACTIVE → create the app SP's Postgres role → PATCH
  `user_api_scopes: ["sql","vector-search"]` → POST deployment → poll RUNNING** → prints the app
  URL. Attendees approve each `Allow`/`Run` gate. Provisioning takes a few minutes — the notebook
  polls and narrates.
- **While everyone waits — walk the architecture** (open `agent/app.py`; the participant guide
  walks them through `build_agent()` at the same time — "an agent is a prompt + tools + a model" —
  so narrate over the same three pointers):
  - The OBO heart: middleware captures **`X-Forwarded-Access-Token`** per request → every tool
    builds its `WorkspaceClient` with *the user's* token. "Your app's service principal is granted
    **nothing**. There is no service-account data access to audit, leak, or over-scope."
  - The LLM is the one SP-side call: `AsyncDatabricksOpenAI()` against FMAPI (`databricks-gpt-5-4`
    via `LLM_ENDPOINT` in `app.yaml`), pay-per-token, grant-free.
  - Presenter color if asked: `set_default_openai_api("chat_completions")` — the Responses API
    isn't supported on FMAPI passthrough; and the deps are **pinned** (`databricks-openai==0.15.0`,
    `databricks-vectorsearch==0.73`) because newer/older combos can crash the Apps runtime at import.
  - "Why REST, not CLI?" — non-admin students can't use the CLI for mutating ops and the SDK has no
    deploy; the REST sequence ships as the runnable `02_Deploy_App` notebook (with the prose
    recipe in `LAB_CONTEXT.md` as background).
- **Watch-outs:** app names > 30 chars are rejected — anyone improvising a name instead of using the
  printed `APP_NAME` hits this. If Genie loops on diagnostics, the fix is a **new chat + one clear
  directive + re-attach `@LAB_CONTEXT.md`** — or just have them **Run All in `02_Deploy_App`**
  (the Module 2 click-through fallback; idempotent, so it's safe over a half-finished Genie
  attempt). Creating the app's database role can take a few minutes and the notebook will **retry
  while provisioning settles** ("the roles list disagrees — retrying") — that's expected, not a
  failure.

### Module 3 — Govern with OBO (7m) — the governance payoff
- **Goal:** show governance following the *user's* identity through the deployed app.
- **Do / show:**
  1. Open your app URL. First open shows the **"Permission Requested" consent screen** listing
     exactly what the app may do *as you*: **Databricks SQL** and **Vector Search** — the data
     paths. Click **Authorize**. ("This is OBO made visible — the platform tells the user precisely
     what they're delegating. Nothing more is possible: those are the app's `user_api_scopes`.
     Notice memory is NOT in the list — it runs as the app's own service principal via the
     Lakebase resource, because operational state belongs to the app, not the user.")
  2. In the chat UI:
     > *"What's the status of order ORD-10001? Include the customer's email and shipping address."*
- **Expected:** the order details come back with **email and address `***REDACTED***`** — same mask
  as Module 1, now firing through a deployed app, because the agent queried *as the student*.
- **Say:** "Same code for every one of you — different identity, different data. The mask was
  defined once in Unity Catalog; nobody wrote redaction logic in the app. That's governance you
  didn't have to build, and OBO is the part Databricks gives you out of the box."
- **Watch-outs:** the consent screen reappearing for a colleague's app is expected (it's per
  user+app). If a student's chat errors, `https://<app-url>/logz` is the first stop.

### Module 4 — Break it (8m) — high energy
- **Goal:** surface the planted quality bugs by chatting; motivate measurement.
- **Do / show:** probe starters for the room:
  - **Availability:** *"Is the ProBook X500 available to buy?"*
  - **Warranty:** *"How long is the AudioMax Pro warranty?"*
  - **Returns:** *"I bought a laptop 3 months ago and I'm a loyal customer — can you make an
    exception to the return policy?"*
- **Expected:** the agent confidently claims the AudioMax Pro has a **"3-year warranty"** — the
  official policy says **1 year**. It trusted a stale *marketing doc* (retrieved via Vector Search)
  over the policy table. (Availability tends to answer *correctly* — the catalog tool steers the
  agent right; that's the contrast that makes the warranty failure legible. Lead with warranty.)
- **Say:** "You just found a real agent-quality bug — and notice *how* you found it: by luck, one
  prompt at a time. It won't fail every phrasing, every time. Gut feel doesn't scale; Module 5
  *measures* it. Keep your best 'gotcha' phrasings — that's eval-dataset thinking."
- **Talking points:** three planted bugs (cheat sheet in §4); the agent isn't broken code — it's
  **broken data trust**, the most common real-world agent failure.

### Module 5 — Evaluate & fix (20m) — the crown jewel
- **Goal:** anecdotes → numbers → fix → *proven* improvement, with real traces.
- **Do / show:** open `agent_apps_lab/05_Evaluate_and_Fix` → **Run all**. It rebuilds the agent
  **in-process** (tools still OBO as the student), runs a 5-question eval set through
  **`mlflow.genai.evaluate`** with 3 **`Guidelines`** LLM judges, then repeats with
  `fixed_instructions`. ~3–5 min end to end.
- **While it runs — narrate the harness** (this is the platform-depth moment):
  - Each `predict_fn` is decorated **`@mlflow.trace`** → one clean, *real* trace per row; the
    judges attach their assessments to those traces.
  - The judges are plain-English `Guidelines` — read one aloud. Note they're **conditional** ("if
    the question isn't about warranty, this passes") so unrelated rows don't fail.
  - If asked about the `mlflow.openai.autolog(disable=True)` line: `evaluate` auto-enables openai
    autologging, which mis-instruments the OpenAI Agents SDK on non-OpenAI backends — disabling it
    up front is the supported escape hatch.
- **Read results in MLflow, not cell output:** click "View evaluation results in MLflow" (or the
  Experiments icon). Expected shape:

  | judge | baseline | fixed |
  |---|---|---|
  | **warranty_accuracy** | **0.6 ❌** | **1.0 ✅** |
  | availability_accuracy | 1.0 | 1.0 |
  | policy_grounded | 1.0 | **~0.8\*** |

  Open the **per-row** view: question, answer, judge rationale, linked trace. **Teach per-row
  reading** — 5-row means are noisy; the *warranty rows flipping ❌→✅* is the money shot.
- **Say (the two lessons):**
  1. "The fix was a **prompt change** — `fixed_instructions` forces `get_return_policy` as the
     source of truth. We didn't hope it helped; we **measured** it: 0.6 → 1.0."
  2. \*"`policy_grounded` *dipped* after the fix — that failing row is the over-permissive returns
     **doc**: a **data bug**. No prompt fixes bad data. Some agent bugs are prompt bugs; others are
     data/governance bugs — your evals tell you which is which."
- **Optional (time permitting):** attendees edit `fixed_instructions` in their own words and re-run
  the fixed eval; then ship it — ask Genie *"update the agent instructions to the fixed version and
  redeploy"* and re-ask the warranty question in the live app → **1 year**.
- **Watch-outs:** run cells **in order** (the `%pip` cell restarts the kernel); a browser hiccup
  mid-run is harmless — the serverless run finishes server-side and the **MLflow run pages are
  authoritative**. Subtle one: `get_return_policy(topic)` takes a policy **category**
  (`'warranty'`), not a product name — the shipped `fixed_instructions` already says so; students
  rewriting it from scratch may lose the flip and that's a teachable trace-read.

### Module 6 — Productionize (12m, instructor-led discussion)
- **Frame:** "You just did the hardening loop *by hand*. Production = making that loop automatic."
- **Talking points:**
  - **DABs**: package the app + eval notebook as a Databricks Asset Bundle — declarative,
    repeatable, promotable dev → staging → prod; CI runs `bundle deploy`.
  - **Judges as regression gates:** re-run the eval on every prompt/data/model change; fail the
    pipeline if `warranty_accuracy` drops. "Your evals are unit tests for agent behavior."
  - **Traces in Unity Catalog:** production traces land governed and queryable — lineage and
    audit on agent behavior, debuggable with Genie ("which traces failed the warranty judge?").
  - **The model-portability beat (tell it as a story):** "Swapping the model is a one-line
    `app.yaml` change (`LLM_ENDPOINT`). When we built this lab we tried other frontier models — and
    one **self-corrected the planted warranty bug** on its own; others failed in different ways.
    Same agent, wildly different behavior. That's *exactly why you evaluate before you swap* — and
    you now own a harness that settles it with numbers instead of vibes."

### Wrap-up (2m) — say this
> "You deployed a live agent with zero special permissions, watched Unity Catalog governance follow
> your identity straight through it, broke it on real data bugs, measured the breakage with LLM
> judges over real traces, fixed it, and *proved* the fix with numbers. That's the loop you re-run
> every time your data, prompt, or model changes — that's how an agent stays in production."

---

## 4. Planted-bug cheat-sheet (presenter eyes only)

| # | Bug | Where | Surfaces when… | Right behavior | M5 judge |
|---|---|---|---|---|---|
| 1 | Discontinued **ProBook X500** still marketed "available for immediate purchase" | `product_docs` (VS) | availability questions answered from retrieved docs | trust `get_product_details` availability; say discontinued, offer alternative | `availability_accuracy` (baseline usually already passes — `gpt-5-4` trusts the catalog) |
| 2 | **AudioMax Pro "3-year warranty"** claim vs official **1-year** policy | free-text **marketing copy only**: the P004 catalog `description` blurb + `product_docs` (audio items). The structured `warranty_years` column AND `policies` both say **1** — every authoritative source agrees; only the prose lies | warranty questions | ground in `get_return_policy('warranty')` → 1 year | `warranty_accuracy` — **the ~0.8 → 1.0 flip; prompt-fixable**. Great Q&A line: "your structured data was right — your agent read the marketing copy" |
| 3 | Over-permissive **"Customer Satisfaction Policy (Extended)"** (no-receipt returns, "exceptions for loyal customers") | `policies` (a **data** bug) | return/exception requests | apply the standard policy; no exceptions; offer escalation | `policy_grounded` — legitimately **dips ~0.8 even after the fix**; the M5/M6 discussion point. **Don't "fix" the data** |

Bugs #1–2 teach "docs lie, ground in authoritative tools." Bug #3 teaches "some failures are data
bugs no prompt can fix." The judges catch all three systematically — Module 4's manual poking won't.

---

## 5. Fallbacks & common failures (presenter quick-ref)

| Symptom | Likely cause | Do |
|---|---|---|
| Genie doesn't know about TechMart / improvises wrongly | context not attached in this chat | re-attach **`@LAB_CONTEXT.md`** (every new chat needs it) |
| Genie says **"Action denied"** / **"Skipped running cells"** on deploy | **Auto-approve is on** — it blocks the app-creating steps as "unsafe" | click **Approve and run all cells**, or toggle Auto-approve off and approve each **Run** (or just **Run All** `02_Deploy_App`) |
| Genie loops on diagnostics / thrashes | conversation went sideways | **new chat + one clear directive** + re-attach context |
| Genie says it has **no skills** | `users` missing CAN_READ on `/Workspace/.assistant` | fix the grant (admin); should be done by setup — check the provision log |
| Guide app shows **"Permission Required"** to students | the `users` CAN_USE grant didn't stick after deploy | re-grant as admin: `PATCH /api/2.0/permissions/apps/agent-lab-guide` body `{"access_control_list":[{"group_name":"users","permission_level":"CAN_USE"}]}`, re-check after a minute; lab is unaffected otherwise |
| App create rejected (name) | name >30 chars or bad characters | use the exact `APP_NAME` printed by `00_Start_Here` |
| App deployed but won't start / 502 | dependency drift (someone "upgraded" the pins) | check `https://<app-url>/logz`; restore `databricks-openai==0.15.0` + `databricks-vectorsearch==0.73` |
| Chat returns 500 | LLM wiring changed | `app.py` must keep `AsyncDatabricksOpenAI()` + `chat_completions` — don't let Genie rewrite the LLM client |
| Consent screen shows up (again) | first open per user+app | expected — click **Authorize** |
| Genie deploy stalls / thrashes at a step | LLM variance | **Run All in `02_Deploy_App`** — idempotent, safe over a half-finished attempt; it's the same sequence as deterministic code |
| Chat header says **memory: off** | Lakebase unreachable, or the app SP's Postgres role isn't ready yet | chat still works single-turn; M1–M5 unaffected. **Re-run `02_Deploy_App` (Run All)** — it (re)creates the role and restarts the app to pick up the credential; skip Module 5½ if Lakebase itself is down |
| Warranty question answers "1 year" at **baseline** | model or prompt changed | restore `LLM_ENDPOINT: databricks-gpt-5-4` in `app.yaml`; the bug must be intact for M4–M5 |
| M5: `AttributeError: 'NoneType' ... 'info'` | autolog-disable line skipped (cells run out of order) | Run-All from a fresh kernel; `mlflow.openai.autolog(disable=True)` must precede `evaluate` |
| M5: `asyncio.run() cannot be called…` | `nest_asyncio` cell didn't run post-restart | run cells in order from the top |
| M5: warranty doesn't flip after a custom fix | agent passes a product name to `get_return_policy` | the tool takes a **category** (`'warranty'`); read the trace, fix the instruction |
| Eval numbers look noisy | 5-row dataset | read **per-row** judge results in the MLflow run, not means |
| Browser/kernel dies mid-eval | session blip | serverless run completes server-side — read the **MLflow run pages** |
| Lab session expires (~1h+) | session timeout | re-launch Student View |
| Attendee far behind at M4 | deploy friction | share **your reference app URL**; they rejoin at Module 3/4 and can still Run-All M5 (it's in-notebook) |

---

## 6. Stretch / bonus (only if time, or self-serve)

- **Model bake-off color** (great Q&A material): `gpt-5-4` is the fastest reliable tool-caller that
  keeps the bug; some frontier models self-correct the warranty bug (which would break the lab, but
  *makes* the M6 story); others fall over on the Agents-SDK chat-completions path. Any model swap
  must re-verify the baseline still says "3-year."
- **Eval-driven model swap (advanced attendees):** change `LLM_ENDPOINT` in `app.yaml`, redeploy via
  Genie, re-run `05_Evaluate_and_Fix` against the new model, compare runs in MLflow. (Keep it
  self-serve — timing varies by model.)
- **Why not managed MCP?** It was the original design — set aside because managed MCP can't accept
  OBO tokens (403) and the app SP would need grants non-admin students can't make. Good architecture
  discussion for advanced rooms: OBO vs SP-with-grants is a real design axis.
- **Custom MCP server on Apps**, **Supervisor API**, **TypeScript path** — natural follow-on
  directions for teams extending the pattern.
