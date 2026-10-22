"""Document search agent widget for Databricks notebooks.

A chat agent that searches through chunked & embedded agent documents stored
in Lakebase via the document pipeline. Two retrieval tools:

    search_documents    hybrid (vector + text) search over document chunks
    open_document       fetch the full content of a document by its doc_id

Reuses the same ESM (frontend) as SupportAgentWidget — same chat UI with a
live tool-call trace — but with a different system prompt, tool specs, and
backend dispatch.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import anywidget
import traitlets

# Reuse the ESM from the support agent widget (same folder)
from support_agent_widget import _AGENT_ESM

__all__ = ["DocumentSearchAgentWidget", "DOC_TOOL_SPECS"]


DOC_TOOL_SPECS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Hybrid search (vector + keyword) over chunked knowledge-base documents "
                "stored in Lakebase. Returns the most relevant chunks with their titles, "
                "preview text, and similarity scores. Use this to find information across "
                "all documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What you are looking for in the documents.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "How many chunks to return (1-10, default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_document",
            "description": (
                "Retrieve the full content of a specific document by its doc_id. "
                "Use this after search_documents has identified a relevant document "
                "and you need the complete text to answer in detail."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "The document identifier returned by search_documents.",
                    },
                },
                "required": ["doc_id"],
            },
        },
    },
]


_DOC_SYSTEM_PROMPT = """You are a knowledge base assistant. You help users find and read
documents from the document library — buying guides, playbooks, and product guides
that have been chunked, embedded, and indexed in Lakebase.

You have two retrieval tools:

1. search_documents — hybrid (vector + keyword) search over document chunks.
   Use this to find relevant passages across all documents.
2. open_document — fetch the full text of a document by its doc_id.
   Use this when a user wants to read or learn about a specific document.

Workflow:
1. When the user asks a question, search_documents with a good query.
2. If a chunk looks relevant and the user wants detail, call open_document
   to retrieve the full document.
3. Summarize the relevant information in plain language.

