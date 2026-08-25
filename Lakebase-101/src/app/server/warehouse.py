"""Query the lakehouse (Delta) via SQL Warehouse — the 'before reverse-ETL' path, for the speed comparison."""
import time
from databricks.sdk.service.sql import StatementState
from .config import get_workspace_client, WAREHOUSE_ID, GOLD_TABLE


def run_sql(sql: str):
    w = get_workspace_client()
    resp = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID, statement=sql, wait_timeout="50s",
    )
    if resp.status and resp.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(f"warehouse query failed: {resp.status.state} {getattr(resp.status,'error',None)}")
    cols = [c.name for c in resp.manifest.schema.columns] if resp.manifest and resp.manifest.schema else []
    sid = resp.statement_id
    rows = []
    result = resp.result
    while result is not None:
        for row in (result.data_array or []):
            rows.append(dict(zip(cols, row)))
        nxt = result.next_chunk_index
        if nxt is None:
            break
        result = w.statement_execution.get_statement_result_chunk_n(sid, nxt)
    return rows


def timed_run_sql(sql: str):
    t0 = time.perf_counter()
    rows = run_sql(sql)
    ms = (time.perf_counter() - t0) * 1000.0
    return rows, ms


def fetch_gold(since=None):
    """Read curated customer-360 rows from the lakehouse gold table (reverse-ETL source).

    If `since` (a 'yyyy-MM-dd HH:mm:ss.SSSSSS' watermark) is given, return only rows whose
    gold_updated_at advanced past it — the incremental reverse-ETL path. gold_updated_at is
    returned as a fixed-width string so lexicographic max == chronological max.
    """
    cols = ("customer_id,full_name,email,city,segment,lifetime_value,total_orders,avg_order_value,"
            "churn_risk_score,churn_risk_band,recommended_product_id,recommended_product_name,"
            "recommended_category,recommended_price,last_order_date,"
            "date_format(gold_updated_at,'yyyy-MM-dd HH:mm:ss.SSSSSS') AS gold_updated_at")
    sql = f"SELECT {cols} FROM {GOLD_TABLE}"
    if since:
        sql += f" WHERE gold_updated_at > timestamp'{since}'"
    sql += " ORDER BY gold_updated_at, customer_id"
    return run_sql(sql)
