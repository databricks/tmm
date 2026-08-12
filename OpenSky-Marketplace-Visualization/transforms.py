"""Compact raw SQL rows into the app's artifact JSON shapes.

Pure functions ported from ../data-prep/process_{prism,density,anomaly}.py. The
arithmetic, rounding, key order, and constants MUST stay identical to the offline
scripts so runtime-regenerated artifacts are byte-for-byte drop-in compatible with
the shipped snapshot. Each function takes a list of row dicts (column name -> value,
values are strings as returned by the SQL Statement Execution JSON_ARRAY format) and
returns the compact dict; to_gz() serializes + gzips exactly as shipped.
"""
import gzip
import json

DAY_START = 1772323200  # 2026-03-01T00:00:00Z
BUCKET = 600
_BASE_TB = DAY_START // BUCKET


def _pts(v):
    """collect_list(struct(...)) comes back JSON-string-encoded from the offline
    export and (per JSON_ARRAY disposition) at runtime; tolerate a pre-parsed list
    too. Output is unaffected either way."""
    return json.loads(v) if isinstance(v, str) else v


def prism(raw: list) -> dict:
    flights = []
    minlon = minlat = 1e9
    maxlon = maxlat = -1e9
    for r in raw:
        pts = _pts(r["pts_unsorted"])
        rows = []
        for p in pts:
            ts = int(float(p["ts"]))
            lat = float(p["lat"]); lon = float(p["lon"])
            alt = p.get("alt"); alt = float(alt) if alt not in (None, "null") else 0.0
            vel = p.get("vel"); vel = float(vel) if vel not in (None, "null") else 0.0
            rows.append((ts, lon, lat, alt, vel))
        rows.sort(key=lambda x: x[0])
        if not rows:
            continue
        path, tarr, sarr = [], [], []
        for ts, lon, lat, alt, vel in rows:
            rel = ts - DAY_START
            path.append([round(lon, 4), round(lat, 4), round(alt)])
            tarr.append(rel)
            sarr.append(round(vel))
            minlon = min(minlon, lon); maxlon = max(maxlon, lon)
            minlat = min(minlat, lat); maxlat = max(maxlat, lat)
        flights.append({
            "id": r["icao24"],
            "cs": r["callsign"].strip(),
            "t0": tarr[0],
            "path": path,
            "ts": tarr,
            "spd": sarr,
        })
    return {
        "day_start": DAY_START,
        "bbox": [round(minlon, 3), round(minlat, 3), round(maxlon, 3), round(maxlat, 3)],
        "flights": flights,
    }


def density(density_raw: list, curve_raw: list) -> dict:
    hex_ids = {}
    frames = {}
    max_frame = 0
    max_cell = 0
    for r in density_raw:
        frame = int(r["tb"]) - _BASE_TB
        if frame < 0:
            continue
        h = r["hex"]
        if h not in hex_ids:
            hex_ids[h] = len(hex_ids)
        hid = hex_ids[h]
        c0 = int(r["c0"]); c1 = int(r["c1"]); c2 = int(r["c2"])
        frames.setdefault(frame, []).append([hid, c0, c1, c2])
        max_frame = max(max_frame, frame)
        max_cell = max(max_cell, c0, c1, c2)

    n_frames = max_frame + 1
    frame_list = [frames.get(f, []) for f in range(n_frames)]

    curve_by_frame = {}
    for r in curve_raw:
        f = int(r["tb"]) - _BASE_TB
        curve_by_frame[f] = [int(r["total"]), int(r["c0"]), int(r["c1"]), int(r["c2"])]
    curve = [curve_by_frame.get(f, [0, 0, 0, 0]) for f in range(n_frames)]

    hexes = [None] * len(hex_ids)
    for h, i in hex_ids.items():
        hexes[i] = h

    return {
        "day_start": DAY_START, "bucket_sec": BUCKET, "n_frames": n_frames,
        "hexes": hexes, "frames": frame_list, "curve": curve, "max_cell": max_cell,
    }


def anomaly(raw: list) -> dict:
    items = []
    for r in raw:
        pts = _pts(r["pts_unsorted"]) if "pts_unsorted" in r else _pts(r["pts"])
        rows = []
        for p in pts:
            ts = int(float(p["ts"]))
            lat = float(p["lat"]); lon = float(p["lon"])
            alt = p.get("alt"); alt = float(alt) if alt not in (None, "null") else 0.0
            rows.append((ts, lon, lat, alt))
        rows.sort(key=lambda x: x[0])
        if len(rows) < 2:
            continue
        e75 = int(r["e75"]); e76 = int(r["e76"]); e77 = int(r["e77"])
        maxvr = float(r["max_vr"]) if r.get("max_vr") not in (None, "null") else 0.0
        if e77:
            kind, label = "emergency", "7700 · general emergency"
        elif e76:
            kind, label = "radio", "7600 · radio failure"
        elif e75:
            kind, label = "hijack", "7500 · unlawful interference"
        else:
            kind, label = "steep", f"steep · {maxvr:.0f} m/s vertical"
        t_emerg = r.get("t_emerg")
        t = (int(float(t_emerg)) - DAY_START) if t_emerg not in (None, "null", "") else None
        path = [[round(lon, 4), round(lat, 4), round(alt)] for _, lon, lat, alt in rows]
        ts_arr = [ts - DAY_START for ts, _, _, _ in rows]
        items.append({
            "id": r["icao24"], "cs": r["callsign"].strip(),
            "kind": kind, "label": label,
            "t": t, "maxvr": round(maxvr, 1),
            "path": path, "ts": ts_arr,
        })

    order = {"hijack": 0, "emergency": 1, "radio": 2, "steep": 3}
    items.sort(key=lambda i: (order[i["kind"]], -i["maxvr"]))
    return {"day_start": DAY_START, "items": items}


def to_json_bytes(obj: dict) -> bytes:
    """Compact JSON bytes, identical formatting to the offline json.dump."""
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def to_gz(obj: dict) -> bytes:
    """Gzip the compact JSON. mtime=0 for reproducible bytes."""
    return gzip.compress(to_json_bytes(obj), mtime=0)