Answer style: plain text, no markdown, concise (100-150 words max).
Always cite the document title. Never invent information that was not in a
tool result.
"""

_DOC_SUGGESTIONS = [
    "What documents are in the knowledge base?",
    "Find information about USB-C charging",
    "Open the headphones buying guide",
    "What switch types are recommended for typing?",
]


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


class DocumentSearchAgentWidget(anywidget.AnyWidget):
    """Chat agent that searches chunked documents in Lakebase."""

    _esm = _AGENT_ESM

    turns_json = traitlets.Unicode("[]").tag(sync=True)
    suggestions_json = traitlets.Unicode("[]").tag(sync=True)
    input_text = traitlets.Unicode("").tag(sync=True)
    command = traitlets.Unicode("").tag(sync=True)
    busy = traitlets.Bool(False).tag(sync=True)
    status = traitlets.Unicode("").tag(sync=True)
    error = traitlets.Unicode("").tag(sync=True)
    model_label = traitlets.Unicode("").tag(sync=True)
    customer_name = traitlets.Unicode("Document Search").tag(sync=True)
    max_steps = traitlets.Int(6).tag(sync=True)

    def __init__(
        self,
        *,
        chat_fn: Callable[[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]], Dict[str, Any]],
        fetch_fn: Callable[..., Any],
        embed_fn: Callable[[str, str], Sequence[float]],
        fetch_document_fn: Callable[[str], Optional[Dict[str, Any]]],
        database_name: str = "",
        chunks_table: str = "synced_document_chunks",
        embedding_model: str = "databricks-gte-large-en",
        suggestions: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self._chat_fn = chat_fn
        self._fetch_fn = fetch_fn
        self._embed_fn = embed_fn
        self._fetch_document_fn = fetch_document_fn
        self._database_name = database_name
        self._chunks_table = chunks_table
        self._embedding_model = embedding_model
        kwargs.setdefault("suggestions_json", json.dumps(suggestions or _DOC_SUGGESTIONS))
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
        self.turns_json = json.dumps(turns)

    def _history(self, past_turns: List[Dict[str, Any]], keep: int = 6) -> List[Dict[str, Any]]:
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
            {"role": "system", "content": _DOC_SYSTEM_PROMPT}
        ]
        msgs.extend(history)
        msgs.append({"role": "user", "content": user_text})

        started = time.perf_counter()
        searches = 0
        model_calls = 0

        try:
            for step in range(max(1, int(self.max_steps))):
                self.status = "thinking" if step == 0 else f"thinking (round {step + 1})"
                reply = self._chat_fn(msgs, DOC_TOOL_SPECS)
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
                        "query": self._event_label(name, args),
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
                    except Exception as exc:
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
        out = (text or "").replace("**", "").replace("__", "")
        return "\n".join(
            line.lstrip("#").strip() if line.startswith("#") else line
            for line in out.splitlines()
        ).strip()

    @staticmethod
    def _footer(searches: int, model_calls: int, started: float) -> str:
        label = "search" if searches == 1 else "searches"
        return (
            f"{searches} {label} \u00b7 {model_calls} model calls \u00b7 "
            f"{time.perf_counter() - started:.1f} s"
        )

    @staticmethod
    def _event_label(name: str, args: Dict[str, Any]) -> str:
        if name == "open_document":
            return str(args.get("doc_id", ""))[:120]
        return str(args.get("query", ""))[:120]

    # ------------------------------------------------------------------ tools

    def _dispatch(
        self, name: str, args: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if name == "search_documents":
            query = str(args.get("query") or "").strip()
            if not query:
                raise ValueError("the tool call is missing a query")
            return self._tool_search(query, args)
        if name == "open_document":
            doc_id = str(args.get("doc_id") or "").strip()
            if not doc_id:
                raise ValueError("the tool call is missing a doc_id")
            return self._tool_open(doc_id)
        raise ValueError(f"unknown tool: {name}")

    def _vector_literal(self, query: str) -> str:
        emb = self._embed_fn(query, self._embedding_model)
        return "[" + ",".join(f"{float(v):.12f}" for v in emb) + "]"

    @staticmethod
    def _clamp_k(raw: Any, default: int = 5, high: int = 10) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return max(1, min(high, value))

    def _tool_search(
        self, query: str, args: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        k = self._clamp_k(args.get("top_k"))
        tbl = self._chunks_table
        literal = self._vector_literal(query)
        pool = 40

        df = self._fetch_fn(
            f"WITH q AS (SELECT %s::vector AS qv, %s AS qt), "
            f"vector_ranked AS ("
            f"  SELECT chunk_id, RANK() OVER (ORDER BY dist) AS rank FROM ("
            f"    SELECT chunk_id, c.embedding <=> q.qv AS dist FROM {tbl} c, q ORDER BY dist LIMIT {pool}"
            f"  ) v"
            f"), text_ranked AS ("
            f"  SELECT chunk_id, RANK() OVER (ORDER BY r DESC) AS rank FROM ("
            f"    SELECT chunk_id, ts_rank(to_tsvector('english', chunk_text), plainto_tsquery('english', q.qt)) AS r"
            f"    FROM {tbl} c, q"
            f"    WHERE to_tsvector('english', chunk_text) @@ plainto_tsquery('english', q.qt)"
            f"    ORDER BY r DESC LIMIT {pool}"
            f"  ) t"
            f") SELECT c.chunk_id, c.doc_id, c.chunk_idx, c.title, left(c.chunk_text, 200) AS preview,"
            f"  COALESCE(1.0/(60+v.rank),0)+COALESCE(1.0/(60+t.rank),0) AS rrf_score"
            f" FROM {tbl} c"
            f" LEFT JOIN vector_ranked v ON c.chunk_id = v.chunk_id"
            f" LEFT JOIN text_ranked t ON c.chunk_id = t.chunk_id"
            f" WHERE v.chunk_id IS NOT NULL OR t.chunk_id IS NOT NULL"
            f" ORDER BY rrf_score DESC LIMIT {k}",
            (literal, query),
            dbname=self._database_name,
        )

        llm_rows: List[Dict[str, Any]] = []
        ui_rows: List[Dict[str, Any]] = []
        for record in df.to_dict("records"):
            score = _as_float(record.get("rrf_score"))
            llm_rows.append(
                {
                    "doc_id": record.get("doc_id"),
                    "chunk_idx": record.get("chunk_idx"),
                    "title": record.get("title"),
                    "preview": record.get("preview"),
                }
            )
            ui_rows.append(
                {
                    "title": record.get("title"),
                    "meta": f"{record.get('doc_id')} \u00b7 chunk {record.get('chunk_idx')}",
                    "score": f"rrf {score:.5f}" if score is not None else "",
                }
            )
        return llm_rows, ui_rows

    def _tool_open(
        self, doc_id: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        doc = self._fetch_document_fn(doc_id)
        if doc is None:
            raise ValueError(f"document '{doc_id}' not found")
        content = doc.get("content") or ""
        title = doc.get("title") or doc_id
        length = len(content)
        llm_rows = [
            {
                "doc_id": doc_id,
                "title": title,
                "content": content[:8000],
            }
        ]
        ui_rows = [
            {
                "title": title,
                "meta": f"{doc_id} \u00b7 {length:,} chars",
                "score": "",
            }
        ]
        return llm_rows, ui_rows
