#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

. "$ROOT_DIR/scripts/ensure-node-major.sh"
ensure_node_major_path

: "${VERCEL_TOKEN:?VERCEL_TOKEN is required for preview deployment.}"
: "${VERCEL_SCOPE:?VERCEL_SCOPE is required for preview deployment.}"
: "${VERCEL_PROJECT_ID:?VERCEL_PROJECT_ID is required for preview deployment.}"

require_cmd node
require_cmd npm
require_cmd vercel

echo "[preview-deploy] Installing JavaScript dependencies..."
npm ci

echo "[preview-deploy] Pulling Vercel preview environment..."
vercel pull --yes \
  --environment=preview \
  --token "$VERCEL_TOKEN" \
  --scope "$VERCEL_SCOPE"

echo "[preview-deploy] Building preview deployment with Vercel..."
vercel build \
  --token "$VERCEL_TOKEN" \
  --scope "$VERCEL_SCOPE"

echo "[preview-deploy] Deploying prebuilt preview..."
DEPLOYMENT_URL="$(
  vercel deploy --prebuilt \
    --yes \
    --token "$VERCEL_TOKEN" \
    --scope "$VERCEL_SCOPE" | tail -n 1
)"

if [ -z "$DEPLOYMENT_URL" ]; then
  echo "Preview deployment completed, but no deployment URL was captured." >&2
  exit 1
fi

echo "[preview-deploy] Preview deployment URL: $DEPLOYMENT_URL"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "preview_url=$DEPLOYMENT_URL" >> "$GITHUB_OUTPUT"
fi
