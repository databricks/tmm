"""Databricks I/O for the optional Marketplace-ingest path.

The Databricks SDK is imported LAZILY (only inside these functions), so the static
server boots and serves the bundled snapshot even if `databricks-sdk` isn't
installed or the workspace is unreachable. On Databricks Apps, WorkspaceClient()
with no args picks up the app service principal's injected OAuth credentials.
"""
import io
import json
import time
import urllib.request

_W = None


def client():
    """Lazy WorkspaceClient singleton."""
    global _W
    if _W is None:
        from databricks.sdk import WorkspaceClient
        _W = WorkspaceClient()
    return _W


def _download(url: str) -> bytes:
    # Presigned external-link URLs are pre-authenticated; no auth header.
    with urllib.request.urlopen(url) as resp:
        return resp.read()


def probe(warehouse_id: str, catalog: str, schema: str, timeout_s: float = 30.0) -> bool:
    """True iff `<catalog>.<schema>.state_vectors` exists and is readable.

    Runs a trivial LIMIT 1. A missing table / no grant fails fast (compile error);
    a cold serverless warehouse resolves within wait_timeout. Any error -> False.
    """
    if not warehouse_id:
        return False
    try:
        from databricks.sdk.service.sql import StatementState
        w = client()
        wait = f"{max(5, min(50, int(timeout_s)))}s"
        sql = f"SELECT 1 FROM `{catalog}`.`{schema}`.state_vectors LIMIT 1"
        resp = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id, statement=sql, wait_timeout=wait
        )
        state = resp.status.state if resp.status else None
        # Poll briefly if it didn't settle within wait_timeout.
        sid = resp.statement_id
        deadline = time.time() + timeout_s
        while state in (StatementState.PENDING, StatementState.RUNNING) and time.time() < deadline:
            time.sleep(1.0)
            resp = w.statement_execution.get_statement(sid)
            state = resp.status.state if resp.status else None
        return state == StatementState.SUCCEEDED
    except Exception:
        return False


def run_query(warehouse_id: str, sql: str, poll_s: float = 2.0):
    """Execute `sql` on the warehouse; return (column_names, row_iterator).

    Uses EXTERNAL_LINKS + JSON_ARRAY (result sets exceed the 25 MiB INLINE cap).
    Rows are streamed chunk-by-chunk; each chunk's presigned link is a JSON array
    of row-arrays. Raises RuntimeError on failure.
    """
    from databricks.sdk.service.sql import Disposition, Format, StatementState
    w = client()
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=sql,
        disposition=Disposition.EXTERNAL_LINKS, format=Format.JSON_ARRAY,
        wait_timeout="30s",
    )
    sid = resp.statement_id
    state = resp.status.state if resp.status else None
    while state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(poll_s)
        resp = w.statement_execution.get_statement(sid)
        state = resp.status.state if resp.status else None
    if state != StatementState.SUCCEEDED:
        msg = ""
        if resp.status and resp.status.error:
            msg = resp.status.error.message or ""
        raise RuntimeError(f"statement {state}: {msg}")

    cols = [c.name for c in resp.manifest.schema.columns] if resp.manifest else []

    def rows():
        chunk = resp.result
        while chunk is not None:
            links = chunk.external_links or []
            for link in links:
                data = _download(link.external_link)
                for row in json.loads(data):
                    yield row
            nxt = links[-1].next_chunk_index if links else None
            if nxt is None:
                break
            chunk = w.statement_execution.get_statement_result_chunk_n(sid, nxt)

    return cols, rows()


def rows_as_dicts(cols, rows):
    """Map positional JSON_ARRAY rows back to {column: value} dicts."""
    for row in rows:
        yield {c: v for c, v in zip(cols, row)}


def query_dicts(warehouse_id: str, sql: str) -> list:
    """Convenience: run a query and materialize rows as a list of dicts."""
    cols, rows = run_query(warehouse_id, sql)
    return list(rows_as_dicts(cols, rows))


# ---- UC Volume I/O (Files API). Volume PUT is atomic at the object level, so a
# reader gets either the old or new blob, never a partial one. ----

def write_volume(path: str, data: bytes) -> None:
    client().files.upload(path, io.BytesIO(data), overwrite=True)


def read_volume(path: str):
    """Return file bytes, or None if it doesn't exist."""
    try:
        return client().files.download(path).contents.read()
    except Exception:
        return None


def volume_exists(path: str) -> bool:
    try:
        client().files.get_metadata(path)
        return True
    except Exception:
        return False
