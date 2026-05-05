#!/usr/bin/env bash

set -euo pipefail

TARGET_ALIAS="${TARGET_ALIAS:-tedh.gg}"
DEPLOYMENT_URL="${1:-${DEPLOYMENT_URL:-}}"
VERCEL_SCOPE="${VERCEL_SCOPE:-vem-3506s-projects}"
VERCEL_PROJECT_ID="${VERCEL_PROJECT_ID:-prj_XEEZuAvFCh7RFPafgWfAN0InbeGg}"

if [ -z "${VERCEL_TOKEN:-}" ]; then
  echo "ERROR: VERCEL_TOKEN is required." >&2
  exit 1
fi

if [ -z "$DEPLOYMENT_URL" ]; then
  echo "Fetching latest ready production deployment for project $VERCEL_PROJECT_ID..."
  API_URL="https://api.vercel.com/v6/deployments?projectId=$VERCEL_PROJECT_ID&target=production&state=READY&limit=1&slug=$VERCEL_SCOPE"
  HTTP_STATUS=$(curl -sS \
    -o /tmp/vercel_deployments_response.json \
    -w "%{http_code}" \
    "$API_URL" \
    -H "Authorization: Bearer $VERCEL_TOKEN")

  RESPONSE=$(cat /tmp/vercel_deployments_response.json)

  if [ "$HTTP_STATUS" -lt 200 ] || [ "$HTTP_STATUS" -ge 300 ]; then
    echo "ERROR: Vercel API request failed with HTTP $HTTP_STATUS" >&2
    echo "Response body: $RESPONSE" >&2
    exit 1
  fi

  DEPLOYMENT_URL=$(echo "$RESPONSE" | node -e "
    const data = JSON.parse(require('fs').readFileSync(0, 'utf8'));
    const d = (data.deployments || [])[0];
    if (d?.url) process.stdout.write(d.url);
  ")

  if [ -z "$DEPLOYMENT_URL" ]; then
    echo "ERROR: No ready production deployment found." >&2
    exit 1
  fi
fi

echo "Aliasing $DEPLOYMENT_URL to $TARGET_ALIAS..."
vercel alias set "$DEPLOYMENT_URL" "$TARGET_ALIAS" \
  --token "$VERCEL_TOKEN" \
  --scope "$VERCEL_SCOPE"
