#!/usr/bin/env bash
# Show the output tables produced by the SDP pipeline.
# Must be executed from the sdp-example/ directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

.venv/bin/python show_output.py
