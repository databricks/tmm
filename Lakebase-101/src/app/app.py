"""Lakebase 101 — DAIS demo. Reverse ETL (native synced table) + OLTP speed + Apps."""
import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg2.extras

from server import db, warehouse
from server.config import (
    IS_DATABRICKS_APP, GOLD_TABLE, SYNCED_TABLE, get_sync_pipeline_id, DIRECTORY_TABLE, DIRECTORY_SOURCE,
    SALES_TABLE, SALES_SOURCE, get_pg_params, get_workspace_client, WAREHOUSE_ID,
    sdk_version, lakebase_diagnostics,
)

app = FastAPI(title="Lakebase 101 — Order Ops Console")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# ---------------------------- models ----------------------------
class OrderReq(BaseModel):
    customer_id: int
    product_id: int
    quantity: int = 1


class SyncReq(BaseModel):
    full_refresh: bool = False


# ---------------------------- meta ----------------------------
@app.get("/api/health")
def health():
    pg = get_pg_params()
    out = {
        "mode": "databricks-app" if IS_DATABRICKS_APP else "local",
        "sdk_version": sdk_version(),
        "pg_host": pg["host"], "pg_database": pg["dbname"], "pg_user": pg["user"],
        "warehouse_id": WAREHOUSE_ID, "gold_table": GOLD_TABLE, "synced_table": SYNCED_TABLE,
    }
    try:
        out["lakebase_ok"] = bool(db.query("SELECT 1 AS ok", one=True))
    except Exception as e:
        out["lakebase_ok"] = False
        out["error"] = f"{type(e).__name__}: {e}"
    return out


@app.get("/api/debug")
def debug():
    """Deep connection diagnostic — SDK version, credential mint, connect, visible
    schemas/tables, and per-table counts, with the real error at whichever step fails.
    Hit this first whenever Lakebase access looks broken."""
    return lakebase_diagnostics()


@app.get("/api/customers")
def customers(q: str = "", limit: int = 12):
    """Search the 50k customer directory (managed synced table) — by number prefix or name."""
    limit = max(1, min(int(limit), 50))
    q = (q or "").strip()
    cols = "customer_id, full_name, segment, city, total_sales, num_sales"
    if q.isdigit():
        rows = db.query(
            f"SELECT {cols} FROM {DIRECTORY_TABLE} WHERE customer_id::text LIKE %s ORDER BY customer_id LIMIT %s",
            (q + "%", limit))
    elif q:
        rows = db.query(
            f"SELECT {cols} FROM {DIRECTORY_TABLE} WHERE full_name ILIKE %s ORDER BY customer_id LIMIT %s",
            ("%" + q + "%", limit))
    else:
        rows = db.query(f"SELECT {cols} FROM {DIRECTORY_TABLE} ORDER BY customer_id LIMIT %s", (limit,))
    return {"customers": rows, "total": 50000}


@app.get("/api/stats")
def stats():
    row = db.query(
        f"""
        SELECT
          (SELECT count(*) FROM {SYNCED_TABLE}) AS synced_customers,
          (SELECT max(gold_updated_at) FROM {SYNCED_TABLE}) AS last_sync,
          (SELECT count(*) FROM orders) AS total_orders,
          (SELECT count(*) FROM orders WHERE created_at::date = now()::date) AS orders_today,
          (SELECT coalesce(sum(total),0) FROM orders) AS gmv,
          (SELECT count(*) FROM inventory) AS products,
          (SELECT coalesce(sum(stock_on_hand),0) FROM inventory) AS units_in_stock
        """,
        one=True,
    )
    return row


# ---------------------------- reverse ETL: native managed synced table ----------------------------
@app.post("/api/sync")
def trigger_sync(req: SyncReq):
    """Trigger the managed synced-table pipeline (native reverse ETL: Delta gold -> Lakebase Postgres)."""
    try:
        w = get_workspace_client()
        upd = w.pipelines.start_update(get_sync_pipeline_id(), full_refresh=bool(req.full_refresh))
        return {"triggered": True, "pipeline_id": get_sync_pipeline_id(),
                "update_id": getattr(upd, "update_id", None), "full_refresh": bool(req.full_refresh)}
    except Exception as e:
        raise HTTPException(502, f"failed to trigger pipeline: {e}")


