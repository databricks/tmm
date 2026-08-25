"""Lakebase Postgres access with OAuth token + lazy refresh. Sync psycopg2 (simple & reliable for a demo)."""
import time
import threading
import psycopg2
import psycopg2.extras
from .config import get_pg_params, get_pg_password

_lock = threading.Lock()
_state = {"conn": None, "token_at": 0.0}
_TOKEN_TTL = 40 * 60  # refresh well before the 1h expiry


def _connect():
    params = get_pg_params()
    conn = psycopg2.connect(
        host=params["host"], port=params["port"], dbname=params["dbname"],
        user=params["user"], password=get_pg_password(), sslmode="require",
        connect_timeout=10,
    )
    conn.autocommit = True
    return conn


def _get_conn():
    with _lock:
        c = _state["conn"]
        stale = (time.time() - _state["token_at"]) > _TOKEN_TTL
        if c is None or c.closed or stale:
            try:
                if c is not None and not c.closed:
                    c.close()
            except Exception:
                pass
            _state["conn"] = _connect()
            _state["token_at"] = time.time()
        return _state["conn"]


def query(sql, args=None, one=False):
    """Run a query, return list[dict] (or single dict). Retries once on a dropped connection."""
    for attempt in range(2):
        try:
            conn = _get_conn()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, args or ())
                if cur.description is None:
                    return None
                rows = cur.fetchall()
                rows = [dict(r) for r in rows]
                return (rows[0] if rows else None) if one else rows
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            with _lock:
                _state["conn"] = None
            if attempt == 1:
                raise
            time.sleep(0.2)


def execute(sql, args=None):
    for attempt in range(2):
        try:
            conn = _get_conn()
            with conn.cursor() as cur:
                cur.execute(sql, args or ())
                return cur.rowcount
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            with _lock:
                _state["conn"] = None
            if attempt == 1:
                raise
            time.sleep(0.2)


def timed_query(sql, args=None, one=False):
    """Return (result, server_round_trip_ms)."""
    t0 = time.perf_counter()
    res = query(sql, args, one=one)
    ms = (time.perf_counter() - t0) * 1000.0
    return res, ms


_wstate = {"conn": None, "token_at": 0.0}


def _new_write_conn():
    params = get_pg_params()
    c = psycopg2.connect(
        host=params["host"], port=params["port"], dbname=params["dbname"],
        user=params["user"], password=get_pg_password(), sslmode="require", connect_timeout=15,
    )
    c.autocommit = False
    return c


def get_write_connection():
    """Cached transactional connection (autocommit off). Reused across writes so OLTP stays snappy.

    Caller owns commit/rollback. On a dropped/expired connection the caller should retry once.
    """
    with _lock:
        c = _wstate["conn"]
        stale = (time.time() - _wstate["token_at"]) > _TOKEN_TTL
        if c is None or c.closed or stale:
            try:
                if c is not None and not c.closed:
                    c.close()
            except Exception:
                pass
            _wstate["conn"] = _new_write_conn()
            _wstate["token_at"] = time.time()
        return _wstate["conn"]


def reset_write_connection():
    with _lock:
        c = _wstate["conn"]
        try:
            if c is not None and not c.closed:
                c.close()
        except Exception:
            pass
        _wstate["conn"] = None


# kept for compatibility — bulk sync wants its own throwaway connection
def get_raw_connection():
    return _new_write_conn()
