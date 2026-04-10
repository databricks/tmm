#!/usr/bin/env bash
# Run the SDP example pipeline.
# Must be executed from the sdp-example/ directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Java 17 is required — Java 21+ removed javax.security.auth.Subject.getSubject()
# which Hadoop's UserGroupInformation still calls. Spark 4.x is not compatible with Java 21+.
if ! /usr/libexec/java_home -v 17 &>/dev/null; then
  echo "ERROR: Java 17 not found. Install it with: brew install openjdk@17"
  exit 1
fi
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"

# Point PySpark to the project's virtual environment.
export PYSPARK_PYTHON=".venv/bin/python"
export PYSPARK_DRIVER_PYTHON=".venv/bin/python"

echo "Using Java: $(${JAVA_HOME}/bin/java -version 2>&1 | head -1)"
echo "Using Python: $(.venv/bin/python --version)"
echo "Running pipeline..."
echo ""

.venv/bin/spark-pipelines run