@app.get("/api/sync/status")
def sync_status(update_id: str = None):
    """State of the managed synced-table pipeline (optionally a specific update) + live Lakebase row count."""
    state = None
    try:
        w = get_workspace_client()
        p = w.pipelines.get(get_sync_pipeline_id())
        ups = p.latest_updates or []
        chosen = None
        if update_id:
            chosen = next((u for u in ups if u.update_id == update_id), None)
        chosen = chosen or (ups[0] if ups else None)
        if chosen:
            state = str(chosen.state).split(".")[-1]
    except Exception as e:
        state = f"unknown ({e})"
    lakebase_error = None
    try:
        total = db.query(f"SELECT count(*) AS n FROM {SYNCED_TABLE}", one=True)["n"]
    except Exception as e:
        # Don't silently swallow: a failed count here is what renders as the
        # misleading "0 rows live in Lakebase" in the UI. Surface the real cause.
        total = None
        lakebase_error = f"{type(e).__name__}: {e}"
    return {"state": state, "total_in_lakebase": total, "pipeline_id": get_sync_pipeline_id(),
            "lakebase_error": lakebase_error}


# ---------------------------- speed comparison ----------------------------
@app.get("/api/speed/{customer_id}")
def speed(customer_id: int):
    """Same point lookup, two engines: Lakebase synced table (operational) vs SQL Warehouse (lakehouse Delta)."""
    cols = "customer_id, full_name, segment, lifetime_value, churn_risk_band, recommended_product_name"
    lb_row, lb_ms = db.timed_query(
        f"SELECT {cols} FROM {SYNCED_TABLE} WHERE customer_id=%s", (customer_id,), one=True
    )
    wh_rows, wh_ms = warehouse.timed_run_sql(
        f"SELECT {cols} FROM {GOLD_TABLE} WHERE customer_id={customer_id}"
    )
    if not lb_row:
        raise HTTPException(404, "customer not found in Lakebase")
    speedup = round(wh_ms / lb_ms, 1) if lb_ms > 0 else None
    return {
        "customer": lb_row,
        "lakebase_ms": round(lb_ms, 2),
        "warehouse_ms": round(wh_ms, 1),
        "speedup": speedup,
    }


# ---------------------------- heavy-analytics showdown (lakehouse territory) ----------------------------
SALES_EVENTS = 5_000_000
LB_ANALYTICS_TIMEOUT_MS = 30000


@app.get("/api/aggregate")
def aggregate():
    """The SAME analytical query, two engines. Join 5M sales events to the customer directory."""
    lb_sql = f"""
        SELECT c.segment                        AS segment,
               COUNT(*)                          AS events,
               COUNT(DISTINCT e.customer_id)     AS active_customers,
               ROUND(SUM(e.amount))::bigint      AS revenue,
               ROUND(AVG(e.amount)::numeric, 2)  AS avg_amount
        FROM {SALES_TABLE} e
        JOIN {DIRECTORY_TABLE} c ON c.customer_id = e.customer_id
        GROUP BY c.segment ORDER BY revenue DESC"""
    wh_sql = f"""
        SELECT c.segment                          AS segment,
               COUNT(*)                            AS events,
               COUNT(DISTINCT e.customer_id)       AS active_customers,
               CAST(ROUND(SUM(e.amount)) AS bigint) AS revenue,
               ROUND(AVG(e.amount), 2)             AS avg_amount
        FROM {SALES_SOURCE} e
        JOIN {DIRECTORY_SOURCE} c ON c.customer_id = e.customer_id
        GROUP BY c.segment ORDER BY revenue DESC"""

    import psycopg2
    lb_rows, lb_ms, lb_note = None, None, None
    conn = db.get_raw_connection()
    try:
        conn.autocommit = True
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SET statement_timeout = {LB_ANALYTICS_TIMEOUT_MS}")
            t0 = time.perf_counter()
            cur.execute(lb_sql)
            lb_rows = [dict(r) for r in cur.fetchall()]
            lb_ms = (time.perf_counter() - t0) * 1000.0
    except psycopg2.errors.QueryCanceled:
        lb_ms = float(LB_ANALYTICS_TIMEOUT_MS)
        lb_note = f"timed out at {LB_ANALYTICS_TIMEOUT_MS // 1000}s — not an OLTP workload"
    except Exception as e:
        lb_note = f"error: {e}"
    finally:
        try:
            conn.close()
        except Exception:
            pass

    wh_rows, wh_ms = warehouse.timed_run_sql(wh_sql)

    winner = "warehouse" if (lb_ms is None or wh_ms < lb_ms) else "lakebase"
    factor = round(max(lb_ms, wh_ms) / min(lb_ms, wh_ms), 1) if (lb_ms and wh_ms) else None
    rows = lb_rows if lb_rows else wh_rows
    return {
        "rows": rows,
        "sales_events": SALES_EVENTS,
        "lakebase_ms": round(lb_ms, 1) if lb_ms is not None else None,
        "lakebase_note": lb_note,
        "warehouse_ms": round(wh_ms, 1),
        "winner": winner,
        "factor": factor,
    }


