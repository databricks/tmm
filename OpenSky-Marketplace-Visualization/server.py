#!/usr/bin/env python3
"""Static server for the OpenSky visualization, with an optional Marketplace-ingest API.

Serves the Vite build in ./dist. Pre-gzipped data files (*.json.gz) are served with
Content-Type: application/gzip and NO Content-Encoding, so the browser inflates them
itself via DecompressionStream (identical in local dev and on Databricks Apps).

Optional add-on: when a UC volume + warehouse are configured (env below) and the
Marketplace dataset is available, /data/* is served VOLUME-FIRST (freshly regenerated
artifacts), falling back to the bundled snapshot in ./dist. The ingest itself runs in
the background via the /api/ingest endpoints. All Databricks/SDK work is lazy, so the
static app boots fast and serves the bundled snapshot even with no SDK / no workspace.
"""
import json
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("DATABRICKS_APP_PORT", "8000"))
DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")

# Optional ingest config (unset -> app is bundled-only, exactly like before).
WAREHOUSE_ID = os.environ.get("OPENSKY_WAREHOUSE_ID", "")
VOLUME_ROOT = os.environ.get("OPENSKY_VOLUME_ROOT", "")
DEF_CATALOG = os.environ.get("OPENSKY_CATALOG", "marketplace")
DEF_SCHEMA = os.environ.get("OPENSKY_SCHEMA", "opensky")

# Cheap to import (no SDK is pulled in until an ingest actually runs). Guarded so a
# broken optional dependency can never take down static serving.
try:
    import ingest
except Exception:
    ingest = None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST, **kwargs)

    # ---- headers ----
    def end_headers(self):
        p = self.path.split("?")[0]
        if p.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        elif p.startswith("/data/"):
            # data can be swapped by a regenerate -> must not be pinned immutable
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def guess_type(self, path):
        if path.endswith(".json.gz"):
            return "application/gzip"
        return super().guess_type(path)

    # ---- helpers ----
    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _send_gz(self, data: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "application/gzip")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _volume_bytes_for(self, path: str):
        """If this is a /data/<region>/<file>.json.gz path and a fresh copy exists in
        the volume, return its bytes; else None (caller falls back to bundled dist)."""
        if ingest is None or not VOLUME_ROOT:
            return None
        if not (path.startswith("/data/") and path.endswith(".json.gz")):
            return None
        rel = path[len("/data/"):]
        return ingest.dbx.read_volume(f"{VOLUME_ROOT.rstrip('/')}/{rel}")

    # ---- routing ----
    def do_GET(self):
        parsed = urlparse(self.path)
        p = parsed.path

        if p == "/api/source":
            if ingest is None:
                return self._send_json({"reachable": False, "warehouse_configured": False,
                                        "last_generated": None, "status": "idle"})
            q = parse_qs(parsed.query)
            catalog = (q.get("catalog") or [DEF_CATALOG])[0]
            schema = (q.get("schema") or [DEF_SCHEMA])[0]
            return self._send_json(ingest.source_info(WAREHOUSE_ID, VOLUME_ROOT, catalog, schema))

        if p == "/api/ingest/status":
            if ingest is None:
                return self._send_json({"status": "idle", "step": None, "done": 0, "total": 0,
                                        "region": None, "error": "ingest unavailable", "last_generated": None})
            return self._send_json(ingest.status())

        # volume-first data serving
        vb = self._volume_bytes_for(p)
        if vb is not None:
            return self._send_gz(vb)

        # SPA fallback: unknown non-file routes -> index.html
        full = os.path.join(DIST, p.lstrip("/"))
        if p != "/" and not os.path.exists(full) and "." not in os.path.basename(p):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        p = urlparse(self.path).path
        if p != "/api/ingest":
            return self._send_json({"error": "not found"}, code=404)
        if ingest is None:
            return self._send_json({"error": "ingest unavailable"}, code=503)
        try:
            n = int(self.headers.get("Content-Length", "0") or "0")
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        except Exception:
            body = {}
        catalog = body.get("catalog") or DEF_CATALOG
        schema = body.get("schema") or DEF_SCHEMA
        started = ingest.start(WAREHOUSE_ID, VOLUME_ROOT, catalog, schema)
        if not started:
            st = ingest.status()
            code = 409 if st["status"] == "running" else 400
            return self._send_json({"started": False, **st}, code=code)
        return self._send_json({"started": True, "status": "running", "total": ingest.TOTAL_STEPS}, code=202)

    def log_message(self, *args):
        pass  # quiet


if __name__ == "__main__":
    print(f"Serving {DIST} on 0.0.0.0:{PORT} "
          f"(ingest={'on' if (ingest and WAREHOUSE_ID and VOLUME_ROOT) else 'off'})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
