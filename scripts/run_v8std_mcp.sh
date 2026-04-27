#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${V8STD_REPO_ROOT:-/docs}"
PAGES_PATH="${V8STD_MCP_PAGES:-${REPO_ROOT}/docs/ai/pages.jsonl}"
VECTORS_PATH="${V8STD_MCP_VECTORS:-${REPO_ROOT}/docs/ai/search-vectors.jsonl}"
GENERATE_INDEX="${V8STD_MCP_GENERATE_INDEX:-auto}"
MCP_HOST="${V8STD_MCP_HOST:-0.0.0.0}"
MCP_PORT="${V8STD_MCP_PORT:-8765}"
MCP_PATH="${V8STD_MCP_PATH:-/mcp}"
MCP_CACHE_DIR="${V8STD_MCP_CACHE_DIR:-/tmp/v8std-mcp}"

export V8STD_REPO_ROOT="${REPO_ROOT}"
cd "${REPO_ROOT}"

if [ "${GENERATE_INDEX}" = "always" ] || {
    [ "${GENERATE_INDEX}" = "auto" ] && [ ! -s "${PAGES_PATH}" ]
}; then
    python "${SCRIPT_DIR}/generate_social_cards.py"
    python "${SCRIPT_DIR}/generate_ai_artifacts.py"
    python "${SCRIPT_DIR}/generate_search_vectors.py" --pages "${PAGES_PATH}" --output "${VECTORS_PATH}"
elif [ ! -s "${VECTORS_PATH}" ]; then
    python "${SCRIPT_DIR}/generate_search_vectors.py" --pages "${PAGES_PATH}" --output "${VECTORS_PATH}"
fi

if [ ! -s "${PAGES_PATH}" ]; then
    printf 'error: local MCP index file does not exist: %s\n' "${PAGES_PATH}" >&2
    printf 'hint: run with V8STD_MCP_GENERATE_INDEX=always or build the docs first.\n' >&2
    exit 1
fi

exec python "${SCRIPT_DIR}/v8std_mcp_server.py" \
    --pages "${PAGES_PATH}" \
    --vectors "${VECTORS_PATH}" \
    --cache-dir "${MCP_CACHE_DIR}" \
    --host "${MCP_HOST}" \
    --port "${MCP_PORT}" \
    --mcp-path "${MCP_PATH}" \
    --allowed-host "127.0.0.1:*" \
    --allowed-host "localhost:*" \
    --allowed-host "v8std-mcp:*" \
    --allowed-origin "http://127.0.0.1:*" \
    --allowed-origin "http://localhost:*"
