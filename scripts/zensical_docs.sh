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

if [ "${1:-}" = "build" ] && [ -d "${REPO_ROOT}/site" ]; then
  python3 - "${REPO_ROOT}/site" <<'PY'
import shutil
import sys
import uuid
from pathlib import Path

site_dir = Path(sys.argv[1])
if site_dir.is_dir():
    cleanup_dir = site_dir.with_name(f".site-cleanup-{uuid.uuid4().hex}")
    site_dir.rename(cleanup_dir)
    shutil.rmtree(cleanup_dir, ignore_errors=True)
PY
fi

exec zensical "$@"
