"""TechMart support agent — ALL-OBO starter for Databricks Apps.

Every DATA call (UC function tools, Vector Search) runs **on-behalf-of the signed-in user** via
the `X-Forwarded-Access-Token` header — the app's service principal is granted NOTHING on the
shared data, and UC governance (the PII column mask) follows the user automatically. The LLM
runs as the app SP via Foundation Model APIs (pay-per-token, no grant).

Conversation memory: the app is created with a **`postgres` resource** (the shared Lakebase
project); transcripts are written **as the app SP** into a per-app schema it owns. Memory is
OPTIONAL — if Lakebase is unreachable the chat still works, single-turn.

Chat UI at `GET /` — replies STREAM over SSE (`POST /chat/stream`) with tool calls printed
live; `POST /chat` stays as the classic request/response path (the eval notebook uses it).
The ≡ JOURNAL lists past sessions (`GET /sessions`) to resume. Health at `GET /health`.
Deploy with the shipped `02_Deploy_App` notebook (Run All).
"""

import contextvars
import json
import logging
import os
import re

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem, StatementState
from databricks_openai import AsyncDatabricksOpenAI  # FMAPI-aware OpenAI client (handles routing+auth)
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

# LLM: the Databricks-provided OpenAI client (a hand-built AsyncOpenAI base_url FAILS). Runs as
# the app SP; FMAPI is pay-per-token, no grant needed. Data tools stay OBO below.
set_default_openai_client(AsyncDatabricksOpenAI())
# chat_completions, NOT the Responses API — FMAPI does not support Responses passthrough for
# several models.
set_default_openai_api("chat_completions")
# Stops the SDK shipping traces to api.openai.com (noisy non-fatal 401s otherwise).
set_tracing_disabled(True)

CATALOG = os.getenv("WORKSHOP_CATALOG", "agent_apps_workshop")
SCHEMA = os.getenv("WORKSHOP_SCHEMA", "shared")
VS_INDEX = os.getenv("WORKSHOP_VS_INDEX", "product_docs_vs")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "databricks-gpt-5-4")
# Resolve the warehouse by NAME (portable); an explicit WAREHOUSE_ID env wins.
WAREHOUSE_NAME = os.getenv("WAREHOUSE_NAME", "agent-apps-shared")
_WAREHOUSE_ID = os.getenv("WAREHOUSE_ID", "")
# Lakebase conversation memory (shared autoscaling project created by workshop setup).
# Set LAKEBASE_AUTOSCALING_PROJECT="" to disable memory entirely.
LAKEBASE_PROJECT = os.getenv("LAKEBASE_AUTOSCALING_PROJECT", "agent-apps-memory")
LAKEBASE_BRANCH = os.getenv("LAKEBASE_AUTOSCALING_BRANCH", "production")
# Per-app memory schema: the app SP creates and OWNS it on first use (no cross-SP grants
# needed). ⚠️ Keep `public` free of agent_* tables — search_path is "<schema>, public" and a
# foreign public table breaks create-if-missing.
MEMORY_SCHEMA = os.getenv("MEMORY_SCHEMA") or (
    "memory_" + (re.sub(r"[^a-z0-9_]", "_", os.getenv("DATABRICKS_APP_NAME", "").lower()) or "dev")
)

logger = logging.getLogger("techmart-agent")

# Per-request signed-in-user token (set by the FastAPI middleware from X-Forwarded-Access-Token).
_user_token: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_token", default=None)


def user_client() -> WorkspaceClient:
    """WorkspaceClient acting as the signed-in user (OBO). Falls back to the app SP locally."""
    tok = _user_token.get()
    if tok:
        return WorkspaceClient(token=tok, auth_type="pat")
    return WorkspaceClient()  # local dev / no forwarded token


def _warehouse_id() -> str:
    """Resolve the shared warehouse id: explicit env, else discover by name (cached)."""
    global _WAREHOUSE_ID
    if _WAREHOUSE_ID:
        return _WAREHOUSE_ID
    wh = next((x for x in user_client().warehouses.list() if x.name == WAREHOUSE_NAME), None)
    _WAREHOUSE_ID = wh.id if wh else ""
    return _WAREHOUSE_ID