# ---------------------------- customer 360 (fast read) ----------------------------
@app.get("/api/customer/{customer_id}")
def customer(customer_id: int):
    prof, ms = db.timed_query(
        f"SELECT * FROM {SYNCED_TABLE} WHERE customer_id=%s", (customer_id,), one=True
    )
    if not prof:
        raise HTTPException(404, "customer not found")
    orders = db.query(
        "SELECT order_id, product_name, quantity, unit_price, total, status, created_at "
        "FROM orders WHERE customer_id=%s ORDER BY created_at DESC LIMIT 8",
        (customer_id,),
    )
    return {"profile": prof, "orders": orders, "read_ms": round(ms, 2)}


# ---------------------------- inventory ----------------------------
@app.get("/api/inventory")
def inventory():
    rows, ms = db.timed_query(
        "SELECT product_id, product_name, category, price, stock_on_hand FROM inventory ORDER BY product_id"
    )
    return {"inventory": rows, "read_ms": round(ms, 2)}


# ---------------------------- OLTP write: place order ----------------------------
@app.post("/api/order")
def place_order(req: OrderReq):
    """Real OLTP transaction in Lakebase: insert order + decrement stock, atomically."""
    if req.quantity < 1:
        raise HTTPException(400, "quantity must be >= 1")

    import psycopg2 as _pg
    for attempt in range(2):
        conn = db.get_write_connection()
        try:
            t0 = time.perf_counter()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT product_name, price, stock_on_hand FROM inventory WHERE product_id=%s FOR UPDATE",
                            (req.product_id,))
                prod = cur.fetchone()
                if not prod:
                    conn.rollback()
                    raise HTTPException(404, "product not found")
                if prod["stock_on_hand"] < req.quantity:
                    conn.rollback()
                    raise HTTPException(409, f"insufficient stock ({prod['stock_on_hand']} left)")
                total = float(prod["price"]) * req.quantity
                cur.execute(
                    "INSERT INTO orders (customer_id, product_id, product_name, quantity, unit_price, total) "
                    "VALUES (%s,%s,%s,%s,%s,%s) RETURNING order_id, created_at",
                    (req.customer_id, req.product_id, prod["product_name"], req.quantity, prod["price"], total),
                )
                new = cur.fetchone()
                cur.execute("UPDATE inventory SET stock_on_hand = stock_on_hand - %s, updated_at=now() WHERE product_id=%s",
                            (req.quantity, req.product_id))
            conn.commit()
            write_ms = (time.perf_counter() - t0) * 1000.0
            break
        except (_pg.OperationalError, _pg.InterfaceError):
            db.reset_write_connection()
            if attempt == 1:
                raise
            continue
    return {
        "order_id": new["order_id"], "product_name": prod["product_name"], "quantity": req.quantity,
        "total": total, "created_at": new["created_at"].isoformat(), "write_ms": round(write_ms, 2),
    }


# ---------------------------- static frontend ----------------------------
if os.path.isdir(os.path.join(STATIC_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
