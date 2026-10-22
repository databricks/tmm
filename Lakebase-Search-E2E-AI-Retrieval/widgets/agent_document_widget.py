
'''agent_document_widget.py — Agent-driven document editor with chat history.

Left panel  : document list.
Right panel : chat conversation — document card at top, user prompt bubbles,
              agent diff cards (+ / - lines) inline. Edits are applied
              automatically; chunking and embedding are handled by the MV pipeline.

Styled to match the support_agent_widget (DM Sans/Mono, Databricks oat/navy/lava).
'''
from __future__ import annotations

import difflib
import json
import re
import threading
import time

import anywidget
import traitlets


def _compute_diff(old_text, new_text):
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    sm = difflib.SequenceMatcher(None, old_lines, new_lines)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                ops.append({"type": "equal", "text": old_lines[k]})
        elif tag == "replace":
            for k in range(i1, i2):
                ops.append({"type": "delete", "text": old_lines[k]})
            for k in range(j1, j2):
                ops.append({"type": "insert", "text": new_lines[k]})
        elif tag == "delete":
            for k in range(i1, i2):
                ops.append({"type": "delete", "text": old_lines[k]})
        elif tag == "insert":
            for k in range(j1, j2):
                ops.append({"type": "insert", "text": new_lines[k]})
    return ops