def _run_sql(statement: str, params: list[StatementParameterListItem] | None = None) -> str:
    """Run a one-row SQL statement as the signed-in user and return the scalar result."""
    wh_id = _warehouse_id()
    if not wh_id:
        return f"Order/data lookup unavailable: no warehouse named '{WAREHOUSE_NAME}' found."
    resp = user_client().statement_execution.execute_statement(
        warehouse_id=wh_id, statement=statement, parameters=params or [], wait_timeout="30s",
    )
    if resp.status and resp.status.state != StatementState.SUCCEEDED:
        err = resp.status.error.message if (resp.status and resp.status.error) else str(resp.status.state)
        return f"Query failed: {err}"
    rows = resp.result.data_array if resp.result else None
    return rows[0][0] if rows and rows[0] and rows[0][0] is not None else "No result."


# ---- Tools (ALL on-behalf-of-user) -----------------------------------------------------------

@function_tool
def get_product_details(product_name: str) -> str:
    """Look up a TechMart product by name: price, category, availability, description."""
    return _run_sql(
        f"SELECT {CATALOG}.{SCHEMA}.get_product_details(:p) AS r",
        [StatementParameterListItem(name="p", value=product_name)],
    )


@function_tool
def get_return_policy(topic: str = "") -> str:
    """Return TechMart's official store policies — returns, refunds, exchanges (optionally filtered by topic)."""
    return _run_sql(
        f"SELECT {CATALOG}.{SCHEMA}.get_return_policy(:t) AS r",
        [StatementParameterListItem(name="t", value=topic or None)],
    )


@function_tool
def get_order_status(order_identifier: str) -> str:
    """Look up an order by ID (e.g. ORD-10001) or customer email. Customer PII is column-masked
    by Unity Catalog and — because this runs on-behalf-of-the-user — is redacted unless the
    signed-in user is a workshop admin."""
    return _run_sql(
        f"SELECT {CATALOG}.{SCHEMA}.get_order_status(:a) AS r",
        [StatementParameterListItem(name="a", value=order_identifier)],
    )


@function_tool
def search_products(query: str) -> str:
    """Semantic search over TechMart product docs (Vector Search), as the signed-in user."""
    res = user_client().vector_search_indexes.query_index(
        index_name=f"{CATALOG}.{SCHEMA}.{VS_INDEX}",
        columns=["product_id", "product_name", "indexed_doc"],
        query_text=query,
        num_results=3,
    )
    rows = res.result.data_array if res.result else None
    if not rows:
        return "No matching products."
    return "\n".join(f"{r[1]}: {r[2]}" for r in rows)


@function_tool
def whoami() -> str:
    """Identity the agent is acting as (verifies OBO: a real username = OBO working)."""
    try:
        return user_client().current_user.me().user_name
    except Exception as e:  # noqa: BLE001
        return f"Could not resolve identity (OBO token missing?): {e}"


def build_agent() -> Agent:
    return Agent(
        name="TechMart Support",
        # Deliberately minimal "v1" instructions — no source-of-truth routing. That routing is
        # exactly what Module 5 measures the absence of (the planted warranty bug) and what the
        # fixed_instructions add. Don't harden this prompt; the lab depends on it being naive.
        instructions=(
            "You are TechMart's customer-support agent. Use get_product_details for product facts, "
            "search_products for semantic product questions, get_return_policy for store policies, "
            "and get_order_status for order/PII lookups. Be concise and accurate."
        ),
        tools=[get_product_details, get_return_policy, get_order_status, search_products, whoami],
        model=LLM_ENDPOINT,
    )


# ---- FastAPI app -----------------------------------------------------------------------------

app = FastAPI(title="TechMart Support Agent (all-OBO)")


@app.middleware("http")
async def capture_user_token(request: Request, call_next):
    # Databricks Apps forwards the signed-in user's downscoped token here (user authorization).
    # The DATA tools use it (OBO) so UC governance follows the user; the LLM uses the SP client
    # configured once at module load.
    token = request.headers.get("x-forwarded-access-token")
    reset = _user_token.set(token)
    try:
        return await call_next(request)
    finally:
        _user_token.reset(reset)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # set by the chat UI (one id per browser tab/session)


