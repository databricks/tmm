#!/usr/bin/env python3
"""
Show the output of the SDP example pipeline.

Reads the Parquet files written to spark-warehouse/ by pyarrow —
no Spark session or JVM required.

Usage:
    .venv/bin/python show_output.py
"""

import sys
from pathlib import Path

try:
    import pyarrow.parquet as pq
except ImportError:
    sys.exit("pyarrow not found — run: uv pip install -r requirements.txt")

BASE = Path(__file__).parent / "spark-warehouse"

tables = {
    "raw_events":   "Streaming Table — all ingested events",
    "event_counts": "Materialized View — event counts per type",
}

for table, description in tables.items():
    path = BASE / table
    if not path.exists():
        print(f"[{table}] not found — run ./run_pipeline.sh first\n")
        continue

    t = pq.read_table(str(path))
    print(f"=== {table} ===")
    print(f"    {description}")
    print(f"    {t.num_rows} row(s)\n")
    print(t.to_pandas().sort_values("count", ascending=False).to_string(index=False)
          if table == "event_counts"
          else t.to_pandas().to_string(index=False))
    print()
