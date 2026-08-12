"""Background 'Regenerate from Marketplace' orchestrator.

Runs the extraction SQL (sql.py) against a SQL warehouse, compacts the results
into the app's artifact shapes (transforms.py), gzips them byte-compatibly, and
writes them to a Unity Catalog volume. One run covers all three regions. Progress
lives in an in-memory STATE guarded by a lock; the HTTP layer polls it. Everything
Databricks-touching is lazy (dbx.py), so import of this module is cheap.
"""
import datetime
import threading
import traceback

import dbx
import sql
import transforms as T

REGION_ORDER = ["europe", "north-america", "australia"]
ARTIFACTS = ["prism", "density", "anomaly"]  # what we write per region
TOTAL_STEPS = len(REGION_ORDER) * 4  # 4 queries per region (prism, density, curve, anomaly)

_LOCK = threading.Lock()
STATE = {
    "status": "idle",       # idle | running | done | error
    "started_at": None,
    "finished_at": None,
    "region": None,
    "step": None,
    "done": 0,
    "total": TOTAL_STEPS,
    "error": None,
    "last_generated": None,
}


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _manifest_path(volume_root: str) -> str:
    return f"{volume_root.rstrip('/')}/manifest.json"


def _artifact_path(volume_root: str, region: str, name: str) -> str:
    return f"{volume_root.rstrip('/')}/{region}/{name}.json.gz"


def read_last_generated(volume_root: str):
    """generated_at from the volume manifest, or None."""
    if not volume_root:
        return None
    raw = dbx.read_volume(_manifest_path(volume_root))
    if not raw:
        return None
    try:
        import json
        return json.loads(raw).get("generated_at")
    except Exception:
        return None


def status() -> dict:
    with _LOCK:
        return dict(STATE)


def source_info(warehouse_id: str, volume_root: str, catalog: str, schema: str) -> dict:
    """Backs GET /api/source: is the dataset reachable, and when was it last built."""
    return {
        "reachable": dbx.probe(warehouse_id, catalog, schema),
        "warehouse_configured": bool(warehouse_id),
        "last_generated": read_last_generated(volume_root),
        "status": status()["status"],
    }


def start(warehouse_id: str, volume_root: str, catalog: str, schema: str) -> bool:
    """Launch a background regeneration. Returns False if one is already running
    or the config is incomplete."""
    if not warehouse_id or not volume_root:
        return False
    with _LOCK:
        if STATE["status"] == "running":
            return False
        STATE.update(status="running", started_at=_now(), finished_at=None,
                     region=None, step=None, done=0, total=TOTAL_STEPS, error=None)
    threading.Thread(
        target=_run, args=(warehouse_id, volume_root, catalog, schema), daemon=True
    ).start()
    return True


def _set(**kw):
    with _LOCK:
        STATE.update(**kw)


def _run(warehouse_id, volume_root, catalog, schema):
    import json
    try:
        # Preflight: verify write access up front so a missing grant fails fast.
        dbx.write_volume(f"{volume_root.rstrip('/')}/.preflight", _now().encode())

        done = 0
        for region in REGION_ORDER:
            q = sql.build(region, catalog, schema)

            _set(region=region, step=f"{region}:prism")
            prism_raw = dbx.query_dicts(warehouse_id, q["prism"])
            done += 1; _set(done=done)

            _set(step=f"{region}:density")
            density_raw = dbx.query_dicts(warehouse_id, q["density"])
            done += 1; _set(done=done)

            _set(step=f"{region}:curve")
            curve_raw = dbx.query_dicts(warehouse_id, q["curve"])
            done += 1; _set(done=done)

            _set(step=f"{region}:anomaly")
            anom_raw = dbx.query_dicts(warehouse_id, q["anomaly"])
            done += 1; _set(done=done)

            # compact + gzip + upload (Files API PUT is atomic)
            dbx.write_volume(_artifact_path(volume_root, region, "prism"), T.to_gz(T.prism(prism_raw)))
            dbx.write_volume(_artifact_path(volume_root, region, "density"), T.to_gz(T.density(density_raw, curve_raw)))
            dbx.write_volume(_artifact_path(volume_root, region, "anomaly"), T.to_gz(T.anomaly(anom_raw)))

        generated_at = _now()
        manifest = {
            "generated_at": generated_at,
            "day_start": T.DAY_START,
            "catalog": catalog, "schema": schema,
            "regions": REGION_ORDER,
        }
        dbx.write_volume(_manifest_path(volume_root), json.dumps(manifest).encode())
        _set(status="done", finished_at=generated_at, last_generated=generated_at, step=None, region=None)
    except Exception as e:
        _set(status="error", finished_at=_now(),
             error=f"{type(e).__name__}: {e}".strip())
        traceback.print_exc()