def _memory_session(session_id: str):
    """Lakebase conversation memory — authenticates as THE APP's SP, writes to the per-app
    schema it owns (the deploy notebook sets up the SP's Postgres role). Returns None when
    memory can't be used — the chat then runs memoryless."""
    if not LAKEBASE_PROJECT:
        return None
    try:
        from databricks_openai.agents import AsyncDatabricksSession

        return AsyncDatabricksSession(
            session_id=session_id,
            project=LAKEBASE_PROJECT,
            branch=LAKEBASE_BRANCH,
            schema=MEMORY_SCHEMA,
            create_tables=True,
        )
    except Exception as e:  # noqa: BLE001 — memory is best-effort; never block the chat
        logger.warning("Lakebase memory unavailable (%s) — running memoryless.", e)
        return None


_memory_shared = False


async def _share_memory_schema(session) -> None:
    """One-time: share this app's transcript schema read-only (PUBLIC) so participants can
    browse it in the Lakebase SQL editor (Module 5½). Failure is non-fatal."""
    global _memory_shared
    if _memory_shared:
        return
    try:
        from sqlalchemy import text

        engine = session._lakebase.engine  # noqa: SLF001 — no public engine accessor on the session
        async with engine.begin() as conn:
            await conn.execute(text(f'GRANT USAGE ON SCHEMA "{MEMORY_SCHEMA}" TO PUBLIC'))
            await conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA "{MEMORY_SCHEMA}" TO PUBLIC'))
        _memory_shared = True
        logger.info("Shared memory schema %s read-only with workshop participants", MEMORY_SCHEMA)
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not share memory schema for the Module 5½ browse (%s)", e)


def _tool_calls(result) -> list[dict]:
    """Tool invocations from this run — the app layer surfacing the agent's machinery for the
    chat UI's activity feed. Best-effort: observability must never break the chat."""
    calls = []
    try:
        for item in getattr(result, "new_items", []) or []:
            if getattr(item, "type", "") == "tool_call_item":
                raw = getattr(item, "raw_item", None)
                calls.append({
                    "tool": getattr(raw, "name", "?"),
                    "args": str(getattr(raw, "arguments", "") or "")[:120],
                })
    except Exception:  # noqa: BLE001
        pass
    return calls


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/me")
async def me():
    """Who the agent is acting as right now — OBO made visible in the UI header."""
    try:
        return {"user": user_client().current_user.me().user_name}
    except Exception as e:  # noqa: BLE001
        return {"user": None, "error": str(e)[:200]}


@app.post("/chat")
async def chat(req: ChatRequest):
    agent = build_agent()
    session = _memory_session(req.session_id) if req.session_id else None
    if session is not None:
        try:
            result = await Runner.run(agent, req.message, session=session)
            await _share_memory_schema(session)  # one-time; enables the Module 5½ browse
            return {"response": result.final_output, "memory": "lakebase",
                    "tool_calls": _tool_calls(result)}
        except Exception as e:  # noqa: BLE001 — degrade gracefully, never fail the chat on memory
            logger.warning("Lakebase memory failed mid-chat (%s) — retrying memoryless.", e)
    result = await Runner.run(agent, req.message)
    return {"response": result.final_output, "memory": "off", "tool_calls": _tool_calls(result)}


# ---- Streaming (SSE) -------------------------------------------------------------------------

def _sse(obj: dict) -> str:
    """One server-sent event carrying a JSON payload."""
    return "data: " + json.dumps(obj) + "\n\n"


