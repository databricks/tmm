#!/usr/bin/env bash
# Full reset: removes all pipeline runtime state so the next run starts fresh.
# Deletes: Hive metastore, Spark warehouse tables, and stream checkpoints.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Resetting pipeline state..."
rm -rf metastore_db spark-warehouse derby.log /tmp/sdp_example
echo "Done. Run ./run_pipeline.sh to start fresh."
