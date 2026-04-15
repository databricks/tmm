#!/bin/bash
#
# Databricks App Deployment Script
# Usage: ./deploy-app.sh [app-name] [source-path]
#
# Configuration is loaded from config.env file

set -e

# =============================================================================
# LOAD CONFIGURATION
# =============================================================================

# Load config.env if it exists
if [ -f "config.env" ]; then
    echo "Loading configuration from config.env..."
    # Export variables from config.env (ignore comments and empty lines)
    export $(grep -v '^#' config.env | grep -v '^$' | xargs)
else
    echo "WARNING: config.env not found. Using defaults..."
fi

# =============================================================================
# CONFIGURATION VALUES (loaded from config.env or environment)
# =============================================================================

# App deployment settings
APP_NAME="${APP_NAME:-zerostream}"
SOURCE_PATH="${APP_SOURCE_PATH:-./zero_frontend}"
DATABRICKS_PROFILE="${DATABRICKS_PROFILE:-data-ai-lakehouse}"

# =============================================================================
# COMMAND LINE ARGUMENT OVERRIDES
# =============================================================================

if [ -n "$1" ]; then
    APP_NAME="$1"
fi

if [ -n "$2" ]; then
    SOURCE_PATH="$2"
fi

# =============================================================================
# VALIDATION
# =============================================================================

echo "=== Databricks App Deployment ==="
echo ""

# Verify profile exists in databrickscfg
if ! grep -q "^\[$DATABRICKS_PROFILE\]" ~/.databrickscfg 2>/dev/null; then
    echo "ERROR: Profile '$DATABRICKS_PROFILE' not found in ~/.databrickscfg"
    echo ""
    echo "Available profiles:"
    grep '^\[' ~/.databrickscfg | tr -d '[]'
    echo ""
    echo "Set DATABRICKS_PROFILE in config.env or environment."
    exit 1
fi

# Check if source path exists
if [ ! -d "$SOURCE_PATH" ]; then
    echo "ERROR: Source path '$SOURCE_PATH' does not exist."
    exit 1
fi

# Check if app.yaml exists in source path
if [ ! -f "$SOURCE_PATH/app.yaml" ]; then
    echo "WARNING: No app.yaml found in '$SOURCE_PATH'."
    echo "         Databricks Apps require an app.yaml configuration file."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# =============================================================================
# DEPLOYMENT
# =============================================================================

echo "Configuration:"
echo "  Profile:     $DATABRICKS_PROFILE"
echo "  App Name:    $APP_NAME"
echo "  Source Path: $SOURCE_PATH"
echo ""

# Check if Databricks CLI is installed
if ! command -v databricks &> /dev/null; then
    echo "ERROR: Databricks CLI is not installed."
    echo ""
    echo "Install via:"
    echo "  brew install databricks/tap/databricks  # macOS"
    echo "  curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
    exit 1
fi

WORKSPACE_PATH="/Workspace/Users/$DATABRICKS_USER/apps/$APP_NAME"

echo "Step 1: Creating app (if not exists)..."
databricks apps create "$APP_NAME" --description "Deployed via script" -p "$DATABRICKS_PROFILE" 2>/dev/null || echo "App already exists, continuing..."

echo ""
echo "Step 2: Uploading files to workspace..."
# Use import-dir instead of sync to ensure all files are uploaded correctly
# The sync command has issues with stale state in .databricks/sync-snapshots/
databricks workspace import-dir "$SOURCE_PATH" "/Users/$DATABRICKS_USER/apps/$APP_NAME" --overwrite -p "$DATABRICKS_PROFILE"

echo ""
echo "Step 3: Deploying app..."

# Retry logic for deployment (handles "active deployment in progress" errors)
MAX_RETRIES=5
RETRY_DELAY=10

for attempt in $(seq 1 $MAX_RETRIES); do
    if databricks apps deploy "$APP_NAME" --source-code-path "$WORKSPACE_PATH" -p "$DATABRICKS_PROFILE" 2>&1; then
        echo "Deployment initiated successfully"
        break
    else
        if [ $attempt -lt $MAX_RETRIES ]; then
            echo "Deployment attempt $attempt failed, retrying in ${RETRY_DELAY}s..."
            sleep $RETRY_DELAY
            RETRY_DELAY=$((RETRY_DELAY * 2))  # Exponential backoff
        else
            echo "ERROR: Deployment failed after $MAX_RETRIES attempts"
            exit 1
        fi
    fi
done

echo ""
echo "Step 4: Fetching app URL..."
APP_URL=$(databricks apps get "$APP_NAME" -p "$DATABRICKS_PROFILE" --output json 2>/dev/null | grep -o '"url":"[^"]*"' | cut -d'"' -f4)

echo ""
echo "=== Deployment Complete ==="
echo ""
if [ -n "$APP_URL" ]; then
    echo "App Name: $APP_NAME"
    echo "App URL:  $APP_URL"
    echo ""
    echo "Access your app at:"
    echo "  $APP_URL"
else
    echo "App deployed. To find URL, run:"
    echo "  databricks apps get $APP_NAME -p $DATABRICKS_PROFILE"
fi