async def _agent_events(result):
    """Translate Agents-SDK stream events into the UI's small vocabulary: live 🔧 tool chips
    (`tool_call`) and incremental text (`delta`). Field access is best-effort — observability
    must never break the chat."""
    async for event in result.stream_events():
        if event.type == "raw_response_event":
            if getattr(event.data, "type", "") == "response.output_text.delta":
                delta = getattr(event.data, "delta", "")
                if delta:
                    yield {"type": "delta", "text": delta}
        elif event.type == "run_item_stream_event" and getattr(event.item, "type", "") == "tool_call_item":
            raw = getattr(event.item, "raw_item", None)
            yield {"type": "tool_call", "tool": getattr(raw, "name", "?"),
                   "args": str(getattr(raw, "arguments", "") or "")[:120]}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Streaming twin of POST /chat (which stays untouched for the eval notebook). Events:
    `tool_call` (chips appear WHILE the agent works), `delta` (text), `done` (memory status),
    `error`. Same graceful-degradation contract as /chat: memory failures never kill the chat —
    before the first event we silently retry memoryless; after, we surface an error (a silent
    retry would double-print text already on screen)."""
    async def gen():
        agent = build_agent()
        session = _memory_session(req.session_id) if req.session_id else None
        if session is not None:
            emitted = False
            try:
                result = Runner.run_streamed(agent, req.message, session=session)
                async for ev in _agent_events(result):
                    emitted = True
                    yield _sse(ev)
                await _share_memory_schema(session)  # one-time; enables the Module 5½ browse
                yield _sse({"type": "done", "memory": "lakebase"})
                return
            except Exception as e:  # noqa: BLE001
                logger.warning("Lakebase memory failed mid-stream (%s) — %s.", e,
                               "surfacing error" if emitted else "retrying memoryless")
                if emitted:
                    yield _sse({"type": "error", "detail": str(e)[:200]})
                    return
        try:
            result = Runner.run_streamed(agent, req.message)
            async for ev in _agent_events(result):
                yield _sse(ev)
            yield _sse({"type": "done", "memory": "off"})
        except Exception as e:  # noqa: BLE001
            yield _sse({"type": "error", "detail": str(e)[:200]})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- Session picker (the JOURNAL) ------------------------------------------------------------

def _msg_text(content) -> str:
    """Flatten a stored message's content (plain string OR content-part list) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


@app.get("/sessions")
async def list_sessions(limit: int = 15):
    """This app's recent conversations, read from its OWN Lakebase schema as the app SP — the
    same `agent_sessions`/`agent_messages` tables participants browse in Module 5½. Optional
    chrome: returns [] instead of 500 whenever memory is unavailable."""
    probe = _memory_session("_session_list_probe")  # engines are cached per-config — cheap
    if probe is None:
        return {"sessions": []}
    try:
        from sqlalchemy import text

        q = text(
            f'SELECT s.session_id, to_char(s.updated_at, \'YYYY-MM-DD HH24:MI\') AS updated, '
            f'  (SELECT count(*) FROM "{MEMORY_SCHEMA}".agent_messages m '
            f'    WHERE m.session_id = s.session_id) AS n, '
            f'  (SELECT m.message_data FROM "{MEMORY_SCHEMA}".agent_messages m '
            f'    WHERE m.session_id = s.session_id ORDER BY m.id LIMIT 1) AS first_msg '
            f'FROM "{MEMORY_SCHEMA}".agent_sessions s '
            f'ORDER BY s.updated_at DESC LIMIT :n'
        )
        engine = probe._lakebase.engine  # noqa: SLF001 — same accessor as _share_memory_schema
        async with engine.connect() as conn:
            rows = (await conn.execute(q, {"n": max(1, min(limit, 50))})).fetchall()
        sessions = []
        for sid, updated, n, first in rows:
            title = ""
            try:
                if first:
                    title = _msg_text(json.loads(first).get("content"))[:80]
            except Exception:  # noqa: BLE001
                pass
            sessions.append({"session_id": sid, "updated": updated, "messages": n, "title": title})
        return {"sessions": sessions}
    except Exception as e:  # noqa: BLE001
        logger.warning("Session list unavailable (%s)", e)
        return {"sessions": []}


