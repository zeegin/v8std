#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/zensical-version.sh"

python_supports_project() {
  "$1" - <<'PY'
import sys

raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
}

find_python() {
  local candidate

  if [ -n "${VIRTUAL_ENV:-}" ]; then
    candidate="${VIRTUAL_ENV}/bin/python"
    if [ -x "${candidate}" ] && python_supports_project "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi

  for candidate in python python3.12; do
    if command -v "${candidate}" >/dev/null 2>&1 && python_supports_project "${candidate}"; then
      command -v "${candidate}"
      return 0
    fi
  done

  printf 'error: Python 3.12+ is required to run documentation scripts. Activate a Python 3.12 virtual environment or install python3.12.\n' >&2
  return 1
}

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
PYTHON_BIN="$(find_python)"

"${PYTHON_BIN}" - "${ZENSICAL_VERSION_PYTHON}" <<'PY'
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

"${PYTHON_BIN}" "${SCRIPT_DIR}/generate_social_cards.py"
"${PYTHON_BIN}" "${SCRIPT_DIR}/generate_ai_artifacts.py"

if [ "${1:-}" = "build" ] && [ -d "${REPO_ROOT}/site" ]; then
  "${PYTHON_BIN}" - "${REPO_ROOT}/site" <<'PY'
import shutil
import sys
from pathlib import Path

site_dir = Path(sys.argv[1])
if site_dir.is_dir():
    shutil.rmtree(site_dir)
PY
fi

exec "${PYTHON_BIN}" -m zensical "$@"
