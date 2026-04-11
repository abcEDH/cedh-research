#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

NO_BACKEND=0
for arg in "$@"; do
  case "$arg" in
    --no-backend)
      NO_BACKEND=1
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: ./scripts/quickstart.sh [--no-backend]"
      exit 1
      ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

echo "[quickstart] Checking prerequisites..."
require_cmd node
require_cmd npm
require_cmd python

echo "[quickstart] Installing JavaScript dependencies..."
npm install

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [ ! -f "$dst" ]; then
    cp "$src" "$dst"
    echo "[quickstart] Created $dst from template"
  else
    echo "[quickstart] Keeping existing $dst"
  fi
}

echo "[quickstart] Preparing environment files..."
copy_if_missing ".env.example" ".env"
copy_if_missing "apps/web/.env.example" "apps/web/.env.local"
copy_if_missing "packages/backend/.env.example" "packages/backend/.env"

if [ "$NO_BACKEND" -eq 0 ]; then
  echo "[quickstart] Installing backend Python dependencies..."
  npm run backend:install
else
  echo "[quickstart] Skipping backend Python dependencies (--no-backend)"
fi

echo "[quickstart] Running docs and hygiene checks..."
npm run docs:check
npm run docs:hygiene

echo "[quickstart] Done. Next step: npm run web:dev"
