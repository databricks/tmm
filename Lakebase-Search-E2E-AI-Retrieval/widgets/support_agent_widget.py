"""Agentic retrieval playground widget for Databricks notebooks.

A minimal customer-support chat agent that answers with tool calls only.
It exposes four retrieval tools over Lakebase Postgres:

    search_memory             vector search over past conversations
    vector_search_products    cosine ANN over the product catalogue
    text_search_products      BM25 lexical search
    hybrid_search_products    reciprocal rank fusion of both, with filters

Every tool call is streamed into the UI while the agent is still working, so
the audience can watch it search repeatedly before it answers.

The widget owns the agent loop and the SQL; the notebook injects the LLM and
the database access (``chat_fn`` / ``fetch_fn`` / ``embed_fn``).
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import anywidget
import traitlets

__all__ = ["SupportAgentWidget", "TOOL_SPECS"]


_AGENT_ESM = r'''
function render({ model, el }) {
  if (!document.querySelector('link[data-db-fonts]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.dataset.dbFonts = '1';
    link.href = 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap';
    document.head.appendChild(link);
  }

  const style = document.createElement('style');
  style.textContent = `
    .sa-root {
      --font-sans: "DM Sans", system-ui, -apple-system, sans-serif;
      --font-mono: "DM Mono", ui-monospace, monospace;
      --lava: #FF3621; --lava-h: #FF5A45; --lava-a: #DB2B18;
      --navy: #0B2026; --navy-7: #2C545E;
      --oat: #EEEDE9; --oat-l: #F9F7F4; --white: #FFFFFF;
      --txt: #0B2026; --txt2: #5F6B6E; --txt3: #A3ABAE;
      --success: #00A972; --error: #E5231F;
      --r-sm: 4px; --r-md: 8px; --r-lg: 12px; --r-full: 9999px;
      font-family: var(--font-sans); font-size: 14px; line-height: 1.5; color: var(--txt);
      width: 100%; max-width: 100%; height: 660px;
      display: flex; flex-direction: column; box-sizing: border-box;
      background: var(--white); border: 1px solid var(--oat); border-radius: var(--r-lg);
      overflow: hidden;
    }
    .sa-root *, .sa-root *::before, .sa-root *::after { box-sizing: border-box; }
    .sa-root:fullscreen, .sa-root:-webkit-full-screen {
      max-width: none; height: 100vh; border-radius: 0; border: none;
    }
    .sa-head {
      display: flex; align-items: center; gap: 12px; flex-shrink: 0;
      padding: 12px 16px; background: var(--oat-l); border-bottom: 1px solid var(--oat);
    }
    .sa-logo {
      width: 28px; height: 28px; border-radius: var(--r-full); background: var(--navy);
      color: var(--white); font-size: 12px; font-weight: 700; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
    }
    .sa-head-txt { flex: 1; min-width: 0; }
    .sa-head-title { font-size: 14px; font-weight: 600; }
    .sa-head-sub { font-size: 12px; color: var(--txt2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .sa-pill {
      font-family: var(--font-mono); font-size: 10px; text-transform: uppercase;
      letter-spacing: 0.06em; color: var(--txt2); background: var(--white);
      border: 1px solid var(--oat); border-radius: var(--r-full); padding: 3px 8px; white-space: nowrap;
    }
    .sa-ico-btn {
      width: 30px; height: 30px; flex-shrink: 0; border: 1px solid var(--oat);
      border-radius: var(--r-md); background: var(--white); color: var(--txt2); cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: background 80ms, border-color 80ms, color 80ms;
    }
    .sa-ico-btn:hover { background: var(--oat-l); border-color: var(--navy-7); color: var(--txt); }
    .sa-ico-btn svg { width: 15px; height: 15px; }
    .sa-chat {
      flex: 1; min-height: 0; overflow-y: auto; padding: 18px;
      display: flex; flex-direction: column; gap: 14px;
    }
    .sa-chat::-webkit-scrollbar { width: 6px; }
    .sa-chat::-webkit-scrollbar-track { background: transparent; }
    .sa-chat::-webkit-scrollbar-thumb { background: rgba(11,32,38,0.15); border-radius: var(--r-full); }
    .sa-empty { margin: auto; text-align: center; max-width: 460px; color: var(--txt2); }
    .sa-empty-t { font-size: 15px; font-weight: 600; color: var(--txt); margin-bottom: 4px; }
    .sa-chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 16px; }
    .sa-chip {
      border: 1px solid var(--oat); background: var(--white); border-radius: var(--r-full);
      padding: 7px 13px; font: inherit; font-size: 12px; color: var(--txt); cursor: pointer;
      transition: border-color 80ms, color 80ms;
    }
    .sa-chip:hover { border-color: var(--lava); color: var(--lava); }
    .sa-user {
      align-self: flex-end; max-width: 78%; background: var(--navy); color: #E8F0F2;
      padding: 10px 14px; white-space: pre-wrap;
      border-radius: var(--r-lg) var(--r-lg) var(--r-sm) var(--r-lg);
    }
    .sa-agent { align-self: flex-start; width: 100%; display: flex; flex-direction: column; gap: 8px; }
    .sa-trace { border: 1px solid var(--oat); border-radius: var(--r-md); background: var(--oat-l); overflow: hidden; }
    .sa-trace-head {
      display: flex; align-items: center; gap: 8px; padding: 7px 12px;
      font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
      color: var(--txt2); border-bottom: 1px solid var(--oat);
    }
    .sa-note {
      padding: 8px 12px; font-size: 12px; color: var(--txt2); font-style: italic;
      border-bottom: 1px solid var(--oat);
    }
    .sa-tool { border-bottom: 1px solid var(--oat); }
    .sa-trace > .sa-tool:last-child { border-bottom: none; }
    .sa-tool-row {
      display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer;
      transition: background 80ms;
    }
    .sa-tool-row:hover { background: rgba(11,32,38,0.03); }
    .sa-tdot { width: 8px; height: 8px; border-radius: var(--r-full); flex-shrink: 0; }
    .sa-tname { font-family: var(--font-mono); font-size: 11px; font-weight: 500; white-space: nowrap; }
    .sa-tq {
      flex: 1; min-width: 0; font-size: 12px; color: var(--txt2);
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .sa-tmeta {
      font-family: var(--font-mono); font-size: 10px; color: var(--txt3);
      display: flex; align-items: center; gap: 6px; white-space: nowrap;
    }
    .sa-tmeta.ok { color: var(--success); }
    .sa-tmeta.err { color: var(--error); }
    @keyframes sa-spin { to { transform: rotate(360deg); } }
    .sa-spin {
      width: 12px; height: 12px; border: 2px solid var(--oat); border-top-color: var(--lava);
      border-radius: 50%; animation: sa-spin 0.6s linear infinite;
    }
    .sa-trows { display: none; flex-direction: column; gap: 5px; padding: 0 12px 10px 30px; }
    .sa-trows.open { display: flex; }
    .sa-trow { display: flex; gap: 10px; align-items: baseline; font-size: 12px; }
    .sa-trow-t { color: var(--txt); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .sa-trow-m { font-family: var(--font-mono); font-size: 10px; color: var(--txt3); white-space: nowrap; margin-left: auto; }
    .sa-answer {
      background: var(--white); border: 1px solid var(--oat); border-radius: var(--r-lg);
      padding: 12px 14px; white-space: pre-wrap;
    }
    .sa-answer.pending { color: var(--txt3); font-style: italic; display: flex; align-items: center; gap: 8px; }
    .sa-foot { font-family: var(--font-mono); font-size: 10px; color: var(--txt3); padding-left: 2px; }
    .sa-err { color: var(--error); font-size: 12px; }
    .sa-status {
      flex-shrink: 0; padding: 6px 16px 0; font-family: var(--font-mono); font-size: 11px;
      color: var(--txt2); display: flex; align-items: center; gap: 7px; min-height: 22px;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .sa-composer {
      flex-shrink: 0; display: flex; gap: 10px; align-items: flex-end;
      padding: 10px 14px 14px; background: var(--white);
    }
    .sa-ta {
      flex: 1; resize: none; min-height: 44px; max-height: 120px; padding: 11px 14px;
      border: 1.5px solid var(--oat); border-radius: var(--r-lg); background: var(--white);
      font: inherit; font-size: 14px; color: var(--txt); line-height: 1.4;
      transition: border-color 120ms, box-shadow 120ms;
    }
    .sa-ta:focus { outline: none; border-color: var(--lava); box-shadow: 0 0 0 3px rgba(255,54,33,0.1); }
    .sa-ta::placeholder { color: var(--txt3); }
    .sa-send {
      min-height: 44px; padding: 0 20px; border: none; border-radius: var(--r-lg);
      background: var(--lava); color: var(--white); font: inherit; font-weight: 600;
      cursor: pointer; transition: background 120ms;
    }
    .sa-send:hover { background: var(--lava-h); }
    .sa-send:active { background: var(--lava-a); }
    .sa-send:disabled { background: #c9c8c4; cursor: not-allowed; }
  `;
  el.appendChild(style);

  const root = document.createElement('div');
  root.className = 'sa-root';
  el.appendChild(root);

  const ce = (tag, cls, txt) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = String(txt);
    return n;
  };

  const TOOL_COLORS = {
    search_memory: '#1B73E8',
    vector_search_products: '#7C4DFF',
    text_search_products: '#00A972',
    hybrid_search_products: '#FF3621',
  };

  /* ── header ── */
  const head = ce('div', 'sa-head');
  head.append(ce('div', 'sa-logo', 'S'));
  const headTxt = ce('div', 'sa-head-txt');
  const headTitle = ce('div', 'sa-head-title', 'Store Support Agent');
  const headSub = ce('div', 'sa-head-sub', '');
  headTxt.append(headTitle, headSub);
  head.append(headTxt);
  const pill = ce('div', 'sa-pill', '');
  head.append(pill);

  const svgTrash = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>';
  const svgExpand = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';
  const svgCollapse = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';

  const resetBtn = ce('button', 'sa-ico-btn');
  resetBtn.innerHTML = svgTrash;
  resetBtn.title = 'Clear conversation';
  const fsBtn = ce('button', 'sa-ico-btn');
  fsBtn.innerHTML = svgExpand;
  fsBtn.title = 'Fullscreen';
  head.append(resetBtn, fsBtn);
  root.append(head);

  const isFs = () => {
    const f = document.fullscreenElement || document.webkitFullscreenElement;
    return f && root.contains(f);
  };
  const syncFs = () => {
    fsBtn.innerHTML = isFs() ? svgCollapse : svgExpand;
    fsBtn.title = isFs() ? 'Exit fullscreen' : 'Fullscreen';
  };
  fsBtn.addEventListener('click', () => {
    if (isFs()) { (document.exitFullscreen || document.webkitExitFullscreen || (() => {})).call(document); }
    else if (root.requestFullscreen) { root.requestFullscreen().catch(() => {}); }
    else if (root.webkitRequestFullscreen) { root.webkitRequestFullscreen(); }
  });
  document.addEventListener('fullscreenchange', syncFs);
  document.addEventListener('webkitfullscreenchange', syncFs);

  /* ── transcript + composer ── */
  const chat = ce('div', 'sa-chat');
  const statusBar = ce('div', 'sa-status');
  const composer = ce('div', 'sa-composer');
  const ta = document.createElement('textarea');
  ta.className = 'sa-ta';
  ta.rows = 1;
  ta.placeholder = 'Ask the agent to find something\u2026';
  const sendBtn = ce('button', 'sa-send', 'Send');
  composer.append(ta, sendBtn);
  root.append(chat, statusBar, composer);

  const expanded = new Set();

  const send = (text) => {
    const value = (text != null ? text : ta.value).trim();
    if (!value || model.get('busy')) return;
    ta.value = '';
    ta.style.height = 'auto';
    model.set('input_text', value);
    model.set('command', 'send');
    model.save_changes();
  };
  sendBtn.addEventListener('click', () => send());
  ta.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  ta.addEventListener('input', () => {
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  });
  resetBtn.addEventListener('click', () => {
    if (model.get('busy')) return;
    expanded.clear();
    model.set('command', 'reset');
    model.save_changes();
  });

  const renderToolItem = (item, key) => {
    const box = ce('div', 'sa-tool');
    const row = ce('div', 'sa-tool-row');
    const dot = ce('span', 'sa-tdot');
    dot.style.background = TOOL_COLORS[item.tool] || '#5F6B6E';
    row.append(dot, ce('span', 'sa-tname', item.tool || 'tool'));
    row.append(ce('span', 'sa-tq', item.query || ''));

    const meta = ce('div', 'sa-tmeta');
    if (item.status === 'running') {
      meta.append(ce('div', 'sa-spin'), ce('span', null, 'searching'));
    } else if (item.status === 'error') {
      meta.classList.add('err');
      meta.append(ce('span', null, '\u26a0 failed'));
    } else {
      meta.classList.add('ok');
      const bits = [];
      if (item.count != null) bits.push(item.count + ' hits');
      if (item.ms != null) bits.push(item.ms + ' ms');
      meta.append(ce('span', null, '\u2713 ' + bits.join(' \u00b7 ')));
    }
    row.append(meta);
    box.append(row);

    const rows = ce('div', 'sa-trows');
    if (expanded.has(key)) rows.classList.add('open');
    if (item.status === 'error') {
      rows.append(ce('div', 'sa-err', item.detail || 'tool failed'));
    }
    for (const r of (item.rows || [])) {
      const line = ce('div', 'sa-trow');
      line.append(ce('span', 'sa-trow-t', r.title || ''));
      line.append(ce('span', 'sa-trow-m', [r.meta, r.score].filter(Boolean).join('  ')));
      rows.append(line);
    }
    box.append(rows);
    row.addEventListener('click', () => {
      const open = rows.classList.toggle('open');
      if (open) expanded.add(key); else expanded.delete(key);
    });
    return box;
  };

  const renderTranscript = () => {
    let turns = [];
    try { turns = JSON.parse(model.get('turns_json') || '[]'); } catch (e) {}
    chat.replaceChildren();

    if (!turns.length) {
      const empty = ce('div', 'sa-empty');
      empty.append(ce('div', 'sa-empty-t', 'Ask on the customer\u2019s behalf'));
      empty.append(ce('div', null, 'The agent searches its memory of past conversations and the product catalogue before it answers. Every search shows up here as it runs.'));
      let chips = [];
      try { chips = JSON.parse(model.get('suggestions_json') || '[]'); } catch (e) {}
      if (chips.length) {
        const wrap = ce('div', 'sa-chips');
        for (const c of chips) {
          const b = ce('button', 'sa-chip', c);
          b.addEventListener('click', () => send(c));
          wrap.append(b);
        }
        empty.append(wrap);
      }
      chat.append(empty);
      return;
    }

    turns.forEach((turn, ti) => {
      if (turn.role === 'user') {
        chat.append(ce('div', 'sa-user', turn.content || ''));
        return;
      }
      const block = ce('div', 'sa-agent');
      const trace = turn.trace || [];
      if (trace.length) {
        const traceBox = ce('div', 'sa-trace');
        const th = ce('div', 'sa-trace-head');
        const nTools = trace.filter((i) => i.kind === 'tool').length;
        th.append(ce('span', null, 'retrieval trace'));
        th.append(ce('span', null, '\u00b7 ' + nTools + (nTools === 1 ? ' search' : ' searches')));
        traceBox.append(th);
        trace.forEach((item, ii) => {
          if (item.kind === 'note') {
            traceBox.append(ce('div', 'sa-note', item.text || ''));
          } else {
            traceBox.append(renderToolItem(item, ti + ':' + ii));
          }
        });
        block.append(traceBox);
      }
      if (turn.pending) {
        const pending = ce('div', 'sa-answer pending');
        pending.append(ce('div', 'sa-spin'), ce('span', null, 'working\u2026'));
        block.append(pending);
      } else {
        block.append(ce('div', 'sa-answer', turn.content || ''));
        if (turn.footer) block.append(ce('div', 'sa-foot', turn.footer));
      }
      chat.append(block);
    });

    chat.scrollTop = chat.scrollHeight;
  };

  const renderChrome = () => {
    const busy = Boolean(model.get('busy'));
    sendBtn.disabled = busy;
    sendBtn.textContent = busy ? 'Working\u2026' : 'Send';
    ta.disabled = busy;
    resetBtn.disabled = busy;
    pill.textContent = model.get('model_label') || '';
    const customer = model.get('customer_name') || 'the customer';
    headSub.textContent = 'Acting for ' + customer + ' \u00b7 memory + vector + text + hybrid search on Lakebase';
    statusBar.replaceChildren();
    const err = model.get('error') || '';
    if (err) {
      statusBar.append(ce('span', 'sa-err', err));
    } else if (busy) {
      statusBar.append(ce('div', 'sa-spin'), ce('span', null, model.get('status') || 'thinking\u2026'));
    } else if (model.get('status')) {
      statusBar.append(ce('span', null, model.get('status')));
    }
  };

  model.on('change:turns_json', () => { renderTranscript(); renderChrome(); });
  model.on('change:busy', renderChrome);
  model.on('change:status', renderChrome);
  model.on('change:error', renderChrome);
  model.on('change:suggestions_json', renderTranscript);

  syncFs();
  renderTranscript();
  renderChrome();
}

export default { render };
'''  # end _AGENT_ESM


TOOL_SPECS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": (
                "Semantic search over everything already known about THIS customer: past "
                "conversations, orders, returns, support tickets, stated preferences and "
                "household context. Call this first, and call it again with different wording "
                "if the first pass is thin."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What you want to recall about the customer."},
                    "top_k": {"type": "integer", "description": "How many memories to return (1-8, default 5)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vector_search_products",
            "description": (
                "Dense vector (cosine ANN) search over the product catalogue. Best when the "
                "need is conceptual and the customer's words will not literally appear in the "
                "listing, e.g. 'something that survives a long flight'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language description of the need."},
                    "top_k": {"type": "integer", "description": "How many products to return (1-12, default 8)."},
                    "category": {"type": "string", "description": "Optional exact category pre-filter."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "text_search_products",
            "description": (
                "BM25 lexical search over the product catalogue. Best for exact brand names, "
                "model numbers, sizes and specific keywords the listing must literally contain."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords, brand or model number."},
                    "top_k": {"type": "integer", "description": "How many products to return (1-12, default 8)."},
                    "category": {"type": "string", "description": "Optional exact category pre-filter."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hybrid_search_products",
            "description": (
                "Reciprocal rank fusion of vector + BM25 search, with optional filters. This is "
                "the best default for product discovery and the only tool that can enforce a "
                "price ceiling or a rating floor."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What the customer is looking for."},
                    "top_k": {"type": "integer", "description": "How many products to return (1-12, default 8)."},
                    "category": {"type": "string", "description": "Optional exact category pre-filter."},
                    "max_price": {"type": "number", "description": "Optional maximum price in dollars."},
                    "min_rating": {"type": "number", "description": "Optional minimum star rating, 0-5."},
                },
                "required": ["query"],
            },
        },
    },
]


_SYSTEM_PROMPT = """You are a customer support agent for an online tech retailer.
You are handling a live chat on behalf of {customer}.