_ESM = r'''
function render({ model, el }) {
  if (!document.querySelector('link[data-db-fonts]')) {
    const lk = document.createElement('link');
    lk.rel = 'stylesheet'; lk.dataset.dbFonts = '1';
    lk.href = 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap';
    document.head.appendChild(lk);
  }

  const style = document.createElement('style');
  style.textContent = `
    .ad-root {
      --font-sans: "DM Sans", system-ui, -apple-system, sans-serif;
      --font-mono: "DM Mono", ui-monospace, monospace;
      --lava: #FF3621; --lava-h: #FF5A45; --lava-a: #DB2B18;
      --navy: #0B2026; --navy-7: #2C545E;
      --oat: #EEEDE9; --oat-l: #F9F7F4; --white: #FFFFFF;
      --txt: #0B2026; --txt2: #5F6B6E; --txt3: #A3ABAE;
      --success: #00A972; --error: #E5231F;
      --r-sm: 4px; --r-md: 8px; --r-lg: 12px; --r-full: 9999px;
      font-family: var(--font-sans); font-size: 14px; line-height: 1.5; color: var(--txt);
      width: 100%; height: 720px;
      display: flex; flex-direction: column;
      background: var(--white); border: 1px solid var(--oat); border-radius: var(--r-lg);
      overflow: hidden;
    }
    .ad-root *, .ad-root *::before, .ad-root *::after { box-sizing: border-box; }
    /* Header */
    .ad-head {
      display: flex; align-items: center; gap: 12px; flex-shrink: 0;
      padding: 12px 16px; background: var(--oat-l); border-bottom: 1px solid var(--oat);
    }
    .ad-logo {
      width: 28px; height: 28px; border-radius: var(--r-full); background: var(--navy);
      color: var(--white); font-size: 12px; font-weight: 700; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
    }
    .ad-head-txt { flex: 1; min-width: 0; }
    .ad-head-title { font-size: 14px; font-weight: 600; }
    .ad-head-sub { font-size: 12px; color: var(--txt2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .ad-pill {
      font-family: var(--font-mono); font-size: 10px; text-transform: uppercase;
      letter-spacing: 0.06em; color: var(--txt2); background: var(--white);
      border: 1px solid var(--oat); border-radius: var(--r-full); padding: 3px 8px; white-space: nowrap;
    }
    .ad-ico-btn {
      width: 30px; height: 30px; flex-shrink: 0; border: 1px solid var(--oat);
      border-radius: var(--r-md); background: var(--white); color: var(--txt2); cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: background 80ms, border-color 80ms, color 80ms;
    }
    .ad-ico-btn:hover { background: var(--oat-l); border-color: var(--navy-7); color: var(--txt); }
    .ad-ico-btn svg { width: 15px; height: 15px; }
    .ad-root:fullscreen, .ad-root:-webkit-full-screen { height: 100vh; border-radius: 0; border: none; }
    /* Body */
    .ad-body { flex: 1; min-height: 0; display: flex; overflow: hidden; }
    /* Left sidebar */
    .ad-left {
      width: 220px; flex-shrink: 0; display: flex; flex-direction: column;
      border-right: 1px solid var(--oat); background: var(--oat-l);
    }
    .ad-left-hdr {
      padding: 8px 12px; font-size: 11px; font-weight: 600; color: var(--txt2);
      text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--oat);
    }
    .ad-doc-list { flex: 1; overflow-y: auto; }
    .ad-doc-list::-webkit-scrollbar { width: 4px; }
    .ad-doc-list::-webkit-scrollbar-thumb { background: rgba(11,32,38,0.15); border-radius: var(--r-full); }
    .ad-doc-item {
      padding: 9px 12px; cursor: pointer; border-left: 3px solid transparent;
      transition: background 80ms;
    }
    .ad-doc-item:hover { background: rgba(11,32,38,0.04); }
    .ad-doc-item.active { border-left-color: var(--lava); background: rgba(255,54,33,0.05); }
    .ad-doc-title { font-size: 12px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ad-doc-meta { font-size: 11px; color: var(--txt3); margin-top: 2px; font-family: var(--font-mono); }
    .ad-new-btn {
      margin: 8px; padding: 7px 10px; background: none;
      border: 1px dashed var(--oat); border-radius: var(--r-md);
      color: var(--txt2); cursor: pointer; font: inherit; font-size: 12px;
      text-align: left; transition: border-color 80ms, color 80ms, background 80ms;
    }
    .ad-new-btn:hover { border-color: var(--navy-7); color: var(--navy); background: var(--white); }
    /* Right panel */
    .ad-right { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
    /* Chat area */
    .ad-chat {
      flex: 1; min-height: 0; overflow-y: auto; padding: 16px 18px;
      display: flex; flex-direction: column; gap: 14px;
    }
    .ad-chat::-webkit-scrollbar { width: 6px; }
    .ad-chat::-webkit-scrollbar-track { background: transparent; }
    .ad-chat::-webkit-scrollbar-thumb { background: rgba(11,32,38,0.15); border-radius: var(--r-full); }
    /* Document card (top of chat) */
    .ad-doc-card {
      border: 1px solid var(--oat); border-radius: var(--r-md);
      background: var(--oat-l); overflow: hidden; flex-shrink: 0;
    }
    .ad-doc-card-head {
      display: flex; align-items: center; gap: 10px; padding: 9px 14px;
      cursor: pointer; transition: background 80ms;
    }
    .ad-doc-card-head:hover { background: var(--oat); }
    .ad-doc-card-icon { font-size: 14px; flex-shrink: 0; }
    .ad-doc-card-name {
      flex: 1; font-weight: 600; font-size: 13px; overflow: hidden;
      text-overflow: ellipsis; white-space: nowrap;
    }
    .ad-doc-card-chevron { font-family: var(--font-mono); font-size: 10px; color: var(--txt3); }
    .ad-doc-card-body {
      display: none; border-top: 1px solid var(--oat);
      max-height: 240px; overflow-y: auto;
    }
    .ad-doc-card-body.open { display: block; }
    .ad-doc-card-pre {
      margin: 0; padding: 12px 14px; font-family: var(--font-mono);
      font-size: 11px; line-height: 1.7; color: var(--txt); white-space: pre-wrap;
      word-break: break-word;
    }
    .ad-doc-card-empty { padding: 24px 18px; text-align: center; color: var(--txt3); font-size: 12px; }
    /* User message bubble */
    .ad-user {
      align-self: flex-end; max-width: 80%;
      background: var(--navy); color: #E8F0F2;
      padding: 10px 14px; border-radius: var(--r-lg) var(--r-lg) var(--r-sm) var(--r-lg);
      white-space: pre-wrap; font-size: 14px;
    }
    /* Agent turn */
    .ad-agent-turn { align-self: flex-start; width: 100%; display: flex; flex-direction: column; gap: 8px; }
    /* Pending spinner */
    .ad-pending {
      display: flex; align-items: center; gap: 10px;
      color: var(--txt2); font-size: 13px; padding: 6px 0;
    }
    @keyframes ad-spin { to { transform: rotate(360deg); } }
    .ad-spin {
      width: 14px; height: 14px; border: 2px solid var(--oat); border-top-color: var(--lava);
      border-radius: 50%; animation: ad-spin 0.6s linear infinite; flex-shrink: 0;
    }
    /* Edit card (diff inside agent turn) */
    .ad-edit-card {
      border: 1px solid var(--oat); border-radius: var(--r-md);
      background: var(--oat-l); overflow: hidden;
    }
    .ad-edit-head {
      display: flex; align-items: center; gap: 8px; padding: 7px 14px;
      font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
      color: var(--txt2); border-bottom: 1px solid var(--oat);
    }
    .ad-edit-head-title { flex: 1; }
    .ad-edit-stats { display: flex; gap: 10px; font-family: var(--font-mono); }
    .ad-edit-stats .add { color: #16a34a; }
    .ad-edit-stats .del { color: #dc2626; }
    .ad-edit-body {
      max-height: 280px; overflow-y: auto;
    }
    .ad-edit-body::-webkit-scrollbar { width: 4px; }
    .ad-edit-body::-webkit-scrollbar-thumb { background: rgba(11,32,38,0.12); border-radius: var(--r-full); }
    .ad-diff-line {
      padding: 1px 14px; font-family: var(--font-mono); font-size: 11px;
      line-height: 1.7; white-space: pre-wrap; word-break: break-word;
    }
    .ad-diff-line.equal { color: var(--txt2); }
    .ad-diff-line.insert { background: rgba(22,163,74,0.08); color: #15803d; }
    .ad-diff-line.insert::before { content: '+  '; color: #16a34a; font-weight: 700; }
    .ad-diff-line.delete { background: rgba(220,38,38,0.06); color: #991b1b; text-decoration: line-through; }
    .ad-diff-line.delete::before { content: '-  '; color: #dc2626; font-weight: 700; }
    /* Edit result badge (accepted / discarded) */
    .ad-edit-result {
      padding: 5px 14px; font-family: var(--font-mono); font-size: 11px;
      display: flex; align-items: center; gap: 6px; border-top: 1px solid var(--oat);
    }
    .ad-edit-result.accepted { color: var(--success); }
    .ad-edit-result.discarded { color: var(--txt3); }
    /* Status bar */
    .ad-status {
      flex-shrink: 0; padding: 4px 18px; font-family: var(--font-mono); font-size: 11px;
      color: var(--txt2); min-height: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .ad-empty { padding: 18px; text-align: center; color: var(--txt3); font-size: 12px; }
    /* Composer */
    .ad-composer {
      flex-shrink: 0; display: flex; gap: 10px; align-items: flex-end;
      padding: 10px 18px 14px; background: var(--white); border-top: 1px solid var(--oat);
    }
    .ad-ta {
      flex: 1; resize: none; min-height: 44px; max-height: 120px;
      padding: 11px 14px; border: 1.5px solid var(--oat); border-radius: var(--r-lg);
      background: var(--white); font: inherit; font-size: 14px; color: var(--txt);
      line-height: 1.4; transition: border-color 120ms, box-shadow 120ms;
    }
    .ad-ta:focus { outline: none; border-color: var(--lava); box-shadow: 0 0 0 3px rgba(255,54,33,0.1); }
    .ad-ta::placeholder { color: var(--txt3); }
    .ad-send {
      min-height: 44px; padding: 0 20px; border: none; border-radius: var(--r-lg);
      background: var(--lava); color: var(--white); font: inherit; font-weight: 600;
      cursor: pointer; transition: background 120ms;
    }
    .ad-send:hover { background: var(--lava-h); }
    .ad-send:active { background: var(--lava-a); }
    .ad-send:disabled { background: #c9c8c4; cursor: not-allowed; }
  `;
  el.appendChild(style);

  const root = document.createElement('div');
  root.className = 'ad-root';
  el.appendChild(root);

  const ce = (tag, cls, txt) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = String(txt);
    return n;
  };

  /* ── Header ── */
  const head = ce('div', 'ad-head');
  head.append(ce('div', 'ad-logo', 'D'));
  const headTxt = ce('div', 'ad-head-txt');
  head.append(headTxt);
  const headTitle = ce('div', 'ad-head-title', 'Agent Document Editor');
  const headSub = ce('div', 'ad-head-sub', 'Select a document, then prompt the agent to edit it');
  headTxt.append(headTitle, headSub);
  head.append(ce('div', 'ad-pill', 'agent rag'));

  const svgExpand = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';
  const svgCollapse = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';
  const fsBtn = document.createElement('button');
  fsBtn.className = 'ad-ico-btn'; fsBtn.innerHTML = svgExpand; fsBtn.title = 'Fullscreen';
  head.append(fsBtn);
  root.append(head);

  const isFs = () => { const f = document.fullscreenElement || document.webkitFullscreenElement; return f && root.contains(f); };
  const syncFs = () => { fsBtn.innerHTML = isFs() ? svgCollapse : svgExpand; fsBtn.title = isFs() ? 'Exit fullscreen' : 'Fullscreen'; };
  fsBtn.addEventListener('click', () => {
    if (isFs()) { (document.exitFullscreen || document.webkitExitFullscreen || (() => {})).call(document); }
    else if (root.requestFullscreen) { root.requestFullscreen().catch(() => {}); }
    else if (root.webkitRequestFullscreen) { root.webkitRequestFullscreen(); }
  });
  document.addEventListener('fullscreenchange', syncFs);
  document.addEventListener('webkitfullscreenchange', syncFs);

  /* ── Body ── */
  const bodyEl = ce('div', 'ad-body');
  root.append(bodyEl);

  /* Left sidebar */
  const left = ce('div', 'ad-left');
  left.append(ce('div', 'ad-left-hdr', 'Documents'));
  const docList = ce('div', 'ad-doc-list');
  left.append(docList);
  const newBtn = ce('button', 'ad-new-btn', '+ New document');
  left.append(newBtn);
  bodyEl.append(left);

  /* Right panel */
  const right = ce('div', 'ad-right');
  bodyEl.append(right);

  /* Chat area */
  const chat = ce('div', 'ad-chat');
  right.append(chat);

  /* Status bar */
  const statusBar = ce('div', 'ad-status');
  right.append(statusBar);

  /* Composer */
  const composer = ce('div', 'ad-composer');
  const ta = document.createElement('textarea');
  ta.className = 'ad-ta'; ta.rows = 1;
  ta.placeholder = 'Describe how to edit the document\u2026';
  const sendBtn = ce('button', 'ad-send', 'Send');
  composer.append(ta, sendBtn);
  right.append(composer);

  let docCardOpen = false;

  /* ── Helpers ── */
  const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  /* ── Renderers ── */
  const renderDocList = () => {
    let docs = [];
    try { docs = JSON.parse(model.get('documents_json') || '[]'); } catch(e) {}
    const sel = model.get('selected_doc_id') || '';
    docList.replaceChildren();
    if (!docs.length) { docList.append(ce('div', 'ad-empty', 'No documents yet')); return; }
    for (const d of docs) {
      const item = ce('div', d.doc_id === sel ? 'ad-doc-item active' : 'ad-doc-item');
      item.append(ce('div', 'ad-doc-title', d.title || d.doc_id));
      item.append(ce('div', 'ad-doc-meta', d.updated_at || ''));
      item.addEventListener('click', () => {
        model.set('selected_doc_id', d.doc_id);
        model.set('selected_title', d.title || '');
        model.set('selected_content', d.content || '');
        model.set('turns_json', '[]');
        model.set('status_text', '');
        model.save_changes();
      });
      docList.append(item);
    }
  };

  const buildDocCard = () => {
    const title = model.get('selected_title') || '';
    const content = model.get('selected_content') || '';
    const card = ce('div', 'ad-doc-card');
    const cardHead = ce('div', 'ad-doc-card-head');
    cardHead.append(ce('span', 'ad-doc-card-icon', '\ud83d\udcc4'));
    cardHead.append(ce('span', 'ad-doc-card-name', title || '(untitled)'));
    const chev = ce('span', 'ad-doc-card-chevron', docCardOpen ? '\u25bc' : '\u25b6');
    cardHead.append(chev);
    card.append(cardHead);
    const cardBody = ce('div', docCardOpen ? 'ad-doc-card-body open' : 'ad-doc-card-body');
    if (content) {
      const pre = ce('pre', 'ad-doc-card-pre', content);
      cardBody.append(pre);
    } else {
      cardBody.append(ce('div', 'ad-doc-card-empty', 'No content yet \u2014 use the prompt below to create it'));
    }
    card.append(cardBody);
    cardHead.addEventListener('click', () => {
      docCardOpen = !docCardOpen;
      cardBody.classList.toggle('open', docCardOpen);
      chev.textContent = docCardOpen ? '\u25bc' : '\u25b6';
    });
    return card;
  };

  const buildEditCard = (turn) => {
    const card = ce('div', 'ad-edit-card');
    const head = ce('div', 'ad-edit-head');
    head.append(ce('span', 'ad-edit-head-title', 'Document edit'));
    const stats = ce('span', 'ad-edit-stats');
    stats.append(ce('span', 'add', '+' + (turn.n_add || 0) + ' line' + ((turn.n_add || 0) !== 1 ? 's' : '')));
    stats.append(ce('span', 'del', '-' + (turn.n_del || 0) + ' line' + ((turn.n_del || 0) !== 1 ? 's' : '')));
    head.append(stats);
    card.append(head);
    // Diff body — use live diff_json for the active draft, stored diff for history
    const diff = turn.diff || [];
    if (diff.length) {
      const body = ce('div', 'ad-edit-body');
      for (const op of diff) {
        body.append(ce('div', 'ad-diff-line ' + op.type, op.text || ''));
      }
      card.append(body);
    }
    // Result badge
    if (turn.result) {
      const badge = ce('div', 'ad-edit-result ' + turn.result,
        turn.result === 'accepted' ? '\u2713 Applied' : '\u2717 Discarded');
      card.append(badge);
    }
    return card;
  };

  const renderChat = () => {
    let turns = [];
    try { turns = JSON.parse(model.get('turns_json') || '[]'); } catch(e) {}
    const busy = Boolean(model.get('busy'));
    chat.replaceChildren();

    // Always show the document card at the top
    if (model.get('selected_doc_id') || model.get('selected_title')) {
      chat.append(buildDocCard());
    } else {
      const empty = ce('div', 'ad-doc-card-empty');
      empty.style.cssText = 'text-align:center;padding:40px 20px;color:var(--txt2);';
      empty.innerHTML = '<div style="font-size:15px;font-weight:600;color:var(--txt);margin-bottom:6px">Select a document</div>Choose from the list, then describe your edits in the prompt below.';
      chat.append(empty);
    }

    // Conversation turns
    for (const turn of turns) {
      if (turn.role === 'user') {
        chat.append(ce('div', 'ad-user', turn.content || ''));
      } else if (turn.role === 'agent') {
        const agentDiv = ce('div', 'ad-agent-turn');
        if (turn.status === 'pending') {
          const pend = ce('div', 'ad-pending');
          pend.append(ce('div', 'ad-spin'));
          pend.append(ce('span', null, 'Agent editing document\u2026'));
          agentDiv.append(pend);
        } else {
          agentDiv.append(buildEditCard(turn));
        }
        chat.append(agentDiv);
      }
    }

    chat.scrollTop = chat.scrollHeight;
  };

  const renderChrome = () => {
    const busy = Boolean(model.get('busy'));
    const title = model.get('selected_title') || '';
    headSub.textContent = title ? 'Editing: ' + title : 'Select a document, then prompt the agent to edit it';
    sendBtn.disabled = busy;
    sendBtn.textContent = busy ? 'Working\u2026' : 'Send';
    ta.disabled = busy;
    statusBar.textContent = model.get('status_text') || '';
  };

  /* ── Event handlers ── */
  const send = () => {
    const v = ta.value.trim();
    if (!v || model.get('busy')) return;
    ta.value = ''; ta.style.height = 'auto';
    model.set('prompt', v);
    model.set('command', 'send');
    model.save_changes();
  };
  sendBtn.addEventListener('click', send);
  ta.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  ta.addEventListener('input', () => {
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  });
  newBtn.addEventListener('click', () => {
    model.set('selected_doc_id', '');
    model.set('selected_title', 'New Document');
    model.set('selected_content', '');
    model.set('turns_json', '[]');
    model.set('status_text', 'Describe the document to create in the prompt below');
    model.save_changes();
  });


  /* ── Model observers ── */
  const H = {
    'change:documents_json':    renderDocList,
    'change:selected_doc_id':   () => { renderDocList(); renderChat(); renderChrome(); },
    'change:selected_title':    () => { renderChat(); renderChrome(); },
    'change:selected_content':  renderChat,
    'change:turns_json':       () => { renderChat(); renderChrome(); },
    'change:busy':             renderChrome,
    'change:status_text':       renderChrome,
  };
  for (const [ev, fn] of Object.entries(H)) model.on(ev, fn);
  renderDocList(); renderChat(); renderChrome();
  return () => { for (const [ev, fn] of Object.entries(H)) model.off(ev, fn); };
}
export default { render };
'''


