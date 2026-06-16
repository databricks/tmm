# 🛠️ Build a Custom AI Agent on Databricks Apps — From Prompt to Production

A **~90-minute, coding-agent-driven** hands-on workshop (built for **Data + AI Summit 2026**).
Participants build a custom AI customer-support agent for **TechMart** (a fictional electronics
retailer), deploy it live on **Databricks Apps**, govern it, deliberately **break** it on planted
data bugs, **measure** the breakage with LLM judges, **fix** it, and **prove** the fix with numbers —
the full agent-hardening loop, in one sitting.

> **Coding-agent-driven:** participants direct **Genie Code** (the in-workspace coding agent) in
> plain English; it writes and deploys for them. Every step also has a click-through fallback, so a
> hiccup never blocks the room.

**The platform story:** custom agents on **Databricks Apps** · **OpenAI Agents SDK** harness ·
tools via **UC Functions + Vector Search, all running on-behalf-of-user (OBO)** · conversation
memory in **Lakebase** (managed Postgres) · LLM via **Foundation Model APIs** (`databricks-gpt-5`,
swappable in `app.yaml`) · governance via **OBO + UC column masks** · observability via **MLflow 3
tracing & evaluation**.

---

## What participants do

| # | Module | The beat |
|---|--------|----------|
| 0 | **Meet Genie Code** | Attach `LAB_CONTEXT.md`; the in-workspace coding agent becomes your pair |
| 1 | **Explore the data** | A live UC **column mask** redacts order PII *for you specifically*; the marketing docs look… off |
| 2 | **Build & deploy** | One plain-English prompt → Genie deploys your own app (`sql` + `vector-search` scopes + a `postgres` memory resource, **zero SP grants on the data**) |
| 3 | **Govern with OBO** | The same column mask follows your identity *through the deployed app* — governance you didn't build |
| 4 | **Break it** | Chat with the agent and surface the planted quality bugs (the warranty answer is the star) |
| 5 | **Evaluate & fix** | MLflow **LLM judges** → baseline fails → fix the prompt → re-run → the score flips, with real traces |
| 5½ | **Visit the memory** | Query your own chat transcript out of Lakebase (Postgres) — and the app's **≡ Journal** reads the same tables |
| 6 | **Productionize** | Recap: package as a Databricks Asset Bundle, traces in UC, judges as CI regression gates |

---

## How it works

- **All-OBO data access.** Every tool (UC function calls, Vector Search) runs as the *signed-in
  user* via the app's forwarded token — so the app's service principal needs **no grants** on the
  shared data, and Unity Catalog governance (the PII column mask) follows the user automatically.
  The LLM runs as the app SP on Foundation Model APIs (pay-per-token, no grant).
- **Conversation memory in Lakebase.** The app is created with a `postgres` resource; transcripts
  are written **as the app's own SP** into a per-app schema it owns. Memory is optional — if
  Lakebase is unreachable the chat degrades gracefully to single-turn.
- **The agent is a prompt + tools + a model.** See `agent/app.py` → `build_agent()`. The shipped
  instructions are deliberately minimal ("v1") — Module 5 *measures* what that costs, and the fix
  is an edit to exactly that string.
- **Three planted bugs** drive Modules 4–5: a discontinued product still marketed as available, a
  marketing-copy warranty term (3 yr) that contradicts the official policy (1 yr), and an
  over-permissive returns policy. A good agent trusts the authoritative catalog/policy over the
  marketing prose — and the evals measure exactly that. (The warranty bug is the one that reliably
  flips ❌→✅ after the prompt fix; the returns one is a *data* bug no prompt fully fixes.)

---

## Repository layout

```
agent_apps_workshop/
├── README.md                                  ← you are here
├── docs/lab-guide/                            ← the illustrated participant guide (+ screenshots)
├── slides-app/                                ← the companion "field guide" deck (served at /deck)
│   ├── app.py · app.yaml · requirements.txt   ←   a tiny FastAPI deck viewer
│   └── decks/8-bit-orbit.html                 ←   the deck itself
└── vocareum/voc/private/courseware/           ← the deployable courseware payload
    ├── build_zips.sh · render_guide.py · config.json
    ├── agent_apps_setup/                       ← privileged provisioning notebook + lab-guide app
    │   ├── agent_apps_setup.py                 ←   creates the shared catalog/data/VS/tools/warehouse/Lakebase
    │   └── guide_app/                          ←   the per-workspace lab-guide app (serves the guide + deck)
    └── agent_apps_lab/                         ← per-participant content (copied into each home)
        ├── 00_Start_Here.py · 01_Explore_Data.py · 02_Deploy_App.py · 05_Evaluate_and_Fix.py
        ├── LAB_CONTEXT.md                      ←   the lab brief you hand to Genie Code
        └── agent/                              ←   the all-OBO agent starter participants deploy
```

> The courseware lives under `vocareum/voc/private/courseware/` because it's packaged for the
> **Databricks Academy / Vocareum** lab framework, which expects that path. Nothing about the
> notebooks or the agent is Vocareum-specific — they run on any Databricks workspace that meets the
> prerequisites below.

---

## Run it yourself

### Prerequisites (a Databricks workspace with)
- **Unity Catalog** + **serverless** notebooks/SQL
- **Databricks Apps** with **User Authorization (OBO)** enabled
- **Vector Search**, **Lakebase** (managed Postgres), and **Foundation Model APIs** (a `gpt-5`-class
  endpoint; swappable via `LLM_ENDPOINT` in `agent/app.yaml`)
- **Genie Code** (the in-workspace coding agent) for the driven path — the click-through notebooks
  work without it

### 1. Provision the shared assets (once per workspace)
Run **`agent_apps_setup/agent_apps_setup.py`** as a workspace admin. It creates the shared catalog
`agent_apps_workshop.shared` (TechMart tables + the three planted bugs), the `product_docs_vs`
Vector Search index, the three UC function tools, a shared SQL warehouse, the Lakebase memory
project, the governance (PII column mask + grants), and deploys the shared **lab-guide app**.

### 2. Give each participant the lab content
Copy `agent_apps_lab/` into each participant's workspace home. They start at **`00_Start_Here`**.

### 3. (Vocareum/DB Academy packaging) build the upload artifacts
```bash
bash vocareum/voc/private/courseware/build_zips.sh
# → dist/{config.json, agent_apps_setup.zip, agent_apps_lab.zip}
```
`build_zips.sh` also bakes the lab-guide app payload: it renders `docs/lab-guide/README.md` into a
self-contained `guide.html` (screenshots inlined) and copies `slides-app/decks/8-bit-orbit.html` as
the deck. These are build artifacts (git-ignored) — rebuild them, don't commit them.

---

## Guides & companion deck

- **Participant guide:** [`docs/lab-guide/README.md`](docs/lab-guide/README.md) — the illustrated,
  step-by-step walkthrough (this is also what the lab-guide app serves).
- **Presenter guide:** [`docs/presenter-guide.md`](docs/presenter-guide.md) — for whoever runs the
  room: pitch, timing, a module-by-module script, the planted-bug cheat-sheet, and fallbacks.
- **Companion deck:** `slides-app/decks/8-bit-orbit.html` — the "field guide" deck, served by the
  lab-guide app at `/deck`. Run `slides-app/` locally to preview it.

---

## Credits

Adapted from Robert Mosley's
[databricks-agentic-app-workshop](https://github.com/rmosleydb/databricks-agentic-app-workshop).