You have four retrieval tools over the company's Lakebase database. You may not
answer product or history questions from your own knowledge — everything you
say must come from a tool result in this turn.

Required workflow for every customer message:
1. Call search_memory at least once to recall this customer's preferences, past
   orders, returns and open tickets. If the first pass is thin or generic, call
   it again with different wording.
2. Search the catalogue at least twice, with different tools or different
   phrasings, before recommending anything. hybrid_search_products is the best
   default; vector_search_products for conceptual needs; text_search_products
   for exact brands or model numbers.
3. Read the results critically. If they are off-category, ignore a constraint
   you found in memory (budget, brand, comfort, rating), or look weak, search
   again with a sharper query or a filter instead of settling for them.
4. Only then write the answer.

Answer style: plain text, no markdown, at most 120 words. Recommend at most
three products, each by its exact catalogue title with price and rating. Say in
one clause why each fits, referencing what you recalled from memory. Call out
any conflict between the request and a known preference. Never invent a product
that was not in a tool result.
"""

_SUGGESTIONS = [
    "I have an 11-hour flight next week, what headphones should I get?",
    "Find me a soundbar that works with the TV I already own",
    "I need something for dog hair on thick rugs, under $400",
    "What did I return last time and why?",
]


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None  # drop NaN


class SupportAgentWidget(anywidget.AnyWidget):
    """Chat agent that retrieves from Lakebase, with a live tool-call trace."""

    _esm = _AGENT_ESM

    turns_json = traitlets.Unicode("[]").tag(sync=True)
    suggestions_json = traitlets.Unicode("[]").tag(sync=True)
    input_text = traitlets.Unicode("").tag(sync=True)
    command = traitlets.Unicode("").tag(sync=True)
    busy = traitlets.Bool(False).tag(sync=True)
    status = traitlets.Unicode("").tag(sync=True)
    error = traitlets.Unicode("").tag(sync=True)
    model_label = traitlets.Unicode("").tag(sync=True)
    customer_name = traitlets.Unicode("the customer").tag(sync=True)
    max_steps = traitlets.Int(8).tag(sync=True)

    def __init__(
        self,
        *,
        chat_fn: Callable[[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]], Dict[str, Any]],
        fetch_fn: Callable[..., Any],
        embed_fn: Callable[[str, str], Sequence[float]],
        database_name: str = "",
        products_table: str = "products",
        memory_table: str = "agent_memory",
        embedding_model: str = "databricks-gte-large-en",
        suggestions: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self._chat_fn = chat_fn
        self._fetch_fn = fetch_fn
        self._embed_fn = embed_fn
        self._database_name = database_name
        self._products_table = products_table
        self._memory_table = memory_table
        self._embedding_model = embedding_model
        kwargs.setdefault("suggestions_json", json.dumps(suggestions or _SUGGESTIONS))
        super().__init__(**kwargs)

    # ---------------------------------------------------------------- commands

    @traitlets.observe("command")
    def _handle_command(self, change: Dict[str, Any]) -> None:
        cmd = change["new"]
        if cmd not in ("send", "reset"):
            return
        try:
            if cmd == "reset":
                self.turns_json = "[]"
                self.status = ""
                self.error = ""
                return
            text = (self.input_text or "").strip()
            if not text:
                return
            self.error = ""
            self.busy = True
            try:
                self._run_turn(text)
            finally:
                self.busy = False
                self.status = ""
                self.input_text = ""
        finally:
            self.command = ""

    # ------------------------------------------------------------- agent loop

    def _publish(self, turns: List[Dict[str, Any]]) -> None:
        """Push the transcript to the browser mid-flight so searches stream in."""
        self.turns_json = json.dumps(turns)

    def _history(self, past_turns: List[Dict[str, Any]], keep: int = 8) -> List[Dict[str, Any]]:
        msgs: List[Dict[str, Any]] = []
        for turn in past_turns[-keep:]:
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            msgs.append({"role": turn.get("role", "user"), "content": content})
        return msgs

    def _run_turn(self, user_text: str) -> None:
        try:
            turns = json.loads(self.turns_json or "[]")
        except json.JSONDecodeError:
            turns = []

        history = self._history(list(turns))
        turns.append({"role": "user", "content": user_text})
        turn: Dict[str, Any] = {"role": "assistant", "content": "", "trace": [], "pending": True}
        turns.append(turn)
        self._publish(turns)

        msgs: List[Dict[str, Any]] = [
            {"role": "system", "content": _SYSTEM_PROMPT.format(customer=self.customer_name)}
        ]
        msgs.extend(history)
        msgs.append({"role": "user", "content": user_text})

        started = time.perf_counter()
        searches = 0
        model_calls = 0

        try:
            for step in range(max(1, int(self.max_steps))):
                self.status = "thinking" if step == 0 else f"thinking (round {step + 1})"
                reply = self._chat_fn(msgs, TOOL_SPECS)
                model_calls += 1
                calls = reply.get("tool_calls") or []
                note = (reply.get("content") or "").strip()
                msgs.append(
                    {
                        "role": "assistant",
                        "content": reply.get("content"),
                        "tool_calls": calls or None,
                    }
                )

                if not calls:
                    turn["content"] = self._plain(note) or "(the model returned no answer)"
                    turn["pending"] = False
                    turn["footer"] = self._footer(searches, model_calls, started)
                    self._publish(turns)
                    return

                if note:
                    turn["trace"].append({"kind": "note", "text": note})
                    self._publish(turns)

                for call in calls:
                    fn = call.get("function") or {}
                    name = fn.get("name") or ""
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}

                    searches += 1
                    event: Dict[str, Any] = {
                        "kind": "tool",
                        "tool": name,
                        "query": self._event_label(args),
                        "status": "running",
                        "rows": [],
                    }
                    turn["trace"].append(event)
                    self.status = f"{name}  {event['query'][:60]}"
                    self._publish(turns)

                    t0 = time.perf_counter()
                    try:
                        llm_rows, ui_rows = self._dispatch(name, args)
                        event["status"] = "done"
                        event["count"] = len(llm_rows)
                        event["rows"] = ui_rows[:5]
                        payload: Dict[str, Any] = {"results": llm_rows}
                    except Exception as exc:  # surfaced in the trace, not fatal
                        detail = f"{type(exc).__name__}: {exc}"[:300]
                        event["status"] = "error"
                        event["detail"] = detail
                        payload = {"error": detail}
                    event["ms"] = int((time.perf_counter() - t0) * 1000)
                    self._publish(turns)

                    msgs.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "content": json.dumps(payload)[:12000],
                        }
                    )

            # Step budget exhausted: force a final answer with no tools.
            self.status = "wrapping up"
            msgs.append(
                {
                    "role": "user",
                    "content": "Search budget reached. Answer now using only what you already found.",
                }
            )
            final = self._chat_fn(msgs, None)
            model_calls += 1
            turn["content"] = self._plain(final.get("content") or "") or "(no answer returned)"
            turn["pending"] = False
            turn["footer"] = self._footer(searches, model_calls, started)
            self._publish(turns)
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"[:400]
            turn["pending"] = False
            turn["content"] = turn["content"] or "That turn failed before I could answer."
            turn["footer"] = self._footer(searches, model_calls, started)
            self._publish(turns)

    @staticmethod
    def _plain(text: str) -> str:
        """The answer bubble is plain text, so drop stray markdown emphasis."""
        out = (text or "").replace("**", "").replace("__", "")
        return "\n".join(line.lstrip("#").strip() if line.startswith("#") else line
                         for line in out.splitlines()).strip()

    @staticmethod
    def _footer(searches: int, model_calls: int, started: float) -> str:
        label = "search" if searches == 1 else "searches"
        return (
            f"{searches} {label} \u00b7 {model_calls} model calls \u00b7 "
            f"{time.perf_counter() - started:.1f} s"
        )

    @staticmethod
    def _event_label(args: Dict[str, Any]) -> str:
        parts = [str(args.get("query", ""))]
        for key, prefix in (("category", ""), ("max_price", "\u2264 $"), ("min_rating", "\u2265 ")):
            value = args.get(key)
            if value not in (None, ""):
                parts.append(f"[{prefix}{value}]")
        return " ".join(p for p in parts if p)[:160]

    # ------------------------------------------------------------------ tools

    def _dispatch(self, name: str, args: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        query = str(args.get("query") or "").strip()
        if not query:
            raise ValueError("the tool call is missing a query")
        if name == "search_memory":
            return self._tool_memory(query, args)
        if name == "vector_search_products":
            return self._tool_vector(query, args)
        if name == "text_search_products":
            return self._tool_text(query, args)
        if name == "hybrid_search_products":
            return self._tool_hybrid(query, args)
        raise ValueError(f"unknown tool: {name}")

    def _vector_literal(self, query: str) -> str:
        emb = self._embed_fn(query, self._embedding_model)
        return "[" + ",".join(f"{float(v):.12f}" for v in emb) + "]"

    @staticmethod
    def _clamp_k(raw: Any, default: int = 8, high: int = 12) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return max(1, min(high, value))

    @staticmethod
    def _filters(args: Dict[str, Any]) -> Tuple[str, List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        for key, expr, cast in (
            ("category", "root_category = %s", str),
            ("max_price", "price <= %s", float),
            ("min_rating", "rating >= %s", float),
        ):
            raw = args.get(key)
            if raw in (None, ""):
                continue
            try:
                params.append(cast(raw))
            except (TypeError, ValueError):
                continue
            clauses.append(expr)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params

    def _shape_products(
        self, df: Any, score_col: str, score_prefix: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        llm_rows: List[Dict[str, Any]] = []
        ui_rows: List[Dict[str, Any]] = []
        for record in df.to_dict("records"):
            price = _as_float(record.get("price"))
            rating = _as_float(record.get("rating"))
            category = record.get("root_category") or ""
            llm_rows.append(
                {
                    "title": record.get("title"),
                    "category": category,
                    "price": round(price, 2) if price is not None else None,
                    "rating": round(rating, 1) if rating is not None else None,
                }
            )
            meta = [category]
            if price is not None:
                meta.append(f"${price:,.2f}")
            if rating is not None:
                meta.append(f"{rating:.1f}\u2605")
            score = _as_float(record.get(score_col))
            ui_rows.append(
                {
                    "title": record.get("title"),
                    "meta": " \u00b7 ".join(m for m in meta if m),
                    "score": f"{score_prefix} {score:.4f}" if score is not None else "",
                }
            )
        return llm_rows, ui_rows

    def _tool_memory(self, query: str, args: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        k = self._clamp_k(args.get("top_k"), default=5, high=8)
        literal = self._vector_literal(query)
        df = self._fetch_fn(
            f"SELECT kind, occurred_on, memory, embedding <=> %s::vector AS dist "
            f"FROM {self._memory_table} ORDER BY dist LIMIT {k}",
            (literal,),
            dbname=self._database_name,
        )
        llm_rows, ui_rows = [], []
        for record in df.to_dict("records"):
            dist = _as_float(record.get("dist"))
            llm_rows.append(
                {
                    "kind": record.get("kind"),
                    "date": str(record.get("occurred_on")),
                    "memory": record.get("memory"),
                }
            )
            ui_rows.append(
                {
                    "title": record.get("memory"),
                    "meta": f"{record.get('kind')} \u00b7 {record.get('occurred_on')}",
                    "score": f"cos {dist:.4f}" if dist is not None else "",
                }
            )
        return llm_rows, ui_rows

    def _tool_vector(self, query: str, args: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        k = self._clamp_k(args.get("top_k"))
        where, params = self._filters(args)
        literal = self._vector_literal(query)
        df = self._fetch_fn(
            f"SELECT title, root_category, price, rating, embedding <=> %s::vector AS dist "
            f"FROM {self._products_table}{where} ORDER BY dist LIMIT {k}",
            tuple([literal] + params),
            dbname=self._database_name,
        )
        return self._shape_products(df, "dist", "cos")

    def _tool_text(self, query: str, args: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        k = self._clamp_k(args.get("top_k"))
        where, params = self._filters(args)
        tbl = self._products_table
        _tbl_name = tbl.split(".")[-1]
        bm25_idx = f"{tbl.rsplit('.', 1)[0] + '.' if '.' in tbl else ''}{_tbl_name}_body_bm25_idx"
        score_expr = f"body_tsv <@> to_bm25query(to_tsvector('english', %s), '{bm25_idx}')"
        df = self._fetch_fn(
            f"SELECT title, root_category, price, rating, {score_expr} AS score "
            f"FROM {self._products_table}{where} ORDER BY score LIMIT {k}",
            tuple([query] + params),
            dbname=self._database_name,
        )
        return self._shape_products(df, "score", "bm25")

    def _tool_hybrid(self, query: str, args: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        k = self._clamp_k(args.get("top_k"))
        where, params = self._filters(args)
        tbl = self._products_table
        _tbl_name = tbl.split(".")[-1]
        bm25_idx = f"{tbl.rsplit('.', 1)[0] + '.' if '.' in tbl else ''}{_tbl_name}_body_bm25_idx"
        pool = 60
        literal = self._vector_literal(query)
        df = self._fetch_fn(
            f"WITH vector_ranked AS ("
            f"  SELECT id, RANK() OVER (ORDER BY dist) AS rank FROM ("
            f"    SELECT id, embedding <=> %s::vector AS dist FROM {tbl}{where} "
            f"    ORDER BY dist LIMIT {pool}"
            f"  ) v"
            f"), keyword_ranked AS ("
            f"  SELECT id, RANK() OVER (ORDER BY score) AS rank FROM ("
            f"    SELECT id, body_tsv <@> to_bm25query(to_tsvector('english', %s), '{bm25_idx}') AS score"
            f"    FROM {tbl}{where} ORDER BY score LIMIT {pool}"
            f"  ) k"
            f") SELECT d.title, d.root_category, d.price, d.rating,"
            f"  COALESCE(1.0/(60+v.rank),0)+COALESCE(1.0/(60+k.rank),0) AS rrf_score"
            f" FROM {tbl} d"
            f" LEFT JOIN vector_ranked v ON d.id = v.id"
            f" LEFT JOIN keyword_ranked k ON d.id = k.id"
            f" WHERE v.id IS NOT NULL OR k.id IS NOT NULL"
            f" ORDER BY rrf_score DESC, d.id LIMIT {k}",
            tuple([literal] + params + [query] + params),
            dbname=self._database_name,
        )
        return self._shape_products(df, "rrf_score", "rrf")