class AgentDocumentWidget(anywidget.AnyWidget):
    '''Agent-driven document editor with chat history, diff preview, and re-embedding.'''

    _esm = _ESM

    documents_json   = traitlets.Unicode('[]').tag(sync=True)
    selected_doc_id  = traitlets.Unicode('').tag(sync=True)
    selected_title   = traitlets.Unicode('').tag(sync=True)
    selected_content = traitlets.Unicode('').tag(sync=True)
    # Agent conversation
    turns_json  = traitlets.Unicode('[]').tag(sync=True)
    prompt      = traitlets.Unicode('').tag(sync=True)
    status_text = traitlets.Unicode('').tag(sync=True)
    # Control
    command = traitlets.Unicode('').tag(sync=True)
    busy    = traitlets.Bool(False).tag(sync=True)
    error   = traitlets.Unicode('').tag(sync=True)

    def __init__(self, *, chat_fn, spark_merge_fn,
                 fetch_documents_fn,
                 initial_doc_id='', **kwargs):
        super().__init__(**kwargs)
        self._chat_fn            = chat_fn
        self._spark_merge_fn     = spark_merge_fn
        self._fetch_documents_fn = fetch_documents_fn

        try:
            docs = self._fetch_documents_fn()
            self.documents_json = json.dumps(docs)
            target_id = initial_doc_id or (docs[0]['doc_id'] if docs else '')
            if target_id:
                for d in docs:
                    if d['doc_id'] == target_id:
                        self.selected_doc_id  = d['doc_id']
                        self.selected_title   = d.get('title', '')
                        self.selected_content = d.get('content', '')
                        break
        except Exception as exc:
            self.error = f'Init error: {exc}'

    @traitlets.observe('command')
    def _on_command(self, change):
        cmd = change['new']
        if not cmd:
            return
        self.command = ''
        if cmd == 'send':
            threading.Thread(target=self._do_send, daemon=True).start()

    # ── Helpers ─────────────────────────────────────────────────────────

    def _get_turns(self):
        try:
            return json.loads(self.turns_json or '[]')
        except Exception:
            return []

    def _set_turns(self, turns):
        self.turns_json = json.dumps(turns)

    # ── Command handlers ─────────────────────────────────────────────────

    def _do_send(self):
        self.busy = True
        self.error = ''

        prompt = self.prompt.strip()
        title = self.selected_title or 'New Document'
        content = self.selected_content
        doc_id = self.selected_doc_id.strip()

        # Append user turn + pending agent turn
        turns = self._get_turns()
        turns.append({'role': 'user', 'content': prompt})
        turns.append({'role': 'agent', 'status': 'pending', 'n_add': 0, 'n_del': 0, 'diff': []})
        self._set_turns(turns)

        try:
            sys_msg = (
                'You are a document editor. '
                'Return ONLY the complete edited document text — no preamble, '
                'no explanation, no markdown code fences.'
            )
            if content:
                user_msg = (
                    f'Current title: {title}\n\n'
                    f'Current content:\n{content}\n\n'
                    f'---\nInstruction: {prompt}\n\n'
                    f'Return the complete document text with the edit applied.'
                )
            else:
                user_msg = (
                    f'Title: {title}\n\n'
                    f'Create a document based on this instruction: {prompt}\n\n'
                    f'Return the complete document text.'
                )

            self.status_text = 'Agent editing document\u2026'
            resp = self._chat_fn([{'role': 'system', 'content': sys_msg},
                                   {'role': 'user',   'content': user_msg}])
            new_content = (resp if isinstance(resp, str) else ''.join(resp)).strip()

            # Strip accidental markdown code fences
            if new_content.startswith('```'):
                lines = new_content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                new_content = '\n'.join(lines).strip()

            diff = _compute_diff(content, new_content)
            n_add = sum(1 for d in diff if d['type'] == 'insert')
            n_del = sum(1 for d in diff if d['type'] == 'delete')

            # Auto-apply: generate doc_id for new documents
            if not doc_id:
                slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:50]
                doc_id = slug or f'doc-{int(time.time())}'
                self.selected_doc_id = doc_id

            self.selected_title   = title
            self.selected_content = new_content

            self._spark_merge_fn(doc_id, title, new_content)

            # Update pending agent turn → accepted
            turns = self._get_turns()
            for i in range(len(turns) - 1, -1, -1):
                if turns[i].get('role') == 'agent' and turns[i].get('status') == 'pending':
                    turns[i] = {'role': 'agent', 'status': 'accepted',
                                 'result': 'accepted',
                                 'n_add': n_add, 'n_del': n_del, 'diff': diff}
                    break
            self._set_turns(turns)

            try:
                self.documents_json = json.dumps(self._fetch_documents_fn())
            except Exception:
                pass

            self.status_text = 'Applied \u2014 search index updating automatically'
        except Exception as exc:
            turns = self._get_turns()
            for i in range(len(turns) - 1, -1, -1):
                if turns[i].get('role') == 'agent' and turns[i].get('status') == 'pending':
                    turns[i] = {'role': 'agent', 'status': 'error',
                                 'n_add': 0, 'n_del': 0, 'diff': [],
                                 'error_msg': str(exc)}
                    break
            self._set_turns(turns)
            self.status_text = f'Error: {exc}'
            self.error = str(exc)
        finally:
            self.busy = False

