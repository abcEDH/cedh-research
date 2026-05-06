#!/usr/bin/env bash

ensure_node_major_path() {
  local target_major="${TARGET_NODE_MAJOR:-22}"
  local node_major
  node_major="$(node -p 'process.versions.node.split(".")[0]')"

  if [ "$node_major" = "$target_major" ]; then
    return 0
  fi

  if ! command -v npx >/dev/null 2>&1; then
    echo "Missing required command: npx" >&2
    return 1
  fi

  local node_exec node_bin
  node_exec="$(npx --yes "node@${target_major}" -p 'process.execPath')"
  node_bin="$(dirname "$node_exec")"
  export PATH="$node_bin:$PATH"
}
