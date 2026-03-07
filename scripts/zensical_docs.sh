#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/zensical-version.sh"

find_repo_root() {
  local current

  if [ -n "${V8STD_REPO_ROOT:-}" ]; then
    current="${V8STD_REPO_ROOT}"
  else
    current="$(pwd)"
  fi

  while [ "${current}" != "/" ]; do
    if [ -f "${current}/zensical.toml" ]; then
      printf '%s\n' "${current}"
      return 0
    fi
    current="$(dirname "${current}")"
  done

  if [ -f "/docs/zensical.toml" ]; then
    printf '/docs\n'
    return 0
  fi

  printf 'error: could not locate repository root with zensical.toml\n' >&2
  return 1
}

REPO_ROOT="$(find_repo_root)"
export V8STD_REPO_ROOT="${REPO_ROOT}"
cd "${REPO_ROOT}"

python - "${ZENSICAL_VERSION_PYTHON}" <<'PY'
import importlib.metadata
import sys

expected = sys.argv[1]

try:
    actual = importlib.metadata.version("zensical")
except importlib.metadata.PackageNotFoundError:
    raise SystemExit("error: Zensical is not installed. Run ./scripts/install_zensical.sh first.")

if actual != expected:
    raise SystemExit(
        f"error: expected Zensical {expected}, found {actual}. Run ./scripts/install_zensical.sh to install the pinned version."
    )
PY

python "${SCRIPT_DIR}/generate_social_cards.py"
exec zensical "$@"
