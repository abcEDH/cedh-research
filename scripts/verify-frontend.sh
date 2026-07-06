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

echo "[verify-frontend] Checking prerequisites..."
require_cmd node
require_cmd npm

echo "[verify-frontend] Installing JavaScript dependencies..."
npm ci

echo "[verify-frontend] Running repository hygiene checks..."
npm run docs:hygiene
npm run docs:check

echo "[verify-frontend] Running ESLint..."
npm run web:lint

echo "[verify-frontend] Running unit tests..."
npm run web:test:ci

echo "[verify-frontend] Building the web app..."
npm run web:build

if [[ "${NEXT_PUBLIC_SUPABASE_URL:-}" == *"placeholder.supabase.co"* ]]; then
  echo "[verify-frontend] Supabase placeholder detected. Skipping Playwright E2E tests."
else
  echo "[verify-frontend] Installing Playwright browsers..."
  npx playwright install chromium webkit

  echo "[verify-frontend] Running Playwright E2E tests..."
  npm run web:test:e2e
fi

echo "[verify-frontend] Frontend verification passed."
