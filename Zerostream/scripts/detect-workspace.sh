#!/bin/bash
# Detect workspace ID and construct ZeroBus endpoint
# Run this once when setting up a new workspace
# Usage: ./scripts/detect-workspace.sh

set -e

# Load config
if [ -f "config.env" ]; then
    source config.env
else
    echo "Error: config.env not found"
    exit 1
fi

echo "=== Workspace Detection Utility ==="
echo ""

# Check required config
if [ -z "$DATABRICKS_HOST" ] || [ -z "$DATABRICKS_TOKEN" ]; then
    echo "Error: DATABRICKS_HOST and DATABRICKS_TOKEN must be set in config.env"
    exit 1
fi

echo "Workspace: $DATABRICKS_HOST"
echo "Profile:   $DATABRICKS_PROFILE"
echo ""

# Method 1: Try to get workspace ID from an existing app
echo "Detecting workspace ID..."
WORKSPACE_ID=""

# Try to get from an existing app
APP_URL=$(databricks apps list --profile "$DATABRICKS_PROFILE" --output json 2>/dev/null | \
    python3 -c "import sys,json; apps=json.load(sys.stdin).get('apps',[]); print(apps[0]['url'] if apps else '')" 2>/dev/null || echo "")

if [ -n "$APP_URL" ]; then
    # Extract workspace ID from URL like: https://appname-6051921418418893.staging.aws.databricksapps.com
    WORKSPACE_ID=$(echo "$APP_URL" | grep -oE '[0-9]{16}' | head -1)
fi

if [ -z "$WORKSPACE_ID" ]; then
    echo "Could not auto-detect workspace ID."
    echo "Please enter it manually (16-digit number from any app URL):"
    read -r WORKSPACE_ID
fi

echo "Workspace ID: $WORKSPACE_ID"
echo ""

# Detect region from IAM roles or metastore
echo "Detecting region..."
REGION=$(curl -s -H "Authorization: Bearer $DATABRICKS_TOKEN" \
    "$DATABRICKS_HOST/api/2.0/preview/scim/v2/Me" 2>/dev/null | \
    grep -oE 'us-[a-z]+-[0-9]+' | head -1 || echo "")

if [ -z "$REGION" ]; then
    # Default to us-west-2 for staging
    REGION="us-west-2"
    echo "Could not auto-detect region, using default: $REGION"
else
    echo "Region: $REGION"
fi
echo ""

# Determine if staging or production
if [[ "$DATABRICKS_HOST" == *"staging"* ]]; then
    ZEROBUS_ENDPOINT="${WORKSPACE_ID}.zerobus.${REGION}.staging.cloud.databricks.com"
else
    ZEROBUS_ENDPOINT="${WORKSPACE_ID}.zerobus.${REGION}.cloud.databricks.com"
fi

echo "=== Results ==="
echo ""
echo "Workspace ID:     $WORKSPACE_ID"
echo "Region:           $REGION"
echo "ZeroBus Endpoint: $ZEROBUS_ENDPOINT"
echo ""

# Ask to update config
echo "Would you like to update config.env with these values? (y/n)"
read -r UPDATE_CONFIG

if [ "$UPDATE_CONFIG" = "y" ] || [ "$UPDATE_CONFIG" = "Y" ]; then
    # Check if ZEROBUS_ENDPOINT already exists in config
    if grep -q "^ZEROBUS_ENDPOINT=" config.env; then
        # Update existing
        sed -i.bak "s|^ZEROBUS_ENDPOINT=.*|ZEROBUS_ENDPOINT=$ZEROBUS_ENDPOINT|" config.env
        rm -f config.env.bak
        echo "Updated ZEROBUS_ENDPOINT in config.env"
    else
        # Add new (before UNITY CATALOG section)
        sed -i.bak '/^# UNITY CATALOG CONFIGURATION/i\
# ZeroBus streaming endpoint\
ZEROBUS_ENDPOINT='"$ZEROBUS_ENDPOINT"'\
' config.env
        rm -f config.env.bak
        echo "Added ZEROBUS_ENDPOINT to config.env"
    fi
else
    echo ""
    echo "Add this to your config.env manually:"
    echo "ZEROBUS_ENDPOINT=$ZEROBUS_ENDPOINT"
fi

echo ""
echo "Done!"