@app.get("/sessions/{session_id}/messages")
async def session_messages(session_id: str):
    """One session's transcript, simplified for the chat UI: user/bot turns + 🔧 tool chips.
    Uses the memory session's own get_items() so the parsing matches what the agent replays."""
    session = _memory_session(session_id)
    if session is None:
        return {"messages": []}
    try:
        msgs = []
        for it in await session.get_items():
            if not isinstance(it, dict):
                continue
            if it.get("role") in ("user", "assistant"):
                text_ = _msg_text(it.get("content"))
                if text_:
                    msgs.append({"who": "you" if it["role"] == "user" else "bot", "text": text_})
            elif it.get("type") == "function_call":
                msgs.append({"who": "tool", "tool": it.get("name", "?"),
                             "args": str(it.get("arguments", ""))[:120]})
        return {"messages": msgs}
    except Exception as e:  # noqa: BLE001
        logger.warning("Session transcript unavailable (%s)", e)
        return {"messages": []}


# Minimal single-file chat UI so the agent is testable in the browser. The fetch() below is
# same-origin, so Databricks Apps injects the signed-in user's X-Forwarded-Access-Token — the
# tools run OBO and UC governance (PII masking) follows whoever is signed in.
_CHAT_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>TechMart Support Terminal</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,800&family=Spline+Sans+Mono:wght@400;500;700&family=Libre+Barcode+39+Text&display=swap" rel="stylesheet">
<style>
 /* THE REGISTER TAPE — TechMart is a store, so the support console is a point-of-sale
    back-office terminal: the chat log is a receipt printing on warm paper, tool calls are
    itemized line items with dotted leaders, the session picker is the register journal. */
 :root{--paper:#F2EBDB;--tape:#FBF6EA;--ink:#26201A;--faded:#7A6E5C;--red:#C13B2A;--blue:#2E5E7E;--rule:#C9BCA2}
 *{box-sizing:border-box}
 html,body{margin:0}
 body{background:var(--paper);color:var(--ink);font-family:'Spline Sans Mono',monospace;font-size:15px;line-height:1.55}
 body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:9;opacity:.55;
   background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/><feColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.05 0'/></filter><rect width='180' height='180' filter='url(%23n)'/></svg>")}
 .wrap{max-width:780px;margin:0 auto;padding:36px 24px 70px}
 header{display:flex;justify-content:space-between;align-items:flex-end;gap:18px;border-bottom:3px double var(--ink);padding-bottom:16px}
 .tag{font-size:11px;font-weight:700;letter-spacing:.38em;color:var(--faded);animation:rise .5s .05s both}
 h1{font-family:'Bricolage Grotesque',sans-serif;font-weight:800;font-size:54px;line-height:.95;letter-spacing:-2px;margin:2px 0 0;animation:rise .5s .12s both}
 h1 .tm{color:var(--red)}
 .bc{font-family:'Libre Barcode 39 Text',cursive;font-size:34px;margin-top:2px;animation:rise .5s .2s both}
 .meta{text-align:right;font-size:12.5px;color:var(--faded);max-width:46%;animation:rise .5s .26s both}
 .meta>div{margin-top:3px}
 #who{color:var(--ink)}
 #mem{color:var(--blue);font-weight:500}
 #mem.off{color:var(--red)}
 .btns{margin-top:9px}
 .ghost{font-family:inherit;font-size:11.5px;font-weight:700;letter-spacing:.08em;padding:6px 10px;margin-left:8px;
        background:transparent;border:1.5px solid var(--ink);color:var(--ink);cursor:pointer;box-shadow:2px 2px 0 var(--ink)}
 .ghost:hover{background:var(--ink);color:var(--tape)}
 .ghost:active{transform:translate(1px,1px);box-shadow:1px 1px 0 var(--ink)}
 #sp{display:none;margin:18px 0 0;border:1.5px dashed var(--ink);background:var(--tape)}
 #sp .hd{font-size:11px;font-weight:700;letter-spacing:.3em;color:var(--faded);padding:10px 14px;border-bottom:1px dashed var(--rule)}
 .sess{display:block;width:100%;text-align:left;font-family:inherit;font-size:13px;color:var(--ink);background:transparent;
       border:none;border-bottom:1px dashed var(--rule);padding:10px 14px;cursor:pointer}
 .sess:hover{background:var(--paper);color:var(--red)}
 .sess .meta2{color:var(--faded);font-size:11.5px;letter-spacing:.04em}
 #log{display:flex;flex-direction:column;background:var(--tape);border:1px solid var(--rule);margin:26px 0 0;padding:4px 0 12px;
      box-shadow:0 3px 0 rgba(38,32,26,.07)}
 #log::before,#log::after{content:'';display:block;height:9px;flex:none;
      background:radial-gradient(circle at 9px 0px,var(--paper) 5.5px,transparent 6px);background-size:18px 9px;background-position:center top}
 #log::after{transform:rotate(180deg)}
 .cut{font-size:11px;letter-spacing:.18em;color:var(--faded);text-align:center;padding:10px 16px 8px}
 .msg{position:relative;padding:13px 18px 15px;border-bottom:1px dashed var(--rule);white-space:pre-wrap;animation:printin .3s ease-out both}
 .msg::before{display:block;font-size:10px;font-weight:700;letter-spacing:.3em;margin-bottom:6px}
 .you{background:#F3ECDC}
 .you::before{content:'CUSTOMER ▸';color:var(--faded)}
 .bot::before{content:'✱ TECHMART';color:var(--red)}
 .bot.live::after{content:'▌';color:var(--red);animation:blink .9s steps(1) infinite}
 .tools{display:flex;flex-direction:column;gap:3px;padding:10px 18px 12px;border-bottom:1px dashed var(--rule);animation:printin .3s ease-out both}
 .tools::before{content:'OPERATIONS — RUN AS YOU (OBO)';font-size:10px;font-weight:700;letter-spacing:.3em;color:var(--faded);margin-bottom:4px}
 .chip{display:flex;align-items:baseline;gap:8px;font-size:12.5px;color:var(--blue)}
 .chip .lead{flex:1;border-bottom:2px dotted var(--rule);transform:translateY(-3px)}
 .chip .ok{color:var(--red);font-weight:700}
 form{display:flex;gap:12px;margin-top:24px}
 input{flex:1;padding:14px 15px;background:#FFFCF2;border:2px solid var(--ink);color:var(--ink);font-family:inherit;font-size:15px;box-shadow:3px 3px 0 var(--ink)}
 input::placeholder{color:#A8987F}
 input:focus{outline:none;border-color:var(--red);box-shadow:3px 3px 0 var(--red)}
 #b{padding:14px 26px;border:2px solid var(--ink);background:var(--red);color:#FFF6E8;font-family:'Bricolage Grotesque',sans-serif;
    font-weight:800;font-size:15px;letter-spacing:.06em;cursor:pointer;box-shadow:3px 3px 0 var(--ink)}
 #b:hover{background:var(--ink)}
 #b:active{transform:translate(2px,2px);box-shadow:1px 1px 0 var(--ink)}
 #b:disabled{opacity:.5;cursor:default}
 #sugs{display:flex;flex-wrap:wrap;gap:9px;margin-top:14px}
 .sug{font-family:inherit;font-size:12.5px;color:var(--ink);background:var(--tape);border:1.5px solid var(--ink);
      padding:7px 12px;cursor:pointer;box-shadow:2px 2px 0 var(--ink)}
 .sug:hover{color:var(--red);border-color:var(--red);box-shadow:2px 2px 0 var(--red)}
 .sug:active{transform:translate(1px,1px)}
 #guide{margin-top:26px;font-size:12.5px;color:var(--faded)}
 a{color:var(--red)}
 @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
 @keyframes printin{from{opacity:0;transform:translateY(-5px)}to{opacity:1;transform:none}}
 @keyframes blink{50%{opacity:0}}
</style></head>
<body><div class="wrap">
 <header>
  <div class="brand">
   <div class="tag">CUSTOMER SUPPORT TERMINAL</div>
   <h1>TECH<span class="tm">MART</span></h1>
   <div class="bc">*TECHMART-OBO*</div>
  </div>
  <div class="meta">
   <div id="dt"></div>
   <div id="who">acting as: …</div>
   <div><span id="mem">memory: …</span></div>
   <div class="btns"><button id="ns" class="ghost" type="button">⟳ NEW SESSION</button><button id="ss" class="ghost" type="button">≡ JOURNAL</button></div>
  </div>
 </header>
 <div id="sp"></div>
 <div id="log"></div>
 <form id="f"><input id="m" autocomplete="off" placeholder="Ask the agent…" autofocus><button id="b">SEND</button></form>
 <div id="sugs"></div>
 <div id="guide"></div>
</div>
<script>
 const log=document.getElementById('log'),f=document.getElementById('f'),m=document.getElementById('m'),b=document.getElementById('b'),mem=document.getElementById('mem');
 document.getElementById('dt').textContent=new Date().toISOString().slice(0,10)+' · REG 04 · LANE 1';
 // Link the shared lab-guide app: app hosts are <name>-<workspace-id>.<domain>, so swap our app
 // name for the guide's. Zero API calls; degrades to nothing if the host shape ever changes.
 (function(){const h=location.host.match(/-(\\d+)\\.(.+)$/);if(h){
   const u='https://agent-lab-guide-'+h[1]+'.'+h[2];
   document.getElementById('guide').innerHTML='📖 <a href="'+u+'" target="_blank">Lab guide</a> · <a href="'+u+'/deck" target="_blank">field-guide deck</a>';}})();
 // OBO, visible: ask the app who it is acting as (the /me call carries YOUR forwarded token).
 fetch('/me').then(r=>r.json()).then(j=>{
   document.getElementById('who').textContent='acting as: '+(j.user||'(no OBO token — local dev?)');
 }).catch(()=>{});
 // One conversation session at a time; the transcript lives in Lakebase under this id.
 let SID;
 function cut(t){const d=document.createElement('div');d.className='cut';d.textContent=t;log.appendChild(d);}
 function newSession(){SID=(crypto.randomUUID?crypto.randomUUID():String(Date.now()));log.innerHTML='';
   cut('✂ ─ ─ ─ ─ ─  NEW SESSION  ─ ─ ─ ─ ─');mem.classList.remove('off');
   mem.textContent='memory: session '+SID.slice(0,8)+'… (Lakebase schema __MEMORY_SCHEMA__)';}
 newSession();
 document.getElementById('ns').onclick=()=>{newSession();m.focus();};
 // Quick keys: one per lab beat — click to fill the input, then hit SEND.
 const SUGS=["What's the status of order ORD-10001? Include the customer's email and shipping address.",
             "Is the ProBook X500 available to buy?",
             "How long is the AudioMax Pro warranty?"];
 const sugs=document.getElementById('sugs');
 SUGS.forEach(q=>{const x=document.createElement('button');x.type='button';x.className='sug';
   x.textContent='▸ '+q;x.onclick=()=>{m.value=q;m.focus();};sugs.appendChild(x);});
 function add(t,who){const d=document.createElement('div');d.className='msg '+who;d.textContent=t;log.appendChild(d);d.scrollIntoView();return d;}
 // Itemized line item: tool name, dotted leader, ✓ — the agent's machinery as a receipt line.
 function chipEl(tool,args){const s=document.createElement('span');s.className='chip';
   const t=document.createElement('span');t.textContent='▸ '+tool+'('+(args||'')+')';
   const l=document.createElement('span');l.className='lead';
   const k=document.createElement('span');k.className='ok';k.textContent='✓';
   s.appendChild(t);s.appendChild(l);s.appendChild(k);return s;}
 function chips(tc){if(!tc||!tc.length)return;const w=document.createElement('div');w.className='tools';
   tc.forEach(c=>w.appendChild(chipEl(c.tool,c.args)));log.appendChild(w);w.scrollIntoView();}
 const MEM_OFF='memory: off (Lakebase unavailable — chat still works, single-turn)';
 function memOff(){mem.textContent=MEM_OFF;mem.classList.add('off');}
 // Streaming: read /chat/stream SSE events; print line items and text deltas AS THEY ARRIVE.
 async function streamChat(q){
   const r=await fetch('/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q,session_id:SID})});
   if(!r.ok||!r.body)throw {fresh:true,msg:'HTTP '+r.status};
   const rd=r.body.getReader(),dec=new TextDecoder();let buf='',bot=null,tools=null,fin=null;
   try{
     for(;;){const c=await rd.read();if(c.done)break;buf+=dec.decode(c.value,{stream:true});
       let i;while((i=buf.indexOf('\\n\\n'))>=0){const line=buf.slice(0,i).trim();buf=buf.slice(i+2);
         if(!line.startsWith('data:'))continue;const j=JSON.parse(line.slice(5));
         if(j.type==='delta'){if(!bot){bot=document.createElement('div');bot.className='msg bot live';log.appendChild(bot);}
           bot.textContent+=j.text;bot.scrollIntoView();}
         else if(j.type==='tool_call'){if(!tools){tools=document.createElement('div');tools.className='tools';log.appendChild(tools);}
           tools.appendChild(chipEl(j.tool,j.args));tools.scrollIntoView();}
         else if(j.type==='done'){fin=j.memory;}
         else if(j.type==='error'){throw {fresh:!bot&&!tools,msg:j.detail||'stream error'};}}}
   }finally{if(bot)bot.classList.remove('live');}
   if(fin===null&&!bot)throw {fresh:!tools,msg:'stream ended early'};
   if(fin==='off'){memOff();}
   if(!bot){add('(no reply)','bot');}}
 f.onsubmit=async(e)=>{e.preventDefault();const q=m.value.trim();if(!q)return;add(q,'you');m.value='';b.disabled=true;
   try{await streamChat(q);}
   catch(err){
     if(err&&err.fresh){ // nothing painted yet — fall back to the classic request/response path
       try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q,session_id:SID})});
         const j=await r.json();chips(j.tool_calls);add(j.response||JSON.stringify(j),'bot');
         if(j.memory==='off'){memOff();}}
       catch(e2){add('Error: '+e2,'bot');}}
     else{add('Error: '+((err&&err.msg)||err),'bot');}}
   finally{b.disabled=false;m.focus();}};
 // The JOURNAL: this app's past Lakebase sessions; click an entry to reload + resume it.
 const sp=document.getElementById('sp');
 const HD='<div class="hd">JOURNAL — PAST SESSIONS (THIS APP)</div>';
 function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
 document.getElementById('ss').onclick=async()=>{
   if(sp.style.display==='block'){sp.style.display='none';return;}
   sp.style.display='block';sp.innerHTML=HD+'<div class="sess" style="cursor:default">printing…</div>';
   try{const j=await(await fetch('/sessions')).json();sp.innerHTML=HD;
     if(!j.sessions.length){sp.innerHTML=HD+'<div class="sess" style="cursor:default">no past sessions yet — ring something up first</div>';return;}
     j.sessions.forEach(s=>{const x=document.createElement('button');x.type='button';x.className='sess';
       x.innerHTML='<span class="meta2">'+s.session_id.slice(0,8)+'… · '+s.messages+' items · '+(s.updated||'')+'</span><br>'+esc(s.title||'(empty)');
       x.onclick=()=>resume(s.session_id);sp.appendChild(x);});}
   catch(e){sp.innerHTML=HD+'<div class="sess" style="cursor:default">journal unavailable</div>';}};
 async function resume(sid){sp.style.display='none';
   try{const j=await(await fetch('/sessions/'+encodeURIComponent(sid)+'/messages')).json();
     SID=sid;log.innerHTML='';cut('↻ ─ ─ ─ ─ ─  RESUMED SESSION  ─ ─ ─ ─ ─');mem.classList.remove('off');
     mem.textContent='memory: session '+SID.slice(0,8)+'… (resumed)';
     j.messages.forEach(t=>{if(t.who==='tool'){chips([{tool:t.tool,args:t.args}]);}else{add(t.text,t.who);}});
     m.focus();}
   catch(e){add('Could not load session: '+e,'bot');}}
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    # Surface the per-app memory schema so participants can find THEIR rows in Module 5½.
    return _CHAT_HTML.replace("__MEMORY_SCHEMA__", MEMORY_SCHEMA)
