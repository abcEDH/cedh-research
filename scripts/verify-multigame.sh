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

echo "[verify-multigame] Checking prerequisites..."
require_cmd node
require_cmd npm

echo "[verify-multigame] Installing JavaScript dependencies..."
npm ci

echo "[verify-multigame] Running ESLint..."
npm run multigame:lint

echo "[verify-multigame] Running unit tests..."
npm run multigame:test:ci

echo "[verify-multigame] Building the multigame app..."
export NEXT_PUBLIC_SUPABASE_URL="${NEXT_PUBLIC_SUPABASE_URL:-https://placeholder.supabase.co}"
export NEXT_PUBLIC_SUPABASE_ANON_KEY="${NEXT_PUBLIC_SUPABASE_ANON_KEY:-placeholder}"
npm run multigame:build

echo "[verify-multigame] Multigame verification passed."
